"""Greedy Randomised Adaptive Search Procedure (GRASP) for random-key optimisation.

Objective:
- Iteratively construct and improve solutions by combining a greedy-randomised
  constructive phase with random variable neighbourhood descent (RVND).

Technical approach:
- Construction phase: a line-search heuristic with step h explores candidate
  positions and adds the best gene value to the partial solution each iteration.
  The subset size and order are randomised to yield diverse starting points.
- Improvement phase: RVND refines the constructed solution.
- Step h is halved whenever no global improvement is found; it is reset when a
  new best is discovered.  A Metropolis criterion based on elapsed time controls
  acceptance of non-improving moves.
- Q-Learning (control=1) adapts alpha_grasp, initial step hs, and final step he
  online via an epsilon-greedy policy over a discrete state space.

Flow (pseudocode):
1. Build initial random solution, apply RVND, insert into pool.
2. While time budget not exhausted:
   a. [Q-Learning] choose action, retrieve (alpha_grasp, hs, he).
   b. h = hs; while h >= he and time not exhausted:
      i.   Greedy-randomised construction.
      ii.  RVND.
      iii. If improved globally: update best, insert pool, reset h.
      iv.  Else: halve h.
      v.   Metropolis acceptance for local incumbent.
   c. [Q-Learning] reward, update Q-table.

Important criteria:
- Line-search generates ceil(log2(1/h))+1 shift candidates around the current
  gene value at each constructive step.
- Temperature for Metropolis decreases linearly from 100 to 0 over limit_time.

Inputs/Outputs:
- Input: pool, decoder, cost function, solution size, GRASP parameters,
  control mode, optional Q-Learning grid.
- Output: tuple with empty extras, best key vector, and best cost.
"""

from __future__ import annotations

import math
import numpy as np
import random
from ..components.adaptive_control.q_learning import QLearningController
from ..components.local_search.rvnd import rvnd
from ..components.validation import ParameterValidator
from .base import MetaheuristicBase
from collections.abc import Callable
from typing import Any
from typing import override


def _line_search(
    pos: int,
    h: float,
    keys: np.ndarray,
    decoder: Callable[[np.ndarray], Any],
    cost: Callable[[Any], float],
) -> tuple[float, float]:
    """Find the best shifted value for a single gene via step-h line search.

    Args:
      pos: Index of the gene to optimise.
      h: Step size for generating candidate shifts.
      keys: Current key vector (read-only reference).
      decoder: Solution decoder.
      cost: Objective function.

    Returns:
      Tuple of (best gene value, best cost) found by the line search.
    """
    z = keys[pos]
    num_candidates = math.ceil(math.log2(1.0 / h)) + 1 if h > 0 else 1
    best_val = z
    candidate = keys.copy()
    best_c = cost(decoder(candidate))
    for tau in range(1, num_candidates + 1):
        for shift in (tau * h, -tau * h):
            v = z + shift
            if 0.0 <= v < 1.0:
                candidate[pos] = v
                c = cost(decoder(candidate))
                if c < best_c:
                    best_c = c
                    best_val = v
                candidate[pos] = z
    return best_val, best_c


def _constructive(
    n: int,
    h: float,
    keys: np.ndarray,
    decoder: Callable[[np.ndarray], Any],
    cost: Callable[[Any], float],
) -> tuple[np.ndarray, float]:
    """Build a solution via greedy randomised line search.

    Args:
      n: Number of genes.
      h: Line-search step size.
      keys: Starting key vector (modified in-place copy).
      decoder: Solution decoder.
      cost: Objective function.

    Returns:
      Tuple of (constructed key vector, its cost).
    """
    intensity = int(random.uniform(0.3, 0.7) * n)
    unfixed: list[int] = list(range(n))
    s = keys.copy()
    for _ in range(min(intensity, len(unfixed))):
        k_max = max(int(len(unfixed) * 0.1), 2)
        random.shuffle(unfixed)
        chosen = unfixed[:k_max]
        best_pos = chosen[0]
        best_c = math.inf
        best_v = s[best_pos]
        for pos in chosen:
            val, c = _line_search(pos, h, s, decoder, cost)
            if c < best_c:
                best_c = c
                best_pos = pos
                best_v = val
        s[best_pos] = best_v
        unfixed.remove(best_pos)
    return s, cost(decoder(s))


