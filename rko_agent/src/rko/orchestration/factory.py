"""Factory for constructing configured metaheuristics."""

from __future__ import annotations

from ..components.solution_pool import SolutionPool
from ..metaheuristics.base import MetaheuristicBase
from ..parameters.loader import load_offline
from ..parameters.loader import load_online_grid
from .configuration import MH_SPECS
from .configuration import canonical_mh_name
from .types import CostFn
from .types import DecoderFn
from pathlib import Path
from typing import Any


def _as_int(params: dict[str, Any], key: str, mh_name: str) -> int:
    try:
        return int(params[key])
    except KeyError as exc:
        raise ValueError(f"Missing offline parameter '{key}' for '{mh_name}'.") from exc


def _as_float(params: dict[str, Any], key: str, mh_name: str) -> float:
    try:
        return float(params[key])
    except KeyError as exc:
        raise ValueError(f"Missing offline parameter '{key}' for '{mh_name}'.") from exc


def build_metaheuristic(
    mh_name: str,
    pool: SolutionPool,
    decoder: DecoderFn,
    cost: CostFn,
    tam_solution: int,
    control: int,
    params_dir: Path | None,
) -> MetaheuristicBase:
    """Construct one configured metaheuristic instance from TOML parameters."""
    canonical_name = canonical_mh_name(mh_name)
    spec = MH_SPECS.get(canonical_name)
    if spec is None:
        raise ValueError(f"Unknown metaheuristic name: '{mh_name}'")

    offline = load_offline(canonical_name, params_dir)
    online_grid = load_online_grid(canonical_name, params_dir) if control == 1 else []

    kwargs: dict[str, Any] = {
        "solution_pool": pool,
        "decoder": decoder,
        "cost": cost,
        "tam_solution": tam_solution,
    }

    for key in spec.int_params:
        kwargs[key] = _as_int(offline, key, canonical_name)
    for key in spec.float_params:
        kwargs[key] = _as_float(offline, key, canonical_name)

    if spec.supports_control:
        kwargs["control"] = control
        if online_grid:
            kwargs["parameters"] = online_grid

    return spec.constructor(**kwargs)
