"""Metaheuristic MultiStart (skeleton).

Objective:
- Define estrutura base para multiple starts independent.

Technical approach:
- Provide signature padrão para inicializaction e solve.

Flow (pseudocode):
1. Initializesr instance com pool.
2. Run solve por time limit.
3. Return best resultado quando implementado.

Important criteria:
- Garantir contract of return tipado.

Inputs/Outputs:
- Input: solution pool e time limit.
- Output: tupla com dados extras, vetor e cost.
"""

from .base import MetaheuristicBase


class MultiStart(MetaheuristicBase):
    """Represents the skeleton of the metaheuristic MultiStart.

    Responsabilidades:
    - Define signature of inicializaction.
    - Reserve implementation of rotina of search.
    """

    def __init__(self, solution_pool: object, name: str = "MultiStart") -> None:
        """Initializes a metaheuristic MultiStart.

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
        """Runs MultiStart for up to `limit_time` seconds.

        Args:
          limit_time: Limite of tempo em seconds.

        Raises:
          NotImplementedError: When the search flow has not been implemented yet.
          ValueError: When required by external domain validation.
        """
        self._start_timer()
        raise NotImplementedError("MultiStart.solve has not been implemented yet.")
