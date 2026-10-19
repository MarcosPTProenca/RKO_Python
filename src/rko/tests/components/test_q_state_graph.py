"""Independent Q-state graph and initialization stream contracts.

Objective:
- Preserve distance-one adjacency, state order and initial Q-values exactly.

Technical approach:
- Generate expected states with itertools.product and pairwise comparisons.
- Draw expected weights from a private Random using the production seed.
- Exercise filtered, duplicate, non-reflexive and non-hashable inputs.

Flow (pseudocode):
1. Enumerate and optionally filter the Cartesian parameter combinations.
2. Build an independent ordered graph and its deterministic initial weights.
3. Compare every state field and final RNG state with the controller.

Important criteria:
- Equal values at different grid indices remain distinct states.
- Neighbor order determines Q-value draw order and first-winner ties.
- Standalone legacy scalar behavior is not replaced by numeric coercion.

Inputs/Outputs:
- Input: bounded generated numeric grids and explicit fallback examples.
- Output: exact state serialization, RNG and tie-handling assertions.
"""

from __future__ import annotations

import numpy as np
import pickle
import pytest
import random
from collections.abc import Callable
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from itertools import product
from rko.components.adaptive_control.q_learning import QLearningController
from rko.components.adaptive_control.q_learning import QState
from typing import Any


def _model(
    grid: list[list[Any]], rng: random.Random, predicate: Callable[[list[float]], bool] | None
) -> list[QState]:
    """Construct an independent pairwise graph in Cartesian state order.

    Args:
        grid (list[list[Any]]): Nonempty axes, including legacy scalar examples.
        rng (random.Random): Independent expected initialization stream.
        predicate (Callable | None): Optional pure state-feasibility predicate.

    Returns:
        list[QState]: Ordered states with ordered actions and expected weights.
    """
    if not grid:
        return []
    coordinates = [list(values) for values in product(*grid)]
    if predicate is not None:
        coordinates = [values for values in coordinates if predicate(values)]
    states = [QState(label=index, par=values) for index, values in enumerate(coordinates)]
    for state in states:
        for index, other in enumerate(states):
            if sum(state.par[axis] != other.par[axis] for axis in range(len(grid))) <= 1:
                state.Ai.append(index)
                value = rng.uniform(0.005, 0.01)
                state.Qa.append(value)
                if value > state.maxQ:
                    state.maxQ = value
                    state.maxA = len(state.Ai) - 1
    return states


def _assert_model(grid: list[list[Any]], seed: int, filtered: bool = False) -> None:
    """Compare all fields and restore the caller's global stream.

    Args:
        grid (list[list[Any]]): Parameter grid for the graph comparison.
        seed (int): Matching local/global stream seed.
        filtered (bool): Whether to discard combinations whose sum exceeds 1.5.
    """
    predicate = (lambda values: sum(values) <= 1.5) if filtered else None
    before = pickle.dumps(grid)
    expected_rng = random.Random(seed)
    expected = _model(grid, expected_rng, predicate)
    caller = random.getstate()
    try:
        random.seed(seed)
        actual = QLearningController._create_states(grid, predicate)
        assert pickle.dumps(actual) == pickle.dumps(expected)
        assert random.getstate() == expected_rng.getstate()
        assert pickle.dumps(grid) == before
    finally:
        random.setstate(caller)


@settings(max_examples=45, derandomize=True, deadline=None)
@given(
    grid=st.lists(
        st.lists(st.sampled_from([-0.0, 0.0, 1.0, 2.0]), min_size=1, max_size=3),
        min_size=1,
        max_size=4,
    ),
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    filtered=st.booleans(),
)
def test_generated_graph_matches_pairwise_model(
    grid: list[list[float]], seed: int, filtered: bool
) -> None:
    """Match exhaustive adjacency and weights on bounded generated grids.

    Args:
        grid (list[list[float]]): Numeric axes, potentially containing duplicates.
        seed (int): Initialization seed.
        filtered (bool): Whether joint feasibility removes some states.
    """
    _assert_model(grid, seed, filtered)


