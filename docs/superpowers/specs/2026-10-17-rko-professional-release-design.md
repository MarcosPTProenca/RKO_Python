# RKO Python: release assessment and proposed completion design

Date: 2026-10-17

Status: approved by the user on 2026-10-17. Implement incrementally, committing and pushing each validated implementation. No production code changed during assessment.

## Goal

Deliver a reusable Python Random-Key Optimizer inspired by RKO C++ v2: problem-specific decoding/objective evaluation, cooperating metaheuristics, adaptive parameter control, understandable configuration, repeatable experiments, and dependable packaging. Scientific Python libraries are references for API quality, not mandatory dependencies. Do not turn the optimizer into a machine-learning estimator solely to imitate scikit-learn.

The implementation under review is `RKO-Agent/rko_agent`, not the separately published `RKO_Python` repository. The destination for the final release remains to be confirmed; do not overwrite either repository to consolidate them.

## Verified baseline

Validation used the current working tree, including pre-existing uncommitted changes, on WSL/Linux with standard CPython 3.14.8. The existing Windows `.venv` was left untouched. uv was installed under `/tmp/rko-validation-tools/packages`, with the validation environment at `/tmp/rko-validation-env`.

Commands, from `rko_agent`, using that uv executable and `UV_PROJECT_ENVIRONMENT=/tmp/rko-validation-env`:

- `uv run --locked pytest src/rko/tests -q`: **48 passed**.
- `uv run --locked ruff check . --statistics`: passed.
- `uv run --locked ruff format --check .`: one file needs formatting, `src/rko/examples/run_kp_cpp_instances.py`.
- The current CI test command, `uv run --locked python -m unittest discover -s src/rko/tests -t src -p 'test_*.py'`, runs **8 tests**, not the full pytest suite.

The existing Knapsack example was run with its default ten-algorithm configuration and a requested one-second search budget, without changing parameters. A separate exact 0/1 Knapsack dynamic-programming calculation established reference optima:

| Instance | Exact profit | Three RKO trial profits | Feasible | Observed wall times |
| --- | ---: | --- | --- | --- |
| kp10.txt | 31 | 31, 31, 31 | all | 1.108–1.429 s |
| kp50.txt | 149 | 148, 147, 148 | all | 1.372–1.653 s |

All six returned costs equaled negative decoded profit. These are unseeded smoke trials on small reference instances, not statistical evidence of performance or production readiness. No multicore speedup or C++ runtime comparison was measured.

## Evidence and release blockers

1. **Threads do not establish CPU multicore execution.** `src/rko/orchestration/execution.py` uses `threading.Thread`; `components/solution_pool.py` uses a regular list and `threading.Lock`. Standard CPython CPU-bound Python loops remain subject to the GIL. NumPy may release it for some operations, but that is not a dependable execution strategy for arbitrary problem callbacks.
2. **A direct process substitution breaks shared cooperation.** The current pool is not process-shared. Passing independent copies would silently remove elite exchange, affecting IPR and pool-aware searches.
3. **The existing benchmark callback is not spawn-compatible.** `examples/run_kp_cpp_instances.py:make_cost` returns a nested function. `pickle.dumps(make_cost(instance))` fails with `PicklingError` on the tested interpreter. Use a module-level callable carrying the instance rather than adding a serializer dependency.
4. **Timing is not a hard deadline.** Each algorithm starts its own timer; local searches and initialization need review for budget propagation. Observed end-to-end time exceeds the requested search budget. Document process startup separately, and do not promise hard cancellation of arbitrary user callbacks.
5. **Configuration is only partially wired.** `parameters/config.toml` declares `strategy`, `max_runs`, and `debug`, but `orchestration/configuration.py:parse_run_config` returns only control, pool size, and active algorithms. Declared settings must either work or be removed from the public contract.
6. **Existing algorithm tests are not correctness certification.** `tests/metaheuristics/test_metaheuristics_pytest.py` primarily checks construction and control flags, rather than executing each actual algorithm and validating its output. Differential tests against C++ components are still needed before claiming parity.
7. **CI is misplaced and incomplete.** The tracked workflow is under `rko_agent/.github/workflows/ci.yml`, not the repository-root `.github/workflows/` scanned by GitHub Actions. It also invokes unittest rather than the complete pytest suite, and only configures Ubuntu. Fix the location, working directory, runner command and platform matrix.
8. **Distribution is unfinished.** `pyproject.toml` still has a placeholder description, requires Python >=3.14, and has no explicit build-system configuration. `rko_agent/README.md` is empty. Validate a built wheel outside the source tree, including TOML resources; do not assume import via pytest's `pythonpath` proves installability.
9. **Repository hygiene needs care.** Bytecode and egg-info files are tracked; numerous source files already have local changes. Do not reset, automatically stage everything, or commit generated artifacts.
10. **Pool ownership is weak.** `SolutionPool.best` and `get_elite` expose mutable key lists from internal entries. Review copying, non-finite costs, and invalid vectors at the public boundary.

## Proposed architecture

### Public API and compatibility

Keep `from rko import run` and the current `(best_keys, best_cost)` return working for the first milestone. Retain `decoder`/`cost` separation and existing TOML parameter files. Avoid a wholesale framework rewrite.

