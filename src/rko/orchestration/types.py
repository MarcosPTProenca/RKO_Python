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

RunResult = tuple[list[object], list[float], float]
DecoderFn = Callable[[np.ndarray], Any]
CostFn = Callable[[Any], float]
Hyperparameters = Mapping[str, Mapping[str, int | float]]


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
