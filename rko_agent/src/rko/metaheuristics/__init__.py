"""Available metaheuristics in RKO.

Objective:
- Centralize metaheuristic strategy implementations for random-key optimization.

Technical approach:
- Define a common contract through an abstract base class.
- Specialize each algorithm in its own module.

Flow (pseudocode):
1. Initialize solution and parameters.
2. Run the exploration/intensification loop.
3. Report the best solution and cost.

Important criteria:
- Respect the time limit.
- Keep best-solution updates consistent.

Inputs/Outputs:
- Input: solution pool, decoder/cost functions, and hyperparameters.
- Output: best random-key vector found and associated objective value.
"""