@pytest.mark.parametrize(
    "grid",
    [
        [],
        [[0.0]],
        [[0.0, -0.0, 1.0]] * 4,
        [[float("nan"), 1.0], [float("nan"), 1.0]],
        [[float("inf"), -float("inf")], [0.0, 1.0]],
        [[[0], [1]], [[0], [1]]],
        [["a", "b"], ["x", "x"]],
        [[True, 1, False], [0, 1]],
        [[np.float32(0.5), np.float32(1.0)], [0.0, 1.0]],
        [[10**400, 10**400 + 1], [0, 1]],
    ],
)
def test_special_graphs_preserve_legacy_behavior(grid: list[list[Any]]) -> None:
    """Keep duplicate/signed-zero identity and exotic fallback semantics.

    Args:
        grid (list[list[Any]]): Special numeric or legacy parameter grid.
    """
    for seed in (0, 17, 99):
        _assert_model(grid, seed)


@pytest.mark.parametrize("append", [False, True])
def test_filter_may_normalize_values_or_append_metadata(append: bool) -> None:
    """Index final normalized values but retain legacy width handling for metadata.

    Args:
        append (bool): Whether to append a non-parameter metadata coordinate.
    """
    grid = [[-1.0, 0.0, 1.0], [0.0, 1.0]]

    def transform(values: list[float]) -> bool:
        """Normalize a state in place and optionally attach deterministic metadata.

        Args:
            values (list[float]): Mutable state vector passed to the predicate.

        Returns:
            bool: Always keep the transformed state.
        """
        values[:] = [abs(value) for value in values]
        if append:
            values.append(sum(values))
        return True

    expected_rng = random.Random(17)
    expected = _model(grid, expected_rng, transform)
    caller = random.getstate()
    try:
        random.seed(17)
        actual = QLearningController._create_states(grid, transform)
        assert pickle.dumps(actual) == pickle.dumps(expected)
        assert random.getstate() == expected_rng.getstate()
    finally:
        random.setstate(caller)


def test_shortened_filter_payload_retains_legacy_error() -> None:
    """Do not silently accept parameter coordinates removed by a predicate."""

    def truncate(values: list[float]) -> bool:
        """Remove a required coordinate to exercise the legacy fallback error.

        Args:
            values (list[float]): State vector supplied to the predicate.

        Returns:
            bool: Keep the malformed state for pairwise validation.
        """
        values.pop()
        return True

    with pytest.raises(IndexError):
        QLearningController._create_states([[0.0, 1.0], [0.0, 1.0]], truncate)


def test_filtered_graph_can_remove_all_states() -> None:
    """Return no graph and consume no RNG when the predicate rejects every state."""
    _assert_model([[2.0, 3.0], [2.0, 3.0]], 42, True)
    with pytest.raises(ValueError, match="no feasible states"):
        QLearningController([[2.0]], state_filter=lambda _: False)


def test_tied_weights_retain_ascending_actions_and_first_maximum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep action ordering and the first cached maximum under tied draws.

    Args:
        monkeypatch (pytest.MonkeyPatch): Supply equal initial edge weights.
    """
    calls = []

    def uniform(lower: float, upper: float) -> float:
        """Record one requested initialization interval and return a tied weight.

        Args:
            lower (float): Initialization lower bound.
            upper (float): Initialization upper bound.

        Returns:
            float: Constant initial Q-value.
        """
        calls.append((lower, upper))
        return 0.0075

    monkeypatch.setattr(random, "uniform", uniform)
    states = QLearningController._create_states([[0.0, 1.0], [0.0, 1.0]])
    assert [state.Ai for state in states] == [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]
    assert calls == [(0.005, 0.01)] * 12
    assert all(state.Qa == [0.0075] * 3 and state.maxQ == 0.0075 for state in states)
    assert all(state.maxA == 0 and state.minA == 0 for state in states)
