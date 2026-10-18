# Audit remediation status

Baseline audit: `af4a588`, reviewing production revision `c9765dd`.
Implementation through `85556a6`. The original audit is historical evidence and is
not rewritten to imply its defects never existed.

## Primary API decision

The user requires an RKO class, analogous to the metaheuristic classes. `RKO`
now owns problem settings, validation, configuration loading, backend dispatch
and result state; it does not delegate its implementation to the old `run`.
`RKOResult` is immutable, repeated solves build fresh algorithm state, and failed
attempts clear stale results. `run` is only a backward-compatible adapter.

```python
from rko import RKO

solver = RKO(
    decoder, objective, n_variables=100,
    algorithms=["SA", "BRKGA", "GA", "PSO"],
    n_jobs=4, random_state=42,
)
result = solver.solve(time_limit=15.0)
print(result.keys, result.cost, result.elapsed_seconds)
```

For process execution, callbacks must be importable/pickleable and the script
entry point must be guarded by `if __name__ == "__main__"`.

## Findings mapped to implementation

| # | Finding | Current status |
| --- | --- | --- |
| 1 | Installed wheel missing resources | Addressed: explicit build/discovery, packaged TOMLs/fixtures; isolated wheel and sdist serial/spawn CI |
| 2 | GA selected chromosome fitness | Addressed for skipped crossover and odd populations; deterministic transition tests |
| 3 | Historical Q maximum/action cache | Addressed using current-action Bellman semantics; deliberate reference deviation documented |
| 4 | Sign-sensitive/lost rewards | Addressed with shared bounded policy and ILS/LNS/GRASP transition oracles |
| 5 | TOML order changes grid meaning | Addressed with canonical named axes and schema checks |
| 6 | Ignored run settings | Addressed by removing unsupported defaults and rejecting strategy/max_runs/debug/unknown keys, not pretending they work |
| 7 | Local-search budget overrun | Addressed for RKO execution via callback-boundary sessions, retaining completed candidates; standalone low-level calls have no added deadline and blocked callbacks remain non-preemptible |
| 8 | Semantic parameter validation | Addressed in all direct constructors and parent-side configured preflight; feasible joint online states only, explicit no-feasible-state failures |
| 9 | IPR remainder genes omitted | Addressed with complete block coverage and one-dimensional regression |
| 10 | Corrupt/non-atomic parameter saving | Addressed with scalar escaping, validation, atomic replacement, failure cleanup and watcher logging |
| 11 | Silent thread BaseException | Addressed with caller-visible causes and cooperative peer cancellation; blocked threads still cannot be safely killed |
| 12 | Configuration/result usability | Partially addressed: class API, Python portfolio/control/pool settings and immutable result metadata; programmatic hyperparameters, evaluation counts and stop-reason reporting remain |
| 13 | Global RNG state | Pending: serial still seeds/restores global RNGs; isolated per-search generators must reach all operators/controllers |
| 14 | Practical worker budget | Pending: default portfolio can oversubscribe and smaller n_jobs still rejects rather than schedules; nested native-thread policy remains |
| 15 | IPR busy polling/full-vector count | Addressed hot paths: bounded waiting and scalar count RPC; IPR needs another elite producer for meaningful relinking |
| 16 | C++ behavioral parity | Pending complete contract/table; current-Q, feasible-state, reward, IPR and simplex corrections have explicit deviation notes |
| 17 | Scientific/installed tests | Improved, not complete: 183 tests, deterministic oracles, real online execution of all eight adaptive algorithms, isolated artifact checks; further invariants/fixed-work tests remain |
| 18 | Competitive optimization evidence | Not resolved: six post-fix larger-instance trials are feasible but retain poor quality; best process gap 18.46% versus greedy 0.00474% |
| 19 | Docs/metadata/licensing | Partially addressed: root guide, actual class API and package description; full API/error documentation, support policy and owner-selected project license remain |
| 20 | Duplicate simplex blending | Addressed: reuse shared operator; superior initial simplex seeds are also retained |

## Validation observed

- Ruff lint and format: passed, 59 Python files.
- Full suite: **183 passed in 139.53 s**.
- GitHub Actions passed on Ubuntu and Windows, including isolated wheel/sdist
  serial and spawn checks, for each implementation through `85556a6`.
- Relevant runs: class `39134476139`, packaging `39134774674`, scientific state
  `39135014525`, parameters `39135392372`, rewards `39135756080`, stopping
  `39136755944`, validation `39137640707`, elite/IPC cleanup `39138047201`.
- [Post-core 1000-item benchmark](../benchmarks/2026-10-18-audit-core-knapsack.md):
  six feasible, independently checked trials, no runtime failures; no quality or
  speedup claim is inferred from those successes.
- Unrelated pre-existing CRLF-only changes and untracked files are preserved.

## Next implementation batch

1. Replace package-global RNG use with explicitly owned generators through every
   algorithm, controller and operator; test simultaneous-call isolation and
   fixed-work determinism. Do not merely serialize solver calls with a global lock.
2. Schedule the full requested portfolio under a hardware-aware worker budget
   and a declared fair search budget; do not silently drop algorithms or give
   queued jobs a fresh full duration. Measure native-thread and IPC overhead.
3. Complete Python hyperparameter/result metadata contracts and operator/parity
   specifications, keeping the functional adapter only for compatibility.
4. Profile and validate separate problem-aware decoding/initialization against
   representative datasets and strong baselines without altering reference results.
5. Complete API documentation/support policy and obtain the owner's license choice
   before any public release claim.

**Release assessment: still incomplete.** The class and critical audit fixes are
implemented and published, but this is not a claim of production or scientific
certification.
