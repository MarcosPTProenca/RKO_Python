"""Metaheuristic VNS (skeleton).

Objective:
- Define estrutura base para Variable Neighborhood Search.

Technical approach:
- Expose contract of construction e solve para implementation concrete.

Flow (pseudocode):
1. Initializesr instance com pool.
2. Run solve no time limit.
3. Return best solution quando implementado.

Important criteria:
- Coerência com contract of classe base.

Inputs/Outputs:
- Input: solution pool e time limit.
- Output: tupla com dados extras, vetor e cost.
"""

from .base import MetaheuristicBase


class VNS(MetaheuristicBase):
    """Represents the skeleton of the metaheuristic VNS.

    Responsabilidades:
    - Define signature of inicializaction.
    - Reserve implementation of neighborhoods variable.
    """

    def __init__(self, solution_pool: object, name: str = "VNS") -> None:
        """Initializes a metaheuristic VNS.

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
        """Runs VNS for up to `limit_time` seconds.

        Args:
          limit_time: Limite of tempo em seconds.

        Raises:
          NotImplementedError: When the search flow has not been implemented yet.
          ValueError: When required by external domain validation.
        """
        self._start_timer()
        raise NotImplementedError("VNS.solve has not been implemented yet.")
