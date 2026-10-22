# Baseline contracts and fixed-work diagnostics

This checklist anchors performance experiments to tested behavior. It is not a
claim that Python matches the complete C++ solver, nor a measured bottleneck
ranking. The [performance target](performance.md) remains the acceptance contract.

## Source and baseline identity

The starting revision for this investigation is
`87846d6537627e086caf64ee6e9e58685caaf816`. Its
[CI run](https://github.com/MarcosPTProenca/RKO_Python/actions/runs/39790181646)
succeeded on Ubuntu and Windows, including source checks and installed wheel/sdist
smokes. The Ubuntu suite reported 956 passing tests. This is baseline correctness
and packaging evidence, not performance certification.

For every new measurement retain the actual revision, dirty state, helper/config/
source hashes and environment, not just the package version. Do not reuse the
protected historical benchmark's output or cache, or run a competing experiment
on its host while it remains active. Current-source observations must remain
separate from the historical Python `7ee93ca` comparison.

## Contracts that optimizations must preserve

Paths below are relative to `src/rko/tests/`. These existing tests are executable
anchors, not an assertion that every possible behavior is exhaustively specified.

| Contract / oracle | Regression anchor | Boundary or intentional deviation |
| --- | --- | --- |
| Decoder mutation and objective-retained snapshot isolation | `rko/test_stopping.py` | Both protective copies have observable safety purposes |
| Cooperative stop checks, finite objectives and exception propagation | `rko/test_stopping.py` | An active arbitrary callback cannot be forcibly interrupted; first valid evaluation can exceed budget |
| Completed counts, assigned seeds and immutable results | `rko/test_search_metadata.py`, `rko/test_result_metadata.py` | Decoder calls and completed objectives need not be equal |
| Library-owned RNGs and callback randomness | `rko/test_rng_isolation.py` | Equal seeds across languages do not imply equal random tapes |
| Spawn, failure cleanup, stable worker seeds and managed elites | `rko/test_process_execution.py` | Native code does not automatically eliminate IPC or process startup |
| Nominal GRASP candidate/count rules and sparse extreme steps | `metaheuristics/test_grasp_line_search.py`, `metaheuristics/test_grasp_construction.py` | Exact-ratio Python integers safely extend reference bounds; no fixed-width overflow substitution |
| GRASP h and unused alpha policies | `metaheuristics/test_grasp_h_policy.py`, `metaheuristics/test_grasp_alpha_contract.py` | Preserve documented adaptive effects, not an invented alpha RCL |
| IPR candidate trace, partial blocks, signed zero and no-op pruning | `metaheuristics/test_ipr_relink.py` | Pruning deliberately differs in callback counts; first-tie/path rules remain tested |
| Nominal C++ neighborhood transitions | `components/test_cpp_operator_contracts.py` | Controlled deterministic kernel oracle, not full-driver bitstream equivalence |
| Sign-safe finite rewards and actual adaptive transitions | `components/test_reward_contracts.py` | Python deliberately corrects inherited behavior rather than reproducing defects |
| Shared initialization and optional prefill accounting | `rko/test_pool_prefill.py`, `rko/test_driver_initialization.py` | Capacity is not a seed population; prefill has a separate allowance |
| Standalone operators, legacy and public solver callers | `rko/test_solver.py`, `rko/test_rko_main_pytest.py`, `metaheuristics/test_standalone.py` | Preserve return formats and validation; scheduling backend is not a native-engine selector |

See [C++ compatibility](cpp-compatibility.md), [initialization](driver-initialization.md)
and the linked GRASP/IPR documents for the reference revision and deliberate
corrections. Remaining full-algorithm transitions, initialization, restart and
stopping equivalence require additional evidence. Test coverage is not scientific
quality evidence or a reason to skip independent objective/feasibility validation.

## Reproducible diagnostic entry point

Run from the repository root on noncompeting resources:

```bash
uv run --locked python -m benchmarks.performance_profile \
  --algorithm SA --workload sphere --dimension 20 --evaluations 64 --seed 200

uv run --locked python -m benchmarks.performance_profile \
  --algorithm SA --workload sphere --dimension 20 --evaluations 64 --seed 200 --profile
```

Both commands emit one JSON object. They reuse the existing `fixed_work` search
and its callback boundary, rather than a replacement optimizer. Supported searches
are SA, GA, BRKGA, GRASP, MultiStart and seeded IPR; workloads are sphere, rugged
and stable ordering. IPR's ten initial elite scores are reported separately from
the completed search evaluation cap. The runner restores caller Python/NumPy
random streams; use it in a standalone process, not concurrently with other RNG
users in the same process.

The record includes:

- Schema version, restricted scope, profiled flag, work/CPU/wall observations and
  result/pool/RNG replay fingerprints from the existing runner.
- Actual imported RKO/NumPy locations, Python/NumPy versions, source and bundled
  TOML hashes, lockfile/build metadata and benchmark-helper hashes.
- Git revision, status and tracked-diff hash when Git is available. Missing Git
  observations are null; source hashes remain available. This is not a complete
  archive of untracked files, installed dependencies or the execution environment.
- CPU count/affinity observations, root cgroup-v2 quota text if accessible and
  whitelisted native-thread environment settings. These do not certify effective
  hierarchical quotas, actual native teams, host isolation or reproducible load.
- With `--profile`, the top 20 functions by exclusive cProfile time, with inclusive
  time and primitive/total calls. Inclusive values overlap: do not sum them.

`result.seconds` and `cpu_seconds` cover search only; imports, provenance, algorithm
construction, pool seeding and process startup/shutdown are excluded. Function
profiling covers the existing runner including construction and seeded-pool setup,
so its scope is explicitly different. Profiled times are diagnostic and must not
be used as acceptance timings. cProfile cannot explain all native internals, and
wall profiles are not memory measurements.

This first diagnostic does not yet cover whole public-API invocations, process
portfolios, realistic expensive callbacks, stage counters, peak process-tree memory,
real-clock adaptive quality or C++ equal-resource comparisons. Follow the
[existing startup probes](../benchmarks/README.md#spawn-startup-and-installation-layout)
for separate import/spawn evidence. Do not extrapolate a tiny CI smoke to speed,
quality, a native-backend choice or release readiness.
