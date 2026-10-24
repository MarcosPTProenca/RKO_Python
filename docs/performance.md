# Performance target and native-backend evaluation

**Status: experimental optional Rust blending kernel; not a Rust engine or C++ parity claim.**
The target is to **match or exceed the pinned C++ RKO on declared workloads**, in
solution quality and time under comparable resources. A language change, passing
CI, higher evaluations/second or a faster isolated kernel does not meet that target
by itself. Results outside the evaluated workload/resource envelope remain unknown.

## What the current evidence establishes

The default implementation is Python plus NumPy, with no compiler dependency for users.
Several kernels and allocation paths have measured improvements over earlier Python
versions; [each benchmark identifies its workload and limits](https://github.com/MarcosPTProenca/RKO/blob/main/benchmarks/README.md).
Those measurements do not establish whole-solver C++ performance parity.

The [1,440-pair prefill study](prefill-expanded-work.md) finds broader but not
universal IPR benefits, mixed GRASP and mostly neutral MultiStart. Its 500-variable
GRASP cases cannot finish their first construction within either evaluation cap;
all 102 wins there retain startup best. Fixed-work diagnostics and complete-cycle,
real-clock quality experiments answer different questions. We need both.

The historical long-running Knapsack comparison uses Python revision `7ee93ca`,
which predates subsequent contract and startup corrections. Preserve that run as
historical evidence; do not combine its rows with current-code results or infer the
current library's performance from it. The historical runner is now available as
`benchmarks/cpp_python_knapsack.py`, with the completed two-second reference clearly
separated in [benchmark documentation](https://github.com/MarcosPTProenca/RKO/blob/main/benchmarks/README.md#python-versus-c-knapsack-comparison).
Fresh invocations execute the current checkout, not the archived implementation;
use new source-identified output/cache locations after the protected run finishes.
The integrated runner's TOML/helper fingerprint checks prevent unsafe resume across
those changes. It still needs the additional resource/stage diagnostics below to
serve as a full current-revision acceptance test. No unfinished long-run results
are published by integrating its code.

The [baseline contract checklist and fixed-work diagnostic](performance-baseline.md)
provide source-identified records and optional function-level profiling for the
initial investigation. This is a restricted serial diagnostic, not whole-solver
performance evidence or a selected native backend.

The [invocation and resource study](invocation-profile.md) reuses the startup,
portfolio and native-callback probes in fresh hosted interpreters. Its registered
scopes separate constructor-plus-solve time, internal search timing and sampled
RSS; they are diagnostic evidence, not an achieved optimization or parity claim.

## Optional native blending

The mixed package retains the setuptools Python build. Neither building nor using
Rust is enabled by default. The optional component accelerates only shared
Nelder-Mead blending; SA, GA and BRKGA control and user callbacks remain Python.
`backend` continues to mean `process`, `thread` or `serial`, never a language.

Two explicit controls have different purposes:

| Control | Default | Meaning |
| --- | --- | --- |
| `RKO_BUILD_NATIVE=1` | `0` | Build the optional release extension; requires Rust 1.90.0 and normal-GIL CPython 3.14. A requested compilation failure aborts the build. |
| `RKO_USE_NATIVE=1` | `0` | Activate a compatible installed extension before the first `rko` import. Missing/incompatible binaries produce an actionable warning and use Python. |

```bash
# Ordinary Python wheel/sdist; no Rust compiler required.
uv build

# Explicit mixed build. The pinned Rust toolchain must be available.
RKO_BUILD_NATIVE=1 uv build --wheel

# Development editable build, then explicit runtime activation.
RKO_BUILD_NATIVE=1 uv sync --locked --group dev --reinstall-package rko
RKO_USE_NATIVE=1 uv run --locked --no-sync rko src/rko/examples/instances/kp50.txt
```

In PowerShell, set the equivalent variables with
`$env:RKO_BUILD_NATIVE = "1"` or `$env:RKO_USE_NATIVE = "1"` before the command;
remove them afterward when returning to the default Python mode. A binary wheel
built elsewhere does not require a compiler at installation time. Native source
builds do; ordinary source builds remain Python-only. Build flags do not implicitly
enable runtime acceleration, and changing a runtime variable after imports does
not reconfigure already imported worker modules.

The supported native path requires finite, aligned, C-contiguous float64 parent
arrays and the normal library-owned/builtin Python RNG. Other representations,
custom RNGs and unusual factors retain reference behavior. Parents and output are
not exposed as borrowed Rust slices: the kernel uses safe owned snapshots. It calls
the original RNG twice per gene in the original order and never batches, caches or
rewrites user decoder/objective calls. Native/callback runtime failures propagate;
only known extension-import/compatibility failures select Python fallback.

The source-identified [720-pair kernel confirmation](https://github.com/MarcosPTProenca/RKO/actions/runs/40044712053)
used 30 fresh seeds per group with unchanged scalar, permutation, object-payload
and NumPy callbacks. For 500 genes, the research candidate reduced complete serial
fixed-work invocation medians by 12.5–20.3% across SA/GA/BRKGA. Protected 20-gene and
single-process peak-RSS bounds passed. Those results identify the kernel and scope;
they are not a claim that arbitrary callbacks, timed adaptive quality, portfolios
or all platforms achieve the same gains.

The [installed-wheel confirmation](https://github.com/MarcosPTProenca/RKO/actions/runs/40063949702)
then compared runtime opt-in disabled/enabled in the same installed mixed wheel,
using 720 new paired invocations and 30 fresh seeds per group. It preserved every
result/pool/count/RNG fingerprint and observed 13.35–20.95% median complete-invocation
gains in the 500-gene groups. Predeclared paired bootstrap intervals excluded no
improvement; conservative family-adjusted upper bounds stayed below 3.32% slowdown
for protected 20-gene inputs and 2.42% peak-RSS growth (limits 5% and 10%). This remains
a serial fixed-evaluation scope, not timed/adaptive-quality or C++ parity evidence.

[Packaging CI](https://github.com/MarcosPTProenca/RKO/actions/runs/40063461860)
validated normal-GIL CPython 3.14 source builds and installed wheels/sdists on
Ubuntu, Windows and macOS. It checks real native execution, exact component and
managed-search candidate prefixes, unavailable-extension fallback, pure builds
without usable compilers, and pure builds after native builds. Existing installed
smokes also cover bounded serial/thread/process solves and fixed/adaptive settings;
those are functional checks, not comparative quality or portfolio speed studies.

### Extended qualification and result provenance

When native blending is admitted, `dict(result.versions)` includes
`rko-native-blending: rko-blending-rng-buffer-v1`. Default Python and unavailable
binary fallback preserve the original three version entries. This describes the
selected component, not proof that every algorithm or input invoked it.

The separate [native qualification workflow](https://github.com/MarcosPTProenca/RKO/blob/main/.github/workflows/native-qualification.yml)
builds normal CPython 3.14 wheels through pinned cibuildwheel, with manylinux 2.28
x86-64, native Windows AMD64 and macOS ARM64 targets. Its default auditwheel,
delvewheel and delocate repair stages inspect platform dependencies before
installed replay and timed-portfolio functional checks. Inspection rejects
unreviewed extra bundled native libraries and altered/missing notices. Only digest
and inspection reports are uploaded: compiled wheels are not published or retained
as downloadable release artifacts. Owner licensing/release approval remains open.
An actual free-threaded Python 3.14 job tests Python-only source/installation and
observable fallback; the normal-ABI extension is deliberately unsupported there.

`tools/smoke_portfolio.py --matrix --functional` exercises SA/GA/BRKGA portfolios
with fixed/adaptive parameters, opaque objects/permutations, serial/thread/process
execution, bounded histories, exact final cost recomputation, seed/accounting
metadata, pickle and worker cleanup. Functional probes observe real kernel calls
in participating processes without consuming search streams. These probes must
never enter acceptance timings.

The maintained [timed screening protocol](https://github.com/MarcosPTProenca/RKO/blob/main/benchmarks/native_portfolio.py) instead
runs **without profiling or functional kernel probes**, in fresh isolated workers
using the same installed wheel. It alternates both variants over three preregistered
seeds per group, a configured two-second search limit, 20/500 dimensions, two
callbacks and all six backend/adaptation combinations. Existing budget semantics
are preserved: serial runs give each algorithm its search limit (approximately
six seconds for three algorithms), threads run concurrently, and process workers
divide their common deadline among assigned searches. Compare native/reference
**within** a backend, not unlike end-to-end budgets across backends. Raw quality, evaluation counts, complete process
latency and recursive process-tree sampled PSS are retained. PSS excludes the
collector, includes manager/tracker helpers, and records incomplete snapshots.
It is proportional physical memory, not an exact peak. Normalized quality uses
known fixture objective ranges, not arbitrary epsilon denominators.

This three-seed screen is descriptive only: it does not establish timed quality
noninferiority, portfolio speed/memory acceptance, universal callback gains or C++
parity. Timed trajectories may legitimately differ; unlike fixed-work replay, they
must not be forced to have equal evaluation counts or costs. Do not pool this
protocol with the earlier 720 fixed-work pairs or reinterpret test durations as
performance results.

At source `ba46006`, [CI](https://github.com/MarcosPTProenca/RKO/actions/runs/40094960238)
and [extended qualification](https://github.com/MarcosPTProenca/RKO/actions/runs/40094960432)
passed all 15 jobs, including actual free-threaded Python-only tests and repaired
installed wheels for `manylinux_2_28_x86_64`, `win_amd64` and `macosx_11_0_arm64`.
All 72 timed pairs completed with matched installed-source/binary identities and
no functional probes in measurement. All 24 groups are retained, including small
input groups with slightly lower evaluation throughput. In the twelve 500-key
groups, median paired evaluation-count ratios ranged from 1.26 to 1.43 and
normalized quality deltas were negative (better). Median sampled tree-PSS ratios
across groups were 1.008–1.027. These are descriptive pilot medians, not uncertainty
bounds, acceptance thresholds, shorter fixed-budget latency or universal gains.
The original pilot remains the reference; routine CI repetitions are not pooled.

### Independent thirty-seed timed confirmation

`benchmarks.native_confirmation` freezes a separate protocol before collection:
30 NEW seeds 50000–50029 for every group, the same two-second configured search
limit and callback/dimension/backend/adaptation matrix, Python 3.14.9, NumPy 2.4.3
and one BLAS thread. Six complete source-identified shards yield 720 pairs. Source,
helper, workflow and native build hashes are recorded before the first trial and
verified after collection; pilot seeds, partial shards, duplicate rows, changed
artifacts and profiled functional probes cannot enter the report.

Acceptance concerns paired population medians, not every stochastic trajectory:

- Quality: the simultaneous upper bound of native-minus-Python normalized regret
  must be **at most zero**. No positive loss allowance or epsilon is introduced.
- 500 keys: median completed-evaluation throughput gain at least 10%, with the
  upper bound of complete-process time per evaluation below the Python reference.
- Protected 20 keys: the simultaneous upper bound of time per evaluation at most
  1.05 times the reference. This is throughput under fixed budgets, not shorter
  fixed-budget solve latency.
- Sampled process-tree PSS: simultaneous upper ratio at most 1.10 for every group.

The report uses exact binomial order-statistic median intervals, with Bonferroni
family coverage of at least 95% across 72 quality/time-per-evaluation/PSS intervals,
assuming independent seed-pair observations. Discrete ranks and ties make coverage
conservative. With 30 observations the frozen lower/upper ranks are 6 and 25.
There is no bootstrap fitting, optional stopping, post-data margin selection or
pooling of routine CI repeats. All groups and failed gates remain visible.

Opt in through the native workflow's `study=confirmation` dispatch, or the explicit
`native-confirmation` PR label when the workflow is not yet on the default branch.
Remove the label after starting so later source edits do not request another long
confirmation. No source changes are permitted during collection. A successful
**reporting job** means the experiment was complete and validated; only the JSON
`qualification_status=established` means all predeclared gates passed. A result
`not_established` is preserved rather than converted to a technical CI failure or
misrepresented as proof of harm. Neither outcome authorizes publication.

#### Completed independent confirmation

[Run 40109493113](https://github.com/MarcosPTProenca/RKO/actions/runs/40109493113),
frozen at source `667001be5983df88fd48d32e41091b5faa189d3a`, completed all **720
independent pairs**. Local reanalysis reproduced the hosted report exactly. The
[source-identified reference measurement](https://github.com/MarcosPTProenca/RKO/blob/main/benchmarks/native-timed-confirmation-reference.json)
retains every group, simultaneous interval and gate, including negative findings.

- Time-per-evaluation gates passed in all 24 groups. For 500 keys, median complete
  process time per completed evaluation fell **19.12–30.99%**. This is not shorter
  fixed-budget solver latency.
- The protected 20-key upper slowdown bound was **3.403%**, below 5%.
- Sampled process-tree PSS gates passed in all 24 groups; the largest upper growth
  bound was **3.039%**, below 10%. This is not an exact memory high-water mark.
- Strict zero-loss quality was established in **18/24 groups**, including 11/12
  large-input groups. It was **not established** for the 20-key object callback in
  process/fixed, process/adaptive, serial/adaptive, thread/fixed and thread/adaptive,
  or the 500-key object callback in serial/adaptive. These intervals crossed zero;
  none established quality loss. Nonpositive observed medians do not remove this
  uncertainty.

**Global qualification remains `not_established`.** Criteria and collected sample
counts were not changed after viewing results, and no additional sampling was
performed just to obtain a pass. The reporting workflow completed successfully
because collection/analysis were valid, not because all acceptance gates passed.
Python remains the default and native use remains an explicit experimental opt-in.

#### Negative-control diagnosis of the six inconclusive groups

The separate `benchmarks.native_quality_diagnosis` protocol does **not** extend or
replace that confirmation. It selects exactly its six inconclusive object-callback
groups and collects 30 NEW seeds61000–61029 per group. Each seed has three fresh
workers: PythonA, identical PythonB, and admitted native. All six possible arm orders
occur five times, balancing position without sharing a running interpreter or
changing callbacks. This yields180triads/540timedworkers, not additional acceptance
pairs. The native contrasts share Python controls and are not independent tests.

A separate functional check compares all512candidate prefixes for SA/GA/BRKGA in
adaptive mode at20/500keys under an evaluation-indexed logical clock. Virtual time advances
across learning windows but stays below the functional deadline. This checks
checked-prefix replay when policy timing is held equal; it is not timed quality
or universal replay proof. Real timed workers never run this clock or a profiler.

Existing immutable per-search metadata/histories are serialized after solving;
no new per-evaluation hook is installed. Reports retain PythonB-minus-PythonA and
native-minus-each-Python quality contrasts, wins/ties/losses and per-search changes.
They reuse the original conservative median interval ranks rather than relaxing
confidence or quality margins. Repeat variability in parallel fixed-parameter
searches cannot by itself isolate pool cooperation from OS scheduling. Any
mechanistic interpretation must disclose that limitation. All original gates and
`qualification_status=not_established` remain unchanged regardless of this
**diagnostic-only** outcome. Opt in with workflow `study=diagnosis`.

Run `uv run --locked python tools/validate_native_package.py` on a machine with the
native build prerequisites to check pure/native wheels and sdists, default and
explicit activation, full native tests, managed-search candidate-prefix replay and
post-native pure-build contamination. It builds into temporary directories and
publishes no binary. Platform wheels, release licensing/attribution in `NOTICE`,
and full native-backend adoption remain separate release gates; no automatic
publishing or change to Python defaults is introduced.

## The C++ acceptance target

Reference: [RKO C++ v2, revision
`126e35873e50dc308795b58b8c75d37f8de4c857`](https://github.com/RKO-solver/RKO_Cpp_v2.0/tree/126e35873e50dc308795b58b8c75d37f8de4c857).
Use mathematically valid objective arithmetic; the historical Knapsack experiment
uses an identified 64-bit arithmetic correction rather than relying on signed
integer overflow. Record the patch hash and label the variant, not just “C++”.

Before an experiment, fix the problem families, dimensions, budgets, resource
limits, target gaps and acceptance rules. The minimum comparison record is:

| Axis | Required comparison |
| --- | --- |
| Validity | Independently decode/re-evaluate returned keys; report feasibility and every failed run |
| Quality | Best feasible gap/quality at equal end-to-end and search-only budgets, with initialization costs visible |
| Time to target | Reach rate plus censored time-to-target; do not drop failed/non-reaching trials |
| Throughput | Separate fixed-work callback/framework diagnostics; not a replacement for quality results |
| Resources | Same machine class and available CPU budget; actual workers/native teams, process CPU and memory accounting |
| Repeatability | Multiple seeds and instance families, raw rows, source/data/config/toolchain hashes and declared uncertainty |
| Coverage | Each claimed algorithm/portfolio, offline and real adaptive modes, short and long budgets, complete-stage counts |

C++ fills its shared pool before search; Python starts empty unless prefill is
opted in. The two implementations also have different uniqueness, RNG and scheduling
policies. See [compatibility](cpp-compatibility.md) and [initialization](driver-initialization.md).
Equal pool capacities or nominal `time_limit` values do not establish equal work.
Python serial time is per selected algorithm, and opt-in startup has its own
allowance. Always show complete invocation time as well as component times.

The reference [C++ driver](https://github.com/RKO-solver/RKO_Cpp_v2.0/blob/126e35873e50dc308795b58b8c75d37f8de4c857/Program/src/Main/main.cpp)
requests one OpenMP thread per selected metaheuristic. Python's process workers
are CPU-bounded by default. Comparing their defaults is a product-default study,
not an equal-resource engine test. Verify actual concurrency and queued search
budgets; do not assume setting an environment variable alone equalizes execution.

Do not claim parity from a nonsignificant difference or a pooled average that
hides regressions. Use predeclared non-inferiority/superiority rules and uncertainty
per claimed regime; if the evidence cannot exclude meaningful regression, report
**inconclusive**. No universal “at least C++ speed” guarantee is justified for
arbitrary Python callbacks, dimensions and hardware.

## Why a Python API with Rust underneath is feasible, but not sufficient

PyO3 supports native Python extensions and Maturin supports mixed Python/Rust
packages [1, 4]. The public `RKO`/result interface can remain Python-facing.
However, the current evaluation path is:

```text
search/local-search candidate
    -> deadline/cancellation check
    -> detached chromosome snapshot + decoder-protecting copy
    -> user Python decoder
    -> deadline/cancellation check
    -> user Python objective + finite-value validation
    -> completed-evaluation count and best-incumbent retention
```

These protections are real behavior in
[`SearchSession`](https://github.com/MarcosPTProenca/RKO/blob/main/src/rko/orchestration/search.py), not disposable overhead.
Moving the search loop into Rust still calls Python for arbitrary existing
callbacks. On GIL-enabled CPython those calls require interpreter attachment/GIL
access. Rust-only work can detach; ordinary Python callbacks cannot execute while
detached [1, 2]. NumPy/native callbacks may themselves release the GIL, so the
actual callback mix must be measured rather than assumed.

A useful bound for a **kernel-only** change is `S = 1 / (u + (1-u)/s)`, where `u`
is the measured unchanged fraction and `s` is that kernel's speedup. If unchanged
callback/other work is 80% of runtime, even an infinitely fast remaining core is
limited to 1.25x. This is an illustrative model, **not a measured RKO fraction**.
A full-engine change that also removes IPC/startup has a different decomposition.

## Options worth comparing

| Option | Potential benefit | Main limitation / adoption condition |
| --- | --- | --- |
| Existing Python + NumPy | Lowest packaging cost; optimize proven bulk/allocation paths | Python control and callback overhead remain; NumPy arithmetic is already native |
| Optional coarse Rust kernels through PyO3 | Keep Python API/fallback; move substantial callback-free work across one boundary | Per-gene/per-evaluation FFI may erase gains; profile and prove whole-search benefit |
| Full Rust search engine, Python callbacks | Native state, candidate generation and potentially less manager/process overhead | Repeated Python callbacks, new scheduler/RNG/safety contracts and much larger validation cost |
| Native engine plus explicitly native problem adapter | Can keep most work outside the interpreter; strongest route toward compiled end-to-end execution | Extra adapter work for users; native-only wins are not general Python-callback gains |
| Bind/refactor the C++ implementation or use another compiled extension | A comparison alternative; Rust is not inherently faster than C++ | Existing application/global-state integration, compatibility, ownership and build work remain |

**Recommended investigation order, not implementation approval:** profile first;
then a bounded optional-kernel experiment if callback-free work can justify it.
Evaluate a whole Rust engine only if larger native ownership is necessary to meet
the C++ target. A compiled adapter must remain optional for a general-purpose
library, not a hidden Knapsack-specific repair. No engine-selector API is designed
or introduced here; today's `backend` means process/thread/serial only.

Static source inspection suggests investigating repeated neighborhood/GRASP/IPR
control, candidate construction, blending/RNG bookkeeping, callback boundaries and
manager RPCs. This is a **candidate list, not a measured bottleneck ranking**.
Existing vectorized PSO/NumPy blocks may offer less headroom than scalar control.
Kernel, Python-callback and native-callback paths must be measured separately.

## Gates before adopting a native component

1. **Profile the real cost.** Separate reader/import/spawn, initialization,
   candidate generation, copies, decoder/objective, local search, elite IPC and
   adaptive control. Use cheap, expensive/native and application callbacks, plus
   algorithm-stage completion. No new local timing work during the protected run.
2. **Use a disposable, bounded experiment.** One kernel or one algorithm, same
   objective/problem and work limits, Python fallback, release-mode native build.
   Include native compute with and without Python callbacks to expose bridge cost.
   Reject a microbenchmark-only win or a material regression in a claimed regime.
3. **Preserve contracts.** Callback payload/mutation isolation, retained arrays,
   errors/nonfinite rejection, incumbent recovery, counts and cancellation checks
   stay intact. Random draw order, first-minimum ties, signed zero, partial blocks
   and extreme GRASP lattice bounds need differential tests or explicit deviations.
   Do not silently batch/reorder stateful callbacks or change adaptive timing.
4. **Own native memory safely.** NumPy borrowing checks do not prevent arbitrary
   Python/native code from mutating aliased storage [3]. Do not reuse borrowed
   scratch after giving a callback a retainable/mutable view, or promise zero-copy
   merely because Rust compiles. Test noncontiguous arrays and concurrent access.
5. **Prove delivery.** Pure-Python installation must remain usable. Test built
   wheels/sdists, bundled TOMLs/fixtures, exceptions and results on supported
   platforms. Native wheels add OS/architecture/interpreter/NumPy and toolchain
   compatibility work; Linux distribution needs compatible manylinux/musllinux
   handling [4, 5]. Pin compatible versions in a real prototype; this discovery
   does not choose a crate version or change the current setuptools build.
6. **Separate ABI claims.** Stable-ABI and GIL/free-threaded wheel compatibility
   are distinct, version-sensitive concerns [6]. Do not assume a single `abi3`
   wheel covers CPython 3.14's free-threaded build or every NumPy binding. Current
   RKO CI does not certify a native engine or free-threaded Python.
7. **Resolve attribution and release policy.** The upstream C++ MIT license is
   visible [7], but it does not settle the combined project's imported-code review
   in [NOTICE](https://github.com/MarcosPTProenca/RKO/blob/main/NOTICE). No source-copy/relicensing shortcut follows.
8. **Return to the actual C++ target.** Run fair, current-revision multi-instance
   comparisons and publish losses/failures as well as wins. Only then reconsider
   default engine selection or performance claims.

## Primary sources

External documentation reviewed 2026-10-22. Upstream `main` pages evolve; examples
and versions must be revalidated when an experiment is implemented.

1. [PyO3 performance: callbacks, interpreter attachment and native work](https://pyo3.rs/main/performance).
2. [PyO3 parallelism](https://pyo3.rs/main/parallelism).
3. [rust-numpy borrowing rationale and limitations](https://pyo3.github.io/rust-numpy/numpy/borrow/index.html).
4. [Maturin mixed-project layout](https://www.maturin.rs/project_layout).
5. [Maturin distribution and portable wheels](https://www.maturin.rs/distribution.html).
6. [PyO3 building/distribution and stable ABIs](https://pyo3.rs/main/building-and-distribution).
7. [Pinned C++ MIT license](https://github.com/RKO-solver/RKO_Cpp_v2.0/blob/126e35873e50dc308795b58b8c75d37f8de4c857/LICENSE).
