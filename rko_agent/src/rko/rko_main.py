"""Public entry point for serial, threaded and multicore RKO search.

Objective:
- Minimize a decoded objective with a cooperating metaheuristic portfolio.

Technical approach:
- Validate execution settings and load the configured algorithms.
- Use spawned processes by default, with serial and legacy thread modes.

Flow (pseudocode):
1. Validate dimensions, time, backend and randomness options.
2. Load the portfolio and dispatch through the selected execution backend.
3. Return the best key vector and objective from searches and elite pool.

Important criteria:
- Process callbacks must be pickleable and importable under spawn.
- Timed cooperative searches are not bitwise reproducible from seeds alone.

Inputs/Outputs:
- Input: decoder, objective, dimensions, time and execution settings.
- Output: best random-key vector and minimization objective.
"""

from __future__ import annotations

import logging
import math
import numpy as np
import random
from .components.solution_pool import SolutionPool
from .orchestration.configuration import parse_run_config
from .orchestration.execution import run_metaheuristics_parallel
from .orchestration.execution import select_best_result
from .orchestration.factory import build_metaheuristic
from .orchestration.processes import run_processes
from .orchestration.types import CostFn
from .orchestration.types import DecoderFn
from .parameters.loader import load_config
from numbers import Real
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


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
) -> tuple[list[float], float]:
    """Run a configured portfolio and return its best objective/key pair.

    Args:
        decoder (DecoderFn): Problem-specific random-key decoder.
        cost (CostFn): Objective to minimize after decoding.
        tam_solution (int): Positive key-vector dimension.
        limit_time (float): Positive finite search budget in seconds.
        params_dir (Path | None): Optional directory of parameter TOMLs.
        backend (Literal): Process, legacy thread, or serial execution.
        n_jobs (int | None): Process budget; None allows one per algorithm.
        random_state (int | None): Nonnegative seed for serial/process modes.

    Returns:
        tuple[list[float], float]: Best keys followed by objective value.

    Raises:
        ValueError: If inputs, callback serialization or worker budget are invalid.
        RuntimeError: If an algorithm fails or a process exits unexpectedly.
        TimeoutError: If process startup/search exceeds its grace period.
    """
    if type(tam_solution) is not int or tam_solution <= 0:
        raise ValueError("'tam_solution' must be a positive integer.")
    if (
        isinstance(limit_time, bool)
        or not isinstance(limit_time, Real)
        or not math.isfinite(limit_time)
        or limit_time <= 0
    ):
        raise ValueError("'limit_time' must be positive and finite.")
    if backend not in ("process", "thread", "serial"):
        raise ValueError("'backend' must be 'process', 'thread', or 'serial'.")
    if not callable(decoder) or not callable(cost):
        raise ValueError("'decoder' and 'cost' must be callable.")
    if random_state is not None and (type(random_state) is not int or random_state < 0):
        raise ValueError("'random_state' must be a nonnegative integer or None.")
    if backend != "process" and n_jobs is not None:
        raise ValueError("'n_jobs' is only supported by the process backend.")
    if backend == "thread" and random_state is not None:
        raise ValueError("Thread workers share RNG state; use process or serial with random_state.")

    cfg = parse_run_config(load_config(params_dir))
    logger.debug("Starting RKO backend=%s, active=%s", backend, cfg.active_metaheuristics)
    if backend == "process":
        return run_processes(
            cfg, decoder, cost, tam_solution, limit_time, params_dir, n_jobs, random_state
        )

    pool = SolutionPool(capacity=cfg.pool_size)
    metaheuristics = [
        build_metaheuristic(name, pool, decoder, cost, tam_solution, cfg.control, params_dir)
        for name in cfg.active_metaheuristics
    ]
    if backend == "thread":
        return select_best_result(run_metaheuristics_parallel(metaheuristics, limit_time), pool)

    python_state = random.getstate()
    numpy_state = np.random.get_state()
    try:
        seeds = np.random.SeedSequence(random_state).spawn(len(metaheuristics))
        results = []
        for mh, sequence in zip(metaheuristics, seeds, strict=True):
            seed = int(sequence.generate_state(1)[0])
            random.seed(seed)
            np.random.seed(seed)
            results.append(mh.solve(limit_time))
        return select_best_result(results, pool)
    finally:
        random.setstate(python_state)
        np.random.set_state(numpy_state)
