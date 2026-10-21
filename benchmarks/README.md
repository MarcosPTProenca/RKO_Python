# Performance benchmarks

Each section identifies its workload and limits. Synthetic fixed-work and
allocation probes complement the historical Knapsack reference; no single case
establishes general optimization quality or native-code performance parity.

## Spawn startup and installation layout

```bash
uv run --locked python benchmarks/startup_stages.py
```

This guarded benchmark instruments real parent validation, manager startup,
worker entry/preparation and first decoder calls. It checks every observed
worker's first keys against its reported execution seed, validates final keys/
objective and reports environment/source paths. `--repeats 1` supports alternating
separate interpreter environments; the default runs three one/four-worker pairs.

Explicit reference: [startup-layout-reference.jsonl](startup-layout-reference.jsonl),
2026-10-19 WSL2, four available CPUs, CPython 3.14.8 / NumPy 2.4.3, baseline
`efc40e3`. Eighteen solves alternated three installation layouts, using the same
32 installed distribution name/version pairs and byte-identical 55 installed
Python/TOML files. All used the full ten-algorithm online portfolio, 128 keys,
seed 42 and a 0.2-second common search budget. The checkout, benchmark script,
working directory and temporary observation filesystem stayed fixed.

| Installation layout | Workers | End-to-end median (s) | Manager-start median (s) | Latest first-callback median (s) |
| --- | ---: | ---: | ---: | ---: |
| Windows-mounted environment + editable Windows-mounted source | 1 | 5.507 | 2.336 | 5.116 |
| Linux-local environment + same editable source | 1 | 3.550 | 1.468 | 3.192 |
| Linux-local environment + non-editable Linux-local installation | 1 | 1.559 | 0.494 | 1.115 |
| Windows-mounted environment + editable Windows-mounted source | 4 | 6.174 | 2.298 | 5.746 |
| Linux-local environment + same editable source | 4 | 4.262 | 1.585 | 3.840 |
| Linux-local environment + non-editable Linux-local installation | 4 | 1.786 | 0.493 | 1.363 |

The last layout reduced these environment-specific end-to-end medians by about
71–72%. This is **installation/filesystem evidence, not a library optimization**.
Latest first callback means the maximum across workers in each trial, then the
median across three trials. Parent construction medians were 0.111–0.129 s for
the mounted installation and 0.009–0.014 s for the local non-editable installation;
removing fail-fast validation would miss most of the observed delay.

