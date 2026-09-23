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
valid block. Aggregate path expressions and writable scalar-field commands
are described below; complete programs remain work in progress.
The Lean compiler/runtime and notation implementation are not
verified by the lowering theorem; independent known answers exercise the
authored syntax, JSON boundary and both production interpreters.

Run `scripts/check-lean.sh` from the repo root to build and test both packages
and their audits. Testing this package alone does not run the specification's
audit or tests. After building, run
`P4BLO_REQUIRE_LEAN=1 uv run pytest tests/test_lean_edsl.py` for the 21
cross-language known answers. `scalarExamples` is a test fixture exporter,
not a new general-purpose interpreter or wire protocol.

## Verified scalar command bodies

Writable places add finite declaration modes alongside the existing context;
they do not replace the expression AST or its source environment:

```lean
def permissions : Modes inputs := .cons .local (.cons .local .nil)
def px : Place permissions (.bits 8) := ⟨.here, rfl⟩
def py : Place permissions (.bits 8) := ⟨.there .here, rfl⟩
def body : Cmd permissions :=
  (Cmd.assign px (.read px.ref + bits[8, 1])).seq
    (Cmd.assign py (.read px.ref + .read py.ref))
```

`Cmd.ite condition yes no` adds a boolean conditional; `.done` is empty.
`Cmd.denote` is an independent, total transformation of the source `Env`.
Its sequencing law and lowering-to-list sequencing law are proved. Places
permit locals and `out`/`inout` parameters, rejecting `in` and directionless
ones. `Modes.Agrees` separately checks exact declarations in the actual
scope; the runtime does not itself enforce parameter write permissions.

`Cmd` specializes one `CmdWith Reads Places` implementation. Source
sequencing, conditionals, lowering and target collection are defined once;
the generic finite-prefix proof composes exact per-read/per-write laws.
The public scalar theorem discharges those laws using real scalar frame
operations. Generic callbacks are an internal composition boundary, not a
replacement for concrete correctness premises in the user-facing theorem.

`Cmd.execute_correct` proves typing of the lowered body and successful
execution through the **existing** reference executor, with the exact final
source environment. Only the block-value map can change; all unrelated Run
fields and all names outside the possible target set are preserved. Its
premises require a well-formed context, declaration agreement, exact initial
value agreement, and no active action layer. The underlying `Cmd.steps`
theorem leaves an arbitrary continuation unexecuted, then `Finishes.sound`
connects that finite trace to the actual runner. There is no new fuel limit
or alternate statement interpreter.

`Modes.scope_agrees` and `Modes.frame_matches` give constructive witnesses.
Real `Index.build`/`Frame.forBlock` initialization and writable parameter
execution are also tested; a general theorem connecting these constructors
to whole-program validity is **not** claimed. Scalar-leaf header/metadata
commands are described below; calls, externs, packet operations and
complete-program lowering remain future work.

After the Lean build, run required `pytest tests/test_lean_edsl_statements.py`
for nine independently expected complete-local-state packet cases. The raw
packet wrapper is outside the lowering proof. Differential failures are
saved before expected-answer checks, so Python faults retain replay bundles.

## Aggregate values and scalar paths

`P4blo.Fields` supplies independent finite `Shape`/`Layout` schemas,
heterogeneous `Data`/`Record` values and scalar-leaf `Path`s. Headers carry
their validity bit; structs do not. `Path.get`/`Path.set` operate only on
source data. Proved readback and preservation of **every** header-validity
bit accompany conversion to IR values.

`Fields.Expr roots` is a specialization of the **same** `Scalar.ExprWith`
operator AST used by `Scalar.ExprIn` and closed `Scalar.Expr`. It supports
the same bits/bools/addition/equality/mux and `bits[width, value]` notation.
`Fields.evaluate_lower` proves exact source result and unchanged entire Run
from concrete index/frame agreement. `Fields.lower_typed` independently
uses root well-formedness, index agreement and actual declaration agreement
to derive the spec's new `FieldTyping.Typed` relation. That relation is not
a total aggregate checker or a complete validator.

`Ref` adds a root variable to a path. Exact `FrameMatches` and recursive
`IndexAgrees` premises connect reads to actual `evaluate` and nested writes
to actual `writeLValue`. `Ref.write_matches` gives the exact updated source
store, unchanged non-value Run state and unchanged unrelated roots. These
are primitive operations, not a second expression or command AST.

`LocallyWellFormed` checks widths and each aggregate's field names/kinds;
it does not establish coherence of repeated nominal names. `IndexAgrees`
requires one actual index to agree with every reachable declaration;
it does not by itself check scalar widths or root declarations. Distinct
root names are a separate write-preservation premise. `RootWellFormed` adds
nonempty/distinct root names for expression typing; `RootDeclares` supplies
actual variable declarations. Concrete witnesses and positive/negative
nominal-reuse examples are tested. Root permissions and command integration
are described below; whole-program initialization remains an obligation.

After building, `pytest tests/test_lean_edsl_fields.py` compares seven field
expressions and an independently specified complete stored-state observer.
It evaluates the expression once **before** observing every source field and
validity bit, including invalid-header fields. A regression demonstrates
that a pre-expression observer misses a read-side-effect fault while the
corrected observer saves and replays it. This unverified fixture wrapper is
not a whole-program compiler or a packet-processing application proof.

## Verified scalar-field command bodies

`Fields.Modes roots` assigns the existing local/parameter modes to aggregate
roots. `Fields.Place modes type` pairs a scalar path with evidence that its
**root** is writable. A field under an input or directionless parameter is
readable but not writable. `Modes.Agrees` requires the exact real declaration,
including nominal kind and direction, not merely a matching runtime value.
`Modes.scope_agrees` and `Modes.frame_matches` construct concrete witnesses.

`Fields.Cmd modes` specializes the same `Scalar.CmdWith` implementation.
Use `Cmd.assign`, `Cmd.ite`, `.seq` and `.done`, and `place.read` for a writable
place's expression. Bind typed paths once; ordinary command bodies need no
proof arguments. [FieldCommandExamples.lean](P4blo/FieldCommandExamples.lean)
contains a dependent update and an already-parsed, route-selected Ethernet/
IPv4 rewrite with TTL guards and next-hop MAC/port copies.

`Fields.Cmd.execute_correct` proves authoritative body typing, successful
actual execution and exact full source-store correspondence. All header
validity bits, unrelated roots and non-value Run fields are preserved.
Premises are root well-formedness, exact nominal index agreement, actual
mode/declaration agreement, exact initial values and no active action layer.
`Cmd.steps` retains an arbitrary continuation without executing it. Concrete
path laws discharge the generic read/write assumptions internally.

The body fragment permits only scalar-leaf assignments and conditionals.
It does not parse packets, inspect validity, perform routing-table lookup,
recompute checksums, change header validity or copy whole aggregates. The
forwarding fixture assumes its inputs are already parsed and route-selected;
it is not a verified router. Kernel negatives and actual `Index.build`/
`Frame.forBlock` tests check selected initialization and permission cases,
not a general initializer or complete-program validity theorem.
