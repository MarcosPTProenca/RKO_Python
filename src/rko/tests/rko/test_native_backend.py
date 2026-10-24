"""Contract tests for the compiled native backend.

Objective:
- Verify that the Rust engine honors the public RKO API, metadata and callback contracts.

Technical approach:
- Skip when the extension is not built; otherwise run short solves on a small Knapsack.
- Recompute every returned objective independently in Python.

Flow (pseudocode):
1. Build a deterministic Knapsack instance.
2. Solve with native problems, Python callbacks and each algorithm.
3. Assert objectives, metadata, error propagation and parameter parity.

Important criteria:
- Tests use short budgets and never assert timing-dependent quality.

Inputs/Outputs:
- Input: small synthetic instances and short time limits.
- Output: pass/fail assertions.
"""

import numpy as np
import pytest
from rko import RKO
from rko.orchestration.configuration import MH_SPECS
from rko.orchestration.configuration import parse_run_config
from rko.orchestration.native import NativeRunner
from rko.parameters.loader import load_config

native = pytest.importorskip("rko._native")

PROFITS = [10 + (index * 37) % 91 for index in range(60)]
WEIGHTS = [5 + (index * 53) % 47 for index in range(60)]
CAPACITY = 700
ALL = list(MH_SPECS)


def python_cost(keys: list[float] | np.ndarray) -> float:
    """Score keys with the reference Knapsack objective.

    Args:
        keys (list[float] | np.ndarray): Random keys.

    Returns:
        float: Penalized negative profit.
    """
    chosen = np.asarray(keys) > 0.5
    profit = int(np.dot(chosen, PROFITS))
    weight = int(np.dot(chosen, WEIGHTS))
    return float(100000 * max(0, weight - CAPACITY) - profit)


def test_builtin_problem_result_matches_independent_scoring() -> None:
    """Native results report an objective equal to Python's recomputation."""
    problem = native.KnapsackProblem(PROFITS, WEIGHTS, CAPACITY)
    result = RKO.native(
        problem, algorithms=["BRKGA", "SA"], adaptation="adaptive", random_state=3
    ).solve(0.3)
    assert result.backend == "native"
    assert python_cost(result.keys) == result.cost
    assert result.cost < -500
    assert result.n_workers == 2
    assert [report.algorithm for report in result.searches] == ["BRKGA", "SA"]
    assert all(report.stop_reason == "time_limit" for report in result.searches)
    assert all(report.n_evaluations > 100 for report in result.searches)
    assert all(report.random_state is not None for report in result.searches)
    assert problem.evaluate(list(result.keys)) == result.cost
    assert problem.solution(list(result.keys))[2] is True


@pytest.mark.parametrize("name", ALL)
@pytest.mark.parametrize("adaptation", ["fixed", "adaptive"])
def test_every_algorithm_runs_through_the_public_api(name: str, adaptation: str) -> None:
    """Each registered algorithm completes fixed and adaptive native solves."""
    problem = native.KnapsackProblem(PROFITS, WEIGHTS, CAPACITY)
    result = RKO.native(
        problem, algorithms=[name], adaptation=adaptation, random_state=5, history_limit=8
    ).solve(0.2)
    assert python_cost(result.keys) == result.cost
    report = result.searches[0]
    assert report.algorithm == name
    assert report.n_evaluations > 20
    assert 1 <= len(report.history) <= 8
    assert report.history[-1].cost == report.history[-1].cost
    assert report.history_observations >= len(report.history)


def test_callback_problem_receives_independent_arrays_and_scores() -> None:
    """Python callbacks run through the engine with detached key arrays."""
    seen: list[np.ndarray] = []

    def decoder(keys: np.ndarray) -> np.ndarray:
        assert isinstance(keys, np.ndarray) and keys.shape == (60,)
        seen.append(keys)
        decoded = keys > 0.5
        keys[:] = 0.0
        return decoded

    def cost(chosen: np.ndarray) -> float:
        profit = int(np.dot(chosen, PROFITS))
        weight = int(np.dot(chosen, WEIGHTS))
        return float(100000 * max(0, weight - CAPACITY) - profit)

    result = RKO(decoder, cost, 60, algorithms=["BRKGA"], backend="native", random_state=1).solve(
        0.3
    )
    assert python_cost(result.keys) == result.cost
    assert max(array.max() for array in seen) == 0.0
    assert len({id(array) for array in seen}) == len(seen)
    assert result.searches[0].n_evaluations == len(seen)


