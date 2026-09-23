# Proof-visible execution review

2026-09-23. Independent read-only review of `6c01734` against `27ca25a`.
No confirmed correctness defects.

The actual public execution APIs use the total `Execution.step` and the
`partial_fixpoint` driver, not a parallel unused semantics. The finite
trace theorem has the stated conditional boundary: if a finite trace
finishes, the actual driver returns its outcome. Global termination of
validated programs remains unproved; no fuel changes parser outcomes.

Clean build, 259 Lean checks and 13 required corpus/state DRT tests passed.
The reviewer compiled the old executor in a separate namespace and ran
all seven new continuation/fault regressions against it; all passed.
Six additional nested-parser cases also agreed: empty, extracting and
faulting leaves, and repeated calls with zero/eight-bit separation.

The audit of `drive.eq_def`, `Finishes.sound`, and `run_eq` found only
`propext`, `Classical.choice` and `Quot.sound`. Review tracked files stayed
unchanged. This is not a proof of equivalence with the old executor or
with Python; those connections are independently tested.
