"""Nelder-Mead local search for random-key vectors.

Objective:
- Refine continuous random-key solutions using simplex operations in key space.

Technical approach:
- Maintain a three-point simplex with objective evaluation over decoded solutions.
- Apply reflection, expansion, contraction, and shrink steps until stabilization.

Flow (pseudocode):
1. Initialize the simplex and an auxiliary centroid point.
2. Iterate Nelder-Mead operators according to cost ordering.
3. Return the best point found or the original solution.

Important criteria:
- Reset the stagnation counter when improvement occurs.
- Use a minimum iteration limit based on problem dimension.

Inputs/Outputs:
- Input: key vector, decoder, and objective function.
- Output: best random-key vector and associated cost.
"""

import math
import numpy as np
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class _Point:
    """Represents a simplex point with key vector and cost.

    Attributes:
        keys (np.ndarray): Point key vector.
        ofv (float): Objective function value at the point.
    """

    keys: np.ndarray
    ofv: float


def _evaluate(
    keys: np.ndarray, decoder: Callable[[np.ndarray], Any], cost: Callable[[Any], float]
) -> float:
    """Evaluates the cost of a decoded random-key vector.

    Args:
        keys (np.ndarray): Key vector to evaluate.
        decoder (Callable[[np.ndarray], Any]): Solution decoding function.
        cost (Callable[[Any], float]): Objective function over the decoded solution.

    Returns:
        float: Computed objective function value.

    Raises:
        ValueError: When required by external domain validation.
    """
    return cost(decoder(keys))


def _blend(a: np.ndarray, b: np.ndarray, factor: float) -> np.ndarray:
    """Combines two vectors to generate a simplex transformation candidate.

    Args:
        a (np.ndarray): First base vector.
        b (np.ndarray): Second base vector.
        factor (float): Factor defining normal or complementary mode.

    Returns:
        np.ndarray: Combined candidate vector.

    Raises:
        ValueError: When required by external domain validation.
    """
    n = len(a)
    out = np.empty(n, dtype=float)

    for j in range(n):
        if random.random() < 0.02:
            out[j] = random.random()
        else:
            if random.random() < 0.5:
                out[j] = a[j]
            else:
                if factor == -1:
                    out[j] = min(max(1.0 - b[j], 0.0), 0.9999999)
                else:
                    out[j] = b[j]

    return out


def nelder_mead_search(
    keys: np.ndarray,
    decoder: Callable[[np.ndarray], Any],
    cost: Callable[[Any], float],
) -> tuple[np.ndarray, float]:
    """Runs Nelder-Mead local search on a random-key vector.

    Args:
        keys (np.ndarray): Key vector of the initial solution.
        decoder (Callable[[np.ndarray], Any]): Solution decoding function.
        cost (Callable[[Any], float]): Objective function over the decoded solution.

    Returns:
        tuple[np.ndarray, float]: Best found vector and corresponding cost.

    Raises:
        ValueError: When required by external domain validation.
    """
    n = len(keys)
    if n == 0:
        return keys, _evaluate(keys, decoder, cost)

    x1_origin = keys.copy()
    x1 = _Point(keys.copy(), _evaluate(keys, decoder, cost))

    x2_keys = np.random.random(n)
    x3_keys = np.random.random(n)

    x2 = _Point(x2_keys, _evaluate(x2_keys, decoder, cost))
    x3 = _Point(x3_keys, _evaluate(x3_keys, decoder, cost))

    simplex = sorted([x1, x2, x3], key=lambda p: p.ofv)
    x1, x2, x3 = simplex[0], simplex[1], simplex[2]

    x0_keys = _blend(x1.keys, x2.keys, 1)
    x0 = _Point(x0_keys, _evaluate(x0_keys, decoder, cost))

    x_best = min([x1, x2, x3, x0], key=lambda p: p.ofv)
    improved = x0.ofv < x1.ofv
    improved_x1 = 1 if x_best.ofv < x1.ofv else 0

    iter_count = 1
    max_iter = int(n * math.exp(-2.0))
    if max_iter < 1:
        max_iter = 1

    while iter_count <= max_iter:
        shrink = False

        xr_keys = _blend(x0.keys, x3.keys, -1)
        xr = _Point(xr_keys, _evaluate(xr_keys, decoder, cost))
        if xr.ofv < x_best.ofv:
            x_best = xr
            improved = True
            improved_x1 = 1

        if xr.ofv < x1.ofv:
            xe_keys = _blend(xr.keys, x0.keys, -1)
            xe = _Point(xe_keys, _evaluate(xe_keys, decoder, cost))
            if xe.ofv < x_best.ofv:
                x_best = xe
                improved = True
                improved_x1 = 1

            if xe.ofv < xr.ofv:
                x3 = xe
            else:
                x3 = xr

        else:
            if xr.ofv < x2.ofv:
                x3 = xr
            else:
                if xr.ofv < x3.ofv:
                    xc_keys = _blend(xr.keys, x0.keys, 1)
                    xc = _Point(xc_keys, _evaluate(xc_keys, decoder, cost))
                    if xc.ofv < x_best.ofv:
                        x_best = xc
                        improved = True
                        improved_x1 = 1

                    if xc.ofv < xr.ofv:
                        x3 = xc
                    else:
                        shrink = True
                else:
                    xc_keys = _blend(x0.keys, x3.keys, 1)
                    xc = _Point(xc_keys, _evaluate(xc_keys, decoder, cost))
                    if xc.ofv < x_best.ofv:
                        x_best = xc
                        improved = True
                        improved_x1 = 1

                    if xc.ofv < x3.ofv:
                        x3 = xc
                    else:
                        shrink = True

        if shrink:
            x2_keys = _blend(x1.keys, x2.keys, 1)
            x2 = _Point(x2_keys, _evaluate(x2_keys, decoder, cost))
            if x2.ofv < x_best.ofv:
                x_best = x2
                improved = True
                improved_x1 = 1

            x3_keys = _blend(x1.keys, x3.keys, 1)
            x3 = _Point(x3_keys, _evaluate(x3_keys, decoder, cost))
            if x3.ofv < x_best.ofv:
                x_best = x3
                improved = True
                improved_x1 = 1

        simplex = sorted([x1, x2, x3], key=lambda p: p.ofv)
        x1, x2, x3 = simplex[0], simplex[1], simplex[2]

        x0_keys = _blend(x1.keys, x2.keys, 1)
        x0 = _Point(x0_keys, _evaluate(x0_keys, decoder, cost))
        if x0.ofv < x_best.ofv:
            x_best = x0
            improved = True
            improved_x1 = 1

        if improved:
            improved = False
            iter_count = 0
        else:
            iter_count += 1

    if improved_x1 == 1:
        return x_best.keys.copy(), x_best.ofv
    origin_cost = _evaluate(x1_origin, decoder, cost)
    return x1_origin, origin_cost
