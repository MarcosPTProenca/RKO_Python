"""BRKGA with Community Structure (BRKGA-CS) for random-key optimisation.

Objective:
- Enhance the standard BRKGA by periodically applying a community-structure
  local search that exploits structural correlations within the elite population.

Technical approach:
- Uses Parametric Uniform Crossover with per-gene mutation (pm gate applied
  before the rhoe elite/non-elite inheritance decision).
- After every generation (or every 10 without improvement), the elite
  population is analysed via Pearson correlation:
    * A graph is built where edge (i,j) exists if |corr(elite_i, elite_j)| >= sigma.
    * Label Propagation identifies communities in the graph.
    * One random representative per community is marked as "promising".
    * Promising[0] is refined with RVND; other promising with Nelder-Mead.
    * Non-promising elites undergo a chaotic perturbation: each gene is
      randomised with probability (1 - rhoe).
- Q-Learning (control=1) adapts p, pe, pm, and rhoe online.

Flow (pseudocode):
1. Initialise population, decode, sort.
2. While time budget not exhausted:
   a. [Q-Learning] choose action, update parameters.
   b. Copy elite → offspring with PUX-pm crossover → random mutants.
   c. Perform community-structure search on elite subset.
   d. Sort; update best; insert pool on improvement.
   e. [Q-Learning] reward, update Q-table.

Important criteria:
- Community search is triggered every generation or after 10 stagnant ones.
- sigma defaults to 0.6 (Pearson correlation threshold).
- RVND and Nelder-Mead are the two operators applied during community search.

Inputs/Outputs:
- Input: pool, decoder, cost function, solution size, population and community
  parameters, control mode, optional Q-Learning grid.
- Output: tuple with empty extras, best key vector, and best cost.
"""

from __future__ import annotations

import numpy as np
import random
from ..components.adaptive_control.q_learning import QLearningController
from ..components.local_search.nelder_mead_ls import nelder_mead_search
from ..components.local_search.rvnd import rvnd
from ..components.validation import ParameterValidator
from .base import MetaheuristicBase
from collections.abc import Callable
from typing import Any
from typing import override


def _label_propagation(
    adj: list[list[tuple[int, float]]],
    n_nodes: int,
) -> list[int]:
    """Run Label Propagation for community detection.

    Args:
      adj: Adjacency list where ``adj[i]`` contains ``(j, weight)`` pairs.
      n_nodes: Total number of nodes.

    Returns:
      List of community labels, one per node.
    """
    labels = list(range(n_nodes))
    max_iter = n_nodes * 10
    for _ in range(max_iter):
        order = list(range(n_nodes))
        random.shuffle(order)
        moved = False
        for node in order:
            if not adj[node]:
                continue
            label_weight: dict[int, float] = {}
            for neighbor, weight in adj[node]:
                lbl = labels[neighbor]
                label_weight[lbl] = label_weight.get(lbl, 0.0) + weight
            best_lbl = max(label_weight, key=lambda k: label_weight[k])
            if best_lbl != labels[node]:
                labels[node] = best_lbl
                moved = True
        if not moved:
            break
    return labels


def _ic(
    pop: list[np.ndarray],
    elite_size: int,
    sigma: float,
) -> list[int]:
    """Identify a promising subset of the elite via community structure.

    Builds a Pearson-correlation graph over the elite chromosomes, detects
    communities via Label Propagation, and selects one representative per
    community.

    Args:
      pop: Full population sorted by cost (elite at front).
      elite_size: Number of elite chromosomes.
      sigma: Minimum absolute Pearson correlation to create a graph edge.

    Returns:
      List of indices (into *pop*) of promising representatives, one per
      community.
    """
    elite = [pop[i] for i in range(elite_size)]
    adj: list[list[tuple[int, float]]] = [[] for _ in range(elite_size)]
    for i in range(elite_size):
        for j in range(i + 1, elite_size):
            corr = float(np.corrcoef(elite[i], elite[j])[0, 1])
            if abs(corr) >= sigma:
                weight = abs(corr)
                adj[i].append((j, weight))
                adj[j].append((i, weight))

    labels = _label_propagation(adj, elite_size)

    communities: dict[int, list[int]] = {}
    for idx, lbl in enumerate(labels):
        communities.setdefault(lbl, []).append(idx)

    promising: list[int] = []
    for members in communities.values():
        rep = random.choice(members)
        promising.append(rep)
    return promising