Fresh processes do not imply cold OS caches. Instrumentation, WSL storage and host
load affect timings; preliminary runs varied substantially. Budgets differ by
worker cap and timed trajectories may differ: these are not equal-work throughput,
RSS, quality or native-Windows results. Imports and spawn remain nonzero even in
the fastest layout. No import protocol, worker architecture or validation was
changed. See [WSL setup guidance](../docs/running.md#wsl-startup-and-virtual-environment-placement).

## Bounded process-worker resources

A positive `n_jobs` now keeps the complete selected portfolio while limiting
search processes. Assignments are round-robin. At dispatch, a worker divides its
remaining common-deadline time among its remaining searches. Shorter groups can
use their entire budget; early completion benefits searches queued in that worker.
No new deadline, cross-worker work stealing or restart of finished searches is added. `n_jobs=None` now defaults to
process-usable logical CPUs, capped by portfolio size (one if discovery is unavailable).
Explicit positive limits override CPU discovery. One additional process hosts the pool;
BLAS/OpenMP threads are outside the search-worker limit.

```bash
uv run --locked python benchmarks/process_budget.py > /tmp/rko-process-budget.jsonl
```

The updated script compares automatic defaults against an explicit full-portfolio
worker limit and verifies every seeded initial candidate, worker count and result.
An identified [automatic-default reference](process-auto-reference.jsonl),
2026-10-20, **predates remaining-time scheduling** and retains fixed longest-group
slices. It uses the same Linux-local editable source/dependency environment for
both variants: four available CPUs, CPython 3.14.8 / NumPy 2.4.3, ten algorithms,
offline control, 128 keys and a one-second common budget. Three seeds per neutral
adapter, with alternating trial order, gave these medians:

| Adapter | Requested workers | Observed workers | End-to-end (s) | Sampled parent/children RSS sum (MiB) |
| --- | --- | ---: | ---: | ---: |
| Sphere | Automatic (`None`) | 4 | 2.550 | 287.03 |
| Sphere | Explicit 10 | 10 | 3.856 | 560.58 |
| Ordering | Automatic (`None`) | 4 | 2.413 | 287.19 |
| Ordering | Explicit 10 | 10 | 3.432 | 560.41 |

Two earlier complete repetitions also verified all initial vectors and worker
counts, with sampled RSS medians around 287/560 MiB and variable latency medians.
This is a worker-resource comparison within one source/environment, NOT a
filesystem migration or fixed-work throughput/quality result. All 36 solves
retained the full selection; different slices and live cooperation change search
work/results. RSS sums double-count shared pages and are sampled, not unique
physical memory or exact peaks. No native-thread cap or machine-wide admission
control is implied. See [migration/limits](../docs/process-workers.md).

The historical reference below predates automatic defaults and compares explicit
four-worker scheduling against the then-default ten dedicated workers:
2026-10-19, four-CPU WSL2, CPython 3.14.8 / NumPy 2.4.3, GIL enabled,
packaged ten-algorithm portfolio, offline control, 128 keys and a one-second
common search budget. Three seeds per numerical sphere/permutation adapter,
alternating dedicated/limited execution order, produced these medians:

| Adapter | Worker limit | Observed search workers | First decode (s) | End-to-end (s) | Sampled worker RSS sum (MiB) | Sampled parent/children RSS sum (MiB) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Sphere | None | 10 | 6.632 | 8.122 | 390.4 | 481.9 |
| Sphere | 4 | 4 | 5.465 | 6.637 | 156.3 | 247.6 |
| Permutation | None | 10 | 9.772 | 11.254 | 391.7 | 483.4 |
| Permutation | 4 | 4 | 7.384 | 8.721 | 156.6 | 248.1 |

All twelve runs recorded every algorithm's seeded first decode, respected the
worker cap and returned finite, independently checked objectives and valid keys.
Memory sampling uses Linux procfs every ~20 ms. Reported peaks are maxima of
sampled RSS sums, not exact high-water marks or unique physical memory; shared
pages are counted once per process. The total includes the coordinator, manager,
workers and resource tracker. Other platforms report unavailable RSS as null.
The observation decoder adds instrumentation overhead to both variants.
Absolute startup times varied materially between reference runs on this host;
all six final limited/dedicated trial pairs used less RSS and elapsed time with
four workers, but do not treat these times as portable startup guarantees.

**These are different budget allocations**, not equal-work speedups. Ten searches
on four workers in these HISTORICAL references received at most a nominal one-third
slice each, and shorter groups finished early without redistributing idle time. First-decode latency is an
observable startup bound, not pure import time. Neither long-budget performance
nor better optimization quality is established. Active callback overruns can leave
queued algorithms less time or no time. Native thread policy and cross-worker load
balancing remain separate work; local remaining-time allocation is measured below.

An exploratory versioned elite-snapshot cache made repeated unchanged large
snapshot queries faster, but corrected full-search trials did not demonstrate a
reliable general benefit and small cases sometimes regressed. It was discarded;
no cache or additional retained worker snapshots were shipped.

## Remaining-time worker scheduling

```bash
uv run --locked python benchmarks/scheduling.py --baseline-source /absolute/path/to/trusted-baseline/src
```

Use an archived **ff70a92** checkout as the baseline. This executes trusted local
source in fresh interpreters; do not point it at untrusted downloaded Python.
Place both source trees on the same filesystem and use one interpreter/dependency
environment. The runner verifies the actual imported source paths and copies the
same one-thread native launch settings into both policies without mutating itself.

[Identified reference](worker-scheduling-reference.jsonl): four usable CPUs,
CPython 3.14.8 / NumPy 2.4.3, Linux-local sources/dependencies, offline parameters,
64 keys, 1.2-second common budgets. Two balanced-order repeats over three seeds,
sphere/ordering objectives and three portfolios produced **72 real spawned solves**.
All algorithm seeds, initial keys, worker counts and independent result costs passed;
none reported `not_started`. No full-trajectory equivalence is implied.

| Portfolio / workers | Median unused session time, fixed | Remaining-time policy |
| --- | ---: | ---: |
| Four searches / two workers, sphere | 0.0017 s | 0.0017 s |
| Five searches / two workers, sphere | 0.4015 s | 0.0021 s |
| Five searches / two workers, ordering | 0.4003 s | 0.0018 s |
| Default ten / four workers, sphere | 0.7972 s | 0.0024 s |
| Default ten / four workers, ordering | 0.7989 s | 0.0061 s |

Unused time is summed per worker as max(0, budget minus its search-session wall
seconds). The ten-search cases have 4.8 worker-seconds available. Sessions include
waiting and callback overruns; this is **not a CPU-utilization measurement**.
Dispatch/collection overhead is outside session timing. Dedicated and balanced
workers do not inherently gain extra time from this policy.

The measured benefit is reclaiming a known idle tail in uneven groups, not lower
end-to-end latency or universal evaluation throughput. Paired evaluation ratios
(current/fixed) ranged **0.918–1.063** across the six case/workload medians. Costs
were mixed: uneven ordering's median was 43707 versus 43719 (known minimum 43680),
while the default portfolio sphere reached zero under both policies. More allocated
work is not necessarily better search quality; live elite cooperation and unequal
algorithm budgets change trajectories. Broader scientific-quality validation remains
open. Early-return reuse is covered by deterministic worker tests; built-in searches
generally consume their limit, so these real measurements primarily test shorter groups.

See [allocation contract and migration limits](../docs/process-workers.md).

## Native-thread launch controls

```bash
uv run --locked --with threadpoolctl==3.7.0 python benchmarks/native_threads.py
```

This diagnostic-only dependency is not added to RKO runtime or dev dependencies.
The runner launches fresh interpreters using copied inherited/one-thread native
environments and leaves its own environment/runtime limits unchanged. Three repeats
cover sphere, matrix-vector and dense matrix-matrix callbacks with one/four actual
spawned population searches. Oversized populations stop at 64 finite evaluations,
before full generations or asynchronous elite feedback. Assigned initial keys,
complete candidate fingerprints, counts and independent costs are checked; native
teams are inspected IN workers, not inferred from a parent-only controller.

[Identified reference](native-threads-reference.jsonl): 2026-10-20, CPython 3.14.8,
NumPy 2.4.3 / OpenBLAS 0.3.31.dev, four usable CPUs, 512 keys, same Linux-local
source/dependency environment for both variants. The final dense four-worker prefix
measured slowest-search medians **6.016 vs 3.491 s**, end-to-end **7.564 vs 4.860 s**
and summed callback process CPU **18.574 vs 7.967 s**, inherited four-thread teams
versus one per worker. Two complete passes preserve all 36 paired candidate/count
comparisons (72 primary solves) plus four parent-only negative controls. The earlier
pass also improved dense callbacks, with variable absolute timings. Cheap/vector
search timings were mixed. Parent-only negative controls kept workers at four
threads even while the parent reported one.

This is a fixed initialization-prefix/workload-specific result, not a full-solver,
quality or native-language parity claim. Callback CPU includes native worker threads
but excludes manager/coordinator CPU. Warm-up is excluded from callback timing but
included in search/end-to-end timing. BLAS roundoff is checked tolerantly. The private
benchmark stop signal is not a supported callback protocol. Windows CI runs only:

```bash
uv run --locked --with threadpoolctl==3.7.0 python benchmarks/native_threads.py --repeats 1 --dimension 8 --evaluations 2 --workers 1
```

No Windows performance comparison or automatic library-level native cap is claimed.
See [launch recipes, scope and sources](../docs/native-threads.md).

## Adaptive state-graph initialization and startup

Adaptive controllers formerly compared every state against every other state to
find transitions differing in at most one parameter. Exact-width finite builtin
numeric states now use all-but-one-coordinate signature indexes; candidate labels are
sorted before weights are drawn. State/filter order, duplicate values, action
order, initial weights and first-winner maxima are unchanged. Other scalar types
and nonfinite standalone inputs keep the original pairwise behavior; no input
coercion, skipped validation, grid caching or default parameter change is used.
Dense/duplicate-heavy graphs still need all their output edges and can remain
quadratic; indexing adds temporary memory, not a universal memory improvement.

```bash
uv run --locked python benchmarks/q_learning.py > /tmp/rko-q-learning.jsonl
uv run --locked python benchmarks/startup.py > /tmp/rko-startup.jsonl
```

Reference: 2026-10-19, four-CPU WSL2, GIL-enabled CPython 3.14.8 / NumPy 2.4.3.
The graph benchmark keeps the exact former builder body, warms and alternates
both functions, and checks serialized states and final RNG state. Four-axis,
unique-value grids in the last reference gave these median paired ratios:

| States | Pairwise/indexed initialization ratio |
| ---: | ---: |
| 1 | 1.01× |
| 81 | 3.12× |
| 625 | 16.87× |
| 2,401 | 63.28× |

One-state timings varied around parity, including minor regressions in earlier
runs; no universal gain is claimed. Separately traced graph allocation peaks
were 68,728 → 91,864 bytes at 81 states and 938,040 → 865,280 at 625. Retained traces were 68,728 → 81,728 and
938,040 → 790,880 respectively. Traces include interpreter allocation caches,
exclude input grids, and are not whole-process RSS or pure live-graph sizes.

The same runner swaps builders on the **same controller class** inside complete
PSO searches, using a valid five-value-per-axis grid (625 states). Both variants
run 2,000 evaluations, actual local search/callback isolation and final pool
fingerprinting. Three seeds × three repeats × two dimensions × three workloads
give **54 exact pairs per invocation**. Three runs passed all 162 pairs, including
costs, keys, counts, final pools and both RNG fingerprints.

To isolate search semantics, the adaptive elapsed clock is frozen while callback
stopping still works. This is **not** a real adaptive time policy or whole-RKO
speedup comparison. Latest median paired **wall / process CPU** ratios:

| Keys | Sphere | Rugged numerical | Stable permutation |
| ---: | ---: | ---: | ---: |
| 32 | 3.85 / 3.90 | 2.91 / 3.05 | 3.77 / 3.76 |
| 1,000 | 1.37 / 1.38 | 1.30 / 1.34 | 1.24 / 1.24 |

The separate startup runner executes six real, cold-spawn PSO solves on the same
checkout/environment, alternating original/indexed graph builders for three
seeds. A temporary valid 625-state TOML configuration is re-read normally; the
worker wrapper measures graph creation and the first decoder records its time
and seeded keys. All first-key hashes and final objective accounting passed.
The latest graph phase took 0.390–0.712 s pairwise versus 0.017–0.050 s indexed.
**End-to-end times were mixed:** 5.81–6.66 s versus 4.75–7.06 s for 0.1-second
budgets. Startup/import variation dominated, so these six solves do not establish
whole-process latency gains. A first callback can still exceed its budget.

A preceding instrumented default-portfolio investigation found only 0.12–0.24 s
in parent-side algorithm construction, against 1.92–3.93 s manager startup and
roughly 2.07–3.41 s between manager readiness and worker entry. It did not justify
removing fail-fast constructor validation. Import/spawn latency remains open;
never compare Linux `/tmp` and Windows-mounted checkouts as a code speedup.

## Filter-before-allocation adaptive states

A follow-up preserves the indexed graph but enumerates parameter combinations
with `itertools.product`, applying the feasibility predicate **before** creating
a `QState`. Rejected combinations no longer allocate state records, action lists
or Q-value lists. Axes are snapshotted before predicate visits; mutable predicate
payloads retain their identities. Labels, graph/action order, weights and RNG
consumption remain unchanged for valid grids. Dense accepted graphs still need
all their output edges; predicates retaining rejected payloads keep that memory.

Compare against the **indexed** implementation preceding this follow-up, rather
than crediting the earlier pairwise-to-indexed change again:

```bash
git show 65aa389:src/rko/components/adaptive_control/q_learning.py > /tmp/rko-q-materialized.py
uv run --locked python benchmarks/q_state_memory.py \
  --reference /tmp/rko-q-materialized.py > /tmp/rko-q-state-memory.jsonl
```

Only execute a trusted reference file. The benchmark alternates seven seeded
builds per synthetic grid/filter and compares every state field and RNG state.
Reference: 2026-10-19, the same WSL2 / CPython 3.14.8 / NumPy 2.4.3 setup above.
Two invocations reproduced these traced allocation peaks exactly:

| Combinations | Accepted states | Former peak bytes | New peak bytes | Reduction |
| ---: | ---: | ---: | ---: | ---: |
| 625 | 125 | 243,920 | 161,696 | 33.7% |
| 2,401 | 343 | 957,008 | 532,344 | 44.4% |
| 15,625 | 3,125 | 6,530,080 | 5,603,360 | 14.2% |

These are filtered-grid construction peaks, **not RSS or general solver memory**.
Traces include interpreter allocation caches, not just live graph storage.
All-accepted grids showed essentially unchanged peaks; a one-combination grid
added 416 traced bytes. More selective filters showed larger reductions, but
those synthetic singleton cases are not representative search-quality evidence.

The same runner also completed **108 exact fixed-work adaptive PSO pairs** across
two invocations (sphere/rugged/permutation; 32/1,000 keys). Costs, keys, evaluation
counts, final pools and both RNG fingerprints matched. Whole-search timing was
mixed, so **no reliable full-solver speedup is established**. Adaptive clocks are
frozen only for this replay check; real time-based adaptation and cold process
startup were not benchmarked by this follow-up. No parameter defaults, RNG
implementation, callback isolation or runtime dependencies changed.

## Managed IPR selected elite transfer

IPR previously fetched the whole managed elite pool and then selected two ranks.
The built-in proxy now draws the same two ranks **in the requesting process** and
asks the server to copy only those entries under one lock. Pool occupancy never
decreases, so ranks from the preceding count remain valid if a writer adds
entries. Both entries come from the same current snapshot, in selection order.
No revision cache, stale local snapshot or server-side RNG was introduced.

```bash
uv run --locked python benchmarks/elite_pair.py > /tmp/rko-elite-pair.jsonl
```

Only built-in managed proxies expose the private sampling capability. Local and
custom pools retain full-snapshot sampling with the unchanged `ElitePool`
protocol; two-entry pools also retain it because there is nothing to avoid
transferring. Public `get_elite`, key types, source isolation and validation are
unchanged. The count and pair still require **two RPCs**: this reduces their
payload, not their number. Concurrent timed portfolios remain nondeterministic;
sampling before instead of after a snapshot RPC can change interleavings.

The runner swaps the former and production `solve` methods on the **same IPR
class**, with the same production relinking kernel and real spawned pool server.
Each search starts with ten fresh workload-consistent elites. Both paths warm up
before measurement; execution order alternates and collection occurs before
search timing. At 32 keys each search completes 20,000 evaluations; at
1,000/10,000 it completes 2,000. Three seeds × three repeats × three workloads ×
three dimensions yield **81 exact paired searches per invocation**. Each pair
checks keys, costs, counts, final pool and Python/NumPy RNG fingerprints. The
original method and caller streams are restored in `finally`.

Reference: 2026-10-19, four-CPU WSL2, GIL-enabled CPython 3.14.8 / NumPy 2.4.3.
Two production runs passed all 162 paired comparisons. The following is the last
run's median paired snapshot/selected-transfer ratio, **wall / client CPU**:

| Keys | Sphere | Rugged numerical | Stable permutation |
| ---: | ---: | ---: | ---: |
| 32 | 1.01 / 1.01 | 1.03 / 1.02 | 1.05 / 1.05 |
| 1,000 | 1.45 / 1.30 | 1.16 / 1.11 | 1.15 / 1.10 |
| 10,000 | 2.08 / 1.86 | 1.20 / 1.11 | 1.11 / 1.06 |

Large-vector gains repeated; small-case timing varied in exploratory runs and
individual paired trials can be slower. These results do not establish a
universal gain. **Client CPU excludes server CPU**; wall time includes RPC waits.
Server startup, pool creation/seeding and final fingerprint queries are outside
search timing. No concurrent portfolio writers are used for this timing test;
separate regression coverage tests spawned publication and concurrent writes.

Isolated retrieval median ratios were 2.67× at 1,000 keys and 4.50× at 10,000.
Serializing returned entries with default `pickle` measured 90,175 → 18,046 bytes
at 1,000 keys and 900,463 → 180,100 at 10,000, approximately **80% less entry
data** for a ten-entry pool. These are not packet sizes: RPC envelopes and
transport overhead are excluded. There is no whole-process RSS or total-CPU
claim, and process startup latency is **not** addressed by this change. Full
portfolio speed and scientific solution quality require separate measurements.

## IPR fixed-work block copying

IPR now assigns multi-gene guide blocks with NumPy slices instead of a Python
loop. Single-gene blocks use direct scalar assignment. Candidate ownership,
callback isolation, path order, first-best tie handling and RNG sources remain
unchanged; no dependency or default configuration was added.

```bash
uv run --locked python benchmarks/ipr.py > /tmp/rko-ipr.jsonl
```

The executable scalar reference retains the former `_relink` method body.
Measurements swap that method on the **same IPR class**, avoiding inherited-versus-
direct dispatch differences. All other components are production code, including
SearchSession's protective copies and SolutionPool operations. Initial elites use
the actual workload objective and an independent RNG; they do not count as search
evaluations. Both variants warm up before measurement, alternate order, and restore
the original method and caller RNG states on exit.

Reference: 2026-10-19, four-CPU WSL2, GIL-enabled CPython 3.14.8 / NumPy 2.4.3,
after integrating main's operator-override and property/mutation-testing PRs.
Three seeds × three repeats × three workloads × seven dimensions yielded **189
paired searches**. Every pair matched exact best keys, costs, evaluation counts,
final elite-pool contents and Python/NumPy RNG fingerprints. Runs used 20,000
completed search evaluations through 80 keys and 2,000 at 1,000/10,000 keys.

Median paired scalar/production ratios, **wall / process CPU**; values below one
are slower, not improvements:

| Keys | Sphere | Rugged numerical | Stable permutation |
| ---: | ---: | ---: | ---: |
| 1 | 1.06 / 1.06 | 0.99 / 0.99 | 1.00 / 1.00 |
| 8 | 1.11 / 1.11 | 0.99 / 0.99 | 1.00 / 1.00 |
| 32 | 0.87 / 0.88 | 0.97 / 0.97 | 0.98 / 0.98 |
| 79 | 1.17 / 1.17 | 0.99 / 0.99 | 1.12 / 1.12 |
| 80 | 1.13 / 1.13 | 1.07 / 1.07 | 1.10 / 1.10 |
| 1,000 | 2.47 / 2.47 | 1.34 / 1.34 | 1.30 / 1.30 |
| 10,000 | 3.46 / 3.46 | 1.45 / 1.45 | 1.22 / 1.22 |

Large-vector benefits repeated across exploratory runs; absolute timings varied.
Small cases were inconsistent, including regressions: no universal or small-vector
speedup is claimed. Extra repeated comparisons do not turn these synthetic
workloads into independent real-world problem families.

Separately warmed, isolated `_relink` tracing measured the same peak for both
variants: 40,560 bytes at 1,000 keys and 400,560 at 10,000. Inputs were allocated
before tracing. Full candidate copies remain; this is not a whole-solver memory
or RSS improvement. Forty independent list-model regression cases compare every
evaluated candidate bit-for-bit, including signed zero, partial blocks, stable
ordering ties, source immutability and positive/negative-stride inputs.

These measurements cover complete **serial IPR searches**, not just assignment
microbenchmarks. They exclude process startup, manager IPC, expensive external
callbacks, scientific optimization quality and C++/Rust parity. The runner may
take several minutes on this reference host and is not part of normal CI.

## PSO fixed-work searches

PSO now uses NumPy for independent genes within a particle at 32+ dimensions,
while moving particles sequentially and preserving the two Python RNG draws per
gene, arithmetic order, boundary reversion and callback sequence. Smaller vectors
retain scalar movement. No compiler/JIT or new runtime dependency is required.

A 2026-10-19 Python 3.14.8 / NumPy 2.4.3 WSL2 reference run (four CPUs,
GIL enabled, baseline `577b3c4`) compared the former scalar formula against batched movement using actual PSO, local search, elite exchange
and callback isolation. Each pair has exactly 2,000 evaluations; execution order
alternates across three seeds and three repeats. The table gives median paired
wall-time ratios (**scalar / production**), not microkernel speedups:

| Keys | Sphere | Rugged numerical | Permutation |
| ---: | ---: | ---: | ---: |
| 8 | 1.12× | 0.98× | 0.85× |
| 32 | 1.67× | 1.45× | 1.77× |
| 100 | 1.72× | 1.44× | 1.39× |
| 1,000 | 1.12× | 1.13× | 1.10× |

All 108 pairs matched exact best-key hashes, costs, evaluation counts and both RNG
state hashes. All 54 pairs at 32/100 keys were faster in this run. Eight-key
movement remains scalar; its variable timing is not an improvement claim. Gains
at 1,000 keys were smaller and varied between runs, including a slower rugged
case in an earlier run. Local-search and objective costs limit total benefit.
No general portfolio, process-backend, expensive-callback or quality gain follows.

```bash
uv run --locked python benchmarks/pso.py > /tmp/rko-pso-paired.jsonl
```

The runner reports CPU time separately from elapsed time and traces movement
allocations outside timing. The scalar reference overrides only movement;
production PSO control flow is shared. This introduces the same method-call
boundary on both sides, so tiny-dimensional comparison with the original inline
loop is approximate. Batching needs temporary O(n) scratch: about 40.5 KB peak
for 1,000 keys versus about 120 bytes in the isolated scalar movement probe.
This is a runtime/scratch-allocation tradeoff, not a memory-reduction claim.
All arrays and traces are local; no whole-process RSS measurement is implied.

## Knapsack process reference

Latest measurement: **2026-10-18**, starting at 15:36 UTC, on standalone solver
revision `daa2e94fb1379994705168d5d6f3c2cc8674ba58`. Cleanup moves this runner but
does not change it or the solver. Host: WSL2/Linux, Python 3.14.8 with the GIL,
four available CPUs. This is one reproducible reference experiment, not a
performance guarantee or a release certification.

### Reproduce

The CPU-accounting runner requires Linux/WSL; the library itself is tested on
Windows too. From the repository root:

```bash
uv sync --locked --group dev
curl -fL https://raw.githubusercontent.com/likr/kplib/c5bea0df8169749caaba5ce7dfcf21437aa1ca5c/00Uncorrelated/n01000/R01000/s000.kp \
  -o /tmp/rko-s000.kp
uv run --locked python benchmarks/knapsack.py \
  /tmp/rko-s000.kp benchmarks/results/knapsack.csv
```

Generated `results/` directories are ignored. Do not overwrite the checked-in
[reference CSV](knapsack-reference.csv) without rerunning the experiment and
updating its date, tested revision and interpretation here.

Data: KPLIB, 1000 items, capacity 252480, pinned upstream revision
`c5bea0df8169749caaba5ce7dfcf21437aa1ca5c`.
SHA256: `8f555b2b40dff1298d841a8e5abc327a8f1135ce8188e84249cd1352f959ffed`.
The runner verifies that fingerprint. The external instance is not redistributed
because its licensing has not been verified.

### Method

SA/BRKGA/GA/PSO, online control, pool size 10, 15 search seconds, seeds 42/43/44;
process backend uses four workers, compared with four Python threads. The
threshold decoder (`key > 0.5`) and reference penalty objective are unchanged.
The runner computes an independent 0/1 capacity-DP optimum, self-checks that
oracle on smaller cases and verifies returned cost/decision accounting. CPU
seconds include the parent and reaped children; elapsed time includes startup.
Thread initialization differs from process streams, so trajectories are not
matched. Six runs take approximately two minutes on this host.

Exact optimum: **400811**, DP time 2.669 s. Profit/weight greedy: **400792**,
gap **0.00474%**.

### Current results

All six trials completed without errors and returned feasible solutions with
independently checked costs.

| Backend | Seed | Profit | Gap % | End-to-end seconds |
| --- | ---: | ---: | ---: | ---: |
| process | 42 | 329395 | 17.8179 | 17.2681 |
| process | 43 | 322273 | 19.5948 | 17.5249 |
| process | 44 | 324203 | 19.1132 | 17.6503 |
| thread | 42 | 315909 | 21.1826 | 15.0152 |
| thread | 43 | 310570 | 22.5146 | 15.0109 |
| thread | 44 | 304355 | 24.0652 | 15.0372 |

Mean process gap: **18.8420%**, elapsed 17.4811 s, CPU use 2.8560 cores.
Mean thread gap: **22.5875%**, elapsed 15.0211 s, CPU use 1.0420 cores.

**Quality remains poor**, well behind greedy. Multicore CPU usage is established;
fixed-work speedup, statistical superiority and competitive optimization are not.
Timed searches vary with scheduling/elite exchange even with fixed seeds. One
instance and three seeds are insufficient to generalize or attribute changes
between measurements. Older snapshots remain in Git history, not as a growing
set of dated reports in the current tree.

Problem-aware decoding/initialization, more instance families, independent RNGs
and fixed-work profiling remain [open work](../docs/status.md). Do not silently
replace the reference decoder or omit negative results to improve presentation.

## Blending throughput comparison

A five-seed, 2-second serial SA experiment on a synthetic 1,000-key sphere
objective measured median **3,150 evaluations/s** with the former blending loop
and **4,150 evaluations/s** with the batched offspring-selection implementation
(**31.7% higher throughput**). The optimized function consumes the same Python
random draws in the same order; only offspring selection/complement work is
batched. This synthetic, single-thread result does not imply process or expensive
callback speedups.

Reproduce from the repository root:

```bash
uv run --locked python benchmarks/blending.py
```

The script prints every seed and median throughput. It restores the production
blending operator even if a search fails.

## Genetic-algorithm population memory

A one-generation GA allocation probe used an identity decoder and a sphere
objective with 100 chromosomes of 5,000 keys. Peak `tracemalloc` allocation
fell from **11.72 MiB** at `36c1b8f` to **8.08 MiB** after releasing the previous
population once parent selection is complete (**31.0% lower**). The seeded best
objective stayed exactly `1594.6759`. This isolates population-transition
allocations; the benchmark stubs Nelder-Mead and is not whole-solver RSS evidence.

Run from the repository root:

```bash
uv run --locked python benchmarks/ga_population_memory.py
```

To compare a baseline checkout, copy the runner into that checkout and run the
same command there. Keep dimensions, population size, seeds, Python and NumPy
versions fixed when comparing results.

## Shared incumbent and elite-pool allocations

On Python 3.14.8 / NumPy 2.4.3, the shared callback boundary now retains its
already-detached NumPy key snapshot instead of materializing a Python float list
at every improvement. Public result keys are still lists. Both protective decoder
copies, finite-objective validation and deadline handling remain enabled.

A 1,000-evaluation stream over 10,000 keys with an improving objective measured
retained traced allocation **322,704 → 80,376 bytes** (-75.1%) and peak allocation
**800,608 → 240,656 bytes** (-69.9%). The untraced callback-stream time was
0.2321 → 0.0082 seconds; this deliberately improvement-heavy stream is not a
whole-search throughput claim. Periodic improvements and plateaus are included
in the runner to expose workload sensitivity.

The elite pool also reuses its first validated private list copy rather than
copying that copy again. A capacity-one pool accepting 100 successive improvements
with 10,000 keys measured peak traced allocation **242,008 → 163,512 bytes**
(-32.4%) against `0f3b426`. Retained pool storage is unchanged. These figures
exclude preallocated source data and do not measure process RSS or IPC.

```bash
uv run --locked python benchmarks/search_session.py
uv run --locked python benchmarks/fixed_work.py > /tmp/rko-fixed-work.jsonl
git show 0f3b426:src/rko/orchestration/search.py > /tmp/rko-baseline-search.py
uv run --locked python benchmarks/fixed_work.py \
  --baseline-search /tmp/rko-baseline-search.py > /tmp/rko-paired-search.jsonl
```

The first runner contains the prior incumbent evaluator as a reference; copy it
into the baseline checkout to compare pool allocation. The second runs actual
SA, GA and BRKGA searches with sphere, rugged numerical and stable-permutation
decoders/objectives: three seeds and exactly 2,000 evaluations per search, with
real local search and elite exchange. Compare matching JSON records across
checkouts; costs, key fingerprints, evaluation counts and both RNG fingerprints
must agree before interpreting elapsed times. The optional baseline flag executes
that trusted module and alternates implementations in the same process for three
repeats; other components, including the elite pool, use production code in both
variants. In 81 paired searches all replay checks matched, and per-workload median
paired elapsed changes ranged from -2.6% to +2.6%: no reliable whole-search runtime
gain was established. Avoid interpreting separate Linux-filesystem and mounted
Windows checkouts as a controlled runtime comparison. Serial timing excludes
process startup, configuration I/O and transport, and does not establish
native-code parity.

## Owned RNG replay and overhead

`random_streams.py` compares production searches using private Python/NumPy
streams against a **trusted pre-isolation source package** loaded under a separate
namespace. It warms each case, balances execution order over two repeats and
three seeds, and checks 1,000 evaluations at 64 keys for all eleven algorithms,
only where BOTH constructors share the search contract and requested control.
SA now has an adaptive path absent from the historical pre-isolation baseline;
that mode is `not_comparable`, never mislabeled as equivalent online runs.
GRASP's sampled-lattice and subsequent construction-count/subset corrections change
both modes. Earlier near-only and lattice-only references without the matching
internal replay-contract token are `not_comparable` for both. This
avoids reporting intentional candidate/RNG changes as isolation regressions.
IPR's unchanged-block callback pruning also requires a matching replay token;
older unpruned IPR is explicitly `not_comparable` for RNG-only comparisons.
Offline SA remains comparable; historical 342-pair reference files retain their
original algorithm scope, not coverage of the new GRASP policy. Costs, keys, final elites and both final
RNG states must match exactly. Adaptive policy clocks are frozen, not real timed
cooperation. The reference package executes Python code and must be trusted.

```bash
git worktree add --detach /tmp/rko-rng-baseline-a281c6a a281c6a
uv run --locked python benchmarks/random_streams.py \
  --reference /tmp/rko-rng-baseline-a281c6a/src/rko > /tmp/rko-rng-replay.jsonl
```

One WSL2 reference passed all **342 pairs**. Across its 57 case medians, the median
baseline/owned wall and CPU ratios were **0.981 / 0.983**; individual cases varied
substantially in both directions. These are short serial fixed-work measurements,
not an aggregate throughput ratio or proof of a universal overhead bound.
Per-pair timings are retained in the JSON output. Stream construction, imports,
configuration reads and process startup are outside the timed region.

This is a correctness change, not a speed optimization: independent searches no
longer reseed global generators, and seeded thread searches are now supported.
Callback-global draws are neither implicitly seeded nor rolled back; stochastic
callbacks must own their generators. Standalone built-in operators retain global
RNG compatibility. No RSS, whole-portfolio speedup or quality improvement follows
from these replay checks.

## IPR work and population diagnosis (not timing)

```bash
uv run --locked python benchmarks/ipr_diagnosis.py
```

`ipr-diagnosis-reference.jsonl` contains 36 cases: three seeds, three synthetic
objectives, two starting-population modes and a separately labeled exact-vector
admission control, each charged exactly 1,024 completed objective evaluations.
Production two-seed cases use 2 seed + 1,022 path evaluations; ten-elite cases use
11 + 1,013, including production IPR's unconditional extra initial draw.

In the historical `0c3a573` reference, all three ordinary-bootstrap sphere cases
collapse to one distinct vector in ten pool slots. Rejecting exact clones in the isolated control eliminates identical
parents but does not improve the best score in any of the nine two-seed cases.
A direct one-differing-block pair makes 55 evaluations for only two unique vectors.
More initial seeds improve the sphere/threshold examples here, not all domains;
combining larger populations with duplicate rejection has mixed relative outcomes.

See [diagnostic contracts and findings](../docs/ipr-diagnosis.md) for seed-prefix
matching, source fingerprints, work accounting and reference-source limitations.
The diagnosis itself changed no production policy or active Knapsack benchmark.
The subsequent [chromosome-uniqueness correction](../docs/elite-diversity.md) is
recorded separately in `ipr-unique-elites-reference.jsonl`: all 36 cases retain
unique chromosomes and select zero identical-parent pairs. Equal-budget production
traces now match the isolated control; initialization remains fully charged. Scores
are unchanged in the two-seed cases and mixed versus old ten-seed production.
The header also fingerprints the pool source so admission changes are identifiable.
The subsequent [unchanged-block correction](../docs/ipr-block-pruning.md) has its
own `ipr-pruned-blocks-reference.jsonl`: the direct one-differing-block case falls
from 55 to two callbacks, preserving the virtual path and deterministic minimum.
All 36 cases still charge exactly 1,024 completed evaluations; full-search path/RNG
counts can therefore differ from older work records. Stateful/stochastic callback
results can change. This is not a throughput, feasibility, C++ parity or native
backend result.

The per-gene `ScalarIPR` control in `benchmarks/ipr.py` shares current pruning and
virtual-step rules, so new copy-kernel comparisons vary copying alone. Historical
IPR speed data retains its original policy/version; no new speedup is measured.

RNG-isolation replay deliberately injects the current `SolutionPool` into both
historical and current algorithm implementations. That controls the shared pool
context; it is not a replay of historical application admission semantics or a
reinterpretation of historical timing/result files.
