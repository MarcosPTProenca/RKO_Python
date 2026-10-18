"""Public deadline and worker-failure regression contracts.

Objective:
- Stop returning-callback local searches without losing their completed incumbent.

Technical approach:
- Run the previously overrunning ILS shape through every public backend.
- Inject a BaseException in a thread callback and observe caller-visible failure.

Flow (pseudocode):
1. Define importable returning and failing callbacks.
2. Execute a bounded single-algorithm portfolio.
3. Check valid results, elapsed time or preserved failure causes.

Important criteria:
- Process startup is not part of the requested search budget.
- No claim of safely killing arbitrarily blocked Python threads is made.

Inputs/Outputs:
- Input: short search budget and dimension100 constant-cost problem.
- Output: completion, cost consistency and exception propagation assertions.
"""

import numpy as np
import pytest
import time
from rko import RKO


def decode(keys: np.ndarray) -> np.ndarray:
    """Return the random-key vector.

    Args:
        keys (np.ndarray): Candidate chromosome.

    Returns:
        np.ndarray: Unmodified chromosome.
    """
    return keys


def slow_cost(keys: np.ndarray) -> float:
    """Simulate a valid objective that returns after a short evaluation.

    Args:
        keys (np.ndarray): Unused candidate vector.

    Returns:
        float: Constant finite objective.
    """
    time.sleep(0.001)
    return 1.0


def exit_cost(keys: np.ndarray) -> float:
    """Raise SystemExit inside a callback rather than ending its thread silently.

    Args:
        keys (np.ndarray): Unused candidate.

    Raises:
        SystemExit: Always, to verify worker failure propagation.
    """
    raise SystemExit("callback exit")


@pytest.mark.parametrize("backend", ["serial", "thread", "process"])
def test_returning_callback_local_search_obeys_budget(backend: str) -> None:
    """Preserve an evaluated result without waiting for the full local neighborhood.

    Args:
        backend (str): Execution backend under test.
    """
    started = time.perf_counter()
    result = RKO(
        decode,
        slow_cost,
        100,
        algorithms=["ILS"],
        control=0,
        backend=backend,
    ).solve(0.01)
    assert result.cost == 1.0
    assert len(result.keys) == 100
    assert time.perf_counter() - started < (15.0 if backend == "process" else 1.0)


def test_thread_base_exception_reaches_caller() -> None:
    """Do not return an empty successful-looking result after a thread exits."""
    with pytest.raises(RuntimeError, match="MultiStart") as captured:
        RKO(decode, exit_cost, 3, algorithms=["MultiStart"], control=0, backend="thread").solve(1)
    assert isinstance(captured.value.__cause__, SystemExit)


def test_decoder_cannot_mutate_the_search_chromosome() -> None:
    """Keep returned keys associated with their decoded objective after mutation."""

    def mutating_decoder(keys: np.ndarray) -> np.ndarray:
        """Mutate callback-owned input without changing the algorithm's chromosome.

        Args:
            keys (np.ndarray): Detached candidate input.

        Returns:
            np.ndarray: Shifted decoded solution.
        """
        keys += 0.1
        return keys

    result = RKO(
        mutating_decoder,
        lambda values: float(values.sum()),
        3,
        algorithms=["MultiStart"],
        control=0,
        backend="serial",
    ).solve(0.01)
    assert all(0 <= key < 1 for key in result.keys)
    assert result.cost == pytest.approx(sum(key + 0.1 for key in result.keys))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_objective_is_not_a_completed_result(value: float) -> None:
    """Reject invalid objective values at the shared evaluation boundary.

    Args:
        value (float): Nonfinite callback return value.
    """
    with pytest.raises(ValueError, match="finite"):
        RKO(decode, lambda keys: value, 3, algorithms=["MultiStart"], backend="serial").solve(0.01)
