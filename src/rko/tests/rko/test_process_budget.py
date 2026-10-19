"""Verify bounded portfolio workers and common-deadline search slices.

Objective:
- Execute every cooperative search without exceeding the requested worker count.

Technical approach:
- Record each real algorithm's seeded first candidate and process identity.
- Inspect worker slice deadlines with a simulated session and monotonic clock.

Flow (pseudocode):
1. Assign a five-algorithm portfolio to one, two or dedicated workers.
2. Check first-candidate streams, result accounting and child cleanup.
3. Simulate overrun and startup delay without timing-sensitive assertions.

Important criteria:
- Queued searches never receive a fresh full portfolio budget.
- Constructor RNG consumption must survive preparing several algorithms.

Inputs/Outputs:
- Input: importable callbacks, worker limits and controlled clock cases.
- Output: execution, deadline, RNG and ownership assertions.
"""

import json
import multiprocessing as mp
import numpy as np
import os
import pytest
import random
import threading
import time
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from rko import RKO
from rko.components.random_streams import RandomStreams
from rko.components.solution_pool import SolutionPool
from rko.orchestration import processes
from rko.orchestration.types import CostFn
from rko.orchestration.types import DecoderFn
from rko.orchestration.types import RunConfig
from rko.orchestration.types import RunResult
from types import SimpleNamespace


def decode(keys: np.ndarray) -> np.ndarray:
    """Return candidate keys unchanged.

    Args:
        keys (np.ndarray): Candidate random keys.

    Returns:
        np.ndarray: Unmodified keys.
    """
    return keys


@dataclass
class InitialCost:
    """Identify algorithms through independently predicted first random keys.

    Responsibilities:
    - Record the PID and first Python random sample for each search.

    Attributes:
        directory (Path): Destination for one observation per algorithm.
        expected (tuple[tuple[float, ...], ...]): First keys for each seeded search.
        names (tuple[str, ...]): Algorithm names aligned with the first-key vectors.
        seen (set[int]): Algorithms already observed in this worker.
    """

    directory: Path
    expected: tuple[tuple[float, ...], ...]
    names: tuple[str, ...]
    seen: set[int] = field(default_factory=set)

    def __call__(self, keys: np.ndarray) -> float:
        """Record independently recognizable first keys, then evaluate their norm.

        Args:
            keys (np.ndarray): Candidate vector.

        Returns:
            float: Squared Euclidean norm.

        Raises:
            OSError: If a test observation cannot be written.
        """
        for index, expected in enumerate(self.expected):
            if (
                index not in self.seen
                and tuple(keys) == expected
                and self.names[index] in mp.current_process().name.removeprefix("rko-").split("/")
            ):
                self.seen.add(index)
                self.directory.joinpath(f"{index}.json").write_text(
                    json.dumps(
                        {
                            "pid": os.getpid(),
                            "sample": RandomStreams.python_rng().random(),
                            "at": time.perf_counter(),
                        }
                    ),
                    encoding="utf-8",
                )
        return float(np.dot(keys, keys))


@dataclass
class QueuedFailure:
    """Fail only when the second assigned algorithm reaches its first evaluation.

    Responsibilities:
    - Verify that a prior successful result cannot hide a queued failure.

    Attributes:
        target (tuple[float, ...]): Independently predicted keys of the second search.
    """

    target: tuple[float, ...]

    def __call__(self, keys: np.ndarray) -> float:
        """Evaluate normal candidates and fail at the queued search's first candidate.

        Args:
            keys (np.ndarray): Candidate vector.

        Returns:
            float: Squared norm for candidates other than the failure target.

        Raises:
            ArithmeticError: If the second algorithm begins evaluation.
        """
        if tuple(keys) == self.target:
            raise ArithmeticError("queued objective failed deliberately")
        return float(np.dot(keys, keys))


def test_queued_failure_is_not_hidden_by_completed_result() -> None:
    """Propagate a later algorithm's failure and clean up its shared worker."""
    seed = int(np.random.SeedSequence(42).spawn(2)[1].generate_state(1)[0])
    target = tuple(np.random.RandomState(seed).random_sample(2))
    solver = RKO(
        decode,
        QueuedFailure(target),
        2,
        algorithms=["MultiStart", "SA"],
        control=0,
        n_jobs=1,
        random_state=42,
    )
    before = {child.pid for child in mp.active_children()}
    with pytest.raises(RuntimeError, match="SA") as captured:
        solver.solve(0.2)
    assert isinstance(captured.value.__cause__, ArithmeticError)
    assert "\nSA:\n" in str(captured.value)
    assert solver.result_ is None
    assert {child.pid for child in mp.active_children()} == before


@pytest.mark.parametrize("n_jobs", [1, 2, 8])
def test_worker_limit_runs_every_seeded_algorithm(tmp_path: Path, n_jobs: int) -> None:
    """Execute uneven groups and retain independent per-algorithm random streams.

    Args:
        tmp_path (Path): Destination for first-candidate observations.
        n_jobs (int): Requested process limit, including surplus capacity.
    """
    names = ("MultiStart", "SA", "PSO", "GA", "BRKGA")
    seeds = [int(seed.generate_state(1)[0]) for seed in np.random.SeedSequence(42).spawn(5)]
    expected = tuple(tuple(np.random.RandomState(seed).random_sample(2)) for seed in seeds)
    before = {child.pid for child in mp.active_children()}
    result = RKO(
        decode,
        InitialCost(tmp_path, expected, names),
        2,
        algorithms=names,
        control=0,
        n_jobs=n_jobs,
        random_state=42,
    ).solve(0.9)
    observations = [
        json.loads(tmp_path.joinpath(f"{index}.json").read_text()) for index in range(5)
    ]
    assert len({row["pid"] for row in observations}) == min(n_jobs, len(names))
    assert all(row["pid"] != os.getpid() for row in observations)
    assert [row["sample"] for row in observations] == [
        random.Random(seed).random() for seed in seeds
    ]
    assert result.algorithms == names
    assert len(result.keys) == 2
    assert all(0 <= key < 1 for key in result.keys)
    assert result.cost == pytest.approx(np.dot(result.keys, result.keys))
    assert {child.pid for child in mp.active_children()} == before


