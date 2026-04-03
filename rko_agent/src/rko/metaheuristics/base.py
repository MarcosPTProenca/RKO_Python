"""Foundation of the RKO package metaheuristics."""

from __future__ import annotations

import time
from abc import ABC
from abc import abstractmethod


class MetaheuristicBase(ABC):
    """Abstract base class for all metaheuristic algorithms in the RKO framework.

    Every concrete metaheuristic must inherit from this class and implement
    the :meth:`solve` method, which is the main entry point for the search loop.

    Example::

      class MySA(MetaheuristicBase):
        def solve(self, limit_time: float) -> tuple[list[object], list[float], float]:
          self._start_timer()
          return [], [], 0.0
    """

    def __init__(self, solution_pool: object, name: str = "") -> None:
        """Initialise the metaheuristic.

        Args:
          solution_pool: Shared pool used to exchange elite solutions between
            concurrent metaheuristics.
          name: Human-readable label used in log messages. Defaults to the class name.
        """
        self.solution_pool = solution_pool
        self.name = name or self.__class__.__name__
        self._start_time: float | None = None

    @abstractmethod
    def solve(self, limit_time: float) -> tuple[list[object], list[float], float]:
        """Run the metaheuristic for at most *limit_time* seconds.

        Subclasses must override this method with their search logic.
        Call :meth:`_start_timer` at the beginning and use
        :meth:`time_limit_reached` to check the stopping criterion inside
        the main loop. Whenever a new best solution is found, insert it into
        the shared pool via ``self.pool.insert((cost, keys), self.name, tag)``.

        Args:
          limit_time: Maximum wall-clock time (seconds) allowed for this run.

        Returns:
          A three-element tuple ``(extra, best_keys, best_cost)`` where:

          - ``extra``   – list of supplementary data produced during the run
                   (use an empty list when not needed),
          - ``best_keys`` – random-key vector (``list[float]``) of the best
                   solution found,
          - ``best_cost`` – objective value (``float``) of that solution.
        """

    def elapsed(self) -> float:
        """Return the number of seconds since :meth:`_start_timer` was called.

        Returns 0.0 if the timer has not been started yet.
        """
        if self._start_time is None:
            return 0.0
        return time.perf_counter() - self._start_time

    def time_limit_reached(self, limit_time: float) -> bool:
        """Return ``True`` when :meth:`elapsed` exceeds *limit_time*."""
        return self.elapsed() >= limit_time

    def _start_timer(self) -> None:
        """Record the wall-clock start time.

        Call this once at the very beginning of :meth:`solve` so that
        :meth:`elapsed` and :meth:`time_limit_reached` work correctly.
        """
        self._start_time = time.perf_counter()

    def __repr__(self) -> str:
        """Return a concise debug representation for the metaheuristic."""
        return f"{self.__class__.__name__}(name={self.name!r})"