Expose execution mode and a worker budget explicitly. Provide a serial mode for debugging and tests; processes are the intended multicore mode. A supported process callback must be importable/pickleable, typically a module-level function, `functools.partial`, or callable class with serializable state. Reject incompatible callbacks before starting workers, with an actionable error. Document the `if __name__ == '__main__'` requirement and script execution for Windows/spawn.

A richer result with decoded solution, objective, elapsed time, seed, evaluations and improvement history belongs in a subsequent compatible API addition rather than silently changing the tuple contract.

### Process coordination

Use the standard library with an explicit spawn context for consistent Windows/Linux behavior. Construct algorithm instances inside workers instead of attempting to pickle objects containing local locks.

For the initial correctness milestone, use one process per selected metaheuristic and require that the selected portfolio fits the explicit worker budget. If it does not fit, report the mismatch rather than silently queueing full-duration jobs or dropping algorithms. This is a proposed limited first milestone, not the final adaptive scheduler. The documentation must make process counts visible so users do not accidentally oversubscribe their machine.

Keep one authoritative elite pool behind a managed object/proxy as the simplest initial process-sharing implementation. Preserve insertion and elite-query semantics. Measure communication cost before considering shared memory or batched updates; a manager may be a correctness baseline without being a performance win.

Use a common search deadline once workers are ready. Distinguish startup time from search time and report end-to-end elapsed time. Exceptions must identify the algorithm, stop or cancel the remaining work, preserve the original cause and leave no orphan workers or manager process. Clean up after keyboard interrupts. Forced termination must remain a last resort, not normal completion.

### Randomness and reproducibility

Add a run seed and derive distinct worker seeds in a stable order; cover both Python `random` and NumPy randomness used by the current code. Seeded wall-clock-limited cooperation is still scheduling-dependent. Promise repeatable seed allocation, not bit-identical multicore outputs. Introduce an evaluation/iteration-budget test mode where exact determinism is needed.

### Problem validation and experiments

First validation target: the existing Knapsack reader and decoder, with spawn-compatible objective, independent feasibility/cost checks and exact optima for the two small instances.

Release validation additionally needs a larger, versioned public Knapsack dataset or a user-provided operational instance with provenance and a reference objective. A small toy instance alone does not meet the user's real-problem requirement. Do not silently substitute synthetic data for operational data.

Report objective, feasibility, reference gap, wall time, worker count, selected algorithms, control mode, seed, platform and Python version. Compare serial, existing threads and processes under equal declared budgets and repeated trials. Record quality and throughput separately: stochastic objective improvements are not direct measurements of CPU speedup. Add a fixed-work CPU benchmark and capture child process IDs to establish actual process execution. Do not require universal speedup in CI or invent performance thresholds before measuring overhead.

### Quality and packaging

Respect `AGENTS.md` type hints/docstring requirements and uv tooling. Add integration tests at the public API, not only mocks. CI must run pytest and Ruff at the repository root with the correct working directory on Linux and Windows. Validate wheels and TOML resources in a clean environment. Use standard `logging`, avoiding output files and plots as unavoidable solver side effects.

Retain Python 3.14 initially; evaluate lowering the supported version separately after checking actual syntax and dependency requirements. Do not add scikit-learn, joblib, SciPy, or other dependencies without a concrete capability that warrants them.

## Delivery order and acceptance criteria

1. **Reliable baseline:** document the current behavior, make the benchmark callback pickleable, add independent Knapsack assertions, fix CI discovery/location and the one formatting failure without sweeping unrelated changes.
2. **Multicore correctness:** process-shared pool; spawn worker entry point; explicit worker budget; serial/process public mode; seed allocation; input and callback validation. Test elite exchange across real processes, multiple PIDs, failed workers, cancellation/cleanup, invalid callbacks and cost/key consistency. Run the actual registered metaheuristics on small bounded problems.
3. **Timing and performance:** propagate deadline checks through initialization and expensive local-search loops; distinguish overhead; run fixed-work and repeated Knapsack comparisons. Profile before replacing the baseline manager pool.
4. **C++ feature parity:** review BRKGA-CS, IPR, GRASP, Q-learning and neighborhoods against local `RKO_Cpp_v2.0` and the upstream reference. Wire or remove unused settings. Establish correctness tests before declaring parity; avoid requiring stochastic trajectories to match language-for-language.
5. **Professional release:** stable documented API, installable wheel, packaged parameters, reference benchmark report, clear reproducibility limitations, working CI and release checklist. Reconcile the RKO-Agent implementation with the separate RKO_Python repository only after the destination is confirmed.

## Remaining user decisions

- Design and staged implementation approved; user requests a commit and GitHub push per implementation.
- Continue development in `RKO-Agent/rko_agent` on branch `rko`. Publication through the separate `MarcosPTProenca/RKO_Python` repository remains unconfirmed.
- Select or provide the larger real-world validation instance. Existing Knapsack benchmarks are the immediate validation target, not a substitute for this decision.

## Review

Self-reviewed as the implementing maintainer; no independent subagent review was available. Checked that the design preserves existing local edits and public return values, covers spawn serialization, shared-state semantics, worker limits, timer limitations and Windows validation. No commits or production-code changes were made as part of this assessment.
