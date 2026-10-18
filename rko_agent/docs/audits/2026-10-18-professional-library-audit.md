# RKO Python: full-package professional-library audit

What this repo does: RKO minimizes a user-defined objective by decoding random-key
vectors and running a cooperating portfolio of metaheuristics. The Python package
provides serial, thread and spawn-process execution with a shared elite pool.

Assumed load: a scientist or engineer installs a wheel in a clean environment,
provides trusted callbacks, selects algorithms and parameters in Python, and runs
CPU-bound searches on a workstation. Repeated runs and multiple solver calls in
one application are expected. This is not an untrusted-code execution service.

**Verdict: not ready for a professional library release.** The functional API is
not the central problem. Confirmed algorithm-state bugs, missing installed
resources, broken configuration semantics and incomplete stopping contracts must
be resolved before API polish can justify a quality claim.

## Scope and evidence

- Baseline: `c9765ddb5168a11a22fea4b02704bbfbbf1df98f`, branch `rko`.
- Reviewed all 39 production/package Python files and all nine test Python files
  under `src/rko` (7,093 lines combined), all 12 parameter TOMLs, public exports,
  package/root READMEs, metadata, CI and pre-commit configuration. Also reviewed
  the existing design, implementation plan and benchmark artifacts.
- Traced public input through configuration, factory, each of the 11 algorithms,
  local searches/operators, pool, execution backends, result selection and CSV.
- Compared selected behavior with the local C++ reference: SA control, GA
  chromosome/fitness copying, IPR blocks and GRASP line search. This is not a
  complete mathematical or executable Python/C++ equivalence proof.
- Re-ran Ruff lint and format checks: pass, 49 formatted files.
- Re-ran the full suite: **95 passed in 97.01 seconds**. Existing CI at this
  commit also passed on Ubuntu and Windows (run `39092349847`).
- Built wheel and sdist from a clean `git archive`, installed the wheel into a
  separate Linux Python 3.14 environment and invoked the installed public API
  outside the checkout. The installation exposed missing runtime files.
- Ran ten focused defect probes plus installed-wheel and thread-exit checks.
  Observations are in [`2026-10-18-runtime-evidence.json`](2026-10-18-runtime-evidence.json).
- No production code, default configuration or regression tests were modified by
  this audit. Temporary probes/environments were isolated under `/tmp`.

### How scikit-learn is used as the reference

Primary sources were checked through Context7 (`/scikit-learn/scikit-learn`) and
against the official documentation:

