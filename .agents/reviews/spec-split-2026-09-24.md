# Review: IR specification versus reference architecture specification

Independent read-only review, 2026-09-24, of commit `44ab2fe` against
`3b5a53c`: the split of the Lean IR specification package from a new
reference architecture package, and the generic extern interface. All
findings below were fixed in the follow-up commit that adds this file.

## Verified as consistent

- **Semantics preserved.** Register read/write, counter, checksum16 and
  the CRC width checks, every error string, family dispatch on the
  segment before the first dot, constructor argument checks, and the
  arithmetic all match the archived `ExternState.call`, `make` and `bind`
  byte for byte. States built by `bind` always have the shape the new
  model's match expects; the catch-all is unreachable through binding.
- **Observation format identical**: kind, then width when present, then
  values when present, same key order and hex formatting for all five
  families.
- **Proofs.** The Bloom-insertion theorems gained exactly one premise,
  that the run's extern model is the reference model, discharged by
  `rfl` in the nonvacuity instance; conclusions and generality unchanged.
  No audited theorem was removed with the certificate example.
- **Boundary.** Nothing under `spec/ir/` names an architecture or a
  family; `spec/arch/` depends only on the IR; the Python IR side does
  not import `p4blo.arch`.
- **Tests moved, not lost.** Every previously run test module runs in
  one of the two spec drivers; the ten extern checks and three host-trap
  checks carry the same names and expectations.
- The check script, the Lean workflow's cache key, the ignore rules and
  the layout test all encode the three-package graph.

## Blocking (2), fixed

- The assurance runner's final restored build still asked the IR scratch
  package for `p4blo-lean`, which it no longer defines. Split: audits and
  the codec endpoint in the IR copy, the conformance endpoint in the
  architecture copy.
- The runner's restoration check resolved tracked paths against the
  wrong scratch root since the earlier package move, so it would raise
  instead of comparing. It now resolves against the scratch root.

## Minor, fixed

Two READMEs cited the register rule at its old path; the workflow text
still said "two" build directories; the status page still described two
packages and lacked this checkpoint.

## Notes kept as-is

The model normalizes hand-built states with stray fields, which binding
never produces, and the catch-all error now prints the structure repr;
neither is pinned by a test.

Verdict before fixes: 2 blocking, 6 minor. After fixes: clear.
