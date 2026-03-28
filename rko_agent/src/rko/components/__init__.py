"""RKO framework components.

Objective:
- Group reusable primitives for local search, shaking, initialization, and adaptive control.

Technical approach:
- Organize functions and classes by responsibility in dedicated submodules.
- Provide a common base for integration with metaheuristics.

Flow (pseudocode):
1. Select a specialized component.
2. Apply it to a random-key solution.
3. Return the updated structure to the caller algorithm.

Important criteria:
- Reuse across different metaheuristics.
- Typed interfaces for composition.

Inputs/Outputs:
- Input: random-key vectors, decoder/cost callbacks, and control parameters.
- Output: transformed solutions, costs, and auxiliary states.
"""
