"""Threaded portfolio execution and incumbent selection.

Objective:
- Preserve worker failures and select a valid completed optimization result.

Technical approach:
- Run each search with a private callback budget and shared failure cancellation.
- Collect outcomes by portfolio position and retain the original failure cause.

Flow (pseudocode):
1. Start budget-aware worker threads.
2. Cancel peer work on failure and join returning workers.
3. Propagate failures or choose the best search/pool incumbent.

Important criteria:
- Arbitrarily blocked Python threads cannot be safely force-terminated.
- An absent or nonfinite incumbent is not a successful optimization result.

Inputs/Outputs:
- Input: configured algorithms, duration and shared elite pool.
- Output: completed worker results, best keys/cost or a caller-visible failure.
"""

from __future__ import annotations

import math
import threading
from ..components.solution_pool import ElitePool
from ..metaheuristics.base import MetaheuristicBase
from .search import SearchSession
from .types import RunResult


def run_metaheuristics_parallel(
    metaheuristics: list[MetaheuristicBase],
    limit_time: float,
) -> list[RunResult]:
    """Run thread searches with callback-budget and failure cancellation checks.

    Args:
        metaheuristics (list[MetaheuristicBase]): Fresh configured portfolio.
        limit_time (float): Search seconds per concurrently started algorithm.

    Returns:
        list[RunResult]: Search outcomes in portfolio order.

    Raises:
        RuntimeError: If any worker fails or returns no outcome.
    """
    results: list[RunResult | None] = [None] * len(metaheuristics)
    errors: list[BaseException | None] = [None] * len(metaheuristics)
    cancelled = threading.Event()

    def _worker(index: int, mh: MetaheuristicBase) -> None:
        """Collect one search outcome and cancel peers after any failure.

        Args:
            index (int): Portfolio position for the outcome.
            mh (MetaheuristicBase): Fresh search instance.
        """
        try:
            results[index] = SearchSession(mh.decoder, mh.cost).solve(
                mh,
                limit_time,
                cancelled=cancelled,
            )
        except BaseException as exc:
            errors[index] = exc
            cancelled.set()

    threads = [
        threading.Thread(target=_worker, args=(index, mh), daemon=True, name=mh.name)
        for index, mh in enumerate(metaheuristics)
    ]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except BaseException:
        cancelled.set()
        raise
    failures = [
        f"{mh.name}: {error!r}"
        for mh, error in zip(metaheuristics, errors, strict=True)
        if error is not None
    ]
    if failures:
        cause = next(error for error in errors if error is not None)
        raise RuntimeError("One or more metaheuristics failed: " + "; ".join(failures)) from cause
    if any(result is None for result in results):
        raise RuntimeError("A thread worker returned no outcome.")
    return [result for result in results if result is not None]


def select_best_result(
    results: list[RunResult],
    pool: ElitePool,
) -> tuple[list[float], float]:
    """Choose the best completed candidate across search results and pool.

    Args:
        results (list[RunResult]): Completed search outcomes.
        pool (ElitePool): Shared elite pool.

    Returns:
        tuple[list[float], float]: Detached best keys and finite objective.

    Raises:
        RuntimeError: If no finite nonempty solution exists.
    """
    best_keys: list[float] = []
    best_cost = math.inf
    for _, keys, cost in results:
        if keys and math.isfinite(cost) and cost < best_cost:
            best_cost = cost
            best_keys = list(keys)
    best = pool.best
    if best is not None:
        pool_cost, pool_keys = best
        if pool_cost < best_cost:
            best_cost = pool_cost
            best_keys = list(pool_keys)
    if not best_keys or not math.isfinite(best_cost):
        raise RuntimeError("RKO completed without a finite nonempty solution.")
    return best_keys, best_cost
