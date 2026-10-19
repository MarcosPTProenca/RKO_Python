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

## CPU-sized vs. ten-algorithm portfolio comparison

Measurement on **2026-10-19**, same WSL2 four-CPU host, Python 3.14.8, current
optimized blending code, pinned `s000.kp`, online control and pool size 10. Each
portfolio ran with seeds 42/43/44 and a 10-second search budget. Search budget
excludes worker startup, while the reported wall time includes it and callback
overrun. The four-worker preset completed all three runs in a mean **14.06 s**
versus **17.97 s** for ten workers (**21.8% lower elapsed time**); mean profit
was **322,397** versus **303,548**. All six returned feasible solutions.
This one-instance, three-seed measurement is directional, not a general quality
or speed guarantee; it does not measure peak RSS or equal-work throughput.

| Portfolio | Seeds | Mean elapsed s | Mean profit | Mean gap % | Feasible |
| --- | --- | ---: | ---: | ---: | --- |
| SA, BRKGA, GA, PSO (four) | 42–44 | 14.06 | 322,397 | 19.56 | 3/3 |
| All ten configured algorithms | 42–44 | 17.97 | 303,548 | 24.27 | 3/3 |

Reproduce without changing the checked-in reference CSV:

```bash
uv run --locked python benchmarks/portfolio.py /tmp/rko-s000.kp /tmp/rko-portfolio.csv
```

The runner verifies the pinned instance checksum, feasibility, objective and
independently computed exact optimum. `config.toml` now uses the measured
four-algorithm preset; selecting other algorithms remains explicit and supported.

## Capacity-aware Knapsack decoder comparison

Measurement on **2026-10-19**, same four-CPU WSL2 host and pinned 1,000-item
instance. Both decoders used the same four-algorithm process portfolio, online
control, pool size 10, a 15-second budget, and seeds 42/43/44. The new
`GreedyKnapsackDecoder` ranks items by `key * profit/weight`, selecting each only
if it fits. All six returned feasible solutions. Mean profit increased from
**329,353** with the C++ threshold decoder to **394,957** with the capacity-aware
decoder; mean optimality gap fell from **17.83%** to **1.46%**. The profit/weight
greedy reference remains 400,792 (0.00474% gap), so this decoder still trails
that baseline. It is an alternative example, not a replacement for the C++
reference. The data is one instance and three seeds, not general proof.

| Decoder | Seeds | Mean profit | Mean gap % | Feasible |
| --- | --- | ---: | ---: | --- |
| C++ threshold | 42–44 | 329,353 | 17.83 | 3/3 |
| Capacity-aware | 42–44 | 394,957 | 1.46 | 3/3 |

Reproduce with:

```bash
uv run --locked python benchmarks/decoders.py /tmp/rko-s000.kp /tmp/rko-decoders.csv
```

This independently checks the instance checksum, returned feasibility, objective
accounting, and exact optimum. Elapsed durations can exceed the nominal budget
because callbacks are only stopped at callback boundaries.

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