def _chaotic_ind(keys: np.ndarray, rhoe: float) -> np.ndarray:
    """Apply a chaotic perturbation to a chromosome.

    For each gene, replaces it with a uniform random value with probability
    ``1 - rhoe``.

    Args:
      keys: Chromosome to perturb (modified in place).
      rhoe: Probability of *keeping* the current gene value.

    Returns:
      The perturbed chromosome (same object as input).
    """
    for j in range(len(keys)):
        if random.random() > rhoe:
            keys[j] = random.random()
    return keys


class BRKGA_CS(MetaheuristicBase):
    """BRKGA with Community Structure local search.

    Responsibilities:
    - Evolve a population using PUX-with-mutation crossover.
    - Periodically detect elite communities and apply targeted local search.
    - Optionally adapt population parameters via Q-Learning.

    Attributes:
      decoder (Callable[[np.ndarray], Any]): Solution decoding function.
      cost (Callable[[Any], float]): Objective function over decoded solutions.
      tam_solution (int): Length of the random-key vector.
      p (int): Population size.
      pe (float): Elite fraction (0, 1).
      pm (float): Per-gene mutation probability.
      rhoe (float): Elite inheritance probability per gene.
      sigma (float): Pearson correlation threshold for community edges.
      control (int): 0 = offline; 1 = online Q-Learning.
      parameters (list[list[float]]): Discrete Q-Learning grid
        ``[[p], [pe], [pm], [rhoe]]``.
    """

    def __init__(
        self,
        solution_pool: object,
        decoder: Callable[[np.ndarray], Any],
        cost: Callable[[Any], float],
        tam_solution: int,
        *,
        p: int = 50,
        pe: float = 0.15,
        pm: float = 0.10,
        rhoe: float = 0.70,
        sigma: float = 0.60,
        control: int = 0,
        parameters: list[list[float]] | None = None,
        name: str = "BRKGA_CS",
    ) -> None:
        """Initialises the BRKGA-CS metaheuristic.

        Args:
          solution_pool: Shared pool for exchanging elite solutions.
          decoder: Function that converts a key vector into a problem solution.
          cost: Objective function applied to a decoded solution.
          tam_solution: Length of the random-key vector.
          p: Population size (offline mode).
          pe: Elite fraction (offline mode).
          pm: Per-gene mutation probability (offline mode).
          rhoe: Elite gene inheritance probability (offline mode).
          sigma: Minimum Pearson correlation for community graph edges.
          control: 0 for offline fixed parameters, 1 for Q-Learning.
          parameters: Discrete grid ``[[p values], [pe], [pm], [rhoe]]``.
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
        self.p = p
        self.pe = pe
        self.pm = pm
        self.rhoe = rhoe
        self.sigma = sigma
        self.control = control
        self.parameters: list[list[float]] = (
            parameters
            if parameters is not None
            else [
                [30.0, 50.0, 100.0],
                [0.10, 0.15, 0.20],
                [0.05, 0.10, 0.15],
                [0.60, 0.70, 0.80],
            ]
        )
        self._state_filter = ParameterValidator.check(self, "BRKGA_CS")

    def _pux_cs(
        self,
        pop: list[np.ndarray],
        elite_size: int,
        pm: float,
        rhoe: float,
    ) -> np.ndarray:
        """Parametric Uniform Crossover with per-gene mutation.

        For each gene: if ``random() < pm`` produce a random mutant gene;
        otherwise inherit from the elite parent with probability *rhoe*,
        or from the non-elite parent otherwise.

        Args:
          pop: Current population sorted by cost ascending.
          elite_size: Number of elite chromosomes at the front of pop.
          pm: Per-gene mutation probability.
          rhoe: Elite inheritance probability (used when not mutating).

        Returns:
          New offspring chromosome as a 1-D array.
        """
        n = self.tam_solution
        elite_idx = random.randint(0, elite_size - 1)
        non_elite_idx = random.randint(elite_size, len(pop) - 1)
        child = np.empty(n, dtype=float)
        for j in range(n):
            if random.random() < pm:
                child[j] = random.random()
            elif random.random() < rhoe:
                child[j] = pop[elite_idx][j]
            else:
                child[j] = pop[non_elite_idx][j]
        return child

    @override
    def solve(self, limit_time: float) -> tuple[list[object], list[float], float]:
        """Runs BRKGA-CS for at most *limit_time* seconds.

        Args:
          limit_time: Maximum wall-clock time in seconds.

        Returns:
          Tuple of (empty extras, best key vector as list, best cost).
        """
        self._start_timer()
        n = self.tam_solution
        p = self.p
        pe = self.pe
        pm = self.pm
        rhoe = self.rhoe

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
            if ql.states:
                p = int(ql.states[st].par[0])
                pe = ql.states[st].par[1]
                pm = ql.states[st].par[2]
                rhoe = ql.states[st].par[3]

        pop: list[np.ndarray] = [np.random.random(n) for _ in range(p)]
        pop_costs: list[float] = [self.cost(self.decoder(c)) for c in pop]
        order = sorted(range(p), key=lambda i: pop_costs[i])
        pop = [pop[i] for i in order]
        pop_costs = [pop_costs[i] for i in order]

        best_keys: np.ndarray = pop[0].copy()
        best_cost: float = pop_costs[0]
        self.solution_pool.insert((best_cost, best_keys.tolist()), self.name)

        no_improve = 0

        while not self.time_limit_reached(limit_time):
            if ql is not None:
                epsilon, lf, df, _, _, _ = ql.set_parameters(self.elapsed())
                at = ql.choose_action(st, epsilon)
                i_curr = ql.states[st].Ai[at]
                p = int(ql.states[i_curr].par[0])
                pe = ql.states[i_curr].par[1]
                pm = ql.states[i_curr].par[2]
                rhoe = ql.states[i_curr].par[3]
                while len(pop) < p:
                    new_c = np.random.random(n)
                    pop.append(new_c)
                    pop_costs.append(self.cost(self.decoder(new_c)))
                if len(pop) > p:
                    pop = pop[:p]
                    pop_costs = pop_costs[:p]

            elite_size = max(1, int(p * pe))
            mutant_count = max(0, int(p * (1.0 - pe) * 0.1))
            cross_count = p - elite_size - mutant_count

            pop_inter: list[np.ndarray] = list(pop[:elite_size])
            costs_inter: list[float] = list(pop_costs[:elite_size])

            for _ in range(max(0, cross_count)):
                child = self._pux_cs(pop, elite_size, pm, rhoe)
                pop_inter.append(child)
                costs_inter.append(self.cost(self.decoder(child)))

            for _ in range(mutant_count):
                mutant = np.random.random(n)
                pop_inter.append(mutant)
                costs_inter.append(self.cost(self.decoder(mutant)))

            if elite_size > 1 and (no_improve == 0 or no_improve % 10 == 0):
                promising = _ic(pop_inter, elite_size, self.sigma)
                non_promising = [i for i in range(elite_size) if i not in promising]
                for rank, idx in enumerate(promising):
                    if rank == 0:
                        refined, ref_cost = rvnd(
                            pop_inter[idx].copy(),
                            self.decoder,
                            self.cost,
                            pool=self.solution_pool,
                        )
                    else:
                        refined, ref_cost = nelder_mead_search(
                            pop_inter[idx].copy(),
                            self.decoder,
                            self.cost,
                            pool=self.solution_pool,
                        )
                    pop_inter[idx] = refined
                    costs_inter[idx] = ref_cost

                for idx in non_promising:
                    perturbed = _chaotic_ind(pop_inter[idx].copy(), rhoe)
                    pop_inter[idx] = perturbed
                    costs_inter[idx] = self.cost(self.decoder(perturbed))

            order = sorted(range(len(pop_inter)), key=lambda i: costs_inter[i])
            pop = [pop_inter[i] for i in order]
            pop_costs = [costs_inter[i] for i in order]

            improv = 0
            if pop_costs[0] < best_cost:
                best_cost = pop_costs[0]
                best_keys = pop[0].copy()
                improv = 1
                no_improve = 0
                self.solution_pool.insert((best_cost, best_keys.tolist()), self.name)
            else:
                no_improve += 1

            if ql is not None:
                best_off_cost = (
                    min(costs_inter[elite_size:]) if len(costs_inter) > elite_size else best_cost
                )
                reward = 1.0 if improv else ql.relative_reward(best_cost, best_off_cost)
                st_next = ql.states[st].Ai[at]
                ql.update_q_value(st, at, reward, lf, df)
                st = st_next

        return [], best_keys.tolist(), best_cost
