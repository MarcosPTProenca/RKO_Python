"""Tests for the public RKO entrypoint orchestration flow.

Objective:
- Validate input guards and end-to-end orchestration wiring in `rko_main.run`.

Technical approach:
- Assert explicit validation errors for invalid scalar inputs.
- Monkeypatch orchestration collaborators to isolate control flow.

Flow (pseudocode):
1. Call `run` with invalid inputs and assert raised errors.
2. Stub configuration/factory/execution collaborators.
3. Execute `run` and assert forwarded values and final selection.

Important criteria:
- Input validation must reject non-positive `tam_solution` and `limit_time`.
- Orchestration must use active metaheuristics from parsed config.

Inputs/Outputs:
- Input: mocked orchestration dependencies and synthetic callbacks.
- Output: assertions over selected best result and forwarded arguments.
"""

from __future__ import annotations

import pytest
from rko import rko_main
from rko.orchestration.types import RunConfig


def test_run_rejects_invalid_tam_solution() -> None:
    """Ensure `run` rejects non-positive solution size."""
    with pytest.raises(ValueError, match="tam_solution"):
        rko_main.run(lambda x: x, lambda x: 0.0, tam_solution=0, limit_time=1.0)


def test_run_rejects_invalid_limit_time() -> None:
    """Ensure `run` rejects non-positive execution time limits."""
    with pytest.raises(ValueError, match="limit_time"):
        rko_main.run(lambda x: x, lambda x: 0.0, tam_solution=3, limit_time=0.0)


def test_run_executes_orchestration_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure orchestration collaborators are called and best result is returned."""
    captured: dict[str, object] = {}

    monkeypatch.setattr(rko_main, "load_config", lambda params_dir: {"ok": True})
    monkeypatch.setattr(
        rko_main,
        "parse_run_config",
        lambda cfg: RunConfig(control=0, pool_size=3, active_metaheuristics=("SA", "GA")),
    )
    monkeypatch.setattr(
        rko_main,
        "build_metaheuristic",
        lambda name, pool, decoder, cost, tam_solution, control, params_dir: f"mh:{name}",
    )

    def _fake_parallel(
        metaheuristics: list[object], limit_time: float
    ) -> list[tuple[list[object], list[float], float]]:
        captured["metaheuristics"] = metaheuristics
        captured["limit_time"] = limit_time
        return [([], [0.2, 0.3], 12.0)]

    monkeypatch.setattr(rko_main, "run_metaheuristics_parallel", _fake_parallel)
    monkeypatch.setattr(rko_main, "select_best_result", lambda results, pool: ([0.2, 0.3], 12.0))

    best_keys, best_cost = rko_main.run(
        decoder=lambda keys: keys,
        cost=lambda decoded: float(sum(decoded)),
        tam_solution=2,
        limit_time=5.0,
    )

    assert best_keys == [0.2, 0.3]
    assert best_cost == 12.0
    assert captured["limit_time"] == 5.0
    assert captured["metaheuristics"] == ["mh:SA", "mh:GA"]
