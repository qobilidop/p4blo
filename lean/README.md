# Lean user library

The independent `p4blo` Lake package imports `p4blo-ir` from `../ir`.
Import `P4blo` for the user API. Reference definitions remain under
`P4bloIR`; frontend/library definitions use `P4blo` to avoid collisions.

`prepareSwitch` performs indexing, extern binding and architecture contract
checks, not complete validation. `runSwitch` and the block entry points reuse
the reference functions. Pass returned extern state to the next call. There
is no independent optimized engine or new correctness claim in these aliases.

## Verified scalar authoring

```lean
import P4blo
open P4blo.Scalar
open scoped P4blo.Scalar

def answer : Expr (.bits 8) :=
  .mux ((bits[8, 255] + bits[8, 1]) === bits[8, 0])
    (bits[8, 17] + bits[8, 29]) bits[8, 99]

example : (denote answer).val = 46 := by decide
example (run : P4bloIR.Run) :
    (P4bloIR.evaluate (lower answer)).run run =
      (.ok (toValue (denote answer)), run) := evaluate_lower_run answer run
```

`ExprIn context` is a small typed construction language: typed variable reads, positive-width bit literals,
booleans, wrapping addition, equal-width bit equality, and same-type mux.
`Expr` is its empty-context specialization, not a second AST.
Addition and equality require identical widths; mux requires a boolean
condition. Literals must fit: `bits[0, 0]` and `bits[8, 256]` fail to
elaborate rather than silently wrap. `bits? width value` returns `none` for
invalid dynamic inputs. `bits width value positiveProof fitsProof` supports
symbolic construction without trusting an unchecked cast.

The source denotation is compositional over `Fin (2 ^ width)` and `Bool`;
it does not call lowering or the IR evaluator. `lower_typed` proves scalar
typing, `evaluate_lower` proves the exact value correspondence, and
`evaluate_lower_run` proves successful execution with the entire initial
`Run` unchanged. All are checked by the default `UserProofAudit` target.

For open expressions, bind named references once and pass an independent
heterogeneous environment:

```lean
def inputs : Context := [("x", .bits 8), ("y", .bits 8)]
def x : ExprIn inputs (.bits 8) := .read .here
def y : ExprIn inputs (.bits 8) := .read (.there .here)
def values : Env inputs := .cons 19 (.cons 7 .nil)

example : (denoteIn values (x + y)).val = 26 := by decide
example : FrameMatches values values.frame := values.frame_matches (by decide)
example (run : P4bloIR.Run) (h : FrameMatches values run.frame) :
    (P4bloIR.evaluate (lower (x + y))).run run =
      (.ok (toValue (denoteIn values (x + y))), run) :=
  evaluate_lower_in (x + y) values run h
```

`lower_typed_in` assumes a finite well-formed context: names are unique and
nonempty, and bit widths positive. The spec's total `ScalarTyping.inferIn`
checks this even for unused bindings; it is sound and complete for the
contextual scalar typing relation under that assumption. `evaluate_lower_in`
instead assumes exact `FrameMatches` agreement, using the real action-first
runtime lookup. `Env.frame_matches` constructs a witness; `FrameMatches.typed`
connects exact values to the spec's weaker typed-frame predicate.

These are **expression** correctness claims, not verified whole-program
lowering, serialization correctness, or universal Python equivalence.
`Declares` separately describes declaration/type agreement; a value-matching
frame by itself does not certify declarations, writable directions, or a
valid block. Field references, statements and complete programs remain future
increments. The Lean compiler/runtime and notation implementation are not
verified by the lowering theorem; independent known answers exercise the
authored syntax, JSON boundary and both production interpreters.

Run `scripts/check-lean.sh` from the repo root to build and test both packages
and their audits. Testing this package alone does not run the specification's
audit or tests. After building, run
`P4BLO_REQUIRE_LEAN=1 uv run pytest tests/test_lean_edsl.py` for the 21
cross-language known answers. `scalarExamples` is a test fixture exporter,
not a new general-purpose interpreter or wire protocol.
