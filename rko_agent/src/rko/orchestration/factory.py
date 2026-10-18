"""Factory for constructing configured metaheuristics."""

from __future__ import annotations

import math
from ..components.solution_pool import ElitePool
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
    """Read an integral numeric parameter without truncating fractional values.

    Args:
        params (dict[str, Any]): Parsed offline table.
        key (str): Required parameter name.
        mh_name (str): Algorithm identifier for diagnostics.

    Returns:
        int: Exact integral numeric value.

    Raises:
        ValueError: If the value is missing, nonfinite, fractional or nonnumeric.
    """
    if key in params and type(params[key]) is int:
        return params[key]
    value = _as_float(params, key, mh_name)
    if not value.is_integer():
        raise ValueError(f"{mh_name}: '{key}' must be integral; fractional values are invalid.")
    return int(value)


def _as_float(params: dict[str, Any], key: str, mh_name: str) -> float:
    """Read a finite TOML number without coercing strings or booleans.

    Args:
        params (dict[str, Any]): Parsed offline table.
        key (str): Required parameter name.
        mh_name (str): Algorithm identifier for diagnostics.

    Returns:
        float: Finite numeric parameter.

    Raises:
        ValueError: If the value is missing, nonfinite or nonnumeric.
    """
    try:
        value = params[key]
    except KeyError as exc:
        raise ValueError(f"Missing offline parameter '{key}' for '{mh_name}'.") from exc
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{mh_name}: '{key}' must be a finite number, not a string or boolean.")
    return float(value)


def build_metaheuristic(
    mh_name: str,
    pool: ElitePool,
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
