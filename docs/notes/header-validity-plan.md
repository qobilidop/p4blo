# Typed header-validity reads: scoped implementation plan

2026-09-23. Read-only investigation at committed main `73d0ee5`, before the
command-list integration. No production files changed. Rebase onto its checked
committed interface before changing expression/command adapters or examples.
This plan is for **reads only**: no validity writes, parser, packet extraction,
aggregate assignment or global initialization proof.

## Existing semantics and the missing interface

`P4bloIR.evaluate (.isValid header)` evaluates the operand, requires an actual
`Value.header`, and returns its stored Bool. `docs/semantics.md` already closes
this behavior; neither interpreter nor wire IR needs a semantic change.
`FieldTyping.Path` already describes typed variable/member paths with actual
block declarations and nominal `FieldsOf` agreement, including aggregate
endpoints. Its scalar `Typed` relation currently lacks `isValid`.

Independent `Fields.Data` stores header validity as Bool and struct validity
as Unit. Scalar `Path`/`Ref` deliberately end at scalar leaves and provide
writes which preserve every header-validity bit. Do not add validity as a
writable Boolean scalar `Ref`: that would falsify these existing contracts.
The sole operator AST/evaluator/lowerer is already parameterized by reads:
`Scalar.ExprWith`. The sole command AST is `CmdWith Reads Places`.

## Representation decision

Recommend a constrained `HeaderPath : Shape -> Type`, with `here` only at
`Shape.aggregate .header name fields`, and a member constructor using the
existing `Slot` to navigate aggregates. `HeaderRef roots` packages one root
Slot and such a path. Neither type has `set`, `lvalue`, writable permission or
a conversion to scalar `Ref`/`Place`.

Its independent source observation recursively selects `Record.get` and
returns the actual endpoint's Bool. Its IR expression follows the real root
and member names, then applies `.isValid` at that endpoint. A struct/scalar
cannot be the endpoint by construction, though structs are valid intermediate
containers. Empty headers and directly rooted headers remain useful cases.
Raw source shapes may contain invalid nested-header layouts; as with scalar
paths, runtime correspondence and local/global validity stay separate.

An alternative generic `EndpointPath : Shape -> Shape -> Type` would unify
scalar/header navigation, but replacing the current scalar Path would ripple
through all set/get, exact writeback, noninterference, named-path and validity-
preservation proofs. Leaving both generic and scalar path implementations in
parallel would not buy much reuse yet. For this single read-only capability,
the constrained view is the smaller independently reviewable increment.
It duplicates a short traversal, not expression operators or the interpreter.
Confidence: medium. Revisit when a second aggregate-endpoint operation needs
the same navigation, or the constrained proof/lookup code becomes materially
duplicated. Any later generalization must keep scalar writable endpoints
constrained and retain the present exact preservation laws.

## Small checked checkpoints

### 1. Header-target primitives and authoritative scoped typing

Add the focused HeaderPath/HeaderRef module and exact concrete bridges:

1. For an arbitrary source `Data shape`, actual Run, agreeing Index and exact
   evaluation of the base to that data, evaluating the header-validity path
   returns its independently selected Bool **and the entire unchanged Run**.
2. At the root, discharge the base premise using actual `FrameMatches` and
   `readVar`; public HeaderRef evaluation must contain no arbitrary callback
   correctness assumption.
3. Extend authoritative `FieldTyping.Typed` with an `isValid` rule for a
   `Path index scope operand (.header name)` and exact endpoint
   `FieldLaws.Declared index .header name fields`. Thus the primitive type rule
   requires actual header kind/index agreement, not only an unchecked name.
   Prove concrete HeaderRef typing under RootWellFormed, IndexAgrees and
   RootDeclares, using the same intermediate Path rules as scalar fields.
4. Construct a real agreeing Index, declarations and initialized matching
   frame witness. Cover direct-root/nested/empty headers and opposite validity
   siblings; negative struct/scalar endpoint and forged nominal/declaration
   cases must fail for the intended reason.

Neither a whole aggregate checker nor initialization theorem follows. Runtime
evaluation itself need not assume declaration validity: its exact frame/index
premises suffice, as for scalar reads. The typing theorem separately connects
the actual source root declarations and endpoint nominal kind.

`docs/notes/header-validity-probe.lean` is an isolated feasibility probe, not a
production API/default test. The proposed HeaderPath source/IR primitive and
arbitrary-Run theorem kernel-check against the existing compiled interfaces;
the theorem's exact axiom set is `[propext, Classical.choice, Quot.sound]`.
The probe also rejects struct/scalar `.here` endpoints. Its headers do not
pretend to establish global validity. All imported modules used by the probe
are unchanged between `ae9ca87` and this plan's base.

