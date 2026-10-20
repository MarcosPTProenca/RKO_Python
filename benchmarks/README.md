# Performance benchmarks

Each section identifies its workload and limits. Synthetic fixed-work and
allocation probes complement the historical Knapsack reference; no single case
establishes general optimization quality or native-code performance parity.

## Python versus C++ Knapsack comparison

This benchmark compares the standalone Python RKO library with the pinned C++
reference on the same 500-item 0/1 Knapsack inputs. It measures each of the 11
single algorithms (BRKGA, BRKGA-CS, GA, GRASP, ILS, IPR, LNS, MultiStart,
PSO, SA, and VNS) and the default 10-algorithm portfolio separately. The
portfolio is SA, ILS, VNS, BRKGA, BRKGA-CS, PSO, GA, LNS, GRASP, and IPR; it
excludes MultiStart. The benchmark does not form a composite score or claim
algorithmic equivalence.

### Reproduce

From the repository root, Python downloads and verifies the KPLIB inputs, computes
exact dynamic-programming optima, extracts and builds the pinned C++ source in a
temporary directory, then appends every trial to a raw CSV. No C++ source or
instance data is committed or changed in the historical checkout.

```bash
uv run --locked python -m benchmarks.cpp_python_knapsack \
  --output benchmarks/cpp-python-knapsack-reference.csv \
  --cache-dir /tmp/rko-cpp-python-knapsack-cache
```

The approved main run uses a **120-second search budget** and **5 repetitions per
implementation, solver configuration, and instance**, for 1,800 trials. At the
measured runtime this is expected to take about 60 hours. The pilot option runs
BRKGA, BRKGA-CS, and the full portfolio on one instance for one second; pilot output is
excluded from analysis.

```bash
uv run --locked python -m benchmarks.cpp_python_knapsack --pilot \
  --output /tmp/rko-cpp-python-knapsack-pilot.csv \
  --cache-dir /tmp/rko-cpp-python-knapsack-cache
```

Interrupted main runs can continue with `--resume` only when the raw CSV has the
same source/configuration hash and schema. The runner writes a companion
`*-summary.csv`; that generated file is ignored because the summary is regenerated
from the retained raw reference data.

### Fixed workload and provenance

The sample is pinned to KPLIB commit
`c5bea0df8169749caaba5ce7dfcf21437aa1ca5c`. Three IDs were selected from each
family's 100 `R01000` files using Python seed `20261019`; the selector and SHA-256
checks are in the runner. The paths below are relative to the KPLIB repository;
all are under `n00500/R01000`.

| Family | File | SHA-256 |
| --- | --- | --- |
| `00Uncorrelated` | `s041.kp` | `b764f09ca075cb3b05c9704a7ff57a23a33d73816d0fe7758d3ea34f91a20655` |
| `00Uncorrelated` | `s075.kp` | `6512ca8db5837337ae58a867e88d41be74d61689bdded3b9db54dc7829ea11fc` |
| `00Uncorrelated` | `s092.kp` | `28c37692613a1e3af6b0979f2e27d19b3c0e5d32cec4eb7866c0b87f8cc59f45` |
| `01WeaklyCorrelated` | `s015.kp` | `a5b3f5c82db8f0f6ae3d5790a2ec1aa39573be6e435b44762a84961c45a727c2` |
| `01WeaklyCorrelated` | `s027.kp` | `5009309ca808e864b6c9cc604281e06934cd55f79cf681e41c57a5cbc0eb480f` |
| `01WeaklyCorrelated` | `s060.kp` | `bd44328fd09454961870c69a3b9e7b8d975491584f20245d0287bb3767e4fd65` |
| `02StronglyCorrelated` | `s034.kp` | `d840a1121e0d29e99554ed95267558247180397877c1ea73e4e02cb9da01c6f9` |
| `02StronglyCorrelated` | `s037.kp` | `26e58386ea06bb4eeb0a70dd189dc51c04261c652fe4ae8de49b3e3181519d20` |
| `02StronglyCorrelated` | `s069.kp` | `bf043da2b0ef25e44ade43c55cfcb00365dbe9dfe5db73d59f706a110d0deb96` |
| `05SubsetSum` | `s003.kp` | `1b0783a6ffa08b616b2ff6cf8ebbecce4e10905060abd1b4702f449663aaec97` |
| `05SubsetSum` | `s044.kp` | `951803299442fab73f11adf98f6a06f25599433ea3f0f06baba6ecc104ec8ba4` |
| `05SubsetSum` | `s091.kp` | `04a7bdc7d87ad555d8eb7d776fd521eca6f02c247f7397e485045deb8f635495` |
| `07SpannerUncorrelated` | `s000.kp` | `3dd36adec09e23cbf24b71d1663c315fb5cd7c0456f846b23cd95abd1a3b85dd` |
| `07SpannerUncorrelated` | `s017.kp` | `ee673cd708aba7046f9cbacbf60aaa1ba70d20e0811746d8c0999d9a5aee2ab4` |
| `07SpannerUncorrelated` | `s092.kp` | `f574a32e6b87a832c9c70bc70bb7e2b73567caa3615c7ebb173fb7a075d45652` |

