"""Independent list-model oracles for IPR block-copy optimization.

Objective:
- Protect every evaluated chromosome, final incumbent and array ownership.

Technical approach:
- Model greedy block relinking with Python lists, independently of NumPy copying.
- Compare input/output bits and complete decoder traces at small/large block sizes.

Flow (pseudocode):
1. Build contiguous or strided numerical chromosomes with boundary values.
2. Run the list model and actual IPR with the same deterministic objective.
3. Compare every candidate and verify that neither input was modified or retained.

Important criteria:
- Include partial blocks, single-gene/vectorized boundaries and stable-order ties.
- Preserve negative-zero bits and the first candidate when objective costs tie.

Inputs/Outputs:
- Input: seeded keys for numerical and stable-permutation problems.
- Output: exact candidate-trace, fitness and ownership assertions.
"""

import math
import numpy as np
import pytest
from collections.abc import Callable
from rko.components.solution_pool import SolutionPool
from rko.metaheuristics.ipr import IPR


def _reference_path(
    current: list[float], guide: list[float], evaluate: Callable[[np.ndarray], float]
) -> tuple[list[float], float]:
    """Model the greedy block path without NumPy indexing or assignment.

    Args:
        current (list[float]): Starting chromosome.
        guide (list[float]): Destination chromosome.
        evaluate (Callable): Deterministic candidate evaluator.

    Returns:
        tuple[list[float], float]: First best chromosome and its objective.
    """
    dimension = len(current)
    width = max(1, int(dimension * 0.10))
    count = (dimension + width - 1) // width
    remaining = list(range(count))
    current = current[:]
    best = current[:]
    best_cost = evaluate(np.asarray(current))
    for _ in range(max(1, count - 1)):
        winner: list[float] | None = None
        winner_cost = math.inf
        winner_block = -1
        for block in remaining:
            start = block * width
            end = min(start + width, dimension)
            candidate = current[:]
            candidate[start:end] = guide[start:end]
            cost = evaluate(np.asarray(candidate))
            if cost < winner_cost:
                winner, winner_cost, winner_block = candidate, cost, block
        if winner is not None:
            if winner_cost < best_cost:
                best, best_cost = winner[:], winner_cost
            current = winner[:]
            remaining.remove(winner_block)
    return best, best_cost


@pytest.mark.parametrize("dimension", [1, 8, 19, 20, 32, 79, 80, 81, 101, 1000])
@pytest.mark.parametrize("strided", [False, True])
@pytest.mark.parametrize("ordering", [False, True])
def test_relink_matches_independent_candidate_trace(
    dimension: int, strided: bool, ordering: bool
) -> None:
    """Match all candidates and ownership contracts, not only the winning cost.

    Args:
        dimension (int): Positive chromosome length, including partial-block boundaries.
        strided (bool): Exercise noncontiguous and negative-stride source arrays.
        ordering (bool): Decode into a stable permutation instead of numerical values.
    """
    generator = np.random.RandomState(42)
    current = generator.random_sample(2 * dimension)[::2]
    guide = generator.random_sample(2 * dimension)[::-2]
    if not strided:
        current, guide = current.copy(), guide.copy()
    current[0] = -0.0
    guide[0] = np.nextafter(1.0, 0.0)
    if dimension > 1:
        current[-1], guide[-1] = 0.0, -0.0
    saved_current, saved_guide = current.copy(), guide.copy()
    weights = np.arange(1, dimension + 1)
    reference_trace: list[np.ndarray] = []
    actual_trace: list[np.ndarray] = []

    def decode(keys: np.ndarray) -> np.ndarray:
        """Apply the selected representation.

        Args:
            keys (np.ndarray): Numerical candidate keys.

        Returns:
            np.ndarray: Stable permutation or unchanged keys.
        """
        return np.argsort(keys, kind="stable") if ordering else keys

    def objective(values: np.ndarray) -> float:
        """Compute the numerical or permutation objective.

        Args:
            values (np.ndarray): Decoded candidate.

        Returns:
            float: Finite deterministic minimization value.
        """
        return float(np.dot(values, weights if ordering else values))

    def reference_evaluate(keys: np.ndarray) -> float:
        """Record model candidate bits before evaluating them.

        Args:
            keys (np.ndarray): Independently assembled model chromosome.

        Returns:
            float: Decoded objective value.
        """
        reference_trace.append(keys.view(np.uint64).copy())
        return objective(decode(keys))

    def actual_decode(keys: np.ndarray) -> np.ndarray:
        """Record production candidate bits before applying the same representation.

        Args:
            keys (np.ndarray): IPR candidate chromosome.

        Returns:
            np.ndarray: Decoded candidate.
        """
        actual_trace.append(keys.view(np.uint64).copy())
        return decode(keys)

    expected_keys, expected_cost = _reference_path(
        current.tolist(), guide.tolist(), reference_evaluate
    )
    algorithm = IPR(SolutionPool(), actual_decode, objective, dimension)
    keys, cost = algorithm._relink(current, guide)
    assert cost == expected_cost
    np.testing.assert_array_equal(keys.view(np.uint64), np.asarray(expected_keys).view(np.uint64))
    assert len(actual_trace) == len(reference_trace)
    for actual, expected in zip(actual_trace, reference_trace, strict=True):
        np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(current.view(np.uint64), saved_current.view(np.uint64))
    np.testing.assert_array_equal(guide.view(np.uint64), saved_guide.view(np.uint64))
    assert not np.shares_memory(keys, current)
    assert not np.shares_memory(keys, guide)
