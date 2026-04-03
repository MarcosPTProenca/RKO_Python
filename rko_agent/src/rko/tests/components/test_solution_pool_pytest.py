"""Tests for the shared solution pool component.

Objective:
- Validate insertion, ordering, and capacity constraints of the elite pool.

Technical approach:
- Exercise constructor validation and insertion/update behavior.
- Assert public query methods (`get_elite`, `best`, `size`, `repr`).

Flow (pseudocode):
1. Create pool instances with representative capacities.
2. Insert entries with different costs.
3. Assert ordering, truncation, and empty-state contracts.

Important criteria:
- Capacity must be strictly positive.
- Pool remains sorted by ascending objective value.

Inputs/Outputs:
- Input: synthetic `(cost, keys)` entries.
- Output: assertions over public API behavior.
"""

from __future__ import annotations

import pytest
from rko.components.solution_pool import SolutionPool


def test_capacity_must_be_positive() -> None:
    """Ensure invalid capacities are rejected at construction time."""
    with pytest.raises(ValueError, match="capacity must be >= 1"):
        SolutionPool(capacity=0)


def test_insert_maintains_order_and_capacity() -> None:
    """Ensure insert keeps best entries sorted and capped by capacity."""
    pool = SolutionPool(capacity=2)

    pool.insert((10.0, [0.1, 0.2]), "A")
    pool.insert((5.0, [0.3, 0.4]), "B")
    pool.insert((8.0, [0.5, 0.6]), "C")

    elite = pool.get_elite(2)
    assert pool.size == 2
    assert [entry[0] for entry in elite] == [5.0, 8.0]
    assert pool.best == (5.0, [0.3, 0.4])


def test_get_elite_and_best_with_empty_pool() -> None:
    """Ensure empty pool queries return stable empty-state values."""
    pool = SolutionPool(capacity=3)

    assert pool.get_elite(5) == []
    assert pool.best is None
    assert "capacity=3" in repr(pool)
