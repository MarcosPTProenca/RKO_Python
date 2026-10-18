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

## Still to resolve

- SA's C++ online-control path and GRASP's reference candidate grid/unused alpha.
- Full per-algorithm initialization, transition, restart and stopping contracts.
- Independent search RNG ownership and hardware-bounded cooperative scheduling.
- Mapping additional C++ run settings into actual Python functionality rather
  than accepting unsupported fields. Current terminal/configuration usage is in
  [running.md](running.md).
- Matched-work, multi-instance measurements with strong optimization baselines.

These remain [release limitations](status.md). No competitive-quality or
whole-solver parity claim follows from six neighborhood examples.
