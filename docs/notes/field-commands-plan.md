# Small field-command/write factoring increment

Read-only plan, 2026-09-23, following the reviewed field-expression seam.
Inspected current `ScalarCommands`, `ScalarPlaces`, authoritative
`ScalarStatements`, reviewed `Fields`/`FieldExpressions`, the actual
assignment dispatch and Python validator lvalue permissions. No candidate
edits, builds or new dependencies.

Recommendation: keep the existing done/write/branch-with-tail command
representation, factor its read/write parameters once, and instantiate it
with the already-proved aggregate store operations. Add scalar-leaf field
assignment only. Do not add aggregate assignment, validity-changing commands,
stack indexing, calls or packet operations in this increment.

Confidence is high in the proof obligations and concrete bridge, medium in
the dependent API factoring/ergonomics. The forwarding-body fixture below
is an acceptance test for that choice, not a reason to widen the proof claim.

## Reuse already established facts

- `Scalar.ExprWith Reads` already provides one expression AST, independent
  Fin/Bool denotation, lowering and compositional exact evaluation proof.
- `Fields.Ref.get/set` operate on independent heterogeneous source storage.
  `Ref.write_matches` proves the real nested `writeLValue`, exact updated
  source frame, `ChangesOnlyVars`, and `PreservesOutside [rootName]`.
- `Ref.validities_set` preserves **all** header validity bits, including
  unrelated/nested headers; conversion identifies complete root contents.
- `ScalarCommands.Cmd.steps` already executes an exact finite prefix of the
  actual continuation machine; its continuation remains unexecuted.
- `ScalarStatements.BlockFrame`, `ChangesOnlyVars`, `PreservesOutside` and
  `Execution.Steps` are reusable despite their current namespace. Avoid
  moving/renaming this infrastructure merely to make the new names prettier.

The real assignment dispatch evaluates the RHS, then calls `writeLValue`.
The generic proof must preserve that order and the source denotation must
evaluate subsequent expressions in the updated store, not the initial one.

## One source command implementation

Introduce the generalization in the existing command module, roughly:

```text
CmdWith (Reads Places : Scalar.Ty → Type)
  done
  write (place : Places t) (value : ExprWith Reads t) (next : CmdWith ...)
  branch (condition : ExprWith Reads boolean) (yes no next : CmdWith ...)
```

Its denotation takes a source Store type plus typed source `get` and `set`;
lowering takes typed `lowerRead`/`lowerPlace`; target collection takes
`rootName`. Each function has one recursive implementation. Reuse
`Scalar.denoteWith/lowerWith` for expressions. `assign`, `ite` and `seq`
remain smart constructors, with no synthetic IR sequencing statement.

Keep `Scalar.Cmd modes` as an alias/specialization using existing scalar
Refs, Places and Env. Preserve public named constructors/combinators,
`Cmd.denote/lower/targets`, sequence lemmas and old theorem signatures with
thin wrappers where necessary. Do not retain an old scalar recursive
denotation/lowering alongside a new aggregate version. Add
`Fields.Cmd rootModes` as the second specialization, not a second AST.

Prefer plain explicit parameters or one small internal operation/law record
over a hierarchy of typeclasses. Proof-only laws must not influence source
meaning. If the factor becomes unwieldy, shrink the adapter record; do not
replace the concrete theorem with an arbitrary correctness callback.

## Generic operational law, concretely discharged

Generalize the existing induction for `Cmd.steps`, not the execution engine.
The minimal generic assumptions are per-leaf laws at every related state:

1. Source read/lowered read correspondence returns the exact scalar and
   unchanged entire Run.
2. Writing a lowered Place with a converted scalar succeeds, relates the
   final Run to the independently updated source store, changes only the
   block value map and preserves all roots except `rootName place`.

A lightweight `Matches : SourceStore → Run → Prop` can retain the necessary
index/frame invariant across steps. For fields it can combine exact
`FrameMatches` with `roots.IndexAgrees run.index`; for scalars it is the
existing value agreement. Require `BlockFrame run.frame` explicitly and
carry it forward with `ChangesOnlyVars.blockFrame`. The actual index and
scope are unchanged because `ChangesOnlyVars` fixes every other Run field.
No assumption should assert whole-command execution correctness.

