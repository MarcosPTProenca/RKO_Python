# Documentation

RKO is a random-key **minimization** library. Implement a decoder and an objective
once; use them with any built-in algorithm or a cooperating portfolio. It is a
development library, not a claim of release readiness or C++ equivalence.

## Learn

1. [Getting started](getting-started.md): solve your first problem with one algorithm.
2. [Problem adapters](problem-adapters.md): encode solutions, constraints and maximization.
3. [Parameter reference](parameters.md): choose fixed or adaptive settings and understand each knob.

## Apply and extend

- [Standalone algorithms](standalone.md): all eleven classes, tuning and result metadata.
- [Extension guide](extending.md): replace local search/shaking or implement a new algorithm.
- [Portfolio and execution API](usage.md): sharing elites, processes, budgets and reproducibility.
- [Terminal usage](running.md): the supplied Knapsack adapter and custom TOML files.
- [Contributing](../CONTRIBUTING.md): development setup, tests and release gates.

## Investigate

- [Limitations](status.md) and [C++ compatibility](cpp-compatibility.md).
- [Measurements](../benchmarks/README.md), not general performance promises.
- Algorithm module docstrings describe technical strategy, pseudocode and stopping
  criteria. Read `help(SA.solve_one)` for the standalone call contract and
  `help(SA.__init__)` for the advanced constructor contract.

Guides use `adaptation="fixed"` and `adaptation="adaptive"` rather than legacy
`control=0` / `control=1`. These names describe parameter selection, **not** network
connectivity, model training, execution backend, or a different objective.
