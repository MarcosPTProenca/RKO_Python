"""Public package interface for the RKO Python implementation.

Objective:
- Expose stable package-level imports for the RKO orchestration entrypoints.

Technical approach:
- Mark `src/rko` as a regular Python package for tooling compatibility.
- Re-export the main `run` entrypoint from `rko_main`.

Flow (pseudocode):
1. Import `run` from `rko_main`.
2. Expose it through `__all__`.

Important criteria:
- Keep package API minimal and explicit.

Inputs/Outputs:
- Input: internal module symbols.
- Output: package-level exports.
"""

from .rko_main import run

__all__ = ["run"]
