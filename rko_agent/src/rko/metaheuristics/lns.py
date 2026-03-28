"""Metaheuristic LNS (skeleton).

Objective:
- Define estrutura base of Large Neighborhood Search.

Technical approach:
- Provide contract para inicializaction e solve com tipagem consistent.

Flow (pseudocode):
1. Initializesr com pool e nome.
2. Run rotina solve no time limit.
3. Return best solution quando implementado.

Important criteria:
- Compatibilidade com contract of MetaheuristicBase.

Inputs/Outputs:
- Input: solution pool e time limit.
- Output: tupla com dados extras, vetor e cost.
"""

from .base import MetaheuristicBase


class LNS(MetaheuristicBase):
    """Represents the skeleton of the metaheuristic LNS.

    Responsabilidades:
    - Define signature of inicializaction.
    - Reserve implementation of rotina of search.
    """

    def __init__(self, solution_pool: object, name: str = "LNS") -> None:
        """Initializes a metaheuristic LNS.

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
        """Runs LNS for up to `limit_time` seconds.

        Args:
          limit_time: Limite of tempo em seconds.

        Raises:
          NotImplementedError: When the search flow has not been implemented yet.
          ValueError: When required by external domain validation.
        """
        self._start_timer()
        raise NotImplementedError("LNS.solve has not been implemented yet.")
