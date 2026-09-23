# Contextual scalar expressions review

Independent read-only review, 2026-09-23, of the pending
`p4blo-typed-frames` worktree. Structural inspection and focused execution
found no blocking issue. Final replay evidence and documentation corrections
were subsequently verified below; this increment is cleared for integration
subject to the integrator's merged-tree gates.

## Checker and premise scope

`checkIn` validates the whole finite context before invoking a private
syntax-directed checker. Empty names, duplicate names (even equal-typed
duplicates), and zero-width bits reject even when the expression never
reads them. Unknown variables and operator type/width mismatches reject.
The operator tables are reused, not duplicated; `Typed`, `check`, and
`infer` specialize the same contextual relation/checker to an empty context.
The previous closed soundness theorem remains present.

Acceptance supplies both context well-formedness and typing evidence.
Completeness quantifies this particular scalar typing relation under a
well-formed-context premise, not all valid IR/P4 expressions. Contextual
soundness additionally assumes actual runtime lookup yields values of the
declared scalar types and proves successful evaluation with the entire
input Run preserved. No production evaluator or lookup behavior is changed.

The lower-level `TypedIn` relation and raw source `ExprIn` can be formed
under malformed contexts; they are not themselves executable validators.
The public checker checks the context, and source lowering typing has an
explicit well-formedness premise. This is an important scope boundary to
preserve as statement construction is added.

## Exact lowering and nonvacuity

There is one source AST and one lowering function. Closed `Expr` and its
old constructor conveniences are specializations. Source environments use
heterogeneous Fin/Bool values and positional references; their lookup and
denotation do not call the IR evaluator or use runtime Value as meaning.

`FrameMatches` requires exact values through the real action-first
`Frame.read?`, not merely a matching type. `evaluate_lower_in` concludes
the exact `toValue (denoteIn env e)` and structural equality of the entire
initial Run. Its lack of a separate well-formed-context premise is not a
hole: exact frame agreement already supplies every source reference value;
the well-formedness premise is separately required for typing/name
uniqueness. The closed computation equality follows from this same theorem.

`Env.frame_matches` constructively provides a related frame for every
well-formed context and environment. Kernel-checked examples reject missing
bindings, wrong widths and an action-shadowed old value, and accept the
actual shadow value. The runtime shadowing test also expects 42 rather than
the block's 19. These checks rule out the important vacuous/flattened-frame
mistakes. `FrameMatches.typed` connects exact agreement to checker soundness.

`Declares` is deliberately a separate predicate, not an established whole-
program theorem. The constructive witness has a default declaration scope;
it does not prove that `Frame.forBlock` or arbitrary declarations establish
agreement. Writable permissions, assignments, fields and calls remain open.
Those exclusions are stated in the README and are appropriate for this
read-only expression increment.

## Audits and independent focused checks

After the implementer confirmed its binaries stable, independently invoked
the exporter fixture, exact independent input checks, and all known-answer
cases: **22 passed** (21 expressions plus the default audit/exporter target
guard), command exit zero. This preserves all 13 closed examples and adds
eight open examples, including distinct values for the same addition/mux
syntax. Python builds and validates its own packet wrapper, initializes
named locals, checks fixed expected bytes, then compares with Lean. Exported
bindings must match independently specified names, literal values and widths;
they are not silently trusted as oracle inputs. The wrapper remains outside
the lowering proof, correctly acknowledged in documentation.

Independently queried transitive axiom sets using the pinned Lean binary
over already-built modules, without rebuilding either implementation
package. `lower_typed` and `lower_typed_in` now use `[propext, Quot.sound]`.
The new dependency traces to `Ref.lookup` using `List.mem_map`, which has
exactly that set; `Ref.mem` and `context_tail` use only `propext`, and
`Context.lookup` uses no axioms. The frame witness and exact evaluation
theorem retain only the standard `[propext, Classical.choice, Quot.sound]`
foundations. No `sorryAx`, custom axiom or native-evaluation escape appears.
The audit change is justified, not a relaxation to accept an unexplained
assumption. Checker evidence uses `[propext]`; checker completeness and
contextual soundness use the same standard three foundations.

The implementer's package-gate and focused logs were inspected. Its required
DRT log reports **122 passed, 959 deselected** against its pre-integration
baseline; its full log ends with **1078 passed, 3 xfailed** and `all checks
passed`. This review does not rebrand those numbers as the newer main branch's
test count or claim an independently repeated full gate.

## Adversarial evidence inspected so far

- Appending `"wrong"` to lowered read names fails both the typing proof and
  exact evaluation proof. The displayed residual goal concerns lookup of
  the wrong name versus the required source value. This is proof rejection,
  not an executable Python/Lean mismatch.
- Changing the human-facing `x` accessor to the same-width `y` reference
  builds every default target/audit. Lean's runtime source known answer
  rejects `read-x`; the Python test gets `07` instead of independent `13`.
  Thus a valid-but-unintended source expression is not falsely protected by
  the correct lowering theorem. No replay bundle is expected because the
  known-answer assertion fails before the differential comparison.

- Swapping independent input values compiles with all audits, then the
  Python fixture rejects exported x=7/y=19 instead of x=19/y=7. This is a
  fixture-contract failure before interpreter execution, accurately
  distinguished from DRT. It catches a change that addition's commutativity
  alone could hide.
- Mutating production Python `Env.read` to substitute y for x makes both
  the known-answer test and direct comparison fail. The actual comparison
  log shows **one divergence, zero agreed, zero shared errors**, Python
  `07` versus Lean `13`, with empty equal abstract extern observations.
  This is an executed cross-language semantic mismatch. Source restoration
  was checked independently: the two mutated Lean files equal the candidate
  and Python `interp/env.py` has no diff; restored focused logs show 22 pass.

The final durable `lean/ASSURANCE.md` now separates these four fault classes
and preserves earlier historical experiments. Review requested two last
record corrections: compare_program's argument 4 is the **number of ports**,
not an execution-step bound, and the actual Python mismatch should have a
saved/reconstructed replay with mutant and restored outcomes. Both are now
resolved. The corrected note contains the exact standalone reconstruction
and save/replay commands, actual exit statuses, and expected observations.
Inspected mutant replay reports Python `07` versus Lean `13`; inspected
restored replay reports one agreement. Independently verified the saved
bundle SHA-256
`38451c94a44d22dabafb456feb3b2cc7967ec5d0107106f58caa05a04e2a1615`,
loaded its concrete program/request/ports/seed and checked these equal the
tracked validated `read-x` fixture. Independently replayed that same bundle
against restored implementations: **one agreed, zero diverged, zero shared
errors**, command exit zero. Python mutation source has no remaining diff.
The replay no longer relies on temporary logs or a live fixture generator;
the tracked recipe also permits regenerating its ignored artifact.

No implementation or main-worktree file was edited by the reviewer; only
this report was created in its own worktree.
