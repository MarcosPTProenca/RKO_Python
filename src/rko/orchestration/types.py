"""Shared types for the orchestration layer."""

from __future__ import annotations

import numpy as np
from ..metaheuristics.base import MetaheuristicBase
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

RunResult = tuple[list[object], list[float], float]
DecoderFn = Callable[[np.ndarray], Any]
CostFn = Callable[[Any], float]


@dataclass(frozen=True)
class MhSpec:
    """Declarative specification for constructing a metaheuristic."""

    constructor: Callable[..., MetaheuristicBase]
    int_params: tuple[str, ...] = ()
    float_params: tuple[str, ...] = ()
    supports_control: bool = False


@dataclass(frozen=True)
class RunConfig:
    """Validated execution settings extracted from ``config.toml``."""

    control: int
    pool_size: int
    active_metaheuristics: tuple[str, ...]
