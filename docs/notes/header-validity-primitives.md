# Read-only header validity primitives

2026-09-23. Checkpoint 1 of `header-validity-plan.md`, based on `cdb7a3c`.
The plan/probe had already been committed on main; their untracked duplicate
copies were compared byte-for-byte before removal and the worktree rebased.
They remain tracked and unchanged. No production interpreter or wire semantics
changed in this checkpoint.

## Implemented boundary

`Fields.HeaderPath` navigates existing typed Slots and ends only at a header.
`HeaderRef` adds an actual root Slot. Independent source observation selects
the header's stored Bool directly from `Data`/`Record`; it never calls the IR
interpreter, extracts validity from lowered evaluation, or assumes validity
because fields are nonzero. Lowering follows real member names then applies
the already specified `.isValid`. Empty and directly rooted headers are valid
targets; structs may be intermediate containers, not endpoints.

There is no `set`, `lvalue`, coercion to scalar Ref/Place or command operation.
Existing scalar Ref/Place, all write preservation laws, ExprWith/CmdWith and
their existing specializations remain unchanged. Unified read leaves, named
header construction and a new validity-guarded application are later reviewed
increments, not supplied by this primitive library.

`HeaderPath.evaluate` proves the exact Bool and **entire unchanged Run** for
arbitrary source data and Run, using exact Index agreement and a base-read
premise. `HeaderRef.evaluate` discharges that premise with actual root lookup
under `FrameMatches`, including the existing action-first lookup semantics.
Its public theorem has no arbitrary correctness callback or execution-fuel
assumption. Full-state equality is stronger than the finite runtime observer.

The authoritative `FieldTyping.Typed.isValid` rule requires both a header
Path in actual block declarations and exact endpoint
`FieldLaws.Declared index .header name fields`. Merely naming a header type
does not bypass Index agreement when there are no member steps. The concrete
HeaderPath/Ref typing proofs use the existing intermediate FieldsOf rules;
the root theorem requires RootWellFormed, IndexAgrees and RootDeclares.

Typing and operational frame agreement are separate. A raw path/shape is not
global schema validity; raw malformed nesting remains excluded by the root
well-formedness premise of the typing theorem, not by a new global checker.
Runtime reads do not need writability. The input-header witness demonstrates
read access without creating a writable Boolean validity location.

All four advertised proofs (HeaderPath.evaluate/typed and
HeaderRef.evaluate/typed) are default-audited at exactly
`[propext, Classical.choice, Quot.sound]`, the existing aggregate proof
foundations. No new axioms, `sorry`, native proof escapes or altered semantics.

Confidence: high in the exact read contract, medium in the constrained path
representation. It deliberately duplicates a short navigation view rather than
refactoring established scalar write proofs prematurely. Revisit when a second
aggregate-endpoint operation needs shared traversal; retain the scalar-only
writable endpoint constraint if paths are generalized later.

## Positive and negative evidence

`HeaderFieldTests` is registered in the normal user executable. Kernel tests
give exact lowered Ethernet/IPv4 member spellings, a constructive arbitrary
source-store matching frame and typing witness, and an input empty-header
Index/declaration/store/frame witness for either Bool. Five rejected
constructors exclude struct, Boolean and bitvector endpoints plus conversion
to writable scalar Ref/Place. The spec's independently constructed relation
tests accept all parameter directions for reads and prove five impossibility
results: missing endpoint declaration, struct/bitvector/Boolean endpoint, and
wrong nominal kind in the Index.

Runtime checks cover all four Ethernet/IPv4 validity pairs (eight reads), two
direct empty-header values, and a real `Index.build`/`Frame.forBlock` input
header initialization. They independently expect the requested Bool and check
all stored roots, unrelated header, packet/cursor, emitter, table default,
register cells, parser visits and scope sentinels after reads. Actual production
initialization is a finite witness, not a universal initializer proof.

Candidate gates:

- `nix develop -c scripts/check-lean.sh`: exit 0, both complete packages,
  default audits, previous suites and new registered user tests.
- `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees`:
  exit 0, 469 passed, 1384 deselected, no skips. This is existing regression
  coverage, not a claim that new header reads already have an authored
  Python exporter or a universal Python equivalence theorem.
- Independent read-only review: clear. The reviewer separately ran compiled
  user tests, evaluated HeaderFieldTests.run and checked all four exact audit
  roots, inspected authoritative endpoint/readonly tests and confirmed mutant
  restoration byte-for-byte. Report: `reviews/header-validity-primitives.md`.

## Adversarial campaign

All faults were applied separately in detached
`/Users/qobilidop/my/work/p4blo-header-read-mutants` at `cdb7a3c`, with the
candidate modules/tests/registrations copied in. Baseline default build passed.
For the following commands use that worktree's `lean/` directory in the pinned
Nix environment; restore each edit exactly before trying the next fault.

1. **Constant source validity:** in HeaderFields, replace the first equation
   of HeaderPath.get, `| .here, .aggregate valid _ => valid`, with
   `| .here, .aggregate _ _ => true`. `lake +leanprover/lean4:v4.34.0 build`
   exits 1 at HeaderPath.evaluate: the actual arbitrary Bool cannot equal
   constant true. The fault is a valid source function, not a shape/type error.
2. **Inverted source validity:** replace the same original equation with
   `| .here, .aggregate valid _ => !valid`. The same build exits 1 at the
   exact-value theorem, actual Bool versus its negation. These two faults are
   proof rejections, not runtime Python/Lean mismatch detections.
3. **Valid wrong authored sibling:** restore HeaderFields; in HeaderFieldTests
   replace the runtime loop's `[(ethernetValidity, ev), (ipv4Validity, iv)]`
   with `[(ipv4Validity, ev), (ipv4Validity, iv)]`. Both
   `lake +leanprover/lean4:v4.34.0 build userTests` and `build UserProofAudit`
   exit 0. Running `.lake/build/bin/userTests` exits 1 with
   `independent source header validity` for opposite validity bits. Generic
   correspondence faithfully proves the chosen header; it cannot prove that
   a caller intended Ethernet. The independent expected answers supply that
   distinct check. No differential execution mismatch bundle is invented.

Restore both files byte-for-byte, run default build **and** `build userTests`
(the default target alone does not rebuild the user executable), then run
`.lake/build/bin/userTests`. All three restored commands exited 0; both changed
files compare byte-for-byte with the candidate.
Logs are retained under `/tmp/p4blo-header-mutant-` with suffixes
`constant.log`, `invert.log`, `sibling-build.log`, `sibling-audit.log`,
`sibling-runtime.log`, `restored-build.log`, `restored-tests-build.log` and
`restored-tests.log`. Exact edits and observed outcomes above are the durable
reconstruction record; temporary paths are not necessary to reproduce them.

The next unified-read/application increment must add actual Python return and
read-side-effect faults with complete saved/live/restored DRT replays. Those
are not falsely claimed by this Lean-local primitive campaign. No header
validity write, parser, packet validity policy or global initialization proof
was added here.
