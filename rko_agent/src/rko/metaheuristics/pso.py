"""Metaheuristic PSO (skeleton).

Objective:
- Define estrutura base para Particle Swarm Optimization.

Technical approach:
- Expose inicializaction e solve como pontos of extensão of implementation.

Flow (pseudocode):
1. Initializesr state com pool.
2. Run solve dentro of time limit.
3. Return best solution quando implementado.

Important criteria:
- Preservar compatibilidade com contract of classe base.

Inputs/Outputs:
- Input: solution pool e time limit.
- Output: tupla com dados extras, vetor e cost.
"""

from .base import MetaheuristicBase


class PSO(MetaheuristicBase):
    """Represents the skeleton of the metaheuristic PSO.

    Responsabilidades:
    - Define signature of construction.
    - Reserve implementation of search por enxame.
    """

    def __init__(self, solution_pool: object, name: str = "PSO") -> None:
        """Initializes a metaheuristic PSO.

        Args:
          solution_pool: Shared solution pool.
          name: Name identifier of algorithm.

        Returns:
          None: Initializes instance state.

        Raises:
          ValueError: When required by external domain validation.
        """
        super().__init__(solution_pool=solution_pool, name=name)

    def solve(self, limit_time: float) -> tuple[list[object], list[float], float]:
        """Runs PSO for up to `limit_time` seconds.

        Args:
          limit_time: Limite of tempo em seconds.

        Raises:
          NotImplementedError: When the search flow has not been implemented yet.
          ValueError: When required by external domain validation.
        """
        self._start_timer()
        raise NotImplementedError("PSO.solve has not been implemented yet.")
