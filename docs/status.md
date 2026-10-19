# Current limitations

Status reviewed on 2026-10-19. This development version is **not release-ready**.
Removing internal audit documents does not mean their outstanding work is done.

## Delivered

Class-based RKO API and immutable results; usable installed wheel/sdist resources;
GA parent-fitness ownership, current Q maxima, sign-safe rewards and IPR remainder
coverage; named/validated parameter grids and atomic saves; callback-boundary
stopping, decoder isolation and visible thread failures; scalar pool-count RPCs
and non-busy IPR waiting. A single-instance `rko` command accepts external TOML
configuration while retaining batch/module invocation. The CLI now shows live,
timestamped new-best events and periodic pool status during plateaus (`--quiet`
suppresses them); library progress is opt-in through `verbose=True`. These have regression and installed-artifact
coverage.

## Outstanding

- **RNG isolation:** serial execution seeds/restores global RNGs, so simultaneous
  calls are not safely isolated. Thread mode cannot accept a per-search seed.
- **Worker scheduling:** defaults can oversubscribe hardware. A portfolio larger
  than `n_jobs` is rejected, not fairly scheduled. Native-thread limits, peak RSS
  and fixed-work IPC profiles remain unmeasured.
- **Algorithm contracts:** complete C++ parity/deviation specifications and
  scientific invariants remain, including SA/GRASP adaptive behavior. Six local
  neighborhood cases now match compiled C++ kernels: strategy 1 continues the
  sweep, and supplied indices are reshuffled. See [compatibility](cpp-compatibility.md).
  Corrected Q/reward/grid/IPR behavior is not a promise of unchanged C++ trajectories.
- **Configuration/results:** programmatic hyperparameter configuration, evaluation
  counts and explicit stop reasons are incomplete. Full API/error documentation
  and a supported-version/release policy are still needed.
- **Stopping:** active callbacks cannot be interrupted cooperatively, blocked
  threads cannot be safely killed, and standalone operators receive no RKO
  deadline. A first valid evaluation may exceed the requested duration.
- **Scientific quality:** the C++ threshold decoder remains substantially worse
  than greedy. More instance families, seeds, fixed-work measurements and
  domain-specific validation are needed.
- **Licensing:** confirm imported-code ownership/terms before release; see
  [NOTICE](../NOTICE). An existing license file does not settle that review.

The hot blending kernel now batches offspring selection after consuming the same
Python random draws in the same order. A reproducible 1,000-key serial SA synthetic
benchmark measured median evaluation throughput increasing from 3,150 to 4,150
evaluations/s across five paired seeds; the pinned Knapsack process benchmark did
not show a uniform quality gain from that kernel alone. The change preserves draw
order but may have tiny floating-point differences for unusual non-key numeric
inputs.

The GA now releases the previous population after copying selected parents and
before allocating offspring, reducing peak traced allocation in a synthetic
one-generation, 100 × 5,000-key probe from 11.72 MiB to 8.08 MiB (-31.0%) with
identical seeded objective output. This isolates an internal GA allocation path;
it is not a whole-solver RSS claim. Reproduction and the limitations of this
probe are in [benchmarks](../benchmarks/README.md).

Shared callback sessions now retain detached NumPy incumbent snapshots until a
public result list is needed. A 10,000-key callback allocation probe reduced
retained traced incumbent allocation by 75.1% and peak allocation by 69.9%.
Removing a redundant elite-pool list copy reduced a separate accepted-insertion
allocation probe's peak by 32.4%. Callback isolation and validation are preserved;
these are isolated allocation results, not process RSS or whole-search speedups.
A fixed-evaluation runner now covers numerical and permutation workloads across
SA, GA and BRKGA, with result and RNG fingerprints for cross-revision comparisons.

PSO batches independent genes at 32+ dimensions while preserving sequential
particle/global-best updates and Python RNG draw order. Paired synthetic searches
with real local search were about 1.4–1.8× faster at 32/100 keys in one reference
run; 1,000-key gains were smaller and less consistent between runs. All 108 paired
searches reproduced exact best keys, costs, counts and RNG states. Batching adds
O(n) temporary scratch, not a memory benefit. These measurements do not establish
process/portfolio speed, optimization quality or native-code parity; reproduction
and limitations are in [benchmarks](../benchmarks/README.md).

Detailed working audits and plans are kept locally and excluded from Git. Source
history preserves prior evidence; this page is the maintained public summary.
