"""Compatibility adapter for the class-based RKO solver.

Objective:
- Preserve the original run signature and tuple result for existing callers.

Technical approach:
- Delegate all validation, configuration and execution to RKO.

Flow (pseudocode):
1. Construct an RKO solver using the legacy arguments.
2. Execute solve with the requested search budget.
3. Return detached keys and objective in the original tuple format.

Important criteria:
- RKO is the primary API; no orchestration implementation is duplicated here.

Inputs/Outputs:
- Input: legacy problem definition and execution settings.
- Output: best key list and minimization objective.
"""

from __future__ import annotations

from .orchestration.types import CostFn
from .orchestration.types import DecoderFn
from .solver import RKO
from pathlib import Path
from typing import Literal


def run(
    decoder: DecoderFn,
    cost: CostFn,
    tam_solution: int,
    limit_time: float,
    *,
    params_dir: Path | None = None,
    backend: Literal["process", "thread", "serial"] = "process",
    n_jobs: int | None = None,
    random_state: int | None = None,
    verbose: bool = False,
    prefill_pool: bool | None = None,
) -> tuple[list[float], float]:
    """Delegate a legacy call to RKO and retain its tuple result contract.

    Args:
        decoder (DecoderFn): Problem-specific random-key decoder.
        cost (CostFn): Objective to minimize after decoding.
        tam_solution (int): Positive key dimension, named n_variables in RKO.
        limit_time (float): Positive search seconds, named time_limit in solve.
        params_dir (Path | None): Optional parameter TOML directory.
        backend (Literal): Process, legacy thread or serial execution.
        n_jobs (int | None): Optional process budget.
        random_state (int | None): Nonnegative per-search seed in every backend.
        verbose (bool): Flush lifecycle and pool updates; quiet by default.
        prefill_pool (bool | None): Opt-in reference startup override; None uses TOML.
            Startup has a separate allowance and does not reduce search durations.

    Returns:
        tuple[list[float], float]: Best keys and objective value.

    Raises:
        ValueError: If problem inputs or solver settings are invalid.
        RuntimeError: If an algorithm fails or a worker exits unexpectedly.
        TimeoutError: If process startup or search exceeds its watchdog.
        OSError: If parameter files cannot be read.
    """
    result = RKO(
        decoder,
        cost,
        tam_solution,
        params_dir=params_dir,
        backend=backend,
        n_jobs=n_jobs,
        random_state=random_state,
        verbose=verbose,
        prefill_pool=prefill_pool,
    ).solve(limit_time)
    return list(result.keys), result.cost
