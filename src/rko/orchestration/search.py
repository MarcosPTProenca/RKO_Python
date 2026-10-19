"""Cooperative stopping at the shared decoder/objective boundary.

Objective:
- Bound nested search work and preserve the best evaluated candidate on stopping.

Technical approach:
- Carry a monotonic deadline through the callbacks already passed to every operator.
- Pair decoded payloads with copied keys without changing user callback payloads.
- Stop between callbacks and retain completed evaluations, including initialization.

Flow (pseudocode):
1. Bind a fresh session to one algorithm's decoder and objective.
2. Check deadline/cancellation before each callback after the first valid result.
3. Catch internal budget exhaustion and return the best completed candidate.

Important criteria:
- User callbacks remain trusted and cannot be interrupted while executing.
- A first evaluation is permitted even if initialization consumed the budget.
- Sessions are private to one sequential search, never shared between workers.

Inputs/Outputs:
- Input: algorithm, positive duration, optional absolute deadline/cancellation event.
- Output: incumbent-preserving algorithm result or the original callback exception.
"""

from __future__ import annotations

import math
import numpy as np
import threading
import time
from .types import CostFn
from .types import DecoderFn
from .types import RunResult
from .types import SearchMetadata
from dataclasses import dataclass
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from ..metaheuristics.base import MetaheuristicBase


class _BudgetExpired(Exception):
    """Signal cooperative stopping without treating it as an algorithm failure."""


@dataclass
class _DecodedCandidate:
    """Keep objective payload and its originating chromosome associated.

    Responsibilities:
    - Preserve keys independently of temporary arrays reused by local searches.

    Attributes:
        keys (np.ndarray): Detached originating chromosome.
        payload (Any): Exact decoded value passed to the user's objective.
    """

    keys: np.ndarray
    payload: Any


class SearchSession:
    """Own one search's callback deadline and completed incumbent.

    Responsibilities:
    - Apply the same stopping criterion through all nested operators.
    - Preserve a usable result when a population or local search is interrupted.

    Attributes:
        decoder (DecoderFn): Original problem decoder.
        cost (CostFn): Original objective callback.
        deadline (float): Absolute monotonic stop time.
        cancelled (threading.Event | None): Optional portfolio failure signal.
        best (tuple[np.ndarray, float] | None): Detached best completed evaluation.
        n_evaluations (int): Completed finite objective evaluations in this search.
        metadata (SearchMetadata | None): Immutable report after a successful search.
    """

    def __init__(self, decoder: DecoderFn, cost: CostFn) -> None:
        """Retain trusted problem callbacks without executing them.

        Args:
            decoder (DecoderFn): Original random-key decoder.
            cost (CostFn): Original minimization objective.
        """
        self.decoder = decoder
        self.cost = cost
        self.deadline = math.inf
        self.cancelled: threading.Event | None = None
        self.best: tuple[np.ndarray, float] | None = None
        self.n_evaluations = 0
        self.metadata: SearchMetadata | None = None
        self._stop_reason = "completed"

    def _check(self) -> None:
        """Stop after a valid result exists or when another worker failed.

        Raises:
            _BudgetExpired: If cancellation or the callback deadline is reached.
        """
        if self.cancelled is not None and self.cancelled.is_set():
            self._stop_reason = "cancelled"
            raise _BudgetExpired
        if self.best is not None and time.perf_counter() >= self.deadline:
            self._stop_reason = "time_limit"
            raise _BudgetExpired

    def decode(self, keys: np.ndarray) -> _DecodedCandidate:
        """Decode a candidate while retaining an independent key snapshot.

        Args:
            keys (np.ndarray): Candidate chromosome.

        Returns:
            _DecodedCandidate: Keys paired with the original decoded payload.

        Raises:
            _BudgetExpired: If work must stop before decoding.
        """
        self._check()
        snapshot = np.asarray(keys, dtype=float).copy()
        return _DecodedCandidate(snapshot, self.decoder(snapshot.copy()))

    def evaluate(self, candidate: _DecodedCandidate) -> float:
        """Evaluate the original payload and retain the best completed result.

        Args:
            candidate (_DecodedCandidate): Decoded payload and originating keys.

        Returns:
            float: Finite minimization objective.

        Raises:
            _BudgetExpired: If work must stop before the objective call.
            ValueError: If the objective returns a nonfinite value.
        """
        self._check()
        value = float(self.cost(candidate.payload))
        if not math.isfinite(value):
            raise ValueError("Objective callbacks must return finite costs.")
        self.n_evaluations += 1
        if self.best is None or value < self.best[1]:
            self.best = (candidate.keys, value)
        return value

    def solve(
        self,
        algorithm: MetaheuristicBase,
        duration: float,
        *,
        deadline: float | None = None,
        cancelled: threading.Event | None = None,
        random_state: int | None = None,
    ) -> RunResult:
        """Execute an algorithm using budget-aware callbacks and preserve its incumbent.

        Args:
            algorithm (MetaheuristicBase): Fresh algorithm to execute.
            duration (float): Positive search seconds passed to its solve method.
            deadline (float | None): Common absolute deadline, or duration from now.
            cancelled (threading.Event | None): Shared peer-failure signal.
            random_state (int | None): Actual assigned seed for this search report.

        Returns:
            RunResult: Extras, best evaluated keys and objective; an unevaluated
                cancelled peer has empty keys and infinite cost.

        Raises:
            Exception: Original decoder, objective or algorithm failure is propagated.
        """
        started = time.perf_counter()
        self.best = None
        self.n_evaluations = 0
        self.metadata = None
        self._stop_reason = "completed"
        self.deadline = started + duration if deadline is None else deadline
        self.cancelled = cancelled
        original_decoder, original_cost = algorithm.decoder, algorithm.cost
        original_cancelled = algorithm._cancelled
        algorithm.decoder, algorithm.cost = self.decode, self.evaluate
        algorithm._cancelled = cancelled
        try:
            try:
                result = algorithm.solve(duration)
            except _BudgetExpired:
                result = ([], [], math.inf)
            if self.best is not None and self.best[1] < result[2]:
                result = (result[0], self.best[0].tolist(), self.best[1])
            finished = time.perf_counter()
            reason = self._stop_reason
            if reason == "completed":
                if cancelled is not None and cancelled.is_set():
                    reason = "cancelled"
                elif finished >= self.deadline:
                    reason = "time_limit"
            self.metadata = replace(
                getattr(algorithm, "_search_metadata", None)
                or SearchMetadata(algorithm=algorithm.name),
                random_state=random_state,
                n_evaluations=self.n_evaluations,
                stop_reason=reason,
                time_limit=duration,
                elapsed_seconds=finished - started,
            )
            return result
        finally:
            algorithm.decoder, algorithm.cost = original_decoder, original_cost
            algorithm._cancelled = original_cancelled