1. [Developing estimators](https://scikit-learn.org/stable/developers/develop.html):
   explicit parameters, clear method contracts, validation, isolated randomness,
   introspection and common interface tests.
2. [Controlling randomness](https://scikit-learn.org/stable/common_pitfalls.html#controlling-randomness):
   explicit random-state semantics, avoiding global NumPy seeding.
3. [Parallel resource management](https://scikit-learn.org/stable/computing/parallelism.html):
   resource budgets, nested BLAS/OpenMP concurrency and oversubscription.
4. [Contributing and review guidelines](https://scikit-learn.org/stable/developers/contributing.html):
   test documented behavior, parameter combinations, regressions and public APIs.

These are quality principles, not a requirement to turn optimization into
supervised learning. `fit(X, y)`, `predict`, estimator tags, `BaseEstimator` and
`check_estimator` are required only if a meaningful scikit-learn-compatible
estimator is offered. Generic RKO does not currently make that compatibility
claim. **A public `run(...)` function is a valid library API.** Adding a class or a
scikit-learn runtime dependency by itself would fix none of the bugs below.

## Must fix

### 1. The installed package cannot run

`pyproject.toml:1-9`; `src/rko/parameters/loader.py:90-100`;
`.github/workflows/ci.yml:23-30`.

- **What this is:** The wheel is what a normal library user installs, rather than
  running from a source checkout with `PYTHONPATH=src`.
- **Problem:** A clean build contains zero TOMLs and zero bundled instance files,
  but includes nine test Python files. An installed `rko.run(..., backend="serial")`
  immediately raises `FileNotFoundError` for `parameters/config.toml`.
- **Fix:** Declare the build backend and explicit package/resource inclusion,
  exclude tests from the runtime wheel, and run a wheel-install smoke test from
  outside the source tree in CI.
- **If we skip it:** Tests remain green while the distributed library is unusable.

### 2. GA disconnects selected chromosomes from their fitness

`src/rko/metaheuristics/ga.py:175-207`.

- **What this is:** Tournament selection copies chosen parents into the next
  generation; each chromosome must retain its own objective value.
- **Problem:** `pop_new` comes from selected parents, but its cost list and
  no-crossover branches use original population positions. A controlled run
  selected costs `[0.1, 0.1, 0.1]` but stored `[0.1, 0.2, 0.3]`; odd unpaired
  population members have the same risk.
- **Fix:** Carry selected parent indices/costs alongside the copied chromosomes,
  and use those selected costs whenever a chromosome is not reevaluated.
- **If we skip it:** Selection ranks the wrong fitness and changes search
  behavior; checking only the final incumbent's cost will not detect this.

### 3. Q-learning's cached best action can remain wrong after an update

`src/rko/components/adaptive_control/q_learning.py:236-250`.

- **What this is:** Exploitation chooses `maxA`, and the Bellman target uses
  `maxQ`, both intended to represent the best action value.
- **Problem:** They are updated only when a new value exceeds a historical
  maximum. After `[1.0, 0.5]` becomes `[-1.0, 0.5]`, exploitation still selects
  action 0 and the cached maximum remains 1.0.
- **Fix:** Recompute the current maximum/index after updates if standard
  Q-learning is intended. If historical maxima are an intentional RKO variant,
  specify and test that variant rather than presenting it as a current-action
  maximum; the C++ reference also retains historical maxima.
- **If we skip it:** Adaptive choices and bootstrapped values do not follow the
  usual Q-learning contract, with no test identifying the difference.

### 4. Adaptive rewards encourage some worse solutions and miss improvements

`src/rko/metaheuristics/ils.py:167-177`; `ga.py:229-239`;
`pso.py:239-251`; `brkga.py:254-261`; `lns.py:258-284`;
`grasp.py:247-283`.

- **What this is:** Reward signals determine which parameter settings the online
  controller learns to prefer.
- **Problem:** Negative objectives are valid and used by the Knapsack example.
  An ILS incumbent of -100 followed by a worse -50 receives reward +1.0; LNS and
  GRASP also compare with an already-updated best, so a real improvement may
  receive zero reward.
- **Fix:** Define one sign-safe, finite reward contract using the previous
  incumbent and an absolute scale, and test better/equal/worse cases for positive,
  zero and negative objectives before applying it across algorithms.
- **If we skip it:** Online adaptation is objective-sign dependent and may reward
  deterioration. This is not proof that it alone caused the observed benchmark gap.

### 5. Reordering TOML keys changes the algorithm and can crash it

`src/rko/parameters/loader.py:128-155`;
`src/rko/orchestration/factory.py:46-64`.

- **What this is:** Named parameter files are converted to positional Q-learning
  axes consumed in a fixed order by each algorithm.
- **Problem:** The loader uses dictionary insertion order, not expected parameter
  names. A legal GA table ordered `prob_mut, prob_cros, size_pop` creates a
  population of zero and raises `ValueError: min() iterable argument is empty`.
- **Fix:** Declare each algorithm's online parameter names in its specification,
  resolve axes by those names, and reject missing/extra/invalid axes explicitly.
- **If we skip it:** A harmless-looking file edit silently changes parameter
  meanings; constructors and configuration tests still pass.

### 6. Public configuration accepts settings that never take effect

`src/rko/parameters/config.toml:9-20`;
`src/rko/orchestration/configuration.py:85-119`;
`src/rko/orchestration/types.py:25-31`.

- **What this is:** Configuration promises local-search strategy, repeated runs
  and debugging behavior.
- **Problem:** Parsing retains only control, pool size and algorithm names.
  `strategy=999`, `max_runs=0` and `debug="invalid"` are accepted and discarded;
  local-search strategy is not forwarded through the factory or solve calls.
- **Fix:** Implement and validate supported settings end to end, or reject/remove
  unsupported settings and their claims. Do not silently ignore them.
- **If we skip it:** Users believe they changed the experiment when the executed
  search is unchanged, invalidating comparisons and troubleshooting.

### 7. Local searches break the time-budget contract

`src/rko/metaheuristics/ils.py:141-157`;
`src/rko/components/local_search/rvnd.py:68-94`;
`swap_ls.py:64-93`; `nelder_mead_ls.py:166-247`;
`src/rko/orchestration/processes.py:270-277`.

- **What this is:** The public API accepts a search duration and the process
  coordinator enforces an overrun grace period.
- **Problem:** Initialization and local searches run without the deadline.
  With ILS, dimension 100 and a callback that returns normally after 1 ms per
  evaluation, a 0.01 s search raised a timeout after 7.236 s including startup;
  the worker was still in a valid local search, not a blocked callback.
- **Fix:** Pass a common deadline/cancellation context through nested search and
  initialization loops, checking between evaluations. Keep forced termination as
  a fallback for callbacks that do not return.
- **If we skip it:** Larger valid searches can be killed and lose their result;
  direct serial/thread execution can overrun without the process fallback.

### 8. Validation checks casts, not valid algorithm settings

`src/rko/orchestration/configuration.py:97-111`;
`src/rko/orchestration/factory.py:17-28`;
`src/rko/metaheuristics/ga.py:73-108,175-180`;
`brkga.py:68-114,212-233`.

- **What this is:** Numeric values and parameter combinations determine valid
  populations, probabilities, temperatures and Q-learning states.
- **Problem:** `control=0.9` becomes 0 and `pool_size=2.9` becomes 2; GA accepts
  populations too small for its three-parent tournament. Probabilities, joint
  elite/mutant counts, finite values and online grid dimensions are not checked
  before execution.
- **Fix:** Validate exact types, ranges and cross-parameter constraints before
  starting work, including every reachable online state; return parameter-specific
  errors rather than downstream indexing/sampling failures.
- **If we skip it:** Invalid experiments run with silently changed inputs or fail
  inside workers after startup, sometimes only after an adaptive transition.

### 9. IPR never explores the remainder of some chromosomes

`src/rko/metaheuristics/ipr.py:108-130`.

- **What this is:** Path relinking should partition the chromosome into candidate
  blocks and explore transitions toward an elite guide.
- **Problem:** Floor division drops the final partial block. At dimension 25,
  block size 2 and 12 blocks cover only positions 0 through 23; a profitable
  difference solely at position 24 is never considered. The C++ code has the
  same floor-block issue: this is not claimed as a Python-only regression.
- **Fix:** Include the final partial block, clamp each block's end, and test
  non-divisible and one-dimensional cases against a declared relinking contract.
- **If we skip it:** An advertised search operator cannot reach improvements in
  part of the decision vector.

### 10. Saving parameter grids can corrupt a valid configuration file

`src/rko/parameters/loader.py:181-266`.

- **What this is:** The exported `save_online_grid` API rewrites online settings
  while preserving the offline section.
- **Problem:** `_fmt_value` emits strings without TOML quoting. Saving a grid in
  a file containing `label="stable"` produces an unreadable file; writing directly
  with mode `w` also exposes the original to partial-write failure.
- **Fix:** Either support and correctly escape the declared scalar types or
  reject unsupported values before touching disk; validate the serialized output
  and replace the file atomically from a temporary sibling.
- **If we skip it:** A supported tuning operation can destroy the user's usable
  configuration. File watching currently swallows parse/callback errors as well.

## Should fix

### 11. Thread workers can fail without a caller-visible failure

`src/rko/orchestration/execution.py:17-43`;
`src/rko/rko_main.py:101-105`.

- **What this is:** Thread execution is a supported compatibility backend.
- **Problem:** Workers catch only `Exception`; a callback raising `SystemExit`
  yields `([], inf)` instead of a failure. Joins are unbounded, and one failed
  worker does not cancel the remaining searches.
- **Fix:** Record worker outcomes reliably, never convert a missing result into
  success, preserve causes, and provide cooperative failure cancellation. State
  explicitly that arbitrary blocked Python threads cannot be force-killed safely.
- **If we skip it:** A caller may accept an empty result or wait indefinitely
  after another algorithm has already failed.

### 12. The public API hides experiment configuration and outcome details

`src/rko/rko_main.py:45-75,95-125`; `src/rko/__init__.py:22-24`;
`src/rko/orchestration/configuration.py:22-83`.

- **What this is:** A professional API must make supported choices discoverable
  and expose enough information to interpret a run.
- **Problem:** Algorithm selection/hyperparameters require copying a directory
  and editing files; the returned tuple has no stop reason, evaluation count,
  executed configuration or actual worker allocation. Backends also disagree on
  whether the same duration is a total concurrent or per-algorithm serial budget.
- **Fix:** Expose typed Python configuration and a structured optimization result
  with explicit budget semantics, retaining `run` as a compatibility façade.
  Add a solver object only if configuration/state/introspection justify it.
- **If we skip it:** Notebooks, repeated experiments and tuning tools must depend
  on filesystem conventions and cannot reliably record what executed.

### 13. Global RNG manipulation prevents safe composition of solver calls

`src/rko/rko_main.py:107-125`;
`src/rko/components/adaptive_control/q_learning.py:147-184`;
`src/rko/metaheuristics/sa.py:127-175`.

- **What this is:** Random-state control should belong to a solver/search, not
  change unrelated application randomness.
- **Problem:** Serial mode seeds and restores process-global Python/NumPy RNGs;
  concurrent calls or unrelated threads can consume or lose each other's state.
  Algorithm classes also expose no independent RNG while using global generators.
- **Fix:** Pass per-search RNG objects through algorithms, operators and adaptive
  control, with documented accepted seed types. Test caller-state isolation and
  deterministic fixed-work runs, separately from timed scheduling variability.
- **If we skip it:** A seed appears reproducible in isolation but does not provide
  a composable scientific-library contract.

### 14. Worker settings do not yet provide a practical resource budget

`src/rko/orchestration/processes.py:199-214,225-250`;
`src/rko/parameters/config.toml:23-35`.

- **What this is:** `n_jobs` is expected to express a usable concurrency budget.
- **Problem:** The default launches ten search processes plus a manager on a
  four-core host; `n_jobs=4` rejects that portfolio rather than scheduling it.
  NumPy/BLAS-heavy callbacks may add native threads inside every process, with no
  nested-thread policy. The portfolio restriction was documented and accepted as
  an initial milestone, not completed resource management.
- **Fix:** Define a hardware-aware worker policy and fair scheduling under a
  common overall budget, or expose a clear bounded portfolio API. Document and
  measure nested native threading before choosing limits or a new dependency.
- **If we skip it:** Ordinary workloads can waste CPU and memory, or fail when
  users request a reasonable core count.

### 15. IPR busy-polls and transfers full vectors merely to count entries

`src/rko/metaheuristics/ipr.py:160-170`;
`src/rko/orchestration/processes.py:86-93`.

- **What this is:** IPR waits for two elites and repeatedly asks for pool state.
- **Problem:** When fewer than two entries exist it loops without waiting.
  `PoolProxy.size` fetches every elite vector; at pool size 10 and dimension 1000,
  it transfers 10,000 key values just to get a count, then fetches elites again.
- **Fix:** Expose count directly from the manager and use a bounded wait/backoff
  or notification when no pair exists. Validate/document IPR-only portfolios and
  pool capacities below two.
- **If we skip it:** A default worker spends time on polling and serialized data
  copies rather than useful search, especially at larger dimensions.

### 16. C++ inspiration is not the same as documented behavioral parity

`src/rko/orchestration/configuration.py:23-27`;
`src/rko/metaheuristics/sa.py:37-39`;
`src/rko/metaheuristics/grasp.py:59-84,189-283`;
`src/rko/parameters/grasp.toml:3-15`.

- **What this is:** Users need to know whether this is a faithful port, a selected
  subset, or a revised algorithm family.
- **Problem:** SA says it faithfully mirrors the reference but lacks its online
  control. Python GRASP searches nearby multiples of h, whereas the reference
  samples the full feasible grid; its advertised alpha axis is never consumed
  by the Python algorithm. Some known defects are inherited from upstream.
- **Fix:** Maintain an explicit per-algorithm parity/deviation table, verify
  critical operators with deterministic traces, and remove unused axes/claims or
  implement the intended behavior. Do not copy upstream defects for appearances.
- **If we skip it:** Users cannot distinguish an intended algorithm change from
  an implementation defect or reproduce published reference behavior.

### 17. Tests exercise execution but miss important scientific invariants

`src/rko/tests/rko/test_process_execution.py:357-375`;
`src/rko/tests/components/test_q_learning_pytest.py:46-71`;
`src/rko/tests/metaheuristics/test_metaheuristics_pytest.py:72-87`;
`.github/workflows/ci.yml:23-30`.

- **What this is:** Tests should fail when the scientific algorithm or installed
  user contract breaks, not merely when a class cannot be constructed.
- **Problem:** All 95 tests pass despite findings 1-10. Per-algorithm execution
  tests use tiny offline sphere problems; online tests only inspect construction,
  and CI does not exercise installed wheels or algorithm transition invariants.
- **Fix:** Add shared optimizer contract checks, selected-cost and Q-update
  oracles, negative/zero objective cases, online transitions, malformed parameter
  combinations, budget checks and isolated installed-artifact tests.
- **If we skip it:** Growing the test count can create false confidence without
  preventing repeat regressions. Use coverage as a diagnostic, not a correctness claim.

### 18. Current evidence does not establish a competitive optimizer

`docs/benchmarks/2026-10-17-large-knapsack.md:1-117`;
`src/rko/examples/run_kp_cpp_instances.py:143-224`.

- **What this is:** Numerical software needs credible quality and performance
  baselines, including simple specialized methods.
- **Problem:** On the 1000-item public instance, the best RKO gap was 17.56%,
  versus 0.00474% for greedy; exact DP finished in 2.944 s. Three seeds on one
  instance with different backend RNG streams do not establish general superiority.
- **Fix:** Repair correctness first, then use a separate problem-aware decoder
  without replacing the reference example, multiple instance families and seeds,
  fixed-work and time-to-target measurements, and CPU/memory/profiling evidence.
- **If we skip it:** Working multiprocessing may be mistaken for useful algorithm
  performance. No single root cause of the quality gap is proven by this audit.

### 19. Documentation and distribution policy are not release-grade

`README.md:1`; `pyproject.toml:1-9`;
`src/rko/metaheuristics/base.py:31-46`;
`src/rko/metaheuristics/sa.py:1-20`;
`src/rko/examples/run_kp_cpp_instances.py:143-155`.

- **What this is:** Users need accurate examples, metadata, errors and rights to
  use/distribute the package.
- **Problem:** Root README is a quoted placeholder, package description is a
  placeholder, and 50 exception docstrings use a generic non-contract statement.
  The base example references nonexistent `self.pool` with an incompatible call;
  the project has no tracked project-wide license, only the bundled-data MIT notice.
- **Fix:** Correct executable examples and real error contracts; publish API and
  support/deprecation documentation plus complete metadata. The owner must choose
  a project license and preserve applicable upstream attribution before release.
- **If we skip it:** Users follow broken examples, cannot identify supported
  behavior and lack a clear project-wide permission to reuse/distribute the code.

## Nice to have

### 20. The same blending operator is implemented twice

`src/rko/components/local_search/nelder_mead_ls.py:68-97`;
`src/rko/components/blending/blending.py:28-61`.

- **What this is:** Nelder-Mead uses a private copy of the already-exported
  mutation/inheritance operator.
- **Problem:** The two implementations use the same probabilities and complement
  rule, but only the exported one has a shape check; a future change can update
  one and leave the other behind.
- **Fix:** Import the shared function under the private name or call it directly,
  preserving the existing RNG draw order with a small equivalence regression test.
- **If we skip it:** Two implementations of one rule must be maintained and tested
  independently without a demonstrated need for different behavior.

## Standards assessment

| Area | Current assessment | Release gate |
| --- | --- | --- |
| Public functional API | Valid pattern; configuration/results incomplete | Explicit Python settings and auditable result contract |
| Algorithm correctness | Confirmed state/fitness/reward defects | Deterministic invariant and regression tests |
| Validation | Partial scalar guards; missing semantic checks | Validate all supported parameter combinations |
| Randomness | Stable worker seed allocation; global RNG dependence | Per-search state and fixed-work reproducibility tests |
| Parallelism | Real multicore; process cleanup tested | Deadlines, usable budgets, measured communication/native-thread costs |
| Distribution | Clean wheel build succeeds but installed execution fails | Wheel/sdist install and resource tests outside source checkout |
| Tests/CI | 95 pass; Linux/Windows green | Installed API plus scientific/online contract checks |
| Benchmarks | Useful transparent negative result | Competitive baselines across representative instance families |
| Documentation | Existing design/reporting, inaccurate API details | Executable examples, accurate references and version/support policy |
| Licensing | Data notice present, project-wide license absent | Owner-approved license and attribution review |

The domain-specific contract suite should be shared across all 11 algorithms and
backends: dimensions/range, objective-key consistency, incumbent preservation,
valid parameter transitions, caller-state isolation, failures and stopping.
`check_estimator` becomes relevant only for a genuine ML estimator adapter; it is
not an appropriate pass/fail substitute for these optimization contracts.

## Minimal correction order

1. **Block distribution mistakes:** explicit build/resources and installed-wheel
   CI; choose project license before publishing a release.
2. **Restore scientific correctness:** findings 2-5 and 9, with red/green
   regression tests. Decide intended Q-learning/parity semantics explicitly.
3. **Make settings and stopping trustworthy:** findings 6-8, 10-11 and 13;
   fail early and bound returning-callback work cooperatively.
4. **Make the library ergonomic:** explicit Python configuration, consistent
   result/budget semantics and compatibility façade; no cosmetic class rewrite.
5. **Measure and refine:** findings 14-18, then documentation and duplicate
   cleanup. Re-run larger-instance baselines after correctness changes.

Every correction should be a separate validated increment, not a rewrite of all
algorithms. Do not claim scikit-learn compatibility or a finished professional
release merely because an `RKOSolver` class exists or Ruff is green.

## Reproduction and limitations

Quality gates from `rko_agent`:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/rko-validation-env \
  /tmp/rko-validation-tools/packages/bin/uv run --locked ruff check .
UV_PROJECT_ENVIRONMENT=/tmp/rko-validation-env \
  /tmp/rko-validation-tools/packages/bin/uv run --locked ruff format --check .
UV_PROJECT_ENVIRONMENT=/tmp/rko-validation-env \
  /tmp/rko-validation-tools/packages/bin/uv run --locked pytest src/rko/tests -q
```

Installed-artifact reproduction, without touching the Windows virtualenv:

```bash
mkdir -p /tmp/rko-audit-source /tmp/rko-audit-dist
git archive c9765dd rko_agent | tar -x -C /tmp/rko-audit-source
uv build /tmp/rko-audit-source/rko_agent --out-dir /tmp/rko-audit-dist
uv venv --python 3.14 /tmp/rko-audit-installed
uv pip install --python /tmp/rko-audit-installed/bin/python /tmp/rko-audit-dist/*.whl
cd /tmp
uv run --no-project --python /tmp/rko-audit-installed/bin/python python -c \
 'from rko import run; run(lambda x:x, lambda x:float(sum(x)), 3, .01, backend="serial")'
```

For the other confirmed defects, the JSON records inputs and observed outputs.
The focused probes used controlled one-generation GA parent selection, a negative
Q update, one worse negative-objective ILS transition, equivalent/reordered TOML
settings, a final-gene-only IPR guide, save/reload of a string-valued offline
setting, ILS dimension100 with a returning 1ms callback, and a two-member GA
population that cannot support its three-parent tournament. These probes do not
change the package and are not yet regression tests in its suite.

Security review: callbacks and pickleable state execute trusted user code;
process mode is not a sandbox. No remote service/authentication flow exists in
this package. File replacement and swallowed watcher errors are relevant data
integrity issues, not a claimed remote exploit. No dependency CVE scanner or
formal security assessment was run.

**Verdict:** fix installed execution and scientific state correctness first; the
current package is a tested research foundation, not scikit-learn-level software.

**Lean:** about 29 duplicate implementation lines can be removed; no additional
runtime dependency is required merely to reorganize this API.

**Not checked:** exhaustive mathematical or executable C++ parity; full review of
external NumPy/tooling code; macOS, native Windows manual probes or distributed
execution; peak-memory/load profiling; dependency vulnerabilities; legal ownership
verification; exhaustive data-domain validation across real operational problems.
Windows CI success is observed, not substituted for those checks. Existing
unrelated CRLF-only worktree changes and user untracked files remain untouched.
