# Audit remediation and class-based RKO API

## User direction and implementation choices

The user authorized implementing the audit and explicitly requires a class for
RKO, analogous to its metaheuristics. They delegated API details rather than
requesting further design questions. The primary API is `from rko import RKO`:
construct it with decoder, objective, dimension and execution settings; call
`solve(time_limit)` to execute a fresh portfolio; inspect the returned `RKOResult`
and `solver.result_`. This naming/signature is the implementer's choice.

RKO owns validation, configuration and backend dispatch, not a wrapper around the
old `run` implementation. `run` becomes a compatibility adapter preserving its
signature/tuple output. It is not the primary documented API. Constructor performs
no I/O or execution; solve validates before starting children and clears stale
results on each attempt. Results record immutable keys, objective, end-to-end time,
backend, algorithm selection and seed; do not invent unmeasured evaluation counts.
Python algorithm/control/pool settings override TOML defaults without editing files.

## Scope, risks and boundaries

Reach package exports, orchestration, both benchmarks, README examples, tests,
metadata, lockfile and Linux/Windows installed-artifact CI. Preserve pre-existing
CRLF-only worktree modifications and all unrelated/untracked files. Keep tuple
callers working and real spawn execution/cleanup intact. Choose no project license
on behalf of its owner. No sklearn dependency or artificial ML estimator adapter.

## Validated increments

1. Introduce the actual RKO class and result contract, migrate maintained examples,
   preserve legacy calls, and test repeated runs, failures and Python configuration.
2. Explicit build backend/resources, clean installed-wheel and sdist checks on
   Linux/Windows, complete metadata description and root README. No license claim.
3. Scientific regressions: selected GA fitness, online parameter name ordering,
   Q maxima, sign-safe rewards and IPR remainder handling. Use independent oracles.
4. Parameter validation/configuration semantics and atomic TOML persistence;
   reject unsupported settings instead of silently ignoring them.
5. Cooperative local-search deadlines and failure/cancellation behavior.
6. Local RNG ownership, practical bounded process scheduling and IPC overhead.
7. Algorithm/parity documentation and deterministic contracts; correct real API
   documentation, consolidate duplicated blending, rerun representative benchmarks.

Each increment gets Ruff lint/format, regression tests and the full suite, its own
commit and GitHub push. Update progress below with observed evidence; do not mark
the entire audit resolved after delivering only its API or packaging portion.

## Delivered increments

- `d924f5e`: RKO class owns execution, RKOResult snapshots, Python portfolio
  selection and compatibility adapter; all108 tests passed (86.18s).
- `6d7f650`: explicit setuptools resources/discovery and isolated wheel/sdist
  checks, including serial and spawn; all108 tests passed (89.45s). CI now runs
  the same installed-artifact checks on Linux and Windows.
- Scientific state corrections: GA retains selected parent fitness for skipped
  crossover and odd populations; IPR includes partial final blocks; Q-learning
  uses the actual current maximum after every update. Five deterministic cases
  failed before the changes, and all114 tests passed afterward (88.04s).

- `73c82e2`: canonical named online axes, finite/nonempty grid validation,
  scalar-preserving atomic TOML replacement and visible watcher failures;
  five regressions failed first, all120 tests passed (108.15s).
- Adaptive rewards now share a sign-safe bounded policy: strict improvements
  receive1, equality0, deterioration a normalized penalty in[-1,0]. The previous
  population-size bonuses are removed. LNS/GRASP retain pre-update incumbent
  context; deterministic reward tests cover positive/zero/negative objectives,
  extreme finite costs, and actual ILS/LNS/GRASP transitions. All135 tests passed
  (94.74s); larger benchmark quality has not yet been remeasured.

- Callback-boundary deadline sessions now cover RKO initialization and all nested
  operators without duplicating deadline branches throughout algorithms. Completed
  evaluations survive stopping; the first evaluation is allowed to finish, so this
  is cooperative rather than hard real-time. Decoder input is detached. Thread
  failures include BaseException, preserve causes and signal peer cancellation.
  The dimension100 returning1ms-callback ILS reproducer now returns a valid result
  with a0.01s budget through serial/thread/process instead of timing out. All143
  tests passed (118.75s), including blocked-process cleanup and decoder mutation.

Linux/Windows CI succeeded for class API (`39134476139`), packaging including both
installed artifact checks (`39134774674`), and scientific state fixes (`39135014525`).

The Q-learning choice intentionally follows current-action Bellman semantics,
not the reference C++ historical-maximum cache. IPR preserves the pre-guide
stopping policy for multiple blocks, but no longer drops final genes. These are
explicit correctness deviations, not a claim of unchanged C++ trajectories.

## Remaining release gates

Owner-approved project license; scientific correctness and online transition
coverage; meaningful larger-instance quality; fixed-work speedup/profile evidence;
full installed-artifact validation; explicit parity deviations. The audit remains
the baseline evidence, not a claim that fixes already exist.
