# Field-expression read-seam review

Read-only structural review, 2026-09-23, of `p4blo-typed-fields` after the
separate aggregate source/path checkpoint. No candidate edits or builds.
**Disposition: clear for this separate read-seam checkpoint**, with the
ordinary merged full gate retained as an integration obligation. The concrete
Python observer ordering gap is fixed and independently tested. Final
campaign documentation and restored replay evidence have been reviewed.

## One operator AST and concrete proof boundary

`Scalar.ExprWith Reads` owns literal/read/add/equality/mux syntax exactly
once. `denoteWith` computes independent Fin/Bool operator meanings; the
scalar/context and aggregate APIs instantiate only the typed read family.
`lowerWith` similarly supplies only leaf lowering. Existing `ExprIn`/`Expr`
aliases and named constructors remain, and old scalar commands consume the
same specialization. There is no second aggregate operator interpreter.

The compositional `evaluate_lower_with` legitimately assumes exact leaf
read correspondence with unchanged Run. Crucially, advertised concrete
`Fields.evaluate_lower` discharges that premise through actual `Ref.evaluate`,
`IndexAgrees` and `FrameMatches`, not a user-supplied correctness callback.
Its conclusion is the exact independently computed source result and the
entire unchanged Run, including frame, packet/emitter and extern state.
It does not merely assert type preservation or existence of a matching run.

`FieldTyping.Path` relates actual nonempty root variable declarations and
nominal member declarations to IR paths. `FieldsOf` uses the exact earlier
`FieldLaws.Declared` kind/order/name agreement; it cannot confuse scalar,
struct and header containers. `Typed` adds the existing scalar operator
typing relation. This is a declarative fragment, not a total checker or
soundness/completeness theorem for all IR expressions.

`RootWellFormed` separates unique/nonempty root names and local shape
validity from global nominal `IndexAgrees`. `RootDeclares` independently
requires actual scope lookup, declaration name and declaration type. The
lowering typing theorem uses all three; runtime correspondence instead uses
actual source/runtime value agreement. Concrete kernel examples instantiate
the declaration and nominal premises. General `Index.build`/`Frame.forBlock`
initialization, action-scoped declaration typing, permissions, commands,
parsing and whole-program validity are not established by this increment.

## Fixtures and confirmed observer gap

Seven authored expressions cover wraparound addition, same-width different
field/root references, equality, both mux branches and valid/invalid stored
headers. Lean source known answers are separately listed. The exporter
emits syntax, result width and initial validity only; Python fixes its own
unequal initial field values and expected result bytes, and checks exporter
case identity/coverage. The raw Python wrapper is test scaffolding rather
than a verified field-program compiler.

**Confirmed finding:** initial `field_program` emits snapshots of every
source field, header validity and unrelated binding before assigning the
authored expression result (the final observation). Therefore side effects
of evaluating that expression can escape the supposed full-final-state
oracle if its result remains correct. Requested fix: evaluate the authored
expression exactly once first, then snapshot source fields/validity/other
roots, preserving output field declaration order. Requested adversarial
check: a real Python read/evaluation fault changing a sibling but preserving
the selected result must fail the post-expression state observer and save
a complete replay. Sent to implementer and integrator, and implemented:
output declaration order remains stable while expression evaluation is
first and all source snapshots follow it.

The permanent adversarial regression scopes a real Python `expr.field_of`
fault: reading `H.right` still returns 257 but zeros `H.left`. A reconstructed
old-order observer falsely agrees, while the corrected observer saves the
complete original program and request, diverges only at the left snapshot
byte (`00` versus `ab`), and replays to agreement after restoration. I ran
this regression independently as part of the final focused field file:
**9 passed**, exit 0. This is executable evidence that the new observation
order detects the identified false-acceptance mode, not just a test rewrite.

The comparison already precedes independent expected-answer checking and
retains ProtocolError reports, so divergent exact input programs/requests
can be saved. A same wrong source accepted by both engines must still fail
the independent expected bytes, not be mislabeled a DRT divergence.

## Independently executed preliminary checks

After stable-binary confirmation, executed existing `userTests` from its
package directory: **exit 0**, including old scalar/context/command cases,
seven field expressions, nested path writes and package API tests.
Queried actual compiled axiom roots for generic operator correctness,
`Ref.typed`, concrete field `lower_typed` and `evaluate_lower`: all exactly
`[propext, Classical.choice, Quot.sound]`. Old named constructors and old
open/closed correctness theorem signatures remain available.

After the observer fix, independently ran all three authored Python test
files (scalar/context, statements, fields) against stable binaries with
required Lean enabled: **43 passed**, exit 0. Tests ran from `/tmp` using
the reviewer environment, with bytecode/cache writes disabled and test
artifacts scoped to a reviewer temporary directory.

No new candidate package builds or live mutations were performed by this
reviewer, apart from the scoped fault exercised inside the permanent
regression. Final campaign evidence follows.

## Final campaign, restoration and scope review

Inspected all six recorded fault experiments. Lowering add to subtract,
after adjusting its still-valid typing proof, fails at exact modular
semantic equality in the generic theorem. This is proof rejection only.
The same-width `port := right` accessor and the 85-to-84 literal notation
fault both build/audit successfully and survive DRT agreement; separate
known answers reject 262 versus 8 and 255 versus 0 respectively.

Three production Python edits exercise actual runtime state observations:
read-side sibling corruption, forced validity during member assignment,
and setter sibling corruption. Each retains the exact program/request and
fails live replay with one concrete snapshot-byte divergence and no shared
errors; restoration yields one agreement on the identical artifact. The
setter mutations affect initializer scaffolding, not an as-yet nonexistent
verified source field-command compiler. Final ASSURANCE explicitly states
this distinction and preserves precise edits/reconstruction commands.

Independently reconstructed and checked all three retained programs against
the tracked field fixture, including empty entries/packet, ingress 0, four
ports and seed 0. All three replay through the stable candidate to agreement.
Verified byte lengths and hashes:

- `lean-fields-field-right.json`: 15752 bytes,
  `b023413689d448f2b1d3b299bbfe03d40dc588930a490487ac3039017ecacb73`;
- `lean-fields-field-add-invalid.json`: 16221 bytes,
  `7d3233bf72af3afa712ea206593126e5f6c9c5c535b4552ff1031c41e264d0d6`;
- `lean-fields-field-no.json`: 16340 bytes,
  `e3b174b010a2301b4e9509c7d92b4cddcbd6270463630660de36c5e3742d4f81`.

Confirmed the isolated Python `expr.py` diff is empty. Inspected restored
default-build and user-test success logs, and the final required DRT log
with 250 passes. These full builds/DRT counts are implementer evidence;
the reviewer separately ran the 43 focused authored tests, user binary,
axiom queries and three restored artifact replays described above.

Final README/ASSURANCE correctly bound declarative typing versus a total
checker, concrete read correctness versus whole-program compilation, and
unverified observer initialization versus source command proofs. No further
correctness blocker found. Continue with a single factored write/command
implementation and explicit real declaration/permission correspondence.
