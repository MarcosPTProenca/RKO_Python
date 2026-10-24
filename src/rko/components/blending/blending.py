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
from ..random_streams import RandomStreams
from ._native_loader import load_blending_kernel
from random import Random
from types import BuiltinMethodType


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
    if parent_a.ndim != 1:
        raise ValueError("parent vectors must be one-dimensional")

    n = len(parent_a)
    mutation = np.zeros(n, dtype=bool)
    use_parent_a = np.zeros(n, dtype=bool)
    mutation_values = np.empty(n, dtype=float)
    draw = RandomStreams.python_rng().random

    for j in range(n):
        if draw() < 0.02:
            mutation[j] = True
            mutation_values[j] = draw()
        else:
            use_parent_a[j] = draw() < 0.5

    child = np.where(use_parent_a, parent_a, parent_b).astype(float, copy=False)
    if factor == -1:
        complemented = np.clip(1.0 - child, 0.0, 0.9999999)
        child[~use_parent_a] = complemented[~use_parent_a]
    child[mutation] = mutation_values[mutation]
    return child


_python_blending = blending
_native_blend = load_blending_kernel()


def _accelerated_blending(
    parent_a: np.ndarray, parent_b: np.ndarray, factor: float = 1.0
) -> np.ndarray:
    """Accelerate supported owned-key work while retaining reference input behavior.

    Args:
        parent_a (np.ndarray): First parent, never modified by the operator.
        parent_b (np.ndarray): Second parent, never modified by the operator.
        factor (float): Existing complementary-mode selector.

    Returns:
        np.ndarray: Independent writable float64 child with the original draw sequence.

    Raises:
        Exception: Original validation, RNG and native failures propagate unchanged.
    """
    supported = (
        _native_blend is not None
        and type(parent_a) is np.ndarray
        and type(parent_b) is np.ndarray
        and parent_a.ndim == parent_b.ndim == 1
        and parent_a.shape == parent_b.shape
        and parent_a.dtype == parent_b.dtype == np.dtype("float64")
        and parent_a.flags.c_contiguous
        and parent_b.flags.c_contiguous
        and parent_a.flags.aligned
        and parent_b.flags.aligned
        and type(factor) in (int, float)
        and factor in (-1, 1)
        and np.isfinite(parent_a).all()
        and np.isfinite(parent_b).all()
    )
    if supported:
        draw = RandomStreams.python_rng().random
        supported = (
            type(draw) is BuiltinMethodType
            and type(draw.__self__) is Random
            and draw.__name__ == "random"
        )
    if not supported:
        return _python_blending(parent_a, parent_b, factor)
    result = np.empty(len(parent_a), dtype=np.float64)
    _native_blend(parent_a, parent_b, result, factor == -1, draw)
    return result


if _native_blend is not None:
    blending = _accelerated_blending
