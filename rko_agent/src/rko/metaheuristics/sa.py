"""Metaheuristic Simulated Annealing para random keys.

Objective:
- Minimize a objective function por stochastic search com critério of acceptance térmico.

Technical approach:
- Run ciclos of temperature com perturbation random e acceptance of piores movimentos.
- Apply refinamento local por Nelder-Mead durante o cooling.

Flow (pseudocode):
1. Initializesr solution random e cost current.
2. Iterate neighbors com rule of Metropolis e reduction of temperature.
3. Apply search local e maintain best solution global.

Important criteria:
- Paraof por time limit.
- Reannealing com fraction of temperature inicial.

Inputs/Outputs:
- Input: solution pool, callbacks of decoder/cost e hiperparameters of SA.
- Output: best random-key vector e best value objective.
"""

from __future__ import annotations

import math
import numpy as np
import random
from ..components.local_search.nelder_mead_ls import nelder_mead_search
from ..components.shaking.random import shake
from ..components.validation import ParameterValidator
from .base import MetaheuristicBase
from collections.abc import Callable
from typing import override


class SA(MetaheuristicBase):
    """Simulated Annealing (SA) over a random-key vector.

    Faithfully mirrors ``SA.h`` from the C++ RKO reference implementation.

    Three-level loop structure:

    * **Outer loop** — runs until the time budget is exhausted. After the first
     full cooling schedule the algorithm *reaneals* (restarts from
     ``0.3 * t0``) so the search never stalls.
    * **Temperature loop** — descends from *T* down to 0.0001 using geometric
     cooling ``T ← alpha * T`` at each step.
    * **Metropolis loop** — evaluates *sa_max* neighbours per temperature level
     via :func:`~rko.components.shaking.random.shake`. Improvements are
     always accepted; worsening moves are accepted with probability
     ``exp(−Δ / T)``.

    After every temperature step a Nelder-Mead local search is applied to the
    current solution (delegated to
    :func:`~rko.components.local_search.nelder_mead_ls.nelder_mead_search`).

    Example (in ``rko_main.py``)::

      sa = SA(
        solution_pool=pool,
        decoder=my_decoder,
        cost=my_cost,
        tam_solution=50,
        sa_max=50,
        t0=10_000.0,
        alpha=0.99,
        beta_min=0.05,
        beta_max=0.25,
      )
      _, best_keys, best_cost = sa.solve(limit_time=60.0)
    """

    def __init__(
        self,
        solution_pool: object,
        decoder: Callable[[np.ndarray], object],
        cost: Callable[[object], float],
        tam_solution: int,
        *,
        sa_max: int = 50,
        t0: float = 10_000.0,
        alpha: float = 0.99,
        beta_min: float = 0.05,
        beta_max: float = 0.25,
        name: str = "SA",
    ) -> None:
        """Initializes os parameters of Simulated Annealing.

        Args:
          solution_pool: Shared pool for exchanging elite solutions.
          decoder: Function que converte key vector em solution of problem.
          cost: Function objective aplicaof sobre a solution decodificada.
          tam_solution: Tamanho of random-key vector.
          sa_max: Number of evaluations por level of temperature.
          t0: Temperatura inicial.
          alpha: Rate geometric of cooling.
          beta_min: Intensity mínima of perturbation.
          beta_max: Intensity máxima of perturbation.
          name: Name identifier of the metaheuristic.

        Returns:
          None: Initializes o state internal of the metaheuristic.

        Raises:
          ValueError: When required by external domain validation.
        """
        super().__init__(solution_pool=solution_pool, name=name)
        self.tam_solution = tam_solution
        self.decoder = decoder
        self.cost = cost
        self.sa_max = sa_max
        self.t0 = t0
        self.alpha = alpha
        self.beta_min = beta_min
        self.beta_max = beta_max
        self._state_filter = ParameterValidator.check(self, "SA")

    @override
    def solve(self, limit_time: float) -> tuple[list[object], list[float], float]:
        """Run Simulated Annealing for at most *limit_time* seconds.

        Args:
          limit_time (float): Maximum time of execution em seconds.

        Returns:
          tuple[list[object], list[float], float]: Dados extras, best vetor e best cost.

        Raises:
          ValueError: When required by external domain validation.
        """
        self._start_timer()
        n = self.tam_solution
        keys: np.ndarray = np.random.random(n)
        current_cost: float = self.cost(self.decoder(keys))

        best_keys: np.ndarray = keys.copy()
        best_cost: float = current_cost
        self.solution_pool.insert((best_cost, best_keys.tolist()), self.name)

        reannealing: bool = False
        while not self.time_limit_reached(limit_time):
            T: float = self.t0 if not reannealing else self.t0 * 0.3
            while T > 0.0001 and not self.time_limit_reached(limit_time):
                best_ofv_level: float = math.inf
                iter_t: int = 0
                while iter_t < self.sa_max and not self.time_limit_reached(limit_time):
                    iter_t += 1
                    viz_keys: np.ndarray = shake(keys.copy(), self.beta_min, self.beta_max)
                    viz_cost: float = self.cost(self.decoder(viz_keys))
                    if viz_cost < best_ofv_level:
                        best_ofv_level = viz_cost

                    delta: float = viz_cost - current_cost

                    if delta < 0:
                        keys = viz_keys
                        current_cost = viz_cost

                        if current_cost < best_cost:
                            best_cost = current_cost
                            best_keys = keys.copy()
                            self.solution_pool.insert((best_cost, best_keys.tolist()), self.name)
                    else:
                        if random.random() < math.exp(-delta / T):
                            keys = viz_keys
                            current_cost = viz_cost
                T *= self.alpha
                ls_keys, ls_cost = nelder_mead_search(
                    keys.copy(), self.decoder, self.cost, pool=self.solution_pool
                )
                if ls_cost < best_cost:
                    best_cost = ls_cost
                    best_keys = ls_keys.copy()
                    keys = ls_keys
                    current_cost = ls_cost
                    self.solution_pool.insert((best_cost, best_keys.tolist()), self.name)
            reannealing = True

        return [], best_keys.tolist(), best_cost
