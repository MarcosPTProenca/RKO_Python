# RKO Python

[![CI](https://github.com/MarcosPTProenca/RKO_Python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/MarcosPTProenca/RKO_Python/actions/workflows/ci.yml)

A domain-neutral **random-key optimization** library with cooperating
metaheuristics, inspired by [RKO C++ v2](https://github.com/RKO-solver/RKO_Cpp_v2.0).
You provide a decoder and an objective to minimize; RKO searches for good key
vectors without assuming a problem format or solution representation.

> **Development version: `0.3.0.dev0`, not release-ready or a new PyPI release.**
> Matching or exceeding C++ RKO is a performance target, **not an achieved claim**.
> Read the [limitations](docs/status.md), [compatibility](docs/cpp-compatibility.md)
> and [licensing boundaries](NOTICE) before relying on this development line.

## What it provides

- Configurable portfolios: BRKGA, BRKGA-CS, GA, GRASP, ILS, IPR, LNS, MultiStart,
  PSO, SA and VNS; the packaged default selects ten algorithms.
- Serial, thread and process execution with shared elites, owned library RNG
  streams, validated parameters and immutable result metadata.
- Python callbacks for arbitrary problems; **NumPy is the only runtime dependency**.
  No C++ installation, Rust compiler or agent framework is required.

## Install from source

Requires **Python 3.14+** and [uv](https://docs.astral.sh/uv/).
CI currently tests Python 3.14 on Ubuntu and Windows; other combinations are not
certified by that matrix.

```bash
git clone https://github.com/MarcosPTProenca/RKO_Python.git
cd RKO_Python
uv sync --locked --no-dev
```

Run Python scripts with `uv run --locked --no-dev python your_script.py` from
this checkout. For reproducible use, record the Git revision as well as the lock
file. Do not assume a package named `rko` on PyPI exposes this development API.
The previous implementation is preserved at
[`archive/pre-standalone-migration-2026-10-18`](https://github.com/MarcosPTProenca/RKO_Python/tree/archive/pre-standalone-migration-2026-10-18).

## First solve

Save this as `quickstart.py` and run it with the command above:

```python
import numpy as np
from rko.metaheuristics import SA


def decode(keys: np.ndarray) -> np.ndarray:
    """Return the candidate vector as the domain solution.

    Args:
        keys (np.ndarray): Random-key chromosome.

    Returns:
        np.ndarray: Decoded numerical solution.
    """
    return keys


def objective(solution: np.ndarray) -> float:
    """Evaluate the squared Euclidean norm.

    Args:
        solution (np.ndarray): Decoded numerical solution.

    Returns:
        float: Finite objective to minimize.
    """
    return float(np.dot(solution, solution))


result = SA.solve_one(
    decode,
    objective,
    n_variables=20,
    time_limit=1.0,
    adaptation="fixed",
    random_state=42,
)
print(result.cost, result.keys)
print(result.n_evaluations, result.stop_reason, result.elapsed_seconds)
```

The decoder receives a one-dimensional NumPy key vector; the objective must
return a **finite scalar to minimize**. Readers and feasibility logic belong in
your problem adapter. `random_state` owns library draws, not randomness inside
user callbacks; timed runs can still differ because of scheduling.

`SA.solve_one(...)` manages its own pool and runs one serial algorithm. Substitute
any of the eleven [built-in classes](docs/standalone.md#algorithm-catalog) without
changing your callbacks. Use `RKO(...)` for a cooperating portfolio; its default
is a **process portfolio**: use importable callbacks and a guarded entry point
as shown in the [process-safe example](docs/usage.md#spawn-compatible-callbacks).
Serial mode gives **each selected algorithm** its own search allowance; process
startup is excluded, and opted-in pool prefill has a separate allowance. A callback
can overrun its deadline. `time_limit` is not a hard end-to-end timeout.

## Interactive analysis reports

Install the optional reporting dependency with `uv sync --locked --extra reports`.
Then opt into bounded scalar history when solving:

```python
from rko.reporting import OptimizationReport

result = SA.solve_one(
    decode, objective, 20, time_limit=2.0, random_state=42, history_limit=1000,
)
report = OptimizationReport(result)
report.write_html("run.html")
report.write_json("run.json")
```

The HTML embeds Plotly once and works offline with hover, zoom and trace selection.
Reports are generated after search, never by reevaluating callbacks. History is off
by default; compacted curves are labelled approximate. See [interpretation and
privacy boundaries](docs/reporting.md); automatic PDF export is not included.
Core optimization still requires only NumPy.

## Run the supplied Knapsack adapter

```bash
uv run --locked --no-dev rko src/rko/examples/instances/kp50.txt \
  --limit-time 10 --backend process --random-state 42 \
  --output-csv results/kp50.csv
```

The supplied command handles Knapsack, not arbitrary input formats. Its two
bundled instances are correctness fixtures, not competitive-performance evidence.
See [terminal/configuration usage](docs/running.md) for custom instances,
TOMLs, progress output and worker limits.

## Documentation

Start at the [documentation index](docs/index.md): tutorials, how-to guides,
parameter reference and contributor guidance.

| Need | Guide |
| --- | --- |
| Solve your first problem | [Getting started](docs/getting-started.md) |
| Use any one algorithm without managing a pool | [Standalone algorithms](docs/standalone.md) |
| Implement a decoder, constraints and objective | [Problem adapters](docs/problem-adapters.md) |
| Understand fixed/adaptive modes and every search knob | [Parameter reference](docs/parameters.md) |
| Replace operators or implement an algorithm | [Extension guide](docs/extending.md) |
| Generate offline interactive HTML charts and data-only exports | [Analysis reports](docs/reporting.md) |
| Configure the solver, callbacks, hyperparameters and results | [Usage and API guide](docs/usage.md) |
| Choose workers and understand startup/time accounting | [Execution modes](docs/usage.md#execution-modes), [workers](docs/process-workers.md), [startup](docs/driver-initialization.md) |
| Run from the terminal or avoid WSL setup overhead | [Running guide](docs/running.md) |
| Understand the C++ target and Rust feasibility | [Performance and native-backend evaluation](docs/performance.md) |
| Inspect measurements rather than speed claims | [Benchmarks](benchmarks/README.md), [expanded quality study](docs/prefill-expanded-work.md) |
| Check algorithm differences and remaining risks | [C++ compatibility](docs/cpp-compatibility.md), [current limitations](docs/status.md) |
| Develop, test or report an issue | [Contributing](CONTRIBUTING.md) |

`backend` currently selects **process/thread/serial execution**, not a programming
language. **No Rust engine is implemented.** Prefill remains opt-in: broader IPR
benefits include regressions, and large-GRASP short-budget wins can be startup-only.
Neither passing CI nor an isolated kernel speedup establishes C++ parity.

## Project status and attribution

This is the standalone `MarcosPTProenca/RKO_Python` development repository, not an
agent integration. The API and Python requirement break compatibility with the
archived implementation. Wheel/sdist installation and the full test suite are
checked on Ubuntu and Windows; that is not a supported-version or release guarantee.

The existing [LICENSE](LICENSE) is retained. [NOTICE](NOTICE) records imported
history, fixture licensing and ownership review still required before release.
Report reproducible bugs through [GitHub issues](https://github.com/MarcosPTProenca/RKO_Python/issues).