def test_callback_exceptions_propagate_unchanged() -> None:
    """The original Python exception escapes a native solve."""

    class Boom(Exception):
        """Marker failure."""

    def explode(value: object) -> float:
        raise Boom("callback failed")

    solver = RKO(lambda keys: keys, explode, 10, algorithms=["SA"], backend="native")
    with pytest.raises(Boom, match="callback failed"):
        solver.solve(0.5)


def test_nonfinite_objective_is_rejected() -> None:
    """Non-finite costs fail the solve instead of entering the pool."""
    solver = RKO(lambda keys: keys, lambda value: float("nan"), 10, backend="native")
    solver.algorithms = ["SA"]
    with pytest.raises(RuntimeError, match="finite"):
        solver.solve(0.3)


def test_worker_cap_and_prefill_validation() -> None:
    """Worker caps are honored and unsupported options fail clearly."""
    problem = native.KnapsackProblem(PROFITS, WEIGHTS, CAPACITY)
    result = RKO.native(problem, algorithms=["SA", "BRKGA", "GA"], n_jobs=2, random_state=2).solve(
        0.4
    )
    assert result.n_workers == 2
    assert sum(report.elapsed_seconds for report in result.searches) < 1.0
    prefilled = RKO.native(
        problem, algorithms=["IPR"], pool_size=6, prefill_pool=True, random_state=4
    ).solve(0.2)
    assert prefilled.initialization is not None
    assert prefilled.initialization.n_evaluations == 6
    assert prefilled.initialization.pool_size == 6
    assert prefilled.n_evaluations == prefilled.searches[0].n_evaluations + 6
    with pytest.raises(ValueError, match="process and native"):
        RKO(lambda k: k, lambda v: 0.0, 10, backend="serial", n_jobs=2).solve(0.2)


def test_invalid_native_inputs_raise() -> None:
    """The extension validates dimensions and algorithm names."""
    with pytest.raises(ValueError):
        native.KnapsackProblem([1, 2], [1], 3)
    problem = native.KnapsackProblem(PROFITS, WEIGHTS, CAPACITY)
    with pytest.raises(ValueError, match="Unknown algorithm"):
        native.run(problem, [("Nope", [], [], False)], 0.1, 1, 10)
    with pytest.raises(ValueError, match="time_limit"):
        native.run(problem, [("SA", [1, 1, 0.9, 0.1, 0.2], [], False)], 0.0, 1, 10)


def test_parameter_snapshot_matches_python_factory_and_filters_states() -> None:
    """Native specs reuse validated TOML values and drop infeasible online states."""
    raw = load_config(None)
    raw["run"]["control"] = 1
    raw["active_metaheuristics"] = {"list": ["SA", "BRKGA", "GRASP", "ILS"]}
    config = parse_run_config(raw)
    specs, templates = NativeRunner(config, 50, None, None).specs()
    by_name = {spec[0]: spec for spec in specs}
    sa_offline = by_name["SA"][1]
    assert sa_offline == [1000.0, 1000000.0, 0.99, 0.01, 0.05]
    assert all(state[3] <= state[4] for state in by_name["SA"][2])
    assert by_name["SA"][3] is True
    for state in by_name["BRKGA"][2]:
        population, elite, mutants = int(state[0]), state[1], state[2]
        assert max(1, int(population * elite)) + int(population * mutants) < population
    assert all(state[2] <= state[1] for state in by_name["GRASP"][2])
    assert len(templates) == 4


def test_hyperparameter_overrides_reach_the_engine() -> None:
    """Offline overrides are validated by Python and snapshotted for Rust."""
    raw = load_config(None)
    raw["run"]["control"] = 0
    raw["active_metaheuristics"] = {"list": ["BRKGA"]}
    config = parse_run_config(raw)
    specs, _ = NativeRunner(config, 50, None, {"BRKGA": {"p": 20}}).specs()
    assert specs[0][1][0] == 20.0
    assert specs[0][3] is False


def test_standalone_solver_objects_accept_the_native_backend() -> None:
    """A single-algorithm solver class runs on the compiled engine."""
    from rko.metaheuristics import SA

    result = SA(
        lambda keys: keys,
        lambda keys: python_cost(keys),
        60,
        backend="native",
        random_state=2,
    ).solve(0.2)
    assert result.backend == "native"
    assert result.algorithms == ("SA",)
    assert python_cost(result.keys) == result.cost
