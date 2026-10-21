"""Public package interface for the RKO Python implementation.

Objective:
- Expose stable package-level imports for the RKO orchestration entrypoints.

Technical approach:
- Mark `src/rko` as a regular Python package for tooling compatibility.
- Export RKO and RKOResult as the primary class-based API.
- Preserve run as a compatibility adapter.

Flow (pseudocode):
1. Import the solver, result and compatibility adapter.
2. Expose stable symbols through __all__.

Important criteria:
- Keep package API minimal and explicit.

Inputs/Outputs:
- Input: internal module symbols.
- Output: package-level exports.
"""

from .orchestration.types import PoolInitializationMetadata
from .orchestration.types import SearchMetadata
from .rko_main import run
from .solver import RKO
from .solver import RKOResult

__all__ = ["RKO", "RKOResult", "SearchMetadata", "PoolInitializationMetadata", "run"]
