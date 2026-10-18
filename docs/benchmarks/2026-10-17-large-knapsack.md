# Empirical validation on a public 1,000-item Knapsack instance

## Question and scope

Does the existing solver work beyond the 10/50-item smoke examples, use multiple
CPU cores, and produce competitive solutions? This experiment changes no
production solver code, decoder, hyperparameters or default configuration.

## Data and independent references

Public KPLIB instance: `likr/kplib`,
`00Uncorrelated/n01000/R01000/s000.kp`, revision
`c5bea0df8169749caaba5ce7dfcf21437aa1ca5c`.

- Source: <https://github.com/likr/kplib/blob/c5bea0df8169749caaba5ce7dfcf21437aa1ca5c/00Uncorrelated/n01000/R01000/s000.kp>
- SHA-256: `8f555b2b40dff1298d841a8e5abc327a8f1135ce8188e84249cd1352f959ffed`.
- Items: **1,000**; capacity: **252,480**.
- Exact optimum: **400,811**, computed independently by capacity-indexed 0/1
  dynamic programming, using NumPy int64 storage and O(n * capacity) work.
  Reference computation took **2.944 s** on this host.
- Oracle self-checks: bundled 10/50-item optima (31/149), and a one-item example
  that would fail if the DP incorrectly allowed unlimited copies.
- Deterministic profit/weight greedy baseline: **400,792**, gap **0.00474%**.
  Items are visited in descending profit/weight order, selecting those that fit.

The public input is downloaded separately rather than vendored: its repository
has no detected license file. Source fingerprint verification prevents silently
switching datasets.

## Method

Host: WSL2/Linux, CPython 3.14.8 with the GIL enabled, four available logical
CPUs. Same host/environment as the small-instance baseline.

- Portfolio: **SA, BRKGA, GA, PSO**, selected before observing results.
- Existing online control (`control=1`) and algorithm parameter TOMLs retained;
  shared elite pool size 10. A temporary configuration avoids editing defaults.
- **15 seconds** requested concurrent search per run; explicit **n_jobs=4** for
  process mode. Process startup is excluded from the search budget.
- Seeds: **42, 43, 44**. For each seed, process then thread execution.
- Original `key > 0.5` decoder and 100000-per-excess-weight penalty retained.
- Returned decision count, profit, weight, feasibility and penalized objective
  checked directly, independently of the production solution-evaluation helper.
- CPU seconds include parent process plus reaped children; average CPU cores is
  CPU seconds divided by total elapsed seconds. These include startup, cleanup
  and the small amount of result verification, not just search.
- Thread seeds initialize shared Python/NumPy RNGs. They do not reproduce process
  workers' independent RNG streams; seed labels are not matched trajectories.

## Observations

All six runs completed without exceptions; all returned solutions were feasible
and their reported costs matched negative profit.

| Backend | Seed | Profit | Gap to exact | Weight | Total seconds | Average CPU cores |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Process | 42 | 330,154 | 17.63% | 251,921 | 18.343 | 3.06 |
| Process | 43 | 330,438 | 17.56% | 252,220 | 18.010 | 3.12 |
| Process | 44 | 327,909 | 18.19% | 252,472 | 17.942 | 3.13 |
| Thread | 42 | 316,967 | 20.92% | 251,931 | 16.485 | 1.03 |
| Thread | 43 | 322,138 | 19.63% | 252,094 | 15.862 | 1.02 |
| Thread | 44 | 315,923 | 21.18% | 252,156 | 16.396 | 1.02 |

Mean process gap: **17.79%**, total **18.10 s**, average **3.10 cores**.
Mean thread gap: **20.58%**, total **16.25 s**, average **1.02 cores**.

Raw measurements: [`2026-10-17-large-knapsack.csv`](2026-10-17-large-knapsack.csv).

## Interpretation and limits

1. **Multicore is empirically demonstrated:** aggregate CPU use is greater than
   one core in process mode and approximately one in thread mode.
2. **Optimization quality is not competitive on this instance.** The best RKO
   profit is 330,438 (17.56% gap), far below greedy's 400,792. A successful run or
   feasible output is not enough to call this implementation a strong solver.
3. **This is not a speedup measurement.** Search budgets match, but end-to-end
   process time is greater. Different random streams, only three runs, fixed
   execution order, one easy uncorrelated instance, and no fixed-work target
   prevent a general performance or statistical-superiority claim.
4. **The oracle itself is faster and exact here.** This experiment does not
   establish a reason to prefer generic RKO over a specialized Knapsack solver.
5. **Next diagnostic target:** examine the naive threshold decoder, initialization
   and search behavior against a feasible, problem-aware decoder and simple
   baselines. This is a direction to investigate, not a proven root cause. Do
   not change the reference decoder and then present its results as unchanged
   C++-objective parity.

## Reproduce

From `rko_agent`, with the declared Python/uv environment:

```bash
mkdir -p /tmp/rko-large-benchmark
curl -fL \
  https://raw.githubusercontent.com/likr/kplib/c5bea0df8169749caaba5ce7dfcf21437aa1ca5c/00Uncorrelated/n01000/R01000/s000.kp \
  -o /tmp/rko-large-benchmark/s000.kp
PYTHONPATH=src uv run --locked python docs/benchmarks/large_knapsack.py \
  /tmp/rko-large-benchmark/s000.kp /tmp/rko-large-benchmark/results.csv
```

The runner is a Linux/WSL measurement artifact, not a new supported public API.
It asserts the input hash and runs oracle/solution self-checks. Timing and
stochastic objectives will vary across runs and machines. Original execution
used `/tmp/rko-validation-tools/packages/bin/uv` and
`UV_PROJECT_ENVIRONMENT=/tmp/rko-validation-env` to preserve the Windows venv.
