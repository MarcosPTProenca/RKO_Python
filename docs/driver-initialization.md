# Full-driver initialization: Python and the pinned C++ reference

## Scope and outcome

This is a source-contract audit, not a change to initialization defaults or a
quality/timing comparison. Python's shared-pool capacity does **not** request a
prefilled population. The pinned C++ driver creates a full shared pool before
launching algorithms. Matching `pool_size=10` to `sizePool 10` therefore does not
match initialization work or starting search context.

Reference: `RKO_Cpp_v2.0`, revision
`126e35873e50dc308795b58b8c75d37f8de4c857`, `Program/src/Main/main.cpp`,
`Program/src/Method.h`, and `Program/src/MH/IPR.h`.

## C++ startup pool

`Main/main.cpp` starts its run clock, clears/resizes the shared pool to `sizePool`,
then calls `Method.h::CreatePoolSolutions` before entering the OpenMP algorithm
loop. For positive capacity P and chromosome length n, that function:

1. Generates P random-key vectors and calls `Decoder` on each.
2. Sorts all entries by increasing objective using selection sort.
3. Scans backward once. Whenever adjacent entries have equal objective values,
   it performs the integer loop `j < 0.2*n`: draw a coordinate and replace its key,
   then re-evaluate that entry once. Coordinates can be drawn repeatedly.
4. Re-sorts if at least one entry was perturbed.

This is a **single cost-tie perturbation pass**, not a chromosome-uniqueness
retry loop. For finite scores, let T be the number of adjacent equal-cost pairs
in the initial sorted pool. The source implies P+T decoder calls, between P and
2P-1 inclusive; a flat objective gives 2P-1 calls. These are source-derived
bounds, not measured application counts. Equal costs and duplicate chromosomes
can remain. The stock C++ insertion policy also rejects repeated objective costs;
Python instead retains [one best observation per chromosome](elite-diversity.md).
Copying these policies blindly would undo an explicit Python diversity contract.

The driver records `pool[0]` as its initial best. If a run restarts, it can call
`CreatePoolSolutions` again; that is additional work, not a one-time universal
constant. Individual algorithms may also create their own private populations.
The shared startup pool is not a substitute for those private populations.

## Current Python startup

`RKO._execute` in `src/rko/solver.py` creates an empty `SolutionPool` and constructs
selected algorithms without driver-level candidate evaluation. Serial execution
shares that pool across algorithms in order; threads share it concurrently.
Later serial searches can therefore inherit earlier elites, and thread startup
observations depend on peer progress. There is no global prefill barrier.

Process execution creates an empty managed pool in
`src/rko/orchestration/processes.py::run_processes`. Worker constructors report
ready before their searches run. Releasing the workers starts search work, not
a shared pool-initialization phase. A queued search can inherit elites from
previous/parallel searches; no worker is promised a full initial pool.

Candidates generated inside algorithms pass through `SearchSession`: completed
finite objective calls contribute to that search's count and incumbent, including
interrupted private-population initialization. Current standalone IPR inserts
its first observation when needed and tries at most one extra random candidate
to obtain a pair. It does **not** fill the configured capacity or retry until
all chromosomes are unique. See [the IPR initialization distinction](ipr-diagnosis.md).

## Clock and budget distinctions

C++ `Decoder` returns an objective value; Python separates decoding from objective
evaluation and counts completed finite objective calls. Compare equivalent
candidate-evaluation work, not the sum of Python decoder and objective callbacks.

| Boundary | Pinned C++ driver | Current Python |
| --- | --- | --- |
| Reported elapsed origin | Before initial shared-pool creation | Public solve includes configuration/startup |
| Shared startup callbacks | Decoder calls before algorithms start | No driver-level seed callbacks |
| Algorithm search clock | Fresh local clock, e.g. IPR uses `MAXTIME*restart` | Serial/thread: per-search duration; process: remaining common-deadline allocation |
| Initialization stop boundary | No time/cancellation check inside `CreatePoolSolutions` | Ordinary algorithm callbacks use the session's cooperative boundary |
| Evaluation accounting | No Python-style per-search initialization report in the reference driver | Completed callbacks counted in each search report |

A clock that starts before pool creation does **not** prove its cost was deducted
from algorithm search time. C++ initializes `end_time` before pool creation and
does not refresh it before the first outer-loop condition; algorithms then start
their own clocks. Do not describe this as a strict common deadline. Python also
allows a first valid evaluation after startup has consumed its callback deadline;
active callbacks cannot be interrupted. Neither policy guarantees a hard wall cap.

## Protected benchmark interpretation

The separate `cpp-python-knapsack-benchmark` worktree is pinned at `7ee93ca`.
Its harness sets C++ `sizePool 10`, Python `pool_size=10`, and `restart 1`; it does
not replace C++ pool creation with an equivalent Python prefix. Its C++ telemetry
clock is inserted at the run-clock boundary, before pool creation. Historical
results must retain those semantics; current IPR bootstrap/diversity corrections
must not be retroactively attributed to that pinned Python revision.

This audit neither edits its source/cache/CSV nor restarts or duplicates that run.
It does not establish that startup differences alone caused any feasibility or
quality gap. The same nominal capacity and duration are insufficient evidence of
matched initialization, callback work or search time.

## Next decision and evidence

Before choosing a Python prefill policy, define and measure a separate bounded
initialization phase: candidate budget, RNG ownership, callback isolation, finite
validation, deadline/incumbent recovery and an explicit report of seed evaluations.
Count it once, rather than silently charging it to the first selected algorithm or
adding unreported evaluations before the search. Preserve chromosome uniqueness;
any C++-style cost-tie perturbation would require a separate documented decision.

Then compare the same initial vectors/work budgets against the current empty-pool
policy across general numerical/permutation objectives and relevant instance
families. Separate quality from callback throughput before selecting native kernels.
Do not change `pool_size` from capacity to mandatory seed count without a deliberate
compatibility decision. No prefill option or result-schema extension is added here.

Regression probes use the real public serial/thread dispatchers, factory, callback
sessions and result metadata, replacing only one algorithm body. Capacities 1, 10
and 100 all enter construction/search with zero entries and zero user evaluations;
one completed observation is reported once. They characterize driver policy,
not the private initialization of every algorithm. Process startup and the C++
behavior above are source-audited, not new compiled-C++ or spawned-probe results.
