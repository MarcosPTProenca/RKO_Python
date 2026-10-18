"""Blending recombination operator for random keys.

Objective:
- Generate a child vector from two parent vectors in population-based metaheuristics.

Technical approach:
- Apply uniform gene-by-gene recombination with a small mutation rate.
- Support complementary mode for inversion of the second parent.

Flow (pseudocode):
1. Validate dimensional compatibility of both parents.
2. For each gene, apply mutation or inheritance by probability.
3. Return the generated child vector.

Important criteria:
- Point mutation rate of 2%.
- Preserve valid gene range in [0, 1).

Inputs/Outputs:
- Input: parent_a, parent_b, and blending factor.
- Output: recombined child vector.
"""

import numpy as np
import random


def blending(parent_a: np.ndarray, parent_b: np.ndarray, factor: float = 1.0) -> np.ndarray:
    """Runs uniform recombination between two parent vectors.

    Args:
      parent_a (np.ndarray): First parent vector.
      parent_b (np.ndarray): Second parent vector.
      factor (float): Complementary mode factor when equal to -1.

    Returns:
      np.ndarray: Recombined child vector.

    Raises:
      ValueError: If parent vectors do not have the same shape.
    """
    if parent_a.shape != parent_b.shape:
        raise ValueError("parent_a and parent_b must have the same shape")

    n = len(parent_a)
    child = np.empty(n, dtype=float)

    for j in range(n):
        if random.random() < 0.02:
            child[j] = random.random()
            continue

        if random.random() < 0.5:
            child[j] = parent_a[j]
        else:
            if factor == -1:
                child[j] = min(max(1.0 - float(parent_b[j]), 0.0), 0.9999999)
            else:
                child[j] = parent_b[j]

    return child
