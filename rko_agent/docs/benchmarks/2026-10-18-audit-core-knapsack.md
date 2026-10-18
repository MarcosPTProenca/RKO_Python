# Larger Knapsack validation after audit-core corrections

## Scope

Production revision: `85556a679e36a9d33163901dab11703454b9adb2`.
This repeats the original experiment through the new RKO class after correcting
fitness ownership, Q maxima/rewards, named grid semantics, feasible online states,
IPR remainder handling and Nelder-Mead seed retention. Callback-budget sessions
and pool-count transport also changed. This is not a controlled attribution of
performance to any one fix, and the remaining audit work is not complete.

Use the unchanged threshold decoder (`key > 0.5`) and reference penalty objective,
portfolio SA/BRKGA/GA/PSO, online control, four process workers, 15 search seconds
and seeds 42/43/44. Thread trials initialize application-global RNGs as before;
thread and process streams/trajectories are not matched. The existing independent
DP oracle and greedy comparator are retained.

## Data and reproduction

Public KPLIB `00Uncorrelated/n01000/R01000/s000.kp`, revision
`c5bea0df8169749caaba5ce7dfcf21437aa1ca5c`: 1000 items, capacity 252480.
SHA256: `8f555b2b40dff1298d841a8e5abc327a8f1135ce8188e84249cd1352f959ffed`.
The external instance is not redistributed because its license remains unverified.
The [original report](2026-10-17-large-knapsack.md) records download provenance
and platform; this run uses the same WSL2 four-CPU host and Python 3.14.8.

From `rko_agent`, with the instance downloaded separately:

```bash
uv run --locked python docs/benchmarks/large_knapsack.py \
  /tmp/rko-large-benchmark/s000.kp \
  docs/benchmarks/2026-10-18-audit-core-knapsack.csv
```

The exact DP optimum is **400811**, computed in 3.481 seconds in this run.
Greedy profit remains **400792**, gap **0.00474%**.
Raw results: [`2026-10-18-audit-core-knapsack.csv`](2026-10-18-audit-core-knapsack.csv).

## Observed results

All six searches completed without errors. Independent accounting confirmed
feasibility and objective/key consistency for every returned candidate.

| Backend | Seed | Profit | Gap % | End-to-end seconds | Mean CPU cores |
| --- | ---: | ---: | ---: | ---: | ---: |
| process | 42 | 326820 | 18.4603 | 17.3517 | 2.8826 |
| process | 43 | 326600 | 18.5152 | 17.6872 | 2.7939 |
| process | 44 | 321436 | 19.8036 | 18.1231 | 2.7642 |
| thread | 42 | 307511 | 23.2778 | 15.0342 | 1.0450 |
| thread | 43 | 313889 | 21.6865 | 15.0796 | 1.0439 |
| thread | 44 | 302258 | 24.5884 | 15.0461 | 1.0464 |

Processes averaged gap 18.9264%, elapsed 17.7207 s and 2.8136 CPU cores.
Threads averaged gap 23.1842%, elapsed 15.0533 s and 1.0451 CPU cores.
The process best gap 18.4603% is worse than the earlier sample's 17.56% best gap;
three timed seeds do not establish a statistically reliable regression or its
cause. Multiple code changes and scheduling differences prevent isolating effects.

## Interpretation and remaining work

The class API, installed execution and correctness fixes work on a larger input;
**solution quality is still poor and is not fixed by the audit-core changes**.
Process CPU use still demonstrates multicore execution, not fixed-work speedup.
Callback tracking copies vectors and adds validation overhead; no throughput or
memory advantage is claimed without profiling. Current timings are consistent
with startup overhead and cooperative callback stopping, not a hard deadline.

Before claiming a professional optimizer release: isolate RNG ownership, make
worker budgets practical, establish declared per-algorithm parity/deviations,
profile fixed-work execution, and evaluate separate problem-aware decoding and
initialization across multiple instance families and more seeds. Preserve the
reference decoder and these negative results rather than tuning away the baseline.
