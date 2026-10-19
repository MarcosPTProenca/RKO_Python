# RKO Python

Random-key optimization with cooperating metaheuristics, inspired by RKO C++ v2.
Development lives in [MarcosPTProenca/RKO_Python](https://github.com/MarcosPTProenca/RKO_Python),
branch `main`. This is a standalone library: no agent repository, parent checkout
or C++ installation is required. Packaging, source, documentation and CI live
at the repository root.

## Development setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/MarcosPTProenca/RKO_Python.git
cd RKO_Python
uv sync --locked --group dev
uv run --locked pre-commit run --all-files
```

For automatic commit checks, run `uv run pre-commit install` if Git uses its
standard hooks directory. If `core.hooksPath` is centrally managed, integrate
pre-commit with those existing hooks instead; no global Git settings are changed
by this migration.

The distribution retains the name `rko`; version `0.3.0.dev0` identifies this
unreleased class-based development line, not a PyPI publication. It replaces
the previous implementation on `main`, whose complete code/history is retained
at `archive/pre-standalone-migration-2026-10-18`. The new API and Python 3.14
requirement are breaking changes from that older implementation. Attribution
and licensing boundaries are retained in [NOTICE](NOTICE).

## Class-based solver API

`RKO(decoder, cost, n_variables, ...).solve(time_limit)` minimizes
`cost(decoder(keys))`. The constructor stores configuration without reading files
or starting workers. Each solve builds a fresh portfolio and returns an immutable
`RKOResult` with `keys`, `cost`, `elapsed_seconds`, `backend`, `algorithms` and
`random_state`. `solver.result_` holds the latest successful result and is cleared
before every attempt, including failed solves.

Select `algorithms`, `control` and `pool_size` directly in Python; omitted values
use the packaged TOML defaults. `params_dir` remains available for hyperparameter
files. Library calls are quiet by default; `verbose=True` on `RKO` prints lifecycle
and attributed shared-pool improvements. `rko.run(...)` retains the old tuple API
and also accepts `verbose=True`.

## Execution modes

- **`backend="process"` (default):** one spawned worker per selected algorithm
  when `n_jobs=None`, plus one manager hosting the shared elite pool. The default
  can exceed available CPU cores. A positive `n_jobs` caps search workers without
  dropping algorithms: assignments are round-robin and each worker runs its
  assigned searches sequentially. With N algorithms and W workers, each search
  gets at most `time_limit / ceil(N / W)` seconds, all within one common deadline.
  For example, ten algorithms with `n_jobs=4` use four search workers, three
  slices and one manager—not ten workers or ten fresh full-duration searches.
  Smaller limits change cooperation and per-algorithm budgets; they are not a
  promise of better optimization quality. Active callbacks can overrun a slice
  and leave later searches less time or no time. Algorithms sharing a worker
  also share its callback instances; mutable callback state is not reset between
  searches. Native BLAS/OpenMP threads are separate from this worker limit.
- **`backend="thread"`:** legacy shared-memory execution; arbitrary local
  callbacks work, but CPU-bound Python code is subject to the standard GIL.
- **`backend="serial"`:** debugging/reference execution with shared elites.
  Each algorithm gets its own time budget, so total search time can approach
  algorithm count times `limit_time`. This is not an equal-wall-time benchmark
  against concurrent modes.

IPR consumes elite pairs from other searches. Running it alone returns an initial
candidate without meaningful relinking; select another search alongside it and
use a pool capacity of at least two. With a single worker, schedule IPR after
searches that populate the pool; otherwise its slice may be spent waiting for
searches queued behind it. Waiting uses bounded backoff, and process occupancy
queries transfer only a count rather than the entire pool.

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

### Adapting a custom problem

Keep the problem-specific reader outside RKO. Load the data once, then pass a
one-dimensional NumPy key vector to a decoder that returns your domain solution;
the objective receives that solution and must return a finite scalar to
**minimize**. For `backend="process"`, callbacks must be importable and
pickleable: use module-level functions or callable objects that hold the loaded
data. The `Spawn-compatible callbacks` example above shows a runnable setup; for
a structured problem, replace its identity decoder and sphere objective with
your own adapter. RKO itself does not parse problem files or assume a solution
representation.

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

## Run an instance from the terminal

Like C++ `runTest INSTANCE T`, the supplied problem adapter runs Knapsack:

```bash
uv sync --locked
uv run --locked rko src/rko/examples/instances/kp50.txt \
  --limit-time 10 --backend process --random-state 42 \
  --output-csv results/kp50.csv
```

The terminal command shows clock/elapsed timestamps and new-best algorithms, plus
pool status approximately every second even during plateaus. Add `--quiet` for
final results only.

Pass `--params-dir configs/my-run` to select your own `config.toml` and algorithm
TOMLs. See [running an instance](docs/running.md) for copying/editing configuration,
a four-worker portfolio, instance format, PowerShell and legacy batch selection.
The supplied command does not infer arbitrary problem formats: other problems
require their own reader/decoder, analogous to adapting C++ `Problem.h`.

The two bundled references live in `src/rko/examples/instances/`, with upstream
revision and MIT license. No C++ checkout or `PYTHONPATH` setting is required.
Omit `--output-csv` to save under the caller's `results/` directory.

The decoder uses `key > 0.5`. Cost is negative profit with a penalty of 100000
per excess unit of weight, matching the reference example. Independently
computed exact optima are **31** for `kp10.txt` and **149** for `kp50.txt`. The
CSV records feasibility, objective, backend, requested worker budget, seed and
end-to-end elapsed time. A blank budget means one worker per selected algorithm.
These two small instances are correctness checks, not production-scale evidence.

The [larger benchmark](benchmarks/README.md) includes a runnable experiment and
one current reference CSV. Re-run on October 18 against the standalone solver,
all six trials were feasible, but the best process gap was **17.82%**, versus
**0.00474%** for a simple greedy baseline. This demonstrates multicore execution,
not competitive solution quality or fixed-work speedup.

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

The library is **not yet release-ready**. See [current limitations](docs/status.md)
for the outstanding RNG, scheduling, parity, documentation and licensing work.
[C++ compatibility](docs/cpp-compatibility.md) distinguishes verified reference
behavior from deliberate corrections and still-unimplemented functionality.
Installation and correctness checks are not evidence of competitive optimization.
Internal audits, agent plans and migration diaries are local working material,
not maintained public documentation.