@pytest.mark.parametrize(
    "overrun, duration, expected_slices",
    [
        (0.0, 12.0, [4.0, 4.0, 4.0]),
        (1.0, 12.0, [4.0, 4.0, 2.0]),
        (7.0, 12.0, [4.0, 1.0]),
        (0.0, 0.0, []),
    ],
)
def test_worker_preserves_deadline_and_constructor_rng(
    monkeypatch: pytest.MonkeyPatch,
    overrun: float,
    duration: float,
    expected_slices: list[float],
) -> None:
    """Inspect slices, constructor RNG states and exhausted-deadline behavior.

    Args:
        monkeypatch (pytest.MonkeyPatch): Replace construction, session and clock.
        overrun (float): Simulated callback overrun after each nominal slice.
        duration (float): Remaining common budget, zero simulates late startup.
        expected_slices (list[float]): Durations available to searches actually started.
    """
    assignments = (("MultiStart", 11), ("SA", 22), ("PSO", 33))
    clock = [100.0]
    calls: list[float] = []
    constructed: list[str] = []

    def now() -> float:
        """Return the test-controlled monotonic timestamp.

        Returns:
            float: Current simulated time.
        """
        return clock[0]

    def build(
        name: str,
        pool: object,
        decoder: DecoderFn,
        cost: CostFn,
        dimension: int,
        control: int,
        params_dir: Path | None,
        hyperparameters: dict[str, int | float] | None = None,
    ) -> SimpleNamespace:
        """Consume constructor RNG draws before returning a named test search.

        Args:
            name (str): Algorithm being prepared.
            pool (object): Unused local test pool.
            decoder (DecoderFn): Unused decoder.
            cost (CostFn): Unused objective.
            dimension (int): Unused key dimension.
            control (int): Unused control mode.
            params_dir (Path | None): Unused parameter location.
            hyperparameters (dict[str, int | float] | None): Absent optional overrides.

        Returns:
            SimpleNamespace: Algorithm name used by the simulated session.
        """
        assert hyperparameters is None
        constructed.append(name)
        RandomStreams.python_rng().random()
        RandomStreams.numpy_rng().random()
        return SimpleNamespace(name=name)

    class Session:
        """Simulate completed or overrunning searches at their supplied deadlines.

        Responsibilities:
        - Assert preparation and owned RNG activation before advancing the test clock.
        """

        def __init__(self, decoder: DecoderFn, cost: CostFn) -> None:
            """Accept worker callbacks without evaluating them.

            Args:
                decoder (DecoderFn): Unused decoder.
                cost (CostFn): Unused objective.
            """

        def solve(
            self, algorithm: SimpleNamespace, limit_time: float, *, deadline: float
        ) -> RunResult:
            """Check the reactivated owned stream and simulate one search slice.

            Args:
                algorithm (SimpleNamespace): Named prepared search.
                limit_time (float): Supplied remaining slice duration.
                deadline (float): Absolute deadline bounded by the portfolio.

            Returns:
                RunResult: Consistent synthetic incumbent.
            """
            assert constructed == [name for name, _ in assignments]
            seed = dict(assignments)[algorithm.name]
            python_rng = random.Random(seed)
            numpy_rng = np.random.RandomState(seed)
            python_rng.random()
            numpy_rng.random()
            assert RandomStreams.python_rng().random() == python_rng.random()
            assert RandomStreams.numpy_rng().random() == numpy_rng.random()
            assert deadline <= 100.0 + duration
            assert deadline == pytest.approx(clock[0] + limit_time)
            calls.append(limit_time)
            clock[0] += limit_time + overrun
            return [], [seed / 100], 0.25 if seed >= 22 else 1.0

    python_state, numpy_state = random.getstate(), np.random.get_state()
    parent, child = mp.Pipe(duplex=False)
    start = threading.Event()
    start.set()
    monkeypatch.setattr(processes.time, "perf_counter", now)
    monkeypatch.setattr(processes, "build_metaheuristic", build)
    monkeypatch.setattr(processes, "SearchSession", Session)
    try:
        processes._worker(
            assignments,
            RunConfig(0, 2, tuple(name for name, _ in assignments)),
            SolutionPool(2),
            decode,
            float,
            1,
            None,
            4.0,
            start,
            SimpleNamespace(value=100.0 + duration),
            child,
        )
        assert random.getstate() == python_state
        assert np.array_equal(np.random.get_state()[1], numpy_state[1])
        assert np.random.get_state()[2:] == numpy_state[2:]
        assert parent.recv() == ("ready", None)
        status, payload = parent.recv()
        assert calls == pytest.approx(expected_slices)
        if expected_slices:
            assert status == "result", payload
            assert payload == ([], [0.22], 0.25)
        else:
            assert status == "error"
            assert isinstance(payload[0], TimeoutError)
    finally:
        parent.close()
        child.close()
        random.setstate(python_state)
        np.random.set_state(numpy_state)
