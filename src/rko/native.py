"""Built-in problems evaluated by the compiled engine without the interpreter.

Objective:
- Offer problem definitions whose decoder and objective run entirely in Rust, so
  native portfolios scale across threads instead of serializing on the GIL.

Technical approach:
- Re-export the extension's problem classes under stable public names.

Flow (pseudocode):
1. Import this module only when the compiled extension is installed.
2. Build a problem and pass it to `RKO.native`.

Important criteria:
- Importing this module fails clearly when the extension is unavailable.

Inputs/Outputs:
- Input: problem data such as profits, weights and capacity.
- Output: native problem objects accepted by `RKO.native`.
"""

from ._native import KnapsackProblem as Knapsack

__all__ = ["Knapsack"]
