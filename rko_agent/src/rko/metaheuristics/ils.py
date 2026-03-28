"""ILS metaheuristic (skeleton).

Objective:
- Define the base structure for Iterated Local Search.

Technical approach:
- Expose initialization and execution contracts for concrete implementations.

Flow (pseudocode):
1. Initialize instance.
2. Run `solve` with a time limit.
3. Return the best solution when implemented.

Important criteria:
- Compatibility with the base-class contract.

Inputs/Outputs:
- Input: solution pool and time limit.
- Output: tuple with extra data, vector, and cost.
"""

from .base import MetaheuristicBase


class ILS(MetaheuristicBase):
    """Represents the skeleton of the ILS metaheuristic.

    Responsibilities:
    - Define construction signature.
    - Reserve extension entry point for search.
    """

    def __init__(self, solution_pool: object, name: str = "ILS") -> None:
        """Initializes a metaheuristic ILS.

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
        """Runs ILS for up to `limit_time` seconds.

        Args:
          limit_time: Time limit in seconds.

        Raises:
          NotImplementedError: When the search flow has not been implemented yet.
          ValueError: When required by external domain validation.
        """
        self._start_timer()
        raise NotImplementedError("ILS.solve has not been implemented yet.")
