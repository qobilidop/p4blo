# Closed scalar soundness review

2026-09-23. Independent read-only review of `4a9ca69` in a separate
worktree. No confirmed correctness defects.

The checker matches Python's scalar validity rules: positive widths,
fitting literals, equal-width arithmetic and comparisons, independent
shift widths, bit<1>/bool casts, bounded slices and matching mux branches.
Unsupported forms are rejected even in branches not selected at runtime.

`check` constructs syntax-directed evidence without evaluating values.
`Typed.sound` proves the actual `P4blo.evaluate` is a pure computation of
the inferred type. `check_sound` establishes successful evaluation and
preservation of the entire arbitrary `Run`. Accepted examples reduced in
the kernel; additional acceptance/rejection and shift probes compiled.
Both the proof and test module are imported by checked targets.

Axiom audit for both public theorems: only `propext`, `Classical.choice`
and `Quot.sound`. No `sorryAx`, custom axiom or native-evaluation escape.
No `sorry`, `admit`, `unsafe` or `implemented_by` in the proof or inspected
evaluator dependencies. Clean Nix `lake build` and `lake test` passed:
252 checks, 71 new. Tracked review files remained unchanged.

Boundary: closed scalar type safety and purity, not arithmetic agreement
with a separate specification, Python equivalence, checker completeness,
whole-program validity or statement soundness. The program loader does
not yet enforce this incremental checker.