Prove generic finite-prefix execution for **any continuation**, stopping
with precisely that continuation and the exact independently denoted store.
Retain `denote_seq`, `lower_seq`, root-target collection and outside-root
preservation (both conditional branches contribute to the possible set).
Then obtain empty-continuation execution from `Steps.execute` as before.

The public field theorem must have concrete premises only:

```text
RootWellFormed roots
roots.IndexAgrees initial.index
rootModes.Agrees initial.frame.scope
Fields.FrameMatches source initial.frame
BlockFrame initial.frame
```

Its conclusion includes authoritative body typing; actual `execute` success;
exact complete source-store correspondence with command denotation;
preserved declaration agreement; `ChangesOnlyVars`; and preservation of
every runtime root outside possible targets, including roots not modeled
by the source store. Discharge read laws with reviewed `Ref.evaluate` and
write laws with reviewed `Ref.write_matches`.

Do not weaken this to equality of the assigned leaf alone. Exact converted
source roots account for siblings and ancestors; independent source path
updates preserve those not intentionally written. Add a whole-command
source validity preservation lemma using `Ref.validities_set`, so unchanged
header validity is explicit for this scalar-leaf-only command fragment.

## Actual permissions, separately from mutable storage

Use the existing `Scalar.Mode` distinction and authoritative
`ScalarStatements.writable` rule: locals, out and inout are writable; input
and directionless parameters are not. Avoid a new permissive mode enum.
An aggregate root-modes list indexed by Layout can reuse that Mode type.

`Scalar.Mode.declaration` currently accepts only Scalar.Ty. A tiny generic
IR-type declaration helper is reasonable, with the existing scalar method
delegating to it and retaining its API. Root mode agreement must require
the exact actual `scope.var?` declaration, including name, aggregate nominal
type and direction. Derive the existing `RootDeclares` relation from this
stronger agreement; do not ask callers to provide two disconnected claims.

A field Place contains a typed Ref plus proof that **its root** mode is
writable. Descending through a member never grants new permission. Runtime
presence of a mutable header or `FrameMatches` cannot establish writability:
the current interpreter does not dynamically enforce these source rules.
An allegedly local/writable source mode must not agree with a real input
parameter merely because its name and type match.

Keep the full no-action premise: both `frame.action = none` **and**
`frame.actionVars = none`. The latter affects actual lookup/write precedence;
checking only the former is not equivalent. This increment does not certify
action parameters, block/action calls or copy-in/copy-out.

## Small authoritative specification addition first

In a separately reviewable small spec increment, extend the existing field
typing boundary (or add a small `FieldStatements` module):

- A declarative writable lvalue path has only variable/member constructors.
  Its root requires actual lookup, correct nonempty name/type and
  `writable decl = true`; member descent uses exact existing `FieldsOf`.
- Assignment combines that writable scalar path with the existing
  `FieldTyping.Typed` RHS at the same scalar type.
- Conditional/body rules reuse that same expression typing relation and
  ordinary lists of statements.

These are typing/permission relations over **existing IR**, not new syntax,
runtime semantics, a total aggregate checker or a proof that the complete
Python validator is equivalent. No executable checker is required merely
to make this small relation useful. Reject unknown/empty roots, input and
directionless root writes, wrong nominal declarations and mismatched leaf
widths with independent kernel negatives.

## Constructive witnesses and the first useful authored body

Provide concrete root-modes scope/frame constructors and proofs of their
agreement under root well-formedness, as existing scalar Modes do. Include
a mixed header/metadata store with a separate read-only route record and
an unrelated runtime root; use the final public command theorem on it.
Exercise actual `Index.build`/`Frame.forBlock` in runtime tests for local,
out and inout aggregate roots. Do not label these finite witnesses a general
initialization correctness theorem.

