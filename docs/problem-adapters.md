# Implement a problem adapter

[Documentation index](index.md) · [Getting started](getting-started.md)

## Contract

1. Choose `n_variables`: the chromosome length, not necessarily the number of
   domain decisions after decoding.
2. Implement `decoder(keys: np.ndarray) -> YourSolution`. The library supplies a
   detached, one-dimensional random-key vector. Library-generated keys are in
   `[0, 1)`; historical/custom operators may retain endpoint one.
3. Implement `cost(solution: YourSolution) -> float`. Return a finite scalar to
   **minimize**, including constraint handling where necessary.
4. Call any built-in class's `solve_one` or configure `RKO` with the same callbacks.
5. Decode `np.asarray(result.keys)` and independently verify your constraints.

The library neither reads your file format nor infers feasibility from a scalar.
A completed finite evaluation is not necessarily a feasible domain solution.

## Common encodings

| Domain representation | Typical decoder | Caution |
| --- | --- | --- |
| Permutation | `np.argsort(keys, kind="stable")` | Define deterministic tie handling |
| Binary decisions | `keys > 0.5` | Thresholding does not enforce a capacity constraint |
| Bounded continuous variables | `lower + (upper - lower) * keys` | Validate bounds and shapes when loading data |
| Structured assignment | Rank keys, then construct feasible choices | Decoder work is part of search cost |

For maximization, minimize `-profit(solution)`. Convert the reported cost back
with `profit = -result.cost` **only if** the objective contains no penalties or
other terms. For constrained problems, a feasible decoder/repair is often easier
to interpret than an arbitrary penalty. If using penalties, choose a scale justified
by objective bounds and always report feasibility separately.

## Load data once

Keep instance loading outside the search. Use a callable object or
`functools.partial` carrying the validated data rather than reading disk on every
objective evaluation. Do not print on every callback; repeated I/O can dominate
optimization. Avoid retaining every evaluated candidate unless you need that data.

For process mode, callbacks and their data must be pickleable and importable.
Module-level definitions plus `if __name__ == "__main__":` are the safe script
pattern. Serial `solve_one` does not require callback serialization and can be used
with local functions during exploration. See [process callbacks](usage.md#spawn-compatible-callbacks).

## Failures, randomness and stopping

Raise an informative exception for malformed input; do not hide decoder bugs by
returning a dummy objective. Nonfinite costs are rejected. Large finite penalties
remain valid numeric scores, not proof that the domain constraints were satisfied.

Prefer deterministic callbacks. Own an explicit generator for stochastic callbacks:
`random_state` controls **library** draws, not random calls inside your code.
No solver can interrupt a callback while it is executing. Keep callbacks bounded;
the library checks the deadline between callbacks. A reported best solution is an
observation within that execution model, not a global-optimality certificate.
