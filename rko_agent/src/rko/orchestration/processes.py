"""Spawn-based cooperative metaheuristic execution.

Objective:
- Run CPU-bound searches in separate processes with one shared elite pool.

Technical approach:
- Host SolutionPool in a manager and exchange control/results through pipes.
- Construct each search in its worker and release ready workers together.

Flow (pseudocode):
1. Validate serialization and start the managed pool and workers.
2. Wait for readiness, publish a deadline, and release the search event.
3. Collect results or propagate failures, then close all child resources.

Important criteria:
- No queued search may receive a fresh full-duration budget.
- Startup is bounded to 60 seconds; search overrun grace is five seconds.
- Arbitrary callbacks cannot be interrupted cooperatively.

Inputs/Outputs:
- Input: validated configuration, pickleable callbacks, duration and seed.
- Output: best keys and cost, or an algorithm-specific failure.
"""

from __future__ import annotations

import multiprocessing as mp
import numpy as np
import pickle
import random
import sys
import time
import traceback
from ..components.solution_pool import SolutionPool
from .execution import select_best_result
from .factory import build_metaheuristic
from .types import CostFn
from .types import DecoderFn
from .types import RunConfig
from .types import RunResult
from multiprocessing.connection import Connection
from multiprocessing.connection import wait
from multiprocessing.managers import BaseManager
from multiprocessing.managers import BaseProxy
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.synchronize import Event
from pathlib import Path


class PoolProxy(BaseProxy):
    """Expose the existing elite-pool contract across process boundaries.

    Responsibilities:
    - Delegate mutations and return detached elite snapshots.

    Attributes:
        _exposed_ (tuple[str, ...]): Manager methods available to workers.
    """

    _exposed_ = ("insert", "get_elite")

    def insert(self, entry: tuple[float, list[float]], source: str = "") -> None:
        """Insert a candidate into the authoritative pool.

        Args:
            entry (tuple[float, list[float]]): Finite objective and key vector.
            source (str): Producing algorithm label.

        Raises:
            ValueError: If the candidate violates pool validation.
        """
        self._callmethod("insert", (entry, source))

    def get_elite(self, k: int = 1) -> list[tuple[float, list[float]]]:
        """Fetch detached elite entries from the manager.

        Args:
            k (int): Maximum number of entries to retrieve.

        Returns:
            list[tuple[float, list[float]]]: Cost-ordered elite snapshots.
        """
        return self._callmethod("get_elite", (k,))

    @property
    def size(self) -> int:
        """Return the number of managed entries.

        Returns:
            int: Current pool occupancy.
        """
        return len(self.get_elite(sys.maxsize))

    @property
    def best(self) -> tuple[float, list[float]] | None:
        """Return the best managed entry when available.

        Returns:
            tuple[float, list[float]] | None: Best detached entry or None.
        """
        entries = self.get_elite(1)
        return entries[0] if entries else None


class PoolManager(BaseManager):
    """Host the authoritative pool in a dedicated manager process.

    Responsibilities:
    - Own pool lifetime and serialize access through its existing lock.

    Attributes:
        SolutionPool (Callable): Registered constructor returning a pool proxy.
    """


PoolManager.register("SolutionPool", SolutionPool, proxytype=PoolProxy)


def _worker(
    name: str,
    config: RunConfig,
    pool: PoolProxy,
    decoder: DecoderFn,
    cost: CostFn,
    dimension: int,
    params_dir: Path | None,
    seed: int,
    start: Event,
    deadline: Synchronized,
    connection: Connection,
) -> None:
    """Construct one search and report readiness, result or failure.

    Args:
        name (str): Registered algorithm name.
        config (RunConfig): Validated global settings.
        pool (PoolProxy): Shared elite-pool proxy.
        decoder (DecoderFn): Pickleable problem decoder.
        cost (CostFn): Pickleable objective callback.
        dimension (int): Number of random keys.
        params_dir (Path | None): Optional parameter directory.
        seed (int): Distinct worker seed for Python and NumPy.
        start (Event): Parent-controlled simultaneous release.
        deadline (Synchronized): Common monotonic search deadline.
        connection (Connection): Dedicated result/control pipe.
    """
    try:
        random.seed(seed)
        np.random.seed(seed)
        mh = build_metaheuristic(name, pool, decoder, cost, dimension, config.control, params_dir)
        connection.send(("ready", None))
        start.wait()
        remaining = deadline.value - time.perf_counter()
        if remaining <= 0:
            raise TimeoutError("Search deadline elapsed before worker execution.")
        connection.send(("result", mh.solve(remaining)))
    except BaseException as exc:
        details = traceback.format_exc()
        try:
            pickle.dumps(exc)
            cause = exc
        except Exception:
            cause = RuntimeError(f"{type(exc).__name__}: {exc}")
        connection.send(("error", (cause, details)))
    finally:
        connection.close()


