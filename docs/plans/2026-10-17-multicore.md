# Incremental multicore implementation plan

Approved design: `docs/superpowers/specs/2026-10-17-rko-professional-release-design.md`.

Preserve unrelated working-tree changes. Stage explicit paths only. Commit each validated implementation, then push `origin/rko`; never force-push. Use uv with an isolated Linux environment rather than modifying the Windows `.venv`.

## 1. Benchmark and CI baseline

- Make the existing Knapsack objective a pickleable callable without changing the threshold decoder or penalty.
- Validate instance shape, weights, capacity and callback dimensions.
- Test through the reader/decoder/objective and public solver seams: exact tiny-instance oracle, serialization round-trip, malformed input, feasible solver output.
- Register the existing example as maintained source; remove the one formatting failure.
- Move CI to repository-root `.github/workflows`, set the Python working directory and run the full pytest suite on Ubuntu and Windows.
- Run Ruff lint/format and pytest before committing.

## 2. Shared-pool ownership

- Return detached snapshots from elite reads; reject invalid costs/keys before mutation.
- Keep the existing tuple-based API and internal lock, usable behind a standard-library manager.
- Test caller mutation, sorting/capacity, invalid entries and process-sharing in the next slice.

## 3. Spawn-based multicore

- Extend `rko.run` with explicit execution mode, process budget and worker seed while retaining its tuple return.
- Validate callbacks before launching processes. Construct metaheuristics in workers.
- Keep one authoritative managed pool; coordinate a simultaneous search start.
- Require the selected portfolio to fit the process budget; do not queue full-budget searches.
- Propagate algorithm-specific failures, detect abrupt exits and clean up children on failure/interrupt.
- Test real spawn execution, elite exchange, callback validation, failures, worker-budget validation and serial mode.
- Run the actual algorithms and Knapsack benchmark through the process mode before committing.

## 4. Subsequent release work

Deadline propagation through local searches; fixed-work multicore benchmarks; larger real-world dataset; C++ parity review; configuration wiring; installable wheel/resource checks; release documentation and repository hygiene. These are not complete merely because process-mode tests pass.