First command checks: dependent writes to two fields in the same header;
write followed by branch on the new value; wraparound; both branches and
their shared tail; two writable roots; both initial header validities;
read-only root available for reads but rejected for nested writes. Keep the
existing arbitrary continuation test pattern with a continuation that
genuinely faults if separately run.

For usefulness/ergonomics, add an **already-parsed, route-selected forwarding
body**, using only current operators. Suggested source layout:

- `hdr`: Ethernet destination/source (48 bits) and IPv4 TTL (8 bits), with
  extra untouched fields and explicit stored validity;
- `meta`: egress port (9 bits), drop Bool and an untouched sentinel;
- `route`: read-only hit Bool, next-hop destination/source MACs and port.

The fixture's contract supplies parsed-header validity and route metadata;
it does not pretend to parse packets, perform LPM or prove `isValid` lowering.
On miss or TTL 0/1, set drop. Otherwise copy next-hop MACs, decrement TTL
using the existing eight-bit `ttl + bits[8, 255]`, set egress port and clear
drop. Nested equality/conditionals express the zero/one guard without adding
new operators. Name the fragment accurately (for example route-selected
forwarding rewrite), not a verified router: checksum recomputation, parser,
table lookup, architecture drop behavior and deparser remain outside it.

Define typed field references/places once; the body should read comparably
to existing `Cmd.assign`, `Cmd.ite` and `.seq` scalar examples. Do not bury
the body under explicit proof terms or fresh casts at every use. Additional
surface notation is optional, and if added requires independent source
known answers because the generic theorem does not verify notation intent.

## Acceptance, observation and adversarial checks

Keep both packages/default theorem audits green and all existing scalar
fixtures unchanged. Audit generic steps and the concrete aggregate theorem,
not only the primitive setters. Axiom baselines remain standard foundations.
Use a default test exporter and shared required Lean fixtures/discovery.
Export syntax/declared inputs, not source-computed expected outputs.

The Python wrapper must execute the complete authored body **once before**
observing every stored source/target/sibling field, all header validity bits
and unrelated roots through a separate valid result header. Independent
known answers must describe full final values, including invalid-header
storage. Include both valid and invalid initial headers for the low-level
command cases; forwarding examples can state stronger parsed-input premises.
Add a nonempty untouched packet tail to at least one case so accidental
packet consumption is observable. In direct Lean tests initialize packet,
emitter, visits and unrelated runtime state nontrivially; the theorem already
preserves all non-value Run fields.

Compare/save before expected-answer assertions. Retained replays check exact
program, complete request sequence, port count and seed, actual mismatch
with no shared-error shortcut, and restored agreement on the same input.
Retain the existing weak pre-expression observer control; do not reintroduce
pre-command snapshots while arranging final output fields.

Required faults, isolated one at a time:

- wrong target field or skipped write, preserving typing when possible;
- RHS evaluated against the old store after a dependent write;
- swapped branches or reordered shared tail;
- actual Python setter clobbers sibling or forces validity (now during an
  authored command, not only fixture initialization);
- wrong same-width Place or assignment notation: generic proof may pass,
  but independent source/packet known answers must fail;
- source mode says writable while actual declaration is input: typing must
  fail despite a perfectly matching mutable frame.

Record proof rejection versus compiled runtime kill honestly. Keep aggregate
copy DRT as adjacent evidence; it does not establish the scalar-leaf command
theorem, and this theorem does not establish aggregate copying/copyback.

## Checkpoints and revisit trigger

1. Commit/review the small authoritative writable-path/body relation.
2. Factor one generic command implementation and recover every old scalar
   theorem/API/test before adding field commands.
3. Add concrete aggregate modes/places and the final exact execution theorem,
   constructive witnesses and scoped tests.
4. Add the forwarding-rewrite body, complete final-state cross-language
   fixtures and retained mutation evidence; integrate only with gates green.

No new directory hierarchy, dependencies or general framework is needed.
Revisit the medium-confidence generic API if the concrete forwarding body
needs pervasive type annotations, if the relation record embeds command
correctness instead of leaf laws, or if preserving scalar compatibility
requires parallel recursive implementations. Prefer a narrower, explicit
adapter over pretending those costs are already justified by future features.