def run_processes(
    config: RunConfig,
    decoder: DecoderFn,
    cost: CostFn,
    dimension: int,
    limit_time: float,
    params_dir: Path | None,
    n_jobs: int | None,
    random_state: int | None,
) -> tuple[list[float], float]:
    """Execute a selected portfolio with a common start and managed pool.

    Args:
        config (RunConfig): Validated algorithm selection and pool settings.
        decoder (DecoderFn): Pickleable problem decoder.
        cost (CostFn): Pickleable objective callback.
        dimension (int): Number of random keys.
        limit_time (float): Search seconds excluding process startup.
        params_dir (Path | None): Optional parameter directory.
        n_jobs (int | None): Process budget; None allows one per algorithm.
        random_state (int | None): Seed used to derive independent worker seeds.

    Returns:
        tuple[list[float], float]: Best keys and minimization objective.

    Raises:
        ValueError: If callbacks are not pickleable or the portfolio exceeds budget.
        RuntimeError: If a worker fails or exits without returning a result.
        TimeoutError: If startup or search exceeds its allowed grace period.
    """
    names = config.active_metaheuristics
    if n_jobs is not None and (type(n_jobs) is not int or n_jobs < len(names)):
        raise ValueError("n_jobs must be an integer >= the number of active metaheuristics.")
    try:
        pickle.dumps((decoder, cost))
    except Exception as exc:
        raise ValueError(
            "Process mode requires pickleable decoder/cost callbacks; use module-level "
            "functions or callable classes, not lambdas or nested functions."
        ) from exc

    context = mp.get_context("spawn")
    seeds = np.random.SeedSequence(random_state).spawn(len(names))
    with PoolManager(ctx=context) as manager:
        pool = manager.SolutionPool(config.pool_size)
        start = context.Event()
        deadline = context.Value("d", 0.0)
        processes: list[mp.Process] = []
        connections: list[Connection] = []
        pending: dict[Connection, str] = {}
        ready: set[Connection] = set()
        results: list[RunResult] = []
        expires = time.perf_counter() + 60.0
        try:
            for name, sequence in zip(names, seeds, strict=True):
                parent, child = context.Pipe(duplex=False)
                connections.append(parent)
                process = context.Process(
                    target=_worker,
                    name=f"rko-{name}",
                    args=(
                        name,
                        config,
                        pool,
                        decoder,
                        cost,
                        dimension,
                        params_dir,
                        int(sequence.generate_state(1)[0]),
                        start,
                        deadline,
                        child,
                    ),
                )
                processes.append(process)
                try:
                    process.start()
                finally:
                    child.close()
                pending[parent] = name

            while pending:
                available = wait(list(pending), timeout=max(0.0, expires - time.perf_counter()))
                if not available:
                    phase = "search" if start.is_set() else "startup"
                    raise TimeoutError(
                        f"RKO {phase} timed out; unfinished: {list(pending.values())}"
                    )
                for connection in available:
                    name = pending[connection]
                    try:
                        status, payload = connection.recv()
                    except EOFError as exc:
                        raise RuntimeError(f"{name}: worker exited without a result.") from exc
                    if status == "error":
                        cause, details = payload
                        raise RuntimeError(f"{name}: worker failed.\n{details}") from cause
                    if status == "ready":
                        ready.add(connection)
                    else:
                        results.append(payload)
                        del pending[connection]
                if not start.is_set() and len(ready) == len(names):
                    deadline.value = time.perf_counter() + limit_time
                    expires = deadline.value + 5.0
                    start.set()
            return select_best_result(results, pool)
        finally:
            for process in processes:
                if process.pid is not None:
                    process.join(timeout=0.2)
            for process in processes:
                if process.is_alive():
                    process.terminate()
            for process in processes:
                if process.pid is not None:
                    process.join(timeout=1.0)
                    if process.is_alive():
                        process.kill()
                        process.join()
                process.close()
            for connection in connections:
                connection.close()
