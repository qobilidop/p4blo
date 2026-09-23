# Aggregate source/path checkpoint review

Independent read-only review on 2026-09-23 of the next `p4blo-typed-fields`
checkpoint: `Fields.lean`, `FieldTests.lean`, user exports/test driver/audits
and scoped documentation. No source edits or builds by the reviewer.
**Disposition: clear for the separate aggregate source/path checkpoint.**
Structural review, stable test execution and final mutation/evidence review
found no blocker. Expression/command integration remains separate work.

## Independence and nominal coherence

The mutually finite `Shape`/`Layout` and indexed `Data`/`Record` are an
independent source representation, with Fin/Bool scalar leaves. Headers own
an explicit validity bit; structs use Unit rather than a fictitious validity
state. Positional typed slots and scalar-leaf paths define total source
get/set without evaluating or lowering IR. Source-to-runtime conversion is
a separate operation. No second expression or command AST/evaluator is added
in this intermediate checkpoint; integration into the existing scalar
expression/command seam remains subsequent work.

`IndexAgrees` recursively requires the committed exact nominal declaration
relation for reachable aggregates. Both ordered field declarations and
header/struct kinds are coherent across repeated names. Kernel examples
show repeated equal H shapes work, but two locally valid different H shapes
or header/struct H clashes admit **no** agreeing index. This avoids a false
claim that local schema checks imply global nominal consistency.

Keep the distinction explicit: `LocallyWellFormed` checks positive scalar
widths, local field names and scalar-only header fields; `IndexAgrees` alone
does not establish these complete local validity conditions. Root layout
local well-formedness checks its shapes, not distinct/nonempty root variable
names. Final write correspondence separately needs root-name uniqueness;
scope declarations, root permissions and a general globally valid program
constructor are intentionally not certified here.

## Actual execution and preservation

`Record` conversion proves exact field-list shape and positional read/update
correspondence. Path reads reduce to the existing `fieldOf`; nested writes
reconstruct each actual runtime container through `writeLValue` and then
reduce to the actual root write. The proof does not accept a callback that
already assumes the desired write correctness. The arbitrary-base read
premise states an exact value and unchanged Run; concrete variable-root
theorems discharge it with `FrameMatches`.

`Ref.write_matches` proves exact source-store correspondence after the real
frame update, `ChangesOnlyVars` for every other Run field, and preservation
of all other runtime root bindings, including bindings outside the source
store. Independent `Path`/`Ref.validities_set` fix every stored header
validity bit. The converted complete source root fixes sibling/ancestor
values, not merely the selected scalar result. The no-action-layer premise
is explicit, and permission/declaration correctness is correctly deferred.

Concrete kernel witnesses instantiate mixed metadata/nested-header indices
and stores, including an unrelated aggregate runtime root. They use the
full nested write theorem, not merely the earlier return-value primitive.
Tests cover both validity states, unequal scalar widths/values, nested
read/write, metadata/sibling preservation and unrelated packet/emitter/visit
state. Theorems preserve more fields than the finite runtime sample checks.

## Independently executed checks

After stable-binary confirmation, executed the existing user-test binary from
its package directory: **exit 0**. Output confirms old scalar/context and
command suites, aggregate source/path answers, nested runtime writes, six
negative shape checks and package API checks all pass.

Queried axiom roots via pinned Lean and existing libraries: nominal coherence,
path evaluation/read/write, frame witness and final write correspondence use
only `[propext, Classical.choice, Quot.sound]`; `Path.get_set` has no axioms;
validity preservation uses `[propext, Quot.sound]`. No custom/sorry/native
axiom surfaced. The suggested explicit default audit for public
`Path.readLValue` (not a dependency of the other audited write law) was added,
along with `Ref.get_set`; inspected the final successful default-build log.

No new Python aggregate full-state DRT or typed field-expression/command
lowering is claimed. Those remain the next independent acceptance boundary,
along with root write permissions and whole-program construction.

## Final adversarial and documentation review

Inspected the recorded isolated experiments, without repeating mutations:
the wrong member-name suffix fails specifically at `Path.evaluate`, where
the real altered field lookup cannot satisfy exact source selection. This
is proof/build rejection, not executable divergence detection. The
same-width `port := right` source accessor passes the default build/audits
but fails the independent full-source-aggregate known answer. The expected
result is not computed from that accessor. Restored build/test logs pass,
and the implementer reports exact restored copies of both source/test files.

The final README and ASSURANCE distinguish local well-formedness, nominal
agreement, root uniqueness and operational frame agreement accurately.
They record both mutations, scoped results and deferred permissions,
whole-program initialization and Python aggregate replay obligations.
The implementer reports both-package gate success (392 spec checks) and
34 existing authored-expression/command conformance cases without skips;
these are attributed integration checks, not additional reviewer executions.
