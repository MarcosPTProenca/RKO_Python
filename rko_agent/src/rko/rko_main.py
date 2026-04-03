"""Public entrypoint for running the RKO ensemble."""

from __future__ import annotations

import logging
from .components.solution_pool import SolutionPool
from .orchestration.configuration import parse_run_config
from .orchestration.execution import run_metaheuristics_parallel
from .orchestration.execution import select_best_result
from .orchestration.factory import build_metaheuristic
from .orchestration.types import CostFn
from .orchestration.types import DecoderFn
from .parameters.loader import load_config
from pathlib import Path

logger = logging.getLogger(__name__)


def run(
    decoder: DecoderFn,
    cost: CostFn,
    tam_solution: int,
    limit_time: float,
    *,
    params_dir: Path | None = None,
) -> tuple[list[float], float]:
    """Run all active metaheuristics in parallel and return the best solution."""
    if tam_solution <= 0:
        raise ValueError("'tam_solution' must be > 0.")
    if limit_time <= 0:
        raise ValueError("'limit_time' must be > 0.")

    cfg = parse_run_config(load_config(params_dir))
    pool = SolutionPool(capacity=cfg.pool_size)

    metaheuristics = [
        build_metaheuristic(name, pool, decoder, cost, tam_solution, cfg.control, params_dir)
        for name in cfg.active_metaheuristics
    ]

    logger.debug(
        "Starting RKO run with control=%s, pool_size=%s, active=%s",
        cfg.control,
        cfg.pool_size,
        ", ".join(cfg.active_metaheuristics),
    )

    results = run_metaheuristics_parallel(metaheuristics, limit_time)
    return select_best_result(results, pool)