class GRASP(MetaheuristicBase):
    """Greedy Randomised Adaptive Search Procedure over a random-key vector.

    Responsibilities:
    - Alternate construction and RVND improvement phases.
    - Progressively refine the line-search step h to intensify the search.
    - Optionally adapt algorithm parameters via Q-Learning.

    Attributes:
      decoder (Callable[[np.ndarray], Any]): Solution decoding function.
      cost (Callable[[Any], float]): Objective function over decoded solutions.
      tam_solution (int): Length of the random-key vector.
      hs (float): Initial line-search step size.
      he (float): Minimum line-search step size.
      control (int): 0 = offline (fixed hs/he, random alpha); 1 = Q-Learning.
      parameters (list[list[float]]): Discrete Q-Learning parameter grid
        ``[[alpha_grasp values], [hs values], [he values]]``.
    """

    def __init__(
        self,
        solution_pool: object,
        decoder: Callable[[np.ndarray], Any],
        cost: Callable[[Any], float],
        tam_solution: int,
        *,
        hs: float = 0.25,
        he: float = 0.001,
        control: int = 0,
        parameters: list[list[float]] | None = None,
        name: str = "GRASP",
    ) -> None:
        """Initialises the GRASP metaheuristic.

        Args:
          solution_pool: Shared pool for exchanging elite solutions.
          decoder: Function that converts a key vector into a problem solution.
          cost: Objective function applied to a decoded solution.
          tam_solution: Length of the random-key vector.
          hs: Initial line-search step size (offline mode).
          he: Minimum line-search step size (offline mode).
          control: 0 for offline fixed parameters, 1 for Q-Learning.
          parameters: Discrete grid for Q-Learning
            ``[[alpha_grasp...], [hs...], [he...]]``.
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
        self.hs = hs
        self.he = he
        self.control = control
        self.parameters: list[list[float]] = (
            parameters
            if parameters is not None
            else [
                [0.1, 0.3, 0.5, 0.7, 0.9],
                [0.50, 0.25, 0.10],
                [0.01, 0.001, 0.0001],
            ]
        )
        self._state_filter = ParameterValidator.check(self, "GRASP")

    @override
    def solve(self, limit_time: float) -> tuple[list[object], list[float], float]:
        """Runs GRASP for at most *limit_time* seconds.

        Args:
          limit_time: Maximum wall-clock time in seconds.

        Returns:
          Tuple of (empty extras, best key vector as list, best cost).
        """
        self._start_timer()
        n = self.tam_solution

        ql: QLearningController | None = None
        st = 0
        at = 0
        lf = 1.0
        df = 0.8
        if self.control == 1:
            ql = QLearningController(
                self.parameters,
                epsilon_max=1.0,
                epsilon_min=0.1,
                restart_epsilon=1,
                max_time=limit_time,
                state_filter=self._state_filter,
            )
            st = random.randint(0, max(0, len(ql.states) - 1))

        best_keys: np.ndarray = np.random.random(n)
        best_keys, best_cost = rvnd(best_keys, self.decoder, self.cost, pool=self.solution_pool)
        self.solution_pool.insert((best_cost, best_keys.tolist()), self.name)

        s = best_keys.copy()
        s_cost = best_cost

        hs_cur = self.hs
        he_cur = self.he

        if ql is not None and ql.states:
            hs_cur = ql.states[st].par[1]
            he_cur = ql.states[st].par[2]

        while not self.time_limit_reached(limit_time):
            previous_best = best_cost
            if ql is not None:
                epsilon, lf, df, _, _, _ = ql.set_parameters(self.elapsed())
                at = ql.choose_action(st, epsilon)
                i_curr = ql.states[st].Ai[at]
                hs_cur = ql.states[i_curr].par[1]
                he_cur = ql.states[i_curr].par[2]

            h = hs_cur
            improv = 0
            while h >= he_cur and not self.time_limit_reached(limit_time):
                s_line, _ = _constructive(n, h, s.copy(), self.decoder, self.cost)
                s_line, s_line_cost = rvnd(s_line, self.decoder, self.cost, pool=self.solution_pool)

                if s_line_cost < best_cost:
                    best_cost = s_line_cost
                    best_keys = s_line.copy()
                    improv = 1
                    self.solution_pool.insert((best_cost, best_keys.tolist()), self.name)

                if s_line_cost < s_cost:
                    s = s_line.copy()
                    s_cost = s_line_cost
                else:
                    elapsed = self.elapsed()
                    t_metropolis = max(1e-9, 100.0 - 100.0 * (elapsed / limit_time))
                    delta = s_line_cost - s_cost
                    if random.random() < math.exp(-delta / t_metropolis):
                        s = s_line.copy()
                        s_cost = s_line_cost

                if improv:
                    h = hs_cur
                    improv = 0
                else:
                    h /= 2.0

            if ql is not None:
                reward = 1.0 if best_cost < previous_best else ql.relative_reward(best_cost, s_cost)
                st_next = ql.states[st].Ai[at]
                ql.update_q_value(st, at, reward, lf, df)
                st = st_next

        return [], best_keys.tolist(), best_cost
