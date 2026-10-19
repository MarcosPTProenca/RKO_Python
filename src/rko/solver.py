"""Class-based cooperative random-key optimization.

Objective:
- Own problem callbacks, portfolio configuration, execution and result state.

Technical approach:
- Validate settings at solve time and build a fresh cooperating portfolio.
- Dispatch through existing process, thread or serial backends.

Flow (pseudocode):
1. Construct RKO without starting work or reading configuration files.
2. Validate inputs and combine Python settings with packaged TOML defaults.
3. Execute searches and publish an immutable, measured result.

Important criteria:
- Repeated solves do not reuse algorithm state or a previous successful result.
- Process callbacks must be importable and pickleable under spawn.
- Timed cooperation is scheduling-dependent even with a fixed seed.

Inputs/Outputs:
- Input: problem callbacks, key dimension, execution settings and time budget.
- Output: RKOResult with best keys, objective and execution metadata.
"""

from __future__ import annotations

import math
import numpy as np
import random
import time
from .components.solution_pool import SolutionPool
from .orchestration.configuration import parse_run_config
from .orchestration.execution import run_metaheuristics_parallel
from .orchestration.execution import select_best_result
from .orchestration.factory import build_metaheuristic
from .orchestration.processes import run_processes
from .orchestration.search import SearchSession
from .orchestration.types import CostFn
from .orchestration.types import DecoderFn
from .orchestration.types import RunConfig
from .parameters.loader import load_config
from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class RKOResult:
    """Describe a completed optimization without mutable algorithm state.

    Responsibilities:
    - Preserve best keys and objective together with measured execution metadata.

    Attributes:
        keys (tuple[float, ...]): Best random-key vector.
        cost (float): Objective to minimize, evaluated on the decoded keys.
        elapsed_seconds (float): End-to-end solve duration including startup.
        backend (str): Executed backend.
        algorithms (tuple[str, ...]): Canonical portfolio names.
        random_state (int | None): Requested seed; timed results may still vary.
    """

    keys: tuple[float, ...]
    cost: float
    elapsed_seconds: float
    backend: str
    algorithms: tuple[str, ...]
    random_state: int | None


