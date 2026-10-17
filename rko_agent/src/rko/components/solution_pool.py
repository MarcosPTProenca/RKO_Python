"""Thread-safe shared elite solution pool for cooperative metaheuristics.

Objective:
- Maintain a fixed-capacity sorted pool of the best solutions found across all
  running metaheuristics.

Technical approach:
- Use a threading lock to protect concurrent reads and writes.
- Keep solutions sorted in ascending order of cost so index 0 is always best.
- Expose an insert method compatible with the duck-typed pool contract already
  used by SA, and a get_elite query required by IPR and pool-aware Nelder-Mead.

Flow (pseudocode):
1. Initialise an empty pool with a fixed capacity.
2. On insert: acquire lock; if pool not full or candidate beats worst, add and
   re-sort; release lock.
3. On get_elite: acquire lock; return detached copies of the top-k entries.

Important criteria:
- Pool capacity is fixed at construction time and never exceeded.
- All public methods are thread-safe.
- Pool entries are (cost, keys_list) tuples, identical to the format used by SA.

Inputs/Outputs:
- Input: capacity at construction; (cost, keys_list) tuples on insert.
- Output: sorted list of top-k entries on get_elite; best entry on best property.
"""

import math
import threading
from typing import Protocol


class ElitePool(Protocol):
    """Describe local and process-shared elite-pool access.

    Responsibilities:
    - Keep search code independent of the pool transport mechanism.

    Attributes:
        size (int): Current number of entries.
        best (tuple[float, list[float]] | None): Best detached entry.
    """

    def insert(self, entry: tuple[float, list[float]], source: str = "") -> None:
        """Insert an objective/key pair.

        Args:
            entry (tuple[float, list[float]]): Candidate objective and vector.
            source (str): Producing algorithm label.

        Raises:
            ValueError: If the candidate is invalid.
        """
        ...

    def get_elite(self, k: int = 1) -> list[tuple[float, list[float]]]:
        """Read detached elite entries.

        Args:
            k (int): Maximum requested count.

        Returns:
            list[tuple[float, list[float]]]: Sorted entries.
        """
        ...

    @property
    def size(self) -> int:
        """Return current occupancy.

        Returns:
            int: Stored entry count.
        """
        ...

    @property
    def best(self) -> tuple[float, list[float]] | None:
        """Return the best entry if populated.

        Returns:
            tuple[float, list[float]] | None: Best entry or None.
        """
        ...


class SolutionPool:
    """Thread-safe fixed-capacity pool of elite solutions.

    Responsibilities:
    - Accept solution insertions from any metaheuristic thread.
    - Provide read access to elite solutions for IPR and pool-aware Nelder-Mead.

    Attributes:
      capacity (int): Maximum number of solutions retained in the pool.
      _pool (list[tuple[float, list[float]]]): Sorted list of (cost, keys) pairs.
      _lock (threading.Lock): Mutual-exclusion guard for all pool mutations.
    """

    def __init__(self, capacity: int = 10) -> None:
        """Initialises an empty solution pool.

        Args:
          capacity: Maximum number of solutions to keep. Must be >= 1.

        Returns:
          None: Initialises internal state.

        Raises:
          ValueError: If capacity is less than 1.
        """
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity: int = capacity
        self._pool: list[tuple[float, list[float]]] = []
        self._lock: threading.Lock = threading.Lock()

    def insert(self, entry: tuple[float, list[float]], source: str = "") -> None:
        """Inserts a candidate solution if it improves the pool.

        The pool keeps at most *capacity* solutions sorted by cost (ascending).
        A new entry is accepted when the pool is not yet full, or when the
        candidate cost is strictly better than the current worst elite.

        Args:
          entry: A ``(cost, keys_list)`` pair describing the candidate.
          source: Human-readable label of the metaheuristic that produced the
            solution (used for traceability only; not stored in the pool).

        Returns:
          None: Mutates the pool in-place when the candidate is accepted.

        Raises:
          ValueError: If the cost or keys are nonfinite, or the vector is empty.
        """
        cost, keys = entry
        keys = list(keys)
        if not math.isfinite(cost) or not keys or not all(math.isfinite(key) for key in keys):
            raise ValueError("Pool entries require a finite cost and a nonempty finite key vector.")
        with self._lock:
            if len(self._pool) < self.capacity or cost < self._pool[-1][0]:
                self._pool.append((cost, list(keys)))
                self._pool.sort(key=lambda t: t[0])
                if len(self._pool) > self.capacity:
                    self._pool.pop()

    def get_elite(self, k: int = 1) -> list[tuple[float, list[float]]]:
        """Returns up to *k* elite solutions sorted by cost (ascending).

        Args:
          k: Number of top solutions to return. Clamped to the current pool
            size if larger.

        Returns:
          list[tuple[float, list[float]]]: Detached copies of the top-k entries
            as ``(cost, keys_list)`` pairs.

        Raises:
          ValueError: When required by external domain validation.
        """
        with self._lock:
            limit = min(k, len(self._pool))
            return [(cost, keys.copy()) for cost, keys in self._pool[:limit]]

    @property
    def size(self) -> int:
        """Number of solutions currently stored in the pool.

        Returns:
          int: Current pool occupancy.
        """
        with self._lock:
            return len(self._pool)

    @property
    def best(self) -> tuple[float, list[float]] | None:
        """Best (lowest-cost) solution in the pool, or None when empty.

        Returns:
          tuple[float, list[float]] | None: The entry with the smallest cost,
            or None if the pool has not been populated yet.
        """
        with self._lock:
            if not self._pool:
                return None
            cost, keys = self._pool[0]
            return cost, keys.copy()

    def __repr__(self) -> str:
        """Return a short debug representation of the pool.

        Returns:
          str: String summarising capacity and current occupancy.
        """
        return f"SolutionPool(capacity={self.capacity}, size={self.size})"
