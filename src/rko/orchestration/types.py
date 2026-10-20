"""Shared execution and parameter mapping contracts.

Objective:
- Name callback, result and configuration types used across backends.

Technical approach:
- Use immutable configuration records and structural callback/mapping aliases.

Flow (pseudocode):
1. Describe problem callbacks and selected algorithm schemas.
2. Normalize configuration and partial overrides before backend dispatch.
3. Exchange compatible result tuples across serial, thread and process modes.

Important criteria:
- Hyperparameter mappings are read-only inputs, normalized to plain dictionaries.
- Existing tuple result and callback contracts remain unchanged.

Inputs/Outputs:
- Input: callback functions, named parameter mappings and run settings.
- Output: shared type aliases and immutable configuration/specification records.
"""

from __future__ import annotations

import numpy as np
from ..metaheuristics.base import MetaheuristicBase
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Literal

RunResult = tuple[list[object], list[float], float]
DecoderFn = Callable[[np.ndarray], Any]
CostFn = Callable[[Any], float]
Hyperparameters = Mapping[str, Mapping[str, int | float]]


@dataclass(frozen=True)
class SearchMetadata:
    """Preserve one algorithm's initial configuration and completed work.

    Responsibilities:
    - Snapshot validated initial scalar parameters and ordered adaptive axes.
    - Report finite objective completions without retaining candidate populations.

    Attributes:
        algorithm (str): Canonical portfolio name.
        control (int): Effective control; unsupported adaptive algorithms use zero.
        parameters (tuple): Named initial scalars, including Python overrides.
        parameter_grid (tuple): Adaptive axes in algorithm schema order, not a trajectory.
        random_state (int | None): Actual assigned generator seed when known.
        n_evaluations (int): Successfully completed finite objective evaluations.
        stop_reason (str): Completed, time_limit, cancelled, or not_started.
        time_limit (float): Assigned search seconds excluding startup; zero if not started.
        elapsed_seconds (float): Search/session duration, excluding startup and queueing.
    """

    algorithm: str
    control: int = 0
    parameters: tuple[tuple[str, int | float], ...] = ()
    parameter_grid: tuple[tuple[int | float, ...], ...] = ()
    random_state: int | None = None
    n_evaluations: int = 0
    stop_reason: Literal["completed", "time_limit", "cancelled", "not_started"] = "not_started"
    time_limit: float = 0.0
    elapsed_seconds: float = 0.0


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
