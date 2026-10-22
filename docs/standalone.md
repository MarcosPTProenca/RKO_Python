# Standalone algorithms

[Documentation index](index.md) · [Parameter reference](parameters.md)

All built-in classes inherit the same `solve_one` class method:

```python
from rko.metaheuristics import PSO

result = PSO.solve_one(
    decode, objective, n_variables=64,
    time_limit=60.0,
    adaptation="fixed",
    hyperparameters={"p_size": 20, "w": 0.6},
    random_state=42,
)
```

Use the callbacks from [getting started](getting-started.md) or your own adapter.
No explicit pool is needed; local search and shaking have built-in defaults.
The method runs one **registered built-in class**, serially, with no shared-pool
prefill. It delegates validation, seeded RNG ownership, callback isolation,
evaluation accounting and stopping to the existing single-member solver lifecycle.
It does not run the default ten-algorithm portfolio.

## Algorithm catalog

| Class imported from `rko.metaheuristics` | Portfolio identifier | Search strategy | Adaptive parameters? |
| --- | --- | --- | --- |
| `SA` | `SA` | Thermal acceptance, geometric cooling, local refinement | Yes |
| `ILS` | `ILS` | Perturb best solution, refine, retain improvements | Yes |
| `VNS` | `VNS` | Increase perturbation neighborhood until improvement | Yes |
| `LNS` | `LNS` | Destroy keys, repair with Farey candidates, thermal acceptance | Yes |
| `BRKGA` | `BRKGA` | Elite-biased crossover, random mutants, local refinement | Yes |
| `BRKGA_CS` | `BRKGA_CS` | Biased crossover with elite community-based refinement | Yes |
| `GeneticAlgorithm` | `GA` | Tournament selection, uniform crossover, mutation | Yes |
| `PSO` | `PSO` | Personal/global best velocity updates and local refinement | Yes |
| `GRASP` | `GRASP` | Randomized coordinate construction, line search and RVND | Yes |
| `IPR` | `IPR` | Relink blocks between elite chromosomes | No |
| `MultiStart` | `MultiStart` | Repeated independent random candidates, no local refinement | No |

There is no universally best choice. MultiStart is a useful random baseline;
compare algorithms under explicit budgets on representative instances.
IPR requires at least two distinct elite chromosomes to relink. Its bounded
standalone startup tries to seed a pair; use `pool_size >= 2`. It does **not** repair
infeasible solutions. Small pools, duplicate decoded solutions and weak initial
candidates can limit it even when execution succeeds.

## Options

| Keyword | Meaning |
| --- | --- |
| `time_limit` | Required positive finite search seconds, not a hard end-to-end timeout |
| `adaptation="fixed"` | Fixed TOML settings; use `"adaptive"` for supported Q-learning searches |
| `hyperparameters=None` | Flat mapping for this algorithm only; partial scalar overrides require fixed mode |
| `random_state=None` | Nonnegative seed or fresh assigned seed; timed trajectories can differ |
| `pool_size=None` | Elite capacity from config, not initial population size |
| `params_dir=None` | Optional directory with complete required TOML files |
| `verbose=False` | Opt-in lifecycle and shared-pool progress |
| `history_limit=0` | Disabled by default; 2–10000 caps incumbent observations per search for [reports](reporting.md) |

`IPR` and `MultiStart` do not adapt, even if adaptive mode is requested. Inspect
`result.searches[0].control` for the effective mode. Unknown parameters and invalid
scalar/joint domains raise `ValueError`; user callback failures propagate.

## Advanced: direct constructors

Existing constructors and `solve()` remain available and unchanged:

```python
from rko.components import SolutionPool
from rko.metaheuristics import SA

algorithm = SA(
    SolutionPool(), decode, objective, tam_solution=10,
    sa_max=100, t0=1000.0, alpha=0.98,
)
extra, keys, cost = algorithm.solve(limit_time=2.0)
```

This low-level interface returns the historical tuple, **not** `RKOResult`.
Its constructor defaults can differ from packaged TOML defaults. It does not
activate the high-level callback budget session, isolated seeded RNG context, or
immutable evaluation reports. Prefer `solve_one` for ordinary standalone use;
use direct constructors when managing pools or replacing operators yourself.

Custom subclasses can implement the low-level `MetaheuristicBase` contract, but
are not automatically registered for `solve_one`. See [extension](extending.md).