class RKO:
    """Configure and execute a cooperating portfolio of random-key searches.

    Responsibilities:
    - Own problem definition and explicit execution/portfolio settings.
    - Validate each solve, create fresh search state and expose its result.

    Attributes:
        decoder (DecoderFn): Random-key decoder.
        cost (CostFn): Objective applied to decoded candidates.
        n_variables (int): Positive key dimension.
        algorithms (Sequence[str] | None): Selection overriding TOML defaults.
        control (int | None): Offline 0 or online 1; None uses TOML defaults.
        pool_size (int | None): Shared elite capacity; None uses TOML defaults.
        params_dir (Path | None): Optional parameter directory.
        backend (str): Process, thread or serial execution.
        n_jobs (int | None): Positive process-worker limit, excluding the pool manager.
        random_state (int | None): Nonnegative serial/process seed.
        verbose (bool): Print lifecycle and attributed shared-pool updates; default False.
        result_ (RKOResult | None): Last successful solve; cleared before each attempt.
    """

    def __init__(
        self,
        decoder: DecoderFn,
        cost: CostFn,
        n_variables: int,
        *,
        algorithms: Sequence[str] | None = None,
        control: int | None = None,
        pool_size: int | None = None,
        params_dir: Path | None = None,
        backend: Literal["process", "thread", "serial"] = "process",
        n_jobs: int | None = None,
        random_state: int | None = None,
        verbose: bool = False,
    ) -> None:
        """Store problem and solver settings without I/O or search execution.

        Args:
            decoder (DecoderFn): Problem-specific random-key decoder.
            cost (CostFn): Objective to minimize after decoding.
            n_variables (int): Positive key dimension.
            algorithms (Sequence[str] | None): Portfolio overriding configuration.
            control (int | None): Offline 0 or online 1, or configured default.
            pool_size (int | None): Elite capacity, or configured default.
            params_dir (Path | None): Optional parameter TOML directory.
            backend (Literal): Process, legacy thread or serial execution.
            n_jobs (int | None): Positive worker limit; None allows one per algorithm.
                Smaller limits share workers and split the common search budget.
            random_state (int | None): Nonnegative seed for serial/process modes.
            verbose (bool): Flush lifecycle and shared-pool progress to stdout.
        """
        self.decoder = decoder
        self.cost = cost
        self.n_variables = n_variables
        self.algorithms = algorithms
        self.control = control
        self.pool_size = pool_size
        self.params_dir = params_dir
        self.backend = backend
        self.n_jobs = n_jobs
        self.random_state = random_state
        self.verbose = verbose
        self.result_: RKOResult | None = None

    def solve(self, time_limit: float) -> RKOResult:
        """Execute a fresh portfolio and retain its measured result.

        Args:
            time_limit (float): Positive finite search seconds, excluding startup;
                serial mode currently gives each algorithm this duration.

        Returns:
            RKOResult: Best candidate and execution metadata.

        Raises:
            ValueError: If callbacks, dimensions, settings or serialization are invalid.
            RuntimeError: If an algorithm fails or a process exits unexpectedly.
            TimeoutError: If process startup/search exceeds its grace period.
            OSError: If parameter files cannot be read.
        """
        self.result_ = None
        started = time.perf_counter()
        if type(self.n_variables) is not int or self.n_variables <= 0:
            raise ValueError("'n_variables' must be a positive integer.")
        if (
            isinstance(time_limit, bool)
            or not isinstance(time_limit, Real)
            or not math.isfinite(time_limit)
            or time_limit <= 0
        ):
            raise ValueError("'time_limit' must be positive and finite.")
        if type(self.verbose) is not bool:
            raise ValueError("'verbose' must be a boolean.")
        if self.backend not in ("process", "thread", "serial"):
            raise ValueError("'backend' must be 'process', 'thread', or 'serial'.")
        if not callable(self.decoder) or not callable(self.cost):
            raise ValueError("'decoder' and 'cost' must be callable.")
        if self.random_state is not None and (
            type(self.random_state) is not int or self.random_state < 0
        ):
            raise ValueError("'random_state' must be a nonnegative integer or None.")
        if self.backend != "process" and self.n_jobs is not None:
            raise ValueError("'n_jobs' is only supported by the process backend.")
        if self.backend == "thread" and self.random_state is not None:
            raise ValueError(
                "Thread workers share RNG state; use process or serial with random_state."
            )
        raw = load_config(self.params_dir)
        if not isinstance(raw.get("run"), dict):
            raise ValueError("Configuration section 'run' must be a table.")
        if self.algorithms is not None:
            if isinstance(self.algorithms, (str, bytes)) or not isinstance(
                self.algorithms, Sequence
            ):
                raise ValueError("'algorithms' must be a nonempty sequence of names.")
            raw["active_metaheuristics"] = {"list": list(self.algorithms)}
        for key, value in (("control", self.control), ("pool_size", self.pool_size)):
            if value is not None:
                raw["run"][key] = value
        config = parse_run_config(raw)
        if self.verbose:
            print(
                f"RKO START backend={self.backend} "
                f"algorithms=[{', '.join(config.active_metaheuristics)}] "
                f"search_budget={time_limit:g}s",
                flush=True,
            )
        keys, value = self._execute(config, time_limit, started_at=started)
        result = RKOResult(
            keys=tuple(float(key) for key in keys),
            cost=float(value),
            elapsed_seconds=time.perf_counter() - started,
            backend=self.backend,
            algorithms=config.active_metaheuristics,
            random_state=self.random_state,
        )
        if self.verbose:
            print(
                f"RKO DONE best={result.cost:.8g} elapsed={result.elapsed_seconds:.3f}s",
                flush=True,
            )
        self.result_ = result
        return result

    def _execute(
        self, config: RunConfig, time_limit: float, *, started_at: float
    ) -> tuple[list[float], float]:
        """Dispatch a validated portfolio without retaining worker state.

        Args:
            config (RunConfig): Validated selection and elite settings.
            time_limit (float): Positive search duration.
            started_at (float): Solve's monotonic origin, including configuration/startup.

        Returns:
            tuple[list[float], float]: Best keys and objective.

        Raises:
            ValueError: If process callbacks or worker budget are invalid.
            RuntimeError: If a worker fails.
            TimeoutError: If process execution exceeds its watchdog.
        """
        pool = SolutionPool(capacity=config.pool_size, verbose=self.verbose, started_at=started_at)
        metaheuristics = [
            build_metaheuristic(
                name,
                pool,
                self.decoder,
                self.cost,
                self.n_variables,
                config.control,
                self.params_dir,
            )
            for name in config.active_metaheuristics
        ]
        if self.backend == "process":
            return run_processes(
                config,
                self.decoder,
                self.cost,
                self.n_variables,
                time_limit,
                self.params_dir,
                self.n_jobs,
                self.random_state,
                verbose=self.verbose,
                started_at=started_at,
            )
        pool.start_progress()
        try:
            if self.backend == "thread":
                return select_best_result(
                    run_metaheuristics_parallel(metaheuristics, time_limit), pool
                )
            python_state = random.getstate()
            numpy_state = np.random.get_state()
            try:
                seeds = np.random.SeedSequence(self.random_state).spawn(len(metaheuristics))
                results = []
                for mh, sequence in zip(metaheuristics, seeds, strict=True):
                    seed = int(sequence.generate_state(1)[0])
                    random.seed(seed)
                    np.random.seed(seed)
                    results.append(SearchSession(self.decoder, self.cost).solve(mh, time_limit))
                return select_best_result(results, pool)
            finally:
                random.setstate(python_state)
                np.random.set_state(numpy_state)
        finally:
            pool.stop_progress()
