# Current limitations

Status reviewed on 2026-10-18. This development version is **not release-ready**.
Removing internal audit documents does not mean their outstanding work is done.

## Delivered

Class-based RKO API and immutable results; usable installed wheel/sdist resources;
GA parent-fitness ownership, current Q maxima, sign-safe rewards and IPR remainder
coverage; named/validated parameter grids and atomic saves; callback-boundary
stopping, decoder isolation and visible thread failures; scalar pool-count RPCs
and non-busy IPR waiting. A single-instance `rko` command accepts external TOML
configuration while retaining batch/module invocation. The CLI now shows live,
attributed pool updates by default (`--quiet` suppresses them); library progress
is opt-in through `verbose=True`. These have regression and installed-artifact
coverage.

## Outstanding

- **RNG isolation:** serial execution seeds/restores global RNGs, so simultaneous
  calls are not safely isolated. Thread mode cannot accept a per-search seed.
- **Worker scheduling:** defaults can oversubscribe hardware. A portfolio larger
  than `n_jobs` is rejected, not fairly scheduled. Native-thread limits and
  fixed-work throughput/IPC profiles remain to be established.
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
- **Scientific quality:** the [current larger benchmark](../benchmarks/README.md)
  remains substantially worse than greedy. More instance families, seeds,
  fixed-work measurements and separate problem-aware decoding studies are needed.
- **Licensing:** confirm imported-code ownership/terms before release; see
  [NOTICE](../NOTICE). An existing license file does not settle that review.

Detailed working audits and plans are kept locally and excluded from Git. Source
history preserves prior evidence; this page is the maintained public summary.
