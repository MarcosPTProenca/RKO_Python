# Larger Knapsack benchmark

Latest measurement: **2026-10-18**, starting at 15:36 UTC, on standalone solver
revision `daa2e94fb1379994705168d5d6f3c2cc8674ba58`. Cleanup moves this runner but
does not change it or the solver. Host: WSL2/Linux, Python 3.14.8 with the GIL,
four available CPUs. This is one reproducible reference experiment, not a
performance guarantee or a release certification.

## Reproduce

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

## Method

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

## Current results

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
