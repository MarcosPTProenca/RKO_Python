# Automatic process-worker defaults

## Behavior change

Previously, omitted/`None` `n_jobs` created one spawned search worker per selected
algorithm. It now uses the smaller of portfolio size and the process-usable logical
CPU count from `os.process_cpu_count()`, with a conservative one-worker fallback
when discovery is unavailable. This also applies to `run()` and the CLI when
`--n-jobs` is omitted. Existing positive explicit limits retain their meaning,
including limits greater than the detected CPU count. Zero, negative, boolean and
non-integer limits remain invalid. Serial and thread execution are unchanged.

Every selected algorithm remains assigned in portfolio order, round-robin across
workers. Existing common-deadline semantics remain: each search gets at most
`time_limit / ceil(number_of_algorithms / number_of_workers)` seconds. Unused slices
are not redistributed. Callbacks can overrun their slice and starve later searches;
queued algorithms may consequently report `not_started`.

**Changing the default worker count changes timed trajectories and per-algorithm
budgets.** This is not a promise of equal-work speedups or better solution quality.
Sequential algorithms in a worker share callback instances without resetting
mutable state; with one worker, place elite-dependent IPR after pool-populating
searches. Owned library RNG seeds remain assigned by portfolio position, not by
worker count, but timed/cooperative final results need not match.

## Preserve dedicated workers

Choose a portfolio explicitly and request its size:

```python
algorithms = ["SA", "GA", "PSO"]
optimizer = RKO(decoder, objective, dimension, algorithms=algorithms,
                n_jobs=len(algorithms))
```

For the current shipped ten-algorithm CLI portfolio, use `--n-jobs 10`.
No `-1`/`all` sentinel or new CLI flag is introduced.

## Resource accounting

`result.n_jobs` retains the requested limit (`None` for automatic). New
`result.available_cpus` records the usable logical CPU discovery once per process
solve; it is `None` for nonprocess runs and legacy manually constructed results.
The existing `result.n_workers` property uses that immutable snapshot and the
requested cap. Later affinity changes do not rewrite earlier results, and the
next solve discovers capacity again. Legacy six-argument `RKOResult` construction
keeps its historical worker estimate when no capacity snapshot exists.

The cap covers **search processes only**, not the pool manager, coordinator,
resource tracker, callback subprocesses or BLAS/OpenMP/native threads. It is per
solve, not a machine-wide allocator shared by concurrent RKO instances. Affinity
and Python CPU-count overrides are respected, but not every container CPU quota
is reflected in the discovered count; supply a positive explicit `n_jobs` for such
limits. The library does not change environment variables or native thread settings
inside an already running application.

See [the resource benchmark](../benchmarks/README.md#bounded-process-worker-resources)
for measured scope and limitations. Installation/filesystem startup gains remain a
separate [WSL setup concern](running.md#wsl-startup-and-virtual-environment-placement).
