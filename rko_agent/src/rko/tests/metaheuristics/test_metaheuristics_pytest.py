"""Tests for metaheuristic base behavior and factory construction.

Objective:
- Validate common base contracts and factory creation for all registered specs.

Technical approach:
- Use a lightweight `DummyMH` implementation for base timing checks.
- Parametrize factory tests using the live orchestration registry.

Flow (pseudocode):
1. Instantiate dummy metaheuristic and verify timer/repr behavior.
2. Build all registered metaheuristics in offline mode.
3. Build control-enabled metaheuristics in online mode.

Important criteria:
- Every spec in the registry must construct successfully.
- Online-capable specs must expose control flag set to `1`.

Inputs/Outputs:
- Input: orchestration spec names and synthetic decoder/cost callbacks.
- Output: assertions over constructed object contracts.
"""

from __future__ import annotations

import numpy as np
import pytest
from rko.components.solution_pool import SolutionPool
from rko.metaheuristics.base import MetaheuristicBase
from rko.orchestration.configuration import MH_SPECS
from rko.orchestration.factory import build_metaheuristic


class DummyMH(MetaheuristicBase):
    """Minimal concrete implementation for testing the base contract."""

    def solve(self, limit_time: float) -> tuple[list[object], list[float], float]:
        """Run a trivial solve routine and return a fixed feasible result."""
        self._start_timer()
        return [], [0.0], 0.0


def test_metaheuristic_base_timer_and_repr() -> None:
    """Ensure base timer helpers and representation are functional."""
    mh = DummyMH(solution_pool=object(), name="Dummy")
    assert mh.elapsed() == 0.0
    _, keys, cost = mh.solve(limit_time=0.01)
    assert keys == [0.0]
    assert cost == 0.0
    assert mh.elapsed() >= 0.0
    assert "Dummy" in repr(mh)


@pytest.mark.parametrize("mh_name", sorted(MH_SPECS.keys()))
def test_build_metaheuristic_offline_for_all_specs(mh_name: str) -> None:
    """Ensure every registered spec can be built in offline mode."""
    mh = build_metaheuristic(
        mh_name=mh_name,
        pool=SolutionPool(capacity=4),
        decoder=lambda keys: keys,
        cost=lambda decoded: float(np.sum(decoded)),
        tam_solution=6,
        control=0,
        params_dir=None,
    )

    assert isinstance(mh, MetaheuristicBase)
    assert mh.name


@pytest.mark.parametrize(
    "mh_name",
    sorted(name for name, spec in MH_SPECS.items() if spec.supports_control),
)
def test_build_metaheuristic_online_sets_control_flag(mh_name: str) -> None:
    """Ensure control-enabled specs are built with online control flag."""
    mh = build_metaheuristic(
        mh_name=mh_name,
        pool=SolutionPool(capacity=4),
        decoder=lambda keys: keys,
        cost=lambda decoded: float(np.sum(decoded)),
        tam_solution=6,
        control=1,
        params_dir=None,
    )

    assert mh.control == 1
