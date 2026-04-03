"""Implicit Path Relinking (IPR) for random-key optimisation.

Objective:
- Explore the solution space between pairs of elite pool solutions by
  iteratively moving blocks of genes from one solution toward another.

Technical approach:
- At each iteration, two solutions are drawn at random from the shared pool.
- The key vector is divided into fixed-size blocks (10 % of chromosme length).
- A greedy block-relinking procedure selects, one block at a time, the most
  improving swap from the current position toward the guide solution.
- The best solution encountered along the explored path is inserted back into
  the pool.
- No Q-Learning or auxiliary parameters are required; all decisions are
  deterministic once the pair of solutions is chosen.

Flow (pseudocode):
1. Wait until pool contains at least two solutions.
2. Draw ``atual`` and ``guia`` randomly from the pool.
3. Divide the chromosome into num_blocks = n // block_size blocks.
4. Repeat num_blocks-1 times:
   a. For every unfixed block i, evaluate swapping those genes to guia.
   b. Fix the block with the best improvement; update s_current.
5. Insert the best solution seen along the path into the pool.

Important criteria:
- Block size is always at least 1 gene; num_blocks = n // block_size.
- Only num_blocks-1 swaps are performed (the last block is implicitly the
  guide solution and is left out to preserve path diversity).
- The routine repeats continuously until the time budget is exhausted,
  drawing a fresh pair from the pool at each IPR call.

Inputs/Outputs:
- Input: pool, decoder, cost function, solution size.
- Output: tuple with empty extras, best key vector found during IPR calls,
  and its cost.
"""

from __future__ import annotations

import math
import numpy as np
import random
from .base import MetaheuristicBase
from collections.abc import Callable
from typing import Any
from typing import override


class IPR(MetaheuristicBase):
    """Implicit Path Relinking between pool elite solutions.

    Responsibilities:
    - Draw pairs of solutions from the shared pool.
    - Greedily relink them block by block toward the guide solution.
    - Insert the best path solution back into the pool.

    Attributes:
      decoder (Callable[[np.ndarray], Any]): Solution decoding function.
      cost (Callable[[Any], float]): Objective function over decoded solutions.
      tam_solution (int): Length of the random-key vector.
    """

    def __init__(
        self,
        solution_pool: object,
        decoder: Callable[[np.ndarray], Any],
        cost: Callable[[Any], float],
        tam_solution: int,
        *,
        name: str = "IPR",
    ) -> None:
        """Initialises the IPR metaheuristic.

        Args:
          solution_pool: Shared pool for exchanging elite solutions (needs >= 2).
          decoder: Function that converts a key vector into a problem solution.
          cost: Objective function applied to a decoded solution.
          tam_solution: Length of the random-key vector.
          name: Human-readable identifier for logging.

        Returns:
          None: Initialises instance state.

        Raises:
          ValueError: When required by external domain validation.
        """
        super().__init__(solution_pool=solution_pool, name=name)
        self.decoder = decoder
        self.cost = cost
        self.tam_solution = tam_solution

    def _relink(
        self,
        atual_keys: np.ndarray,
        guia_keys: np.ndarray,
    ) -> tuple[np.ndarray, float]:
        """Perform block-by-block path relinking from atual toward guia.

        Args:
          atual_keys: Starting solution chromosome.
          guia_keys: Guide solution chromosome.

        Returns:
          Tuple of (best chromosome found along the path, its cost).
        """
        n = self.tam_solution
        block_size = max(1, int(n * 0.10))
        num_blocks = max(2, n // block_size)
        fixed_block = [False] * num_blocks

        s_current = atual_keys.copy()
        best_path_keys = s_current.copy()
        best_path_cost: float = self.cost(self.decoder(s_current))

        for _ in range(num_blocks - 1):
            best_iter_cost = math.inf
            best_iter_keys: np.ndarray | None = None
            best_block = -1

            for b in range(num_blocks):
                if fixed_block[b]:
                    continue
                s_viz = s_current.copy()
                start = b * block_size
                end = min((b + 1) * block_size, n)
                for k in range(start, end):
                    s_viz[k] = guia_keys[k]
                viz_cost = self.cost(self.decoder(s_viz))
                if viz_cost < best_iter_cost:
                    best_iter_cost = viz_cost
                    best_iter_keys = s_viz.copy()
                    best_block = b

            if best_iter_cost < best_path_cost and best_iter_keys is not None:
                best_path_cost = best_iter_cost
                best_path_keys = best_iter_keys.copy()

            if best_block >= 0 and best_iter_keys is not None:
                s_current = best_iter_keys.copy()
                fixed_block[best_block] = True

        return best_path_keys, best_path_cost

    @override
    def solve(self, limit_time: float) -> tuple[list[object], list[float], float]:
        """Runs IPR continuously until the time budget is exhausted.

        Args:
          limit_time: Maximum wall-clock time in seconds.

        Returns:
          Tuple of (empty extras, best key vector as list, best cost).
        """
        self._start_timer()

        best_keys: np.ndarray = np.random.random(self.tam_solution)
        best_cost: float = self.cost(self.decoder(best_keys))

        while not self.time_limit_reached(limit_time):
            pool_size: int = getattr(self.solution_pool, "size", 0)
            if pool_size < 2:
                continue

            elite = self.solution_pool.get_elite(pool_size)
            indices = list(range(len(elite)))
            k1, k2 = random.sample(indices, 2)
            atual_keys = np.array(elite[k1][1], dtype=float)
            guia_keys = np.array(elite[k2][1], dtype=float)

            path_keys, path_cost = self._relink(atual_keys, guia_keys)
            self.solution_pool.insert((path_cost, path_keys.tolist()), self.name)

            if path_cost < best_cost:
                best_cost = path_cost
                best_keys = path_keys.copy()

        return [], best_keys.tolist(), best_cost
