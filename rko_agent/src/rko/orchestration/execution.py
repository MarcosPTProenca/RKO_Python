"""Concurrent execution helpers for metaheuristics."""

from __future__ import annotations

import threading
from ..components.solution_pool import ElitePool
from ..metaheuristics.base import MetaheuristicBase
from .types import RunResult


def run_metaheuristics_parallel(
    metaheuristics: list[MetaheuristicBase],
    limit_time: float,
) -> list[RunResult]:
    """Run all metaheuristics in parallel and return their results."""
    results: list[RunResult | None] = [None] * len(metaheuristics)
    errors: list[Exception | None] = [None] * len(metaheuristics)

    def _worker(index: int, mh: MetaheuristicBase) -> None:
        try:
            results[index] = mh.solve(limit_time)
        except Exception as exc:
            errors[index] = exc

    threads = [
        threading.Thread(target=_worker, args=(index, mh), daemon=True, name=mh.name)
        for index, mh in enumerate(metaheuristics)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    failures = [
        f"{mh.name}: {error!r}"
        for mh, error in zip(metaheuristics, errors, strict=False)
        if error is not None
    ]
    if failures:
        raise RuntimeError("One or more metaheuristics failed: " + "; ".join(failures))

    return [result if result is not None else ([], [], float("inf")) for result in results]


def select_best_result(
    results: list[RunResult],
    pool: ElitePool,
) -> tuple[list[float], float]:
    """Return the best (keys, cost) considering thread results and shared pool."""
    best_keys: list[float] = []
    best_cost = float("inf")

    for _, keys, cost in results:
        if cost < best_cost:
            best_cost = cost
            best_keys = list(keys)

    best = pool.best
    if best is not None:
        pool_cost, pool_keys = best
        if pool_cost < best_cost:
            best_cost = pool_cost
            best_keys = list(pool_keys)

    return best_keys, best_cost
