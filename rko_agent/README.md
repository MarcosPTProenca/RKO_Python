# RKO Python

Random-key optimization with cooperating metaheuristics, inspired by RKO C++ v2.
Development lives in `MarcosPTProenca/RKO-Agent`, branch `rko`. This is not yet a
finished replacement release for the separate `RKO_Python` package.

## Class-based solver API

`RKO(decoder, cost, n_variables, ...).solve(time_limit)` minimizes
`cost(decoder(keys))`. The constructor stores configuration without reading files
or starting workers. Each solve builds a fresh portfolio and returns an immutable
`RKOResult` with `keys`, `cost`, `elapsed_seconds`, `backend`, `algorithms` and
`random_state`. `solver.result_` holds the latest successful result and is cleared
before every attempt, including failed solves.

Select `algorithms`, `control` and `pool_size` directly in Python; omitted values
use the packaged TOML defaults. `params_dir` remains available for hyperparameter
files. `rko.run(...)` is only a compatibility adapter retaining the old tuple API.

## Execution modes

- **`backend="process"` (default):** one spawned worker per selected algorithm,
  plus one manager hosting the shared elite pool. `n_jobs=None` permits that
  many workers, even if the selection exceeds available CPU cores. Specify a
  budget explicitly to prevent accidental oversubscription. A portfolio larger
  than `n_jobs` is rejected, not queued or silently truncated.
- **`backend="thread"`:** legacy shared-memory execution; arbitrary local
  callbacks work, but CPU-bound Python code is subject to the standard GIL.
- **`backend="serial"`:** debugging/reference execution with shared elites.
  Each algorithm gets its own time budget, so total search time can approach
  algorithm count times `limit_time`. This is not an equal-wall-time benchmark
  against concurrent modes.

Algorithm hyperparameters are currently in packaged `rko/parameters/` TOMLs.
Use `algorithms=["SA", "GA"]` to select a smaller portfolio without copying files.
Custom hyperparameter TOMLs can still be supplied through `params_dir`.
Constructors and configured runs validate scalar domains, population sizes and
joint constraints before execution. Online grids retain named axes and exclude
infeasible joint combinations (such as reversed perturbation bounds); an entirely
infeasible grid is rejected. No scalar value is silently truncated.

Only `control` and `pool_size` are supported under `[run]`. Remove the formerly
ignored `strategy`, `max_runs` and `debug` fields from custom configurations;
unsupported keys now raise an error. Portfolio local search currently uses
best-improvement defaults. Repeat `solve` for independent trials and use standard
Python logging for diagnostics.

### Spawn-compatible callbacks

Use module-level functions, `functools.partial`, or callable instances carrying
serializable state. Lambdas and nested functions are rejected in process mode.
The defining module must be importable in a fresh interpreter. Run from a script
rather than an interactive notebook cell, and guard the entry point:

```python
import numpy as np
from rko import RKO


def decode(keys):
    return keys


def objective(solution):
    return float(np.sum(solution**2))


if __name__ == "__main__":
    solver = RKO(
        decode, objective, n_variables=10,
        algorithms=["SA", "GA"], n_jobs=2, random_state=42,
    )
    result = solver.solve(time_limit=5.0)
    print(result.keys, result.cost, result.elapsed_seconds)
```

`random_state` gives distinct, repeatable seed allocation to Python and NumPy
worker RNGs. Timed searches still depend on scheduling and elite exchange;
identical seeds do not guarantee identical results. Thread mode rejects a seed
because its workers share global RNG state. Serial mode restores caller RNG
state after execution.

Process startup is excluded from the requested search duration. Workers start
searching together after construction. A per-search callback session carries the
same deadline through initialization and every nested operator, stopping between
decoder/objective calls and preserving the best completed evaluation. A first
valid evaluation is allowed even if initialization used the budget. User callbacks
receive ordinary decoded payloads; candidate arrays are isolated from decoder
mutation. Low-level operator calls made outside RKO do not acquire this budget.

Startup has a 60-second watchdog; process execution has five seconds of grace
for callbacks that are still running. A blocked process callback or excessive
overrun raises `TimeoutError` and stops workers. Thread mode propagates worker
failures and cooperatively cancels peers, but cannot force-kill a blocked Python
thread. This is not a hard real-time API. Algorithm failures identify the search
and preserve exception causes. The parent cleans up processes and the manager
on failure or keyboard interruption.

The managed pool is a correctness-first baseline. IPC and process startup can
outweigh parallelism on tiny problems; no universal speedup is promised.

## Run the Knapsack reference benchmark

Requires Python 3.14+ and uv. From this directory, on Linux/WSL:

```bash
uv sync --locked
PYTHONPATH=src uv run --locked python -m rko.examples.run_kp_cpp_instances \
  --backend process --limit-time 2 --random-state 42 \
  --output-csv /tmp/rko-knapsack.csv
```

In PowerShell, set `$env:PYTHONPATH = "src"` before the same `uv run` command and
choose a Windows output path. The two default reference instances are bundled
in `src/rko/examples/instances/`, with upstream revision and MIT license. No
separate C++ checkout is required. Omit `--output-csv` to save under the caller's
`results/` directory.

The decoder uses `key > 0.5`. Cost is negative profit with a penalty of 100000
per excess unit of weight, matching the reference example. Independently
computed exact optima are **31** for `kp10.txt` and **149** for `kp50.txt`. The
CSV records feasibility, objective, backend, requested worker budget, seed and
end-to-end elapsed time. A blank budget means one worker per selected algorithm.
These two small instances are correctness checks, not production-scale evidence.

A [1,000-item public-instance experiment](docs/benchmarks/2026-10-17-large-knapsack.md)
confirms multi-core CPU use, but also exposes poor optimization quality: best
RKO gap 17.56%, versus 0.00474% for a simple greedy baseline. Do not interpret
working process execution as evidence of a competitive Knapsack solver.

## Quality checks

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest src/rko/tests -q
```

GitHub Actions runs the full suite on Linux and Windows. Tests include real
spawn execution, shared elites, independent RNG streams, algorithm execution,
callback exceptions, abrupt exits, blocked callbacks and interruption cleanup.

## Remaining release work

See `docs/plans/2026-10-18-audit-remediation.md` for delivered increments and
remaining work: complete parameter/configuration validation, per-search RNG
ownership, bounded portfolio scheduling, C++ behavioral/deviation contracts,
stronger quality/performance evidence, API documentation and owner-approved
project licensing. Wheel/sdist installation and callback-boundary stopping are
now tested. Do not infer scientific or production readiness from smoke tests.
