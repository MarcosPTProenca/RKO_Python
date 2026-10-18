# First spawn-backend validation

Environment: WSL2/Linux, standard CPython 3.14.8 with GIL enabled; four available
logical CPUs. Execution from the Windows-mounted working tree. This machine has
only four logical CPUs, while the default portfolio selects ten algorithms.

Command from `rko_agent` (validation used an isolated uv environment):

```bash
PYTHONPATH=src uv run --locked python -m rko.examples.run_kp_cpp_instances \
  --backend process --limit-time 1 --random-state 42 \
  --output-csv /tmp/rko-knapsack-process.csv
```

One trial per instance, ten algorithm workers and one managed elite pool:

| Instance | Profit | Exact optimum | Gap | Weight / capacity | Total solver time |
| --- | ---: | ---: | ---: | --- | ---: |
| kp10 | 31 | 31 | 0% | 20 / 20 | 6.353 s |
| kp50 | 146 | 149 | 2.01% | 100 / 100 | 6.188 s |

Both solutions are feasible and returned minimization cost equals negative
profit. Total times include process/manager startup and cleanup; they are not
search-only measurements. Seeds govern stream allocation, not deterministic
wall-clock-limited trajectories.

These results establish end-to-end process-backend execution, **not a speedup**.
The earlier unseeded thread smoke tests reached 31 and 147–148 respectively with
roughly 1.1–1.65 s total solver time. Those were separate trials and are not a
controlled algorithm-performance comparison. Here startup and oversubscription
dominate a one-second budget, and objective quality did not improve on kp50.

Real-process integration tests separately verify distinct worker PIDs,
parent/child elite exchange, distinct stable initial RNG streams, all registered
algorithms, callback failures, abrupt process exit, blocked-callback timeouts and
parent interruption cleanup. Linux execution is local; Windows validation is
provided by the GitHub Actions matrix, not assumed from spawn compatibility.

Before claiming a performance benefit, select a portfolio within the machine's
core budget, run longer searches and a fixed-work benchmark, and repeat on larger
instances. The current one-process-per-algorithm milestone rejects a selection
larger than an explicit `n_jobs` budget instead of silently queueing searches.
