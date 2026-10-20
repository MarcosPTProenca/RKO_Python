# C++ reference and compatibility

Behavioral reference: [RKO_Cpp_v2.0](https://github.com/RKO-solver/RKO_Cpp_v2.0),
revision `126e35873e50dc308795b58b8c75d37f8de4c857`. Compare executable behavior,
not only comments or algorithm names. Full solver equivalence is **not proven**.

## Checked neighborhood contracts

The reference `Program/src/Method.h` calls strategy 1 "first improvement", but its
immediate `return` statements are commented out. `SwapLS`, `InvertLS` and `FareyLS`
therefore continue the sweep after accepting an improvement. All three shuffle
`RKorder` unconditionally. Python already followed that transition policy;
changing it to immediate return would diverge from this reference.

| Setting | Reference behavior preserved in Python |
| --- | --- |
| strategy 1 | Sequential acceptance: next candidate starts from the best accepted vector; finish the sweep |
| strategy 2 | Evaluate all neighbors from the fixed input; return the best improvement |
| supplied order | Base indices are reshuffled, not treated as a fixed exploration schedule |

Six deterministic cases (three operators, both strategies) were verified by
compiling the unmodified C++ function bodies with minimal solution/data types,
a linear decoder and controlled exploration order/Farey midpoint draws.
The same outputs and full candidate counts are regression-tested in
`src/rko/tests/components/test_cpp_operator_contracts.py`. This was a kernel
comparison, not a build/test of the complete C++ application or random generator.
The normalized reference `Method.h` SHA256 is
`0f202c543c424a77db3f44220986ee956b3b17c0900a2454fcb122f25339262d`.

Python returns new vectors and copies the supplied index list instead of
mutating caller-owned input as C++ does. Random streams and repeated-call index
state are not identical; these tests compare matched deterministic transitions.
The portfolio currently uses strategy 2 defaults; a run-level strategy setting
is not yet exposed. Operator docstrings describe actual sweep semantics.

## Deliberate corrections, not unchanged trajectories

Python now keeps selected GA fitness with its chromosome, recomputes current
Q maxima after updates, handles negative/extreme rewards consistently, filters
infeasible joint parameter states, covers partial IPR blocks and retains superior
initial simplex vertices. Some issues were inherited from the reference.
These are explicit correctness choices; do not silently revert them just to
match a historical defect or claim byte-for-byte C++ search trajectories.

## IPR initialization contract

The C++ driver calls `CreatePoolSolutions` before invoking its selected searches;
standalone IPR therefore starts with an elite population. Python previously started
with an empty pool and could spend its entire allocation waiting, returning only
its first random candidate. This is an initialization difference, not evidence
that compiling the same waiting loop would improve search quality.

Python IPR now inserts its initial evaluated candidate and tries at most one extra
seed if fewer than two elites exist at startup. Both evaluations use ordinary
callbacks, assigned RNGs and the existing search deadline. Prefilled pools retain
their initialization draw order. Initialization is bounded even when a custom pool
or capacity-one pool cannot retain a pair; existing backoff then applies.

This restores usable standalone relinking, **not full-driver parity**: C++ seeds
its configured pool population, whereas Python only bootstraps the missing pair
locally in IPR. Global initialization, random engines, block-path transitions and
throughput still require separate matched comparisons. Random seeds are not generic
feasibility repairs; no C++-matching quality claim follows from this correction.

## SA adaptive and GRASP construction audit

SA now implements online actions rather than silently falling back to fixed
settings. [The SA control contract](sa-control.md) describes actual parameter
application and migration to `control=0` for the legacy path. Python uses the
sampled initial Q state, credits completed levels including refinement with the
shared sign-safe reward, and applies selected t0 to the next schedule. C++ leaves
its initial Q source at zero and never applies later t0 selections. These are
explicit corrections, not claims of identical trajectories or scientific quality.
Python's legacy refinement/current-incumbent transition is retained; full SA
transition parity remains unproven.

The read-only GRASP audit identified these differences, **not corrected yet**:

| Contract | Pinned C++ | Current Python |
| --- | --- | --- |
| Line candidate universe | Bounded lattice around the gene, then randomized subset | Nearby plus/minus shifts up to a logarithmic radius |
| Candidate evaluation count | At most `ceil(log2(int(1/h)))+1` sampled lattice values | Current value plus both signs of each logarithmic shift when valid |
| Small unfixed sets | Search every remaining coordinate when the 10% subset is below two | Search at most two |
| Construction intensity | Integer loop against a real bound (effectively ceiling) | Truncated integer count |
| Improving fine-grid step | Keep the current h | Reset h to hs |
| Initial refinement | Score the initial vector before construction | Apply initial RVND |
| Alpha parameter | Read/selected but unused by construction | Adaptive axis selected but unused by construction |

A dense-step line search can therefore miss candidates available to C++ while
making more callback evaluations. This is a contract finding, not evidence that
all reference choices should replace Python's behavior. Isolate candidate-coverage
correction from alpha policy, initialization and refinement changes, and validate
without editing or competing with the ongoing paired benchmark.

## Still to resolve

- GRASP candidate-coverage/subset semantics and an explicit unused-alpha decision.
- Full SA/GRASP transition and refinement comparisons beyond adaptive plumbing.
- Full per-algorithm initialization, transition, restart and stopping contracts.
- Full-driver population initialization and comparable timing/work accounting;
  owned search RNGs and CPU-bounded remaining-time process scheduling are implemented.
- Mapping additional C++ run settings into actual Python functionality rather
  than accepting unsupported fields. Current terminal/configuration usage is in
  [running.md](running.md).
- Matched-work, multi-instance measurements with strong optimization baselines.

These remain [release limitations](status.md). No competitive-quality or
whole-solver parity claim follows from six neighborhood examples.
