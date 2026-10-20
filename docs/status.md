# Current limitations

Status reviewed on 2026-10-20. This development version is **not release-ready**.
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
coverage. Library random draws now use privately owned per-search Python/NumPy
streams in all backends, including seeded threads; standalone operators retain
their global-RNG behavior. Custom callbacks must own their stochastic state.

## Outstanding

- **Callback concurrency:** library RNGs are isolated, but user callbacks and
  operator overrides must manage their own randomness and mutable state. Global
  callback draws are neither implicitly seeded nor rolled back. Independent
  solver instances may overlap; simultaneous calls on the same mutable instance
  are not supported.
- **Worker scheduling:** omitted/`None` `n_jobs` now caps process search workers to
  affinity-aware usable logical CPUs (one if unavailable); explicit positive caps
  still override discovery. Every selected algorithm remains assigned. CPU capacity
  is recorded once per solve for immutable result accounting. Round-robin groups
  keep equal nominal slices under the common deadline; unused time is not
  redistributed, and callbacks may exhaust later slices. Native threads,
  concurrent solver instances and container quotas not reflected by discovery can
  still oversubscribe hardware. Native-thread controls, adaptive load balancing and
  broader RSS/IPC profiles remain open. A controlled Linux comparison across 36
  solves verified all seeded initial candidates; the identified reference measured
  sampled summed RSS around 287 versus 560 MiB for four automatic versus ten
  dedicated workers. This is not unique physical memory, fixed-work throughput or
  scientific-quality evidence. See [migration/limits](process-workers.md) and
  [benchmarks](../benchmarks/README.md#bounded-process-worker-resources).
- **Algorithm contracts:** complete C++ parity/deviation specifications and
  scientific invariants remain, including SA/GRASP adaptive behavior. Six local
  neighborhood cases now match compiled C++ kernels: strategy 1 continues the
  sweep, and supplied indices are reshuffled. See [compatibility](cpp-compatibility.md).
  Corrected Q/reward/grid/IPR behavior is not a promise of unchanged C++ trajectories.
- **Configuration/results:** named offline hyperparameters now accept validated
  Python overrides; adaptive grids still require TOML. Results now include finite
  objective counts, per-search stopping classifications, actual seeds, initial
  scalar/grid snapshots, worker settings and runtime versions across all backends.
  Full callback/data/source provenance and adaptive trajectories are not recorded.
  Full API/error documentation and a supported-version/release policy are needed.
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

A domain-neutral ten-algorithm process reference now measures startup latency,
observed worker counts and sampled parent/child RSS. Setting `n_jobs=4` retained
all ten algorithms and used four search workers rather than ten. On this WSL2
reference, median summed sampled RSS fell from about 482–483 MiB to about 248 MiB,
and one-second-budget end-to-end times fell from 8.12–11.25 s to 6.64–8.72 s.
Per-algorithm time and cooperation differ, so this is a resource/short-run latency
comparison, not equal-work throughput or an optimization-quality improvement.
RSS sums double-count shared pages and are sampled, not exact physical-memory
high-water marks. See [benchmarks](../benchmarks/README.md) for reproduction.

IPR now uses NumPy slice assignment for multi-gene guide blocks and direct
assignment for single-gene blocks, preserving full candidate copies and the
original path/callback ordering. Across 189 fixed-work numerical/permutation
pairs, best keys, costs, counts, final elites and RNG states matched exactly.
In one reference, 1,000-key searches were 1.30–2.47× faster and 10,000-key searches
1.22–3.46× faster; small-vector results were mixed, including regressions.
Isolated traced relinking peaks were unchanged. These are serial IPR results,
not whole-portfolio, process, quality or native-parity claims; see
[benchmarks](../benchmarks/README.md).

Managed IPR now transfers only its two sampled elite entries rather than the
whole pool when occupancy exceeds two. Ranks are drawn in the requesting process
using the same RNG pattern, and both entries are copied under one server lock.
Local/custom pools retain the existing protocol and snapshot path; there is no
cache. Two warmed production benchmark runs passed 162 fixed-work comparisons
including final-pool/RNG fingerprints. In the latest reference, 1,000-key managed
IPR searches were 1.15–1.45× faster and 10,000-key searches 1.11–2.08× faster;
ten-entry returned data was about 80% smaller. These are managed-pool IPR results,
not whole portfolios, process-startup gains, total CPU, RSS or scientific-quality
claims. Concurrent timed trajectories can change with RPC interleavings.

Adaptive Q-state graph construction now indexes finite numeric states by
all-but-one-coordinate signatures instead of comparing unrelated state pairs.
Ascending actions, initial Q-values and RNG draws are preserved; exotic/nonfinite
standalone values retain the pairwise path. Three fixed-work PSO benchmark runs
passed 162 exact comparisons with a frozen adaptive clock; one reference measured
2.91–3.85× at 32 keys and 1.24–1.37× at 1,000 with a 625-state grid. Isolated graph
initialization improved substantially as grids grew, but signature memory can
increase small-grid peaks and dense output remains quadratic. Real cold-spawn
trials confirmed a smaller graph phase, not a reliable end-to-end startup gain:
imports/spawn still dominate. Parent constructor validation and fresh parameter
reads remain intact. See [benchmarks](../benchmarks/README.md) for limits.

A separate 18-solve installation-layout comparison identified substantial WSL
startup overhead from Windows-mounted dependencies and editable source. With
identical locked versions and verified source/TOML bytes, Linux-local non-editable
installation reduced one/four-worker end-to-end medians from 5.51/6.17 seconds to
1.56/1.79 seconds. Moving only dependencies to Linux gave 3.55/4.26 seconds. These
are environment-specific setup gains, NOT library-code, steady-state throughput,
RSS or quality improvements; imports/spawn and callback overruns remain. No worker
architecture or validation was changed. See the identified reference in
[benchmarks](../benchmarks/README.md#spawn-startup-and-installation-layout) and
[WSL setup](running.md#wsl-startup-and-virtual-environment-placement).

A further memory-targeted refinement constructs Q-state records only after their
parameter combinations pass feasibility filtering. Two repeated synthetic slice
benchmarks reduced traced graph-construction peaks by 33.7% (625 combinations,
125 accepted states) and 44.4% (2,401 combinations, 343 accepted). All-accepted
grids showed no meaningful peak reduction; interpreter caches affect retained
traces, and these are not RSS measurements. Another 108 fixed-work adaptive PSO
pairs matched exact fingerprints, but timings were mixed: this does not establish
full-search, real adaptive-clock or cold-start gains. Predicate payload identity,
axis snapshots, action order and initialization draws remain protected by tests.

RNG ownership regression coverage now observes global states inside callbacks,
forces two independently seeded serial solves to overlap, checks all registered
algorithms in offline/adaptive serial/thread execution, and protects nested scope
restoration. A separate trusted pre-isolation replay passed 342 fixed-work pairs
with exact result/pool/RNG fingerprints. Short timing comparisons were mixed;
this closes the library-owned RNG contamination gap, not a speed or scientific
quality gap. Stochastic custom callbacks still need explicitly owned generators.

Detailed working audits and plans are kept locally and excluded from Git. Source
history preserves prior evidence; this page is the maintained public summary.
