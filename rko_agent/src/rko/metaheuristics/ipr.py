"""Metaheuristic IPR (skeleton).

Objective:
- Define estrutura base of Path Relinking para integration futura.

Technical approach:
- Expose signature padronizaof of inicializaction e solve.

Flow (pseudocode):
1. Initializesr com pool e nome.
2. Run solve com time limit.
3. Return best solution quando implementado.

Important criteria:
- Manter contract of return comum.

Inputs/Outputs:
- Input: solution pool e time limit.
- Output: tupla com dados extras, vetor e cost.
"""

from .base import MetaheuristicBase


class IPR(MetaheuristicBase):
    """Represents the skeleton of the metaheuristic IPR.

    Responsabilidades:
    - Define signature of inicializaction.
    - Reserve implementation of solve.
    """

    def __init__(self, solution_pool: object, name: str = "IPR") -> None:
        """Initializes a metaheuristic IPR.

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
        """Runs IPR for up to `limit_time` seconds.

        Args:
          limit_time: Limite of tempo em seconds.

        Raises:
          NotImplementedError: When the search flow has not been implemented yet.
          ValueError: When required by external domain validation.
        """
        self._start_timer()
        raise NotImplementedError("IPR.solve has not been implemented yet.")
