"""Native Rust portfolio execution behind the existing RKO API.

Objective:
- Run the configured portfolio in the compiled engine and report it with the same
  immutable metadata as the Python backends.

Technical approach:
- Reuse the Python factory only to load, validate and snapshot parameters, so TOML
  files, hyperparameter overrides and joint-state feasibility filters keep one
  source of truth; the compiled engine receives plain numeric vectors.
- Wrap decoder/objective callbacks in a native callback problem, or accept a
  built-in native problem evaluated without the interpreter.
- Convert the engine's per-search reports into `SearchMetadata`.

Flow (pseudocode):
1. Build a validated parameter snapshot per selected algorithm.
2. Call the extension with the problem, specs, seed, workers and history cap.
3. Rebuild search metadata and return the incumbent keys and objective.

Important criteria:
- The extension is optional at import time; absence raises a clear error on use.
- Python callbacks serialize on the interpreter lock; native problems do not.
- Pool prefill is a native random fill of `pool_size` evaluated vectors; live progress
  output is not supported by this backend.

Inputs/Outputs:
- Input: validated run configuration, problem, time limit, seed and worker cap.
- Output: best keys/objective and appended `SearchMetadata` records.
"""

from __future__ import annotations

import dataclasses
import secrets
from ..components.solution_pool import SolutionPool
from .configuration import MH_SPECS
from .factory import build_metaheuristic
from .types import CostFn
from .types import DecoderFn
from .types import HistoryPoint
from .types import Hyperparameters
from .types import NativeProblem
from .types import PoolInitializationMetadata
from .types import RunConfig
from .types import SearchMetadata
from itertools import product
from pathlib import Path
from types import ModuleType
from typing import Any


class NativeRunner:
    """Execute one portfolio through the compiled engine.

    Responsibilities:
    - Translate validated Python configuration into native algorithm specifications.
    - Translate native reports back into public metadata.

    Attributes:
        config (RunConfig): Validated algorithm selection and shared settings.
        n_variables (int): Positive random-key dimension.
        params_dir (Path | None): Optional parameter TOML directory.
        hyperparameters (Hyperparameters | None): Normalized offline overrides.
    """

    def __init__(
        self,
        config: RunConfig,
        n_variables: int,
        params_dir: Path | None,
        hyperparameters: Hyperparameters | None,
    ) -> None:
        """Store validated settings without importing the extension.

        Args:
            config (RunConfig): Validated algorithm selection and shared settings.
            n_variables (int): Positive random-key dimension.
            params_dir (Path | None): Optional parameter TOML directory.
            hyperparameters (Hyperparameters | None): Normalized offline overrides.
        """
        self.config = config
        self.n_variables = n_variables
        self.params_dir = params_dir
        self.hyperparameters = hyperparameters or {}

    @staticmethod
    def module() -> ModuleType:
        """Import the compiled extension lazily.

        Returns:
            ModuleType: The `rko._native` module.

        Raises:
            RuntimeError: If the extension was not built for this installation.
        """
        try:
            from .. import _native
        except ImportError as error:
            raise RuntimeError(
                "The native backend requires the compiled rko._native extension; "
                "install a native wheel or build with maturin."
            ) from error
        return _native

    def specs(self) -> tuple[list[tuple[str, list[float], list[list[float]], bool]], list[Any]]:
        """Snapshot validated parameters for every selected algorithm.

        Returns:
            tuple: Native specifications and the Python algorithms that carry metadata.

        Raises:
            ValueError: If any parameter or online grid is invalid.
            OSError: If parameter files cannot be read.
        """
        scratch = SolutionPool(capacity=1)
        specs: list[tuple[str, list[float], list[list[float]], bool]] = []
        templates: list[Any] = []
        for name in self.config.active_metaheuristics:
            spec = MH_SPECS[name]
            algorithm = build_metaheuristic(
                name,
                scratch,
                lambda keys: keys,
                lambda value: 0.0,
                self.n_variables,
                self.config.control,
                self.params_dir,
                self.hyperparameters.get(name),
            )
            offline = [
                float(getattr(algorithm, key)) for key in spec.int_params + spec.float_params
            ]
            if name == "BRKGA_CS":
                offline.append(float(algorithm.sigma))
            adaptive = bool(spec.supports_control and self.config.control == 1)
            states: list[list[float]] = []
            if adaptive:
                feasible = algorithm._state_filter
                states = [
                    [float(value) for value in state]
                    for state in product(*algorithm.parameters)
                    if feasible is None or feasible(list(state))
                ]
            specs.append((name, offline, states, adaptive))
            templates.append(algorithm)
        return specs, templates

    def run(
        self,
        problem: NativeProblem | tuple[DecoderFn, CostFn],
        time_limit: float,
        random_state: int | None,
        workers: int | None,
        history_limit: int,
        search_metadata: list[SearchMetadata] | None,
        initialization_metadata: list[PoolInitializationMetadata] | None = None,
    ) -> tuple[list[float], float]:
        """Run the portfolio and publish metadata.

        Args:
            problem (NativeProblem | tuple): A native problem or a `(decoder, cost)` callback pair.
            time_limit (float): Positive search seconds.
            random_state (int | None): Base seed; a random seed is drawn when None.
            workers (int | None): Native worker threads, or one per algorithm.
            history_limit (int): Per-search history cap; zero disables recording.
            search_metadata (list[SearchMetadata] | None): Optional report collector.
            initialization_metadata (list | None): Optional prefill report collector.

        Returns:
            tuple[list[float], float]: Best keys and objective.

        Raises:
            RuntimeError: If the extension is missing or a native worker fails.
            ValueError: If the native engine rejects the configuration.
            Exception: Original callback exceptions propagate unchanged.
        """
        native = self.module()
        specs, templates = self.specs()
        if isinstance(problem, tuple):
            problem = native.CallbackProblem(problem[0], problem[1], self.n_variables)
        seed = secrets.randbits(63) if random_state is None else random_state
        result = native.run(
            problem,
            specs,
            float(time_limit),
            seed,
            self.config.pool_size,
            workers,
            history_limit,
            1,
            self.config.prefill_pool,
        )
        if search_metadata is not None:
            for report, template in zip(result["reports"], templates, strict=True):
                base = getattr(template, "_search_metadata", None) or SearchMetadata(
                    algorithm=report["algorithm"]
                )
                search_metadata.append(
                    dataclasses.replace(
                        base,
                        random_state=report["seed"],
                        n_evaluations=report["evaluations"],
                        stop_reason=report["stop"],
                        time_limit=report["budget"],
                        elapsed_seconds=report["elapsed"],
                        history=tuple(HistoryPoint(*point) for point in report["history"]),
                        history_limit=history_limit,
                        history_observations=report["history_observations"],
                    )
                )
        initial = result.get("initialization")
        if initial is not None and initialization_metadata is not None:
            initialization_metadata.append(
                PoolInitializationMetadata(
                    random_state=initial["seed"],
                    n_evaluations=initial["evaluations"],
                    elapsed_seconds=initial["elapsed"],
                    pool_size=initial["pool_len"],
                    stop_reason="completed",
                    time_limit=float(time_limit),
                )
            )
        return list(result["keys"]), float(result["cost"])