The raw CSV includes each input hash, capacity, exact optimum, Python seed, C++
seed when available, execution mode, compiler flags, source fingerprints, and
host/runtime versions. Exact optimum computation is outside solver timing. The
KPLIB data is downloaded to an external cache and is not redistributed here;
attribute the instances to KPLIB (Kellerer, Pferschy, and Pisinger). The
[official README](https://github.com/likr/kplib/tree/c5bea0df8169749caaba5ce7dfcf21437aa1ca5c)
states CC BY 4.0.

### Method and interpretation

Python solo algorithms run serially; the Python default portfolio uses one process
per algorithm. C++ solo algorithms use one OpenMP thread, while its ten-member
portfolio uses ten OpenMP threads. These execution models and checked-in
parameters are not equivalent. Python uses online control, pool size 10, and its
default local search. C++ uses `control=1`, pool size 10, `strategy=1`, and its
reference first-improvement behavior. The comparison is of the tested configured
implementations, not a conformance or parameter-parity test.

The temporary C++ copy is built with `g++` and OpenMP using the exact flags
recorded in each row. Its only evaluator correction changes the knapsack cost
and penalty multiplication to 64-bit arithmetic. The historical C++ evaluator
uses signed 32-bit `int`; a UBSan run overflowed during actual search on the
selected 500-item workload. Results are therefore labeled **C++ (64-bit objective
fix)**, not an untouched C++ build. No algorithm or random-draw code is changed.

Time-to-target starts immediately before Python `RKO.solve()` or at the C++
search-start marker, and misses are right-censored at the common 120-second search
budget in the approved run. Targets are feasible profits within 10%, 1%, and 0% of the exact optimum;
first feasible candidate evaluations trigger benchmark-only telemetry. The raw
CSV separately records process-launch-to-exit time, including process startup and
orchestration but excluding post-run verification and analysis. The pilot validates
build, input, telemetry, and runner behavior; its measurements are not pooled with
the main sample. Algorithms may finish a generation after the configured budget;
raw elapsed time exposes this overrun, and capped target times never count hits
beyond the budget.

C++ clock-derived engine seeds are recorded, but exact replay is not guaranteed:
the reference creates additional `std::random_device` engines for GRASP and
BRKGA-CS shuffles. Python trials use recorded independent seeds. Trials alternate
Python/C++ order within each cell and run sequentially, with no concurrent
benchmark job.

For each solver and metric, the approved summary first reduces 5 repetitions
within each instance (median for objective/time, mean for feasibility/success rates), then
compares the 15 paired instance summaries using an exact two-sided sign test. It
reports the median paired difference and a deterministic 95% bootstrap percentile
interval over instances (10,000 resamples). Failed trials count as misses for
feasibility and target success, and are censored at the budget for target latency;
objective summaries use verified successful outputs. The summary reports success
and failure counts for each implementation. Holm correction is applied separately
across the 12 solver configurations for each of five reported endpoints:
normalized reference-objective difference, feasibility rate, 1%-target success
rate, capped search-time-to-1%, and process-launch-to-exit latency. Search-time
latency is capped at the common budget; process latency exposes startup and
algorithm overruns. Ties are excluded from the sign-test
binomial count and reported. A nonsignificant result is inconclusive, not proof of
equivalence. These 15 selected instances do not establish general Knapsack or
hardware performance. For background, see [COCO performance assessment](https://numbbo.github.io/coco-doc/perf-assessment/)
and [García and Herrera (2008)](https://jmlr.csail.mit.edu/papers/volume9/garcia08a/garcia08a.pdf).

### Approved 120-second run

The approved 120-second × 5-repetition run covers 12 configurations × 15 instances
× 5 repetitions × two implementations (1,800 trials) and is underway. Its results
will replace the preliminary tables below after all trials complete.

### Preliminary 2-second run (superseded)

**Do not treat the following tables as the requested comparison.** They summarize
an earlier 2-second × 30-repetition experiment; the budget was too short to answer
the intended question. The raw file is retained only as a diagnostic. The approved
120-second run uses five repetitions per cell and will receive separate results.

The preliminary run completed all **10,800/10,800 trials**: 12 configurations × 15
instances × 30 repetitions × two implementations. All trials returned valid
records (zero failures), with one source/run signature and no target time beyond
the 2-second censoring budget. Each table reports the median of 15 per-instance
summaries; `Δ` is the median paired Python-minus-C++ difference, with a
10,000-resample bootstrap 95% CI over instances. `p` is the exact paired sign-test
p-value after Holm correction across 12 configurations for that metric. At α=.05,
positive `Δ` favors C++ for lower-is-better metrics and negative `Δ` favors C++
for higher-is-better rates. These results compare the tested configurations, not
algorithmic equivalence.

Penalized objective difference is `100 × (returned minimization objective + exact
optimum) / exact optimum`; it includes the historical overweight penalty, so the
very large Python IPR value reflects infeasible terminal solutions and is
interpreted alongside feasibility. Target-time values are capped at 2 seconds,
with misses scored at the 2-second cap used in this preliminary run. Process latency is measured from process launch
to exit, not just search time.

#### Penalized objective difference from exact optimum (%)

| Solver | Python | C++ (64-bit fix) | Paired Δ Python−C++ (95% CI), pp | Holm p |
|---|---:|---:|---:|---:|
| BRKGA | 5.9 | 2.6 | +2.4 [+1.2, +7.1] | 0.0007324 |
| BRKGA-CS | 8.1 | 0.9 | +7.7 [+1.7, +24.8] | 0.0009766 |
| GA | 5.8 | 4.5 | +1.0 [+0.6, +3.3] | 0.0007324 |
| GRASP | 8.6 | 1.0 | +8.2 [+1.4, +28.5] | 0.0007324 |
| ILS | 9.0 | 0.7 | +8.3 [+2.9, +29.4] | 0.0007324 |
| IPR | 105537.0 | 7.5 | +105526.7 [+37676.1, +119582.6] | 0.0007324 |
| LNS | 6.6 | 2.9 | +3.0 [+2.0, +5.0] | 0.0007324 |
| MultiStart | 7.8 | 7.3 | +0.4 [+0.2, +0.6] | 0.0007324 |
| PSO | 5.9 | 3.4 | +1.7 [+1.2, +3.1] | 0.0007324 |
| SA | 6.8 | 4.0 | +1.9 [+1.4, +3.2] | 0.0007324 |
| VNS | 9.3 | 0.7 | +8.5 [+1.9, +11.7] | 0.0007324 |
| RKO-default | 6.9 | 1.0 | +6.1 [+2.4, +7.3] | 0.0009766 |

#### Feasible terminal solutions (%)

| Solver | Python | C++ (64-bit fix) | Paired Δ Python−C++ (95% CI), pp | Holm p |
|---|---:|---:|---:|---:|
| BRKGA | 100.0 | 100.0 | +0.0 [+0.0, +0.0] | 1 |
| BRKGA-CS | 100.0 | 100.0 | +0.0 [+0.0, +0.0] | 1 |
| GA | 100.0 | 100.0 | +0.0 [+0.0, +0.0] | 1 |
| GRASP | 73.3 | 100.0 | -26.7 [-30.0, -23.3] | 0.0007324 |
| ILS | 73.3 | 100.0 | -26.7 [-33.3, -16.7] | 0.0007324 |
| IPR | 36.7 | 100.0 | -63.3 [-66.7, -50.0] | 0.0007324 |
| LNS | 100.0 | 100.0 | +0.0 [+0.0, +0.0] | 1 |
| MultiStart | 100.0 | 100.0 | +0.0 [+0.0, +0.0] | 1 |
| PSO | 100.0 | 100.0 | +0.0 [+0.0, +0.0] | 1 |
| SA | 100.0 | 100.0 | +0.0 [+0.0, +0.0] | 1 |
| VNS | 73.3 | 100.0 | -26.7 [-30.0, -20.0] | 0.0007324 |
| RKO-default | 100.0 | 100.0 | +0.0 [+0.0, +0.0] | 1 |

#### Runs reaching the 1%-optimality-gap target within 2 seconds (%)

| Solver | Python | C++ (64-bit fix) | Paired Δ Python−C++ (95% CI), pp | Holm p |
|---|---:|---:|---:|---:|
| BRKGA | 0.0 | 0.0 | +0.0 [+0.0, +0.0] | 1 |
| BRKGA-CS | 0.0 | 66.7 | +0.0 [-66.7, +0.0] | 0.125 |
| GA | 0.0 | 0.0 | +0.0 [+0.0, +0.0] | 1 |
| GRASP | 0.0 | 46.7 | -43.3 [-100.0, +0.0] | 0.009766 |
| ILS | 0.0 | 70.0 | -56.7 [-96.7, +0.0] | 0.009766 |
| IPR | 0.0 | 0.0 | +0.0 [+0.0, +0.0] | 1 |
| LNS | 0.0 | 0.0 | +0.0 [+0.0, +0.0] | 1 |
| MultiStart | 0.0 | 0.0 | +0.0 [+0.0, +0.0] | 1 |
| PSO | 0.0 | 0.0 | +0.0 [+0.0, +0.0] | 1 |
| SA | 0.0 | 0.0 | +0.0 [+0.0, +0.0] | 1 |
| VNS | 0.0 | 63.3 | -40.0 [-96.7, -3.3] | 0.005859 |
| RKO-default | 0.0 | 53.3 | -36.7 [-60.0, -20.0] | 0.005859 |

#### Capped time-to-1%-gap (seconds)

| Solver | Python | C++ (64-bit fix) | Paired Δ Python−C++ (95% CI), s | Holm p |
|---|---:|---:|---:|---:|
| BRKGA | 2.000 | 2.000 | +0.000 [+0.000, +0.017] | 0.875 |
| BRKGA-CS | 2.000 | 1.411 | +0.018 [+0.000, +0.870] | 0.07031 |
| GA | 2.000 | 2.000 | +0.000 [+0.000, +0.000] | 1 |
| GRASP | 2.000 | 2.000 | +0.000 [+0.000, +1.505] | 0.125 |
| ILS | 2.000 | 0.640 | +0.777 [+0.000, +1.510] | 0.04297 |
| IPR | 2.000 | 2.000 | +0.000 [+0.000, +0.000] | 1 |
| LNS | 2.000 | 2.000 | +0.000 [+0.000, +0.013] | 0.875 |
| MultiStart | 2.000 | 2.000 | +0.000 [+0.000, +0.000] | 1 |
| PSO | 2.000 | 2.000 | +0.000 [+0.000, +0.000] | 1 |
| SA | 2.000 | 2.000 | +0.000 [+0.000, +0.000] | 1 |
| VNS | 2.000 | 0.714 | +0.546 [+0.000, +1.392] | 0.04297 |
| RKO-default | 2.000 | 1.949 | +0.051 [+0.000, +0.611] | 0.02344 |

#### Process launch-to-exit latency (seconds)

| Solver | Python | C++ (64-bit fix) | Paired Δ Python−C++ (95% CI), s | Holm p |
|---|---:|---:|---:|---:|
| BRKGA | 2.400 | 2.013 | +0.387 [+0.340, +0.651] | 0.0007324 |
| BRKGA-CS | 2.405 | 3.018 | -0.490 [-1.366, -0.430] | 0.00293 |
| GA | 2.384 | 2.019 | +0.363 [+0.313, +0.456] | 0.0007324 |
| GRASP | 2.340 | 2.369 | -0.006 [-0.109, +0.026] | 0.3018 |
| ILS | 2.339 | 2.598 | -0.208 [-0.347, -0.190] | 0.0007324 |
| IPR | 2.304 | 2.004 | +0.300 [+0.281, +0.351] | 0.0007324 |
| LNS | 2.334 | 2.009 | +0.324 [+0.278, +0.392] | 0.0007324 |
| MultiStart | 2.357 | 2.004 | +0.353 [+0.323, +0.426] | 0.0007324 |
| PSO | 2.351 | 2.013 | +0.337 [+0.285, +0.377] | 0.0007324 |
| SA | 2.352 | 2.011 | +0.342 [+0.293, +0.458] | 0.0007324 |
| VNS | 2.336 | 2.528 | -0.192 [-0.413, -0.074] | 0.2369 |
| RKO-default | 4.555 | 2.014 | +2.541 [+2.365, +3.872] | 0.0007324 |

The strongest within-sample signal is lower penalized objective difference for C++
in all 12 configurations after Holm correction. C++ also returned feasible
solutions more often for GRASP, ILS, IPR, and VNS, and reached the 1%-gap target
more often within budget for GRASP, ILS, VNS, and the default portfolio. Only ILS,
VNS, and RKO-default had Holm-significant lower time-to-target; many other
configurations never attained that target within 2 seconds. These conclusions are
limited to this workload and the configured implementations.

The process-latency table includes launch and runtime startup. C++ BRKGA-CS and
ILS had higher median process latency than Python, while Python RKO-default had
higher latency than the ten-thread C++ portfolio. Because stopping is cooperative,
returned terminal quality can reflect work completed after the nominal budget;
search-time target results are censored at 2 seconds, while process latency and
this caveat should be considered when interpreting quality comparisons.

The preliminary raw diagnostic is
[`cpp-python-knapsack-2s-preliminary.csv`](cpp-python-knapsack-2s-preliminary.csv), with
10,800 trial rows and full per-trial provenance. The measured Python baseline is commit
`759309a0d8a74324806faba6b41f806eb3721dbc`; its exact source-state hash is
`30ec92bcaaa681be0b7e2f841e997c44d39d263a141a0b667cff1c42b745c142`. After the
run, the exact-profit DP helper was moved unchanged into portable
`benchmarks/knapsack_utils.py` so Windows CI can import the runner; the raw hash
still records the measured pre-move source. Later changes on `main` are also not
represented, so this is a historical snapshot rather than a performance claim
about newer revisions. The companion summary is regenerated from the raw CSV and
is not committed.

## Bounded process-worker resources

A positive `n_jobs` now keeps the complete selected portfolio while limiting
search processes. Assignments are round-robin; each gets a nominal slice of
`time_limit / ceil(N / W)`, bounded by the original common deadline. No extra
full-duration budgets are granted to queued searches. `n_jobs=None` retains the
previous one-worker-per-algorithm default. One additional process hosts the pool;
BLAS/OpenMP threads are outside the search-worker limit.

```bash
uv run --locked python benchmarks/process_budget.py > /tmp/rko-process-budget.jsonl
```

Reference: 2026-10-19, four-CPU WSL2, CPython 3.14.8 / NumPy 2.4.3, GIL enabled,
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
on four workers receive at most a nominal one-third slice each, and shorter
groups finish early without redistributing idle time. First-decode latency is an
observable startup bound, not pure import time. Neither long-budget performance
nor better optimization quality is established. Active callback overruns can leave
queued algorithms less time or no time. Native thread limits and adaptive load
balancing are still separate work.

An exploratory versioned elite-snapshot cache made repeated unchanged large
snapshot queries faster, but corrected full-search trials did not demonstrate a
reliable general benefit and small cases sometimes regressed. It was discarded;
no cache or additional retained worker snapshots were shipped.

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
with adaptive control where supported. Costs, keys, final elites and both final
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
