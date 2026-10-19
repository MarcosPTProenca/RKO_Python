# Current limitations

Status reviewed on 2026-10-19. This development version is **not release-ready**.
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
coverage.

## Outstanding

- **RNG isolation:** serial execution seeds/restores global RNGs, so simultaneous
  calls are not safely isolated. Thread mode cannot accept a per-search seed.
- **Worker scheduling:** the packaged default is now the measured four-algorithm
  portfolio; custom portfolios can still oversubscribe hardware. A portfolio
  larger than `n_jobs` is rejected, not fairly scheduled. Native-thread limits,
  peak RSS and fixed-work IPC profiles remain unmeasured.
- **Algorithm contracts:** complete C++ parity/deviation specifications and
  scientific invariants remain, including SA/GRASP adaptive behavior. Six local
  neighborhood cases now match compiled C++ kernels: strategy 1 continues the
  sweep, and supplied indices are reshuffled. See [compatibility](cpp-compatibility.md).
  Corrected Q/reward/grid/IPR behavior is not a promise of unchanged C++ trajectories.
- **Configuration/results:** programmatic hyperparameter configuration, evaluation
  counts and explicit stop reasons are incomplete. Full API/error documentation
  and a supported-version/release policy are still needed.
- **Stopping:** active callbacks cannot be interrupted cooperatively, blocked
  threads cannot be safely killed, and standalone operators receive no RKO
  deadline. A first valid evaluation may exceed the requested duration.
- **Scientific quality:** the C++ threshold decoder remains substantially worse
  than greedy. A separate key-weighted capacity-feasible Knapsack decoder closes
  much of that gap on one pinned instance, but more instance families, seeds,
  fixed-work measurements and domain-specific validation are needed.
- **Licensing:** confirm imported-code ownership/terms before release; see
  [NOTICE](../NOTICE). An existing license file does not settle that review.

The hot blending kernel now batches offspring selection after consuming the same
Python random draws in the same order. A reproducible 1,000-key serial SA synthetic
benchmark measured median evaluation throughput increasing from 3,150 to 4,150
evaluations/s across five paired seeds; the pinned Knapsack process benchmark did
not show a uniform quality gain from that kernel alone. The change preserves draw
order but may have tiny floating-point differences for unusual non-key numeric
inputs.

The packaged four-worker portfolio ran the pinned Knapsack trials 21.8% faster
on average than the full ten-worker portfolio and produced higher mean profit in
three seeds; this single-instance result is directional. The additional feasible
decoder averaged profit 394,957 versus 329,353 for the threshold decoder under
matched 15-second budgets and seeds. Reproduction commands and limitations are in
[benchmarks](../benchmarks/README.md).

Detailed working audits and plans are kept locally and excluded from Git. Source
history preserves prior evidence; this page is the maintained public summary.
