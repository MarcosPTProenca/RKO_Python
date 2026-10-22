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
import os
import platform
import time
from .components.random_streams import RandomStreams
from .components.solution_pool import SolutionPool
from .orchestration.adaptation import Adaptation
from .orchestration.adaptation import adaptation_name
from .orchestration.adaptation import normalize_adaptation
from .orchestration.configuration import parse_run_config
from .orchestration.execution import run_metaheuristics_parallel
from .orchestration.execution import select_best_result
from .orchestration.factory import build_metaheuristic
from .orchestration.factory import normalize_hyperparameters
from .orchestration.initialization import initialize_pool
from .orchestration.processes import run_processes
from .orchestration.search import SearchSession
from .orchestration.types import CostFn
from .orchestration.types import DecoderFn
from .orchestration.types import Hyperparameters
from .orchestration.types import PoolInitializationMetadata
from .orchestration.types import RunConfig
from .orchestration.types import SearchMetadata
from .parameters.loader import load_config
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
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
        searches (tuple[SearchMetadata, ...]): All algorithms in portfolio order.
        n_variables (int | None): Requested dimension, when recorded.
        time_limit (float | None): Requested search seconds, excluding startup.
        control (int | None): Requested portfolio control; reports give effective control.
        pool_size (int | None): Configured elite capacity.
        n_jobs (int | None): Requested process-worker cap.
        versions (tuple): RKO distribution, Python and NumPy runtime versions.
        available_cpus (int | None): Usable logical CPUs snapshotted for process execution.
        initialization (PoolInitializationMetadata | None): Separate opt-in startup work.
    """

    keys: tuple[float, ...]
    cost: float
    elapsed_seconds: float
    backend: str
    algorithms: tuple[str, ...]
    random_state: int | None
    searches: tuple[SearchMetadata, ...] = ()
    n_variables: int | None = None
    time_limit: float | None = None
    control: int | None = None
    pool_size: int | None = None
    n_jobs: int | None = None
    versions: tuple[tuple[str, str], ...] = ()
    available_cpus: int | None = None
    initialization: PoolInitializationMetadata | None = None

    @property
    def n_evaluations(self) -> int | None:
        """Return completed finite objectives, or unknown for legacy manual results.

        Returns:
            int | None: Completed startup plus all searches, or unknown for legacy results.
        """
        if not self.searches and self.initialization is None:
            return None
        return sum(report.n_evaluations for report in self.searches) + (
            self.initialization.n_evaluations if self.initialization is not None else 0
        )

    @property
    def stop_reason(self) -> str:
        """Summarize whether any search exhausted its assigned budget.

        Returns:
            str: Cancelled, time_limit, completed, or unknown without reports.
        """
        reasons = {report.stop_reason for report in self.searches}
        if "cancelled" in reasons:
            return "cancelled"
        if reasons.intersection(("time_limit", "not_started")):
            return "time_limit"
        return "completed" if reasons else "unknown"

    @property
    def n_workers(self) -> int:
        """Return search-worker concurrency, excluding managers and native threads.

        Returns:
            int: Configured execution workers rather than CPU-core utilization.
        """
        if self.backend == "serial":
            return 1
        limit = self.n_jobs
        if limit is None and self.backend == "process":
            limit = self.available_cpus
        return min(limit or len(self.algorithms), len(self.algorithms))

    @property
    def adaptation(self) -> Adaptation | None:
        """Return the public adaptation name for the requested control mode.

        Returns:
            Adaptation | None: "fixed", "adaptive", or None when unknown.
        """
        return adaptation_name(self.control)


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
        control (int | None): Legacy mode override; None leaves configuration in charge.
        adaptation (Adaptation | None): Readable fixed/adaptive mode override.
        pool_size (int | None): Shared elite capacity; None uses TOML defaults.
        prefill_pool (bool | None): Opt-in reference-style startup; None uses TOML.
        params_dir (Path | None): Optional parameter directory.
        backend (str): Process, thread or serial execution.
        n_jobs (int | None): Positive process-worker limit, excluding the pool manager.
        random_state (int | None): Nonnegative per-search seed in every backend.
        verbose (bool): Print lifecycle and attributed shared-pool updates; default False.
        hyperparameters (Hyperparameters | None): Partial named offline scalar overrides.
        result_ (RKOResult | None): Last successful solve; cleared before each attempt.
    """

    def __init__(
        self,
        decoder: DecoderFn,
        cost: CostFn,
        n_variables: int,
        *,
        algorithms: Sequence[str] | None = None,
        adaptation: Adaptation | None = None,
        control: int | None = None,
        pool_size: int | None = None,
        prefill_pool: bool | None = None,
        params_dir: Path | None = None,
        backend: Literal["process", "thread", "serial"] = "process",
        n_jobs: int | None = None,
        random_state: int | None = None,
        verbose: bool = False,
        hyperparameters: Hyperparameters | None = None,
    ) -> None:
        """Store problem and solver settings without I/O or search execution.

        Args:
            decoder (DecoderFn): Problem-specific random-key decoder.
            cost (CostFn): Objective to minimize after decoding.
            n_variables (int): Positive key dimension.
            algorithms (Sequence[str] | None): Portfolio overriding configuration.
            adaptation (Adaptation | None): "fixed" parameters chosen before the search
                or "adaptive" Q-learning choices during it; None uses the configured
                default. Prefer this readable name over the legacy integer code.
            control (int | None): Legacy 0 (fixed) or 1 (adaptive); accepted on its own
                for compatibility and rejected when it contradicts `adaptation`.
            pool_size (int | None): Elite capacity, or configured default.
            prefill_pool (bool | None): Reference startup override; adds a separately
                accounted cooperative allowance equal to time_limit before fresh searches.
            params_dir (Path | None): Optional parameter TOML directory.
            backend (Literal): Process, legacy thread or serial execution.
            n_jobs (int | None): Positive worker limit; None uses available logical CPUs.
                Missing CPU discovery falls back to one worker. Smaller limits share
                workers and split the common search budget; explicit limits override CPUs.
            random_state (int | None): Nonnegative seed for owned library RNG streams.
            verbose (bool): Flush lifecycle and shared-pool progress to stdout.
            hyperparameters (Hyperparameters | None): Per-algorithm offline overrides;
                require control=0 and merge with TOML defaults without writing files.
        """
        self.decoder = decoder
        self.cost = cost
        self.n_variables = n_variables
        self.algorithms = algorithms
        self.adaptation = adaptation
        self.control = control
        self.pool_size = pool_size
        self.prefill_pool = prefill_pool
        self.params_dir = params_dir
        self.backend = backend
        self.n_jobs = n_jobs
        self.random_state = random_state
        self.verbose = verbose
        self.hyperparameters = hyperparameters
        self.result_: RKOResult | None = None

    def solve(self, time_limit: float) -> RKOResult:
        """Execute a fresh portfolio and retain its measured result.

        Args:
            time_limit (float): Positive finite search seconds, excluding startup;
                serial mode currently gives each algorithm this duration. Opt-in
                shared initialization has a separate equal cooperative allowance.

        Returns:
            RKOResult: Best candidate and execution metadata.

        Raises:
            ValueError: If callbacks, dimensions, settings or serialization are invalid.
            RuntimeError: If an algorithm fails or a process exits unexpectedly.
            TimeoutError: If process startup, initialization or search exceeds its grace.
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
        raw = load_config(self.params_dir)
        if not isinstance(raw.get("run"), dict):
            raise ValueError("Configuration section 'run' must be a table.")
        if self.algorithms is not None:
            if isinstance(self.algorithms, (str, bytes)) or not isinstance(
                self.algorithms, Sequence
            ):
                raise ValueError("'algorithms' must be a nonempty sequence of names.")
            raw["active_metaheuristics"] = {"list": list(self.algorithms)}
        control = normalize_adaptation(self.adaptation, self.control)
        if control is not None:
            raw["run"].pop("adaptation", None)
        for key, value in (
            ("control", control),
            ("pool_size", self.pool_size),
            ("prefill_pool", self.prefill_pool),
        ):
            if value is not None:
                raw["run"][key] = value
        config = parse_run_config(raw)
        hyperparameters = normalize_hyperparameters(
            self.hyperparameters, config.active_metaheuristics, config.control
        )
        if self.verbose:
            print(
                f"RKO START backend={self.backend} "
                f"algorithms=[{', '.join(config.active_metaheuristics)}] "
                f"search_budget={time_limit:g}s",
                flush=True,
            )
        metadata: list[SearchMetadata] = []
        initialization: list[PoolInitializationMetadata] = []
        backend, n_jobs, random_state, n_variables = (
            self.backend,
            self.n_jobs,
            self.random_state,
            self.n_variables,
        )
        available_cpus = max(1, os.process_cpu_count() or 1) if backend == "process" else None
        keys, value = self._execute(
            config,
            time_limit,
            started_at=started,
            hyperparameters=hyperparameters,
            search_metadata=metadata,
            initialization_metadata=initialization,
            process_worker_limit=n_jobs if n_jobs is not None else available_cpus,
        )
        positions = {name: index for index, name in enumerate(config.active_metaheuristics)}
        try:
            package_version = version("rko")
        except PackageNotFoundError:
            package_version = "unknown"
        result = RKOResult(
            keys=tuple(float(key) for key in keys),
            cost=float(value),
            elapsed_seconds=time.perf_counter() - started,
            backend=backend,
            algorithms=config.active_metaheuristics,
            random_state=random_state,
            searches=tuple(sorted(metadata, key=lambda report: positions[report.algorithm])),
            n_variables=n_variables,
            time_limit=float(time_limit),
            control=config.control,
            pool_size=config.pool_size,
            n_jobs=n_jobs,
            available_cpus=available_cpus,
            initialization=initialization[0] if initialization else None,
            versions=(
                ("rko", package_version),
                ("python", platform.python_version()),
                ("numpy", np.__version__),
            ),
        )
        if self.verbose:
            print(
                f"RKO DONE best={result.cost:.8g} elapsed={result.elapsed_seconds:.3f}s",
                flush=True,
            )
        self.result_ = result
        return result

    def _execute(
        self,
        config: RunConfig,
        time_limit: float,
        *,
        started_at: float,
        hyperparameters: Hyperparameters | None = None,
        search_metadata: list[SearchMetadata] | None = None,
        process_worker_limit: int | None = None,
        initialization_metadata: list[PoolInitializationMetadata] | None = None,
    ) -> tuple[list[float], float]:
        """Dispatch a validated portfolio without retaining worker state.

        Args:
            config (RunConfig): Validated selection and elite settings.
            time_limit (float): Positive search duration.
            started_at (float): Solve's monotonic origin, including configuration/startup.
            hyperparameters (Hyperparameters | None): Owned normalized offline overrides.
            search_metadata (list[SearchMetadata] | None): Optional immutable report collector.
            process_worker_limit (int | None): Resolved per-solve process cap.
            initialization_metadata (list | None): Optional shared startup report collector.

        Returns:
            tuple[list[float], float]: Best keys and objective.

        Raises:
            ValueError: If process callbacks or worker budget are invalid.
            RuntimeError: If a worker fails.
            TimeoutError: If process execution exceeds its watchdog.
        """
        pool = SolutionPool(capacity=config.pool_size, verbose=self.verbose, started_at=started_at)
        seeds = np.random.SeedSequence(self.random_state).spawn(len(config.active_metaheuristics))
        streams = [RandomStreams(int(sequence.generate_state(1)[0])) for sequence in seeds]
        metaheuristics = []
        for name, stream in zip(config.active_metaheuristics, streams, strict=True):
            with stream.activate():
                metaheuristics.append(
                    build_metaheuristic(
                        name,
                        pool,
                        self.decoder,
                        self.cost,
                        self.n_variables,
                        config.control,
                        self.params_dir,
                        (hyperparameters or {}).get(name),
                    )
                )
        if self.backend == "process":
            return run_processes(
                config,
                self.decoder,
                self.cost,
                self.n_variables,
                time_limit,
                self.params_dir,
                process_worker_limit if process_worker_limit is not None else self.n_jobs,
                self.random_state,
                verbose=self.verbose,
                started_at=started_at,
                hyperparameters=hyperparameters,
                search_metadata=search_metadata,
                initialization_metadata=initialization_metadata,
            )
        pool.start_progress()
        try:
            if config.prefill_pool:
                report = initialize_pool(
                    pool,
                    self.decoder,
                    self.cost,
                    self.n_variables,
                    config.pool_size,
                    time_limit,
                    self.random_state,
                )
                if initialization_metadata is not None:
                    initialization_metadata.append(report)
            if self.backend == "thread":
                return select_best_result(
                    run_metaheuristics_parallel(
                        metaheuristics, time_limit, streams, search_metadata=search_metadata
                    ),
                    pool,
                )
            results = []
            for mh, stream in zip(metaheuristics, streams, strict=True):
                with stream.activate():
                    session = SearchSession(self.decoder, self.cost)
                    results.append(session.solve(mh, time_limit, random_state=stream.seed))
                    if search_metadata is not None:
                        assert session.metadata is not None
                        search_metadata.append(session.metadata)
            return select_best_result(results, pool)
        finally:
            pool.stop_progress()