To reproduce after the normal package build, from the repository's `lean/`
working directory use the pinned environment:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 env lean ../docs/notes/header-validity-probe.lean
```

The initial investigation used the same pinned Lean executable with explicit
`LEAN_PATH` entries pointing at the already checked named-path worktree's
`lean/.lake/build/lib/lean` and `ir/.lake/build/lib/lean`, avoiding a production
build. Recorded command exit 0; log `/tmp/p4blo-header-validity-probe.log`.

### 2. One unified read interface, unchanged scalar writes

Introduce `Fields.Read roots t` with exactly two leaf forms:

- existing `Ref roots t`, injected as a scalar read;
- `HeaderRef roots`, yielding `.boolean` by observing validity.

The leaf-level `Read.get`, `Read.expr`, typing and evaluation laws dispatch to
the independently proved concrete scalar/header bridges. They do not copy
the operator denotation or assume a callback theorem. Specialize existing
`Fields.Expr` to `ExprWith (Read roots)` and existing `Fields.Cmd` to
`CmdWith (Read roots) (Place modes)`; **Place and Ref stay unchanged**.
Discharge the generic expression/command laws with these concrete Read laws.
All scalar writes still preserve validity, and arbitrary continuations and
whole-Run/other-root guarantees remain exactly the current command contract.

Use a one-way `Coe (Ref roots t) (Read roots t)` so `.read ref` and
`Place.read` continue to elaborate. The probe checks expected-type-directed
`.read ref` and addition of those reads with this exact sum/coercion pattern.
It uses a placeholder Bool leaf only to test coercion, not as a proposed
production header representation. A helper `HeaderRef.isValid : Expr roots
.boolean` can expose the other leaf without a macro. No second expression
AST, operator evaluator, monad, implicit mutable state or scalar-Ref coercion
in the reverse direction is permitted.

Changing the read parameter changes internal definitional types of Fields.Expr
and Cmd; source-level smart constructors should be preserved, not falsely
claimed definitionally identical to `ExprWith (Ref roots)` forever. Existing
raw proofs that pattern-match read leaves need a sum dispatch; the public
concrete lowering/evaluation theorem statements keep their scoped meaning.
Test every current fixture and export byte-for-byte, and adapt explicit
ForwardPolicy reduction only by transparent Read injection/get definitions.
Its current policy and intended invalid-header stored-value behavior must not
change. Confidence: high in the seam, medium in coercion inference across all
call sites. Revisit if expected types fail in realistic code; prefer an
ordinary explicit `.scalar`/smart constructor over new parsing machinery.

A later small named HeaderRef constructor should reuse the certified unique
Slot lookup already in NamedFields (currently private), with exact actual
spelling and header endpoint rejection. Do not silently repurpose scalar
`Ref.named`, accept ambiguous differently typed matches, or copy a divergent
name-resolution policy. Explicit HeaderRefs suffice for the primitive proof
checkpoint; ergonomic named construction can land with the adapter if small.

### 3. New validity-guarded application, separately named

Keep `FieldCommandExamples.forward` and `ForwardPolicy.policy` unchanged.
Add a new body which requires both Ethernet and IPv4 validity before invoking
the existing hit/TTL rewrite; otherwise set only drop. Use nested existing
`Cmd.ite` guards rather than adding Boolean operators solely for the example.
Define its independent policy over the already complete Snapshot using direct
`ethernetValid && ipv4Valid` and the existing independent hit/TTL policy.
Prove the arbitrary-store source policy then lift through concrete execution.
No valid-header premise should remove invalid inputs from the theorem: invalid
inputs are exactly the new observable branch and must preserve every other
stored value, validity bit, route input and unrelated Run component.

This still does not prove Ethernet type/version/length checks, parsing, route
lookup, checksum maintenance, caller initialization or architecture packet
fate. Those remain separate next application boundaries, not implied by the
new guard. Full initialization/call-copy proof is a larger later checkpoint.

## Tests and adversarial acceptance

- Default audits for primitive exact read, concrete typed/evaluate adapters,
  unchanged command execution/preservation, and the new policy lift.
- Independent source/IR/Python answers for all four header-validity pairs,
  equal versus opposite siblings, direct/empty/nested headers, readonly root
  inputs, both route-hit values and TTL 0/1/2/255. Retain full asymmetric source
  contents so validity results cannot accidentally be inferred from zeros.
- Original examples retain exact exported syntax/bytes and original policy
  answers, including rewrite of invalid stored headers. New validity-guarded
  examples have independent full-state expectations and unchanged payload.
- Observe a validity expression exactly once **before** snapshotting all
  fields/validities/unrelated state. Compare and save DRT mismatches before
  asserting independent answers; use shared lean_binary/test_lean_agrees.
- Mutate header observation to constant true or the opposite Bool: concrete
  source-to-IR proof must reject. Alias one valid typed header to its sibling:
  naming/intent evidence must detect it with opposite validity bits; generic
  faithful-lowering alone cannot certify requested application intent.
- Mutate actual Python `is_valid` return or introduce a read-side effect that
  preserves its returned Bool while changing sibling validity/stored data.
  Full post-expression observers must kill, save and replay the complete
  mismatch live, then agree restored. Do not count failed builds as runtime
  detection. Mutate the new application's skipped validity guard: independent
  arbitrary-store policy must reject it.
- Review each small checkpoint independently; run both Lean package gates,
  full required DRT and scoped Python/schema gates. No Docker image build is
  needed for this authoring-only capability over already specified IR.

Before implementation, root and architecture reviewer should confirm the
constrained-path tradeoff and authoritative endpoint declaration rule. Merge
the completed command-list checkpoint and rebase; do not build against its
uncommitted working files. This investigation makes no production correctness
claim beyond the explicitly isolated feasibility proof above.
