# Verified Lean scalar eDSL review

Reviewed 2026-09-23: the isolated `p4blo-lean-scalars` worktree's uncommitted
increment against interface commit `4b64497`. Independent read-only review
of the construction language, proofs, notation, test/export boundary and
recorded mutation evidence. No blocking defect found.

## Proof boundary

- `Expr` is a genuine typed source datatype. Its literal constructors
  require positive width and a fitting `Fin (2 ^ width)` value. Addition
  and bit equality share one width; mux condition/branch types are enforced
  by constructors. A zero-width expression cannot be finitely constructed
  through these constructors without invalid proof evidence.
- `denote` is a compositional `Fin`/`Bool` semantics. It does not call
  lowering or the IR evaluator. Sharing the scalar type index does not
  make the correctness theorem circular; `toValue` is the explicit value
  correspondence, not source execution.
- `lower_typed` establishes exactly the existing scalar `Typed` relation.
  More importantly, `evaluate_lower` equates the actual evaluator
  computation with the exact denoted value, not just an existential typed
  result. The derived run theorem quantifies every initial `Run`, with no
  hidden well-formed-state assumption, and equates the entire final state.
- Equal-width comparison keeps width-sensitive IR equality consistent with
  value-only source comparison. Literals preserve exact values instead of
  relying on modulo normalization of out-of-range inputs. Addition and mux
  proofs connect the intended arithmetic/branch, not merely their types.
- All three advertised theorems are in the new default `UserProofAudit`.
  Exact expected dependencies are `[propext]` for typing, and the existing
  standard foundation set for semantic/run preservation. No new axiom,
  `sorry`, unchecked cast, or native proof shortcut appears in the diff.

## Tests and trust boundaries

- Six negative elaboration examples cover the intended local rejections.
  Symbolic literal construction separately uses explicit checked proofs;
  dynamic construction returns `none` on invalid width/value.
- The thirteen Lean examples exercise notation, value boundaries, 1-bit and
  65-bit wraparound, equality, both bit/boolean mux arms and nesting. Their
  expected answers are independent of source denotation and lowering.
- The exporter emits source-built syntax and type width, not expected
  answers. Python checks names, uniqueness, complete coverage and widths
  before parsing through generated protobuf bindings. Its separately
  written expected packet bytes correctly include MSB padding for boolean,
  one-bit and 65-bit results. The existing scalar program wrapper is then
  validated/executed by production Python and compared against Lean.
- The tests use the shared `lean_binary` fixture and `test_lean_agrees`
  naming, retaining required-CI discovery. Exporter absence is a failure
  once the reference executable is available, not a silent skip.
- Implemented hardening: separately assert that the user audit/exporter
  remain default build targets, even when Lean is unavailable locally.
  The final inspected Python test checks both default target names without
  depending on the Lean fixture. The agent reports 14 focused tests pass.
- Claims correctly exclude whole-program lowering, typed variables,
  statements, codec correctness, arbitrary surface elaboration, compiled
  Lean trust and universal Python equivalence. Raw wrapper programs are
  not presented as verified whole-program authoring. Arbitrary source
  widths do not establish protobuf representability.

## Adversarial evidence inspected

Read the implementing agent's captured build/test logs and checked them
against the exact edits and essential output recorded in `lean/ASSURANCE.md`.
The following are observed log evidence, not an independently rerun mutation
campaign by this reviewer:

| Mutation | Observed failure boundary |
|---|---|
| Addition lowers to subtraction, with typing derivation adjusted | Build reaches `evaluate_lower`'s addition case and fails on the unequal modular arithmetic expressions |
| Lowered mux arms swapped, with typing derivation adjusted | Build reaches semantic preservation's true/false cases and fails on arbitrary unequal branch values |
| Surface `+` ignores its right operand | Default build succeeds; Lean source known answer fails for `add`; Python independently observes `13` hex instead of expected `1a` |

The first two are correctly classified as proof/build rejection, not runtime
DRT detection. The third demonstrates why a correct typed-core compiler
alone does not validate notation: both interpreters can faithfully run the
same wrong authored AST. Independent known answers detect that fault.
No DRT replay bundle is expected for these specific failures: the first two
never compile, and the third fails the known-answer assertion before DRT.

The implementing agent's restored required-conformance log reports
**108 passed, 911 deselected**, covering the existing 95 plus these 13.
The review did not independently rebuild the modified worktree or run its
full gates; the integrator must retain those acceptance checks. No main or
implementation-worktree source files were modified by this reviewer.
