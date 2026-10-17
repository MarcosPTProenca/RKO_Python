# RKO Python

Random-key optimization with cooperating metaheuristics, inspired by RKO C++ v2.
Development lives in `MarcosPTProenca/RKO-Agent`, branch `rko`. This is not yet a
finished replacement release for the separate `RKO_Python` package.

## Execution modes

`rko.run(decoder, cost, tam_solution, limit_time, ...)` returns
`(best_keys, best_cost)`, minimizing `cost(decoder(keys))`.

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

Configuration and algorithm parameters are currently in `src/rko/parameters/`.
To select fewer algorithms, copy that directory and edit
`[active_metaheuristics].list` in its `config.toml`, then pass `params_dir`.

### Spawn-compatible callbacks

Use module-level functions, `functools.partial`, or callable instances carrying
serializable state. Lambdas and nested functions are rejected in process mode.
The defining module must be importable in a fresh interpreter. Run from a script
rather than an interactive notebook cell, and guard the entry point:

```python
import numpy as np
from rko import run


def decode(keys):
    return keys


def objective(solution):
    return float(np.sum(solution**2))


if __name__ == "__main__":
    keys, value = run(decode, objective, 10, 5.0, random_state=42)
    print(keys, value)
```

`random_state` gives distinct, repeatable seed allocation to Python and NumPy
worker RNGs. Timed searches still depend on scheduling and elite exchange;
identical seeds do not guarantee identical results. Thread mode rejects a seed
because its workers share global RNG state. Serial mode restores caller RNG
state after execution.

Process startup is excluded from the requested search duration. Workers start
searching together after construction. Startup has a 60-second watchdog; search
has five seconds of overrun grace for existing local-search loops. A blocked
callback or excessive overrun raises `TimeoutError` and stops workers. This is
not a hard real-time API; deadline propagation through local searches remains
release work. Algorithm failures identify the search and preserve pickleable
exception causes. The parent cleans up workers and the manager on failure or
keyboard interruption.

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
choose a Windows output path. The default instances come from the sibling
`../RKO_Cpp_v2.0/Instances/KP` directory in this repository.

The decoder uses `key > 0.5`. Cost is negative profit with a penalty of 100000
per excess unit of weight, matching the reference example. Independently
computed exact optima are **31** for `kp10.txt` and **149** for `kp50.txt`. The
CSV records feasibility, objective, backend, requested worker budget, seed and
end-to-end elapsed time. A blank budget means one worker per selected algorithm.
These two small instances are correctness checks, not production-scale evidence.

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

See `docs/plans/2026-10-17-multicore.md` and the approved design under
`docs/superpowers/specs/`. In particular: larger real-world instances,
fixed-work performance measurements, local-search deadlines, C++ behavioral
parity, unused configuration settings, clean wheel/resource installation and
release packaging. Do not infer scientific or production readiness from passing
smoke tests alone.
