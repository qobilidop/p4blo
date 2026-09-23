# Next Program-codec increment: foundational declarations

2026-09-23. Read-only production baseline
`dcbf3928b835dca499ddea3ae49c65bc9f16e6e1`, with an unregistered feasibility
probe in `ir/DeclarationCodecProbe.lean`. No production code, default target,
test endpoint or retained evidence changed. Root and independent review accepted
this plan and probe; implementation remains pending a separate scoped handoff.
See [independent review](reviews/program-codec-next.md).

## Recommendation

Prove actual JSON-value roundtrips for the **nine declaration codecs before
Expr in Json.lean**: Field, HeaderType, StructType, EnumType, Var, Param,
Method, ExternType and ExternInstance. This is one coherent dependency slice,
not a claim of full Program roundtrip. Start with the six foundational type/
binding declarations, then close the three extern declarations in the same
bounded checkpoint if the checked probe's proof size remains representative.
Do not add Action, parser transitions, tables, Block or Program just because
their decoders are already total. Export can wait with Program assembly.

There is **no remaining termination barrier** in the inspected production
codec. Expr, LValue and Stmt are now total and have checked unfolding and
representable roundtrip laws. All remaining declaration/Program decoders are
ordinary definitions in an acyclic dependency graph. They need composition
proofs, representability coverage and independent wire observations, not
another decoder, bounded interpreter, serializer framework or totality refactor.

The nine selected codecs add no direct numeric fields: all numeric bounds
come from existing TypeRepresentable and LiteralRepresentable. Their list
composition can reuse the committed `CodecLaws.array_encoded_roundtrip`.
The probe checks the hardest selected path, Param → Method → ExternType,
including named enums, two ordered arrays and optional type returns.

Confidence: high in this boundary and proof feasibility after the complete
probe; medium-high in keeping the nine-codec implementation review-sized.
If declaration proof duplication becomes substantial, first land the six
foundation laws plus independent tests, keeping Method/ExternType/Instance
explicitly pending. Revisit helper factoring only after duplicated lookup
proofs demonstrate a real need; do not replace universal laws with a small
fixture theorem or admit whole-declaration correctness as a callback premise.

## Actual dependencies and domains

| Selected codec | Dependencies | Wire representability only |
|---|---|---|
| Field | Ty | TypeRepresentable field.type |
| Var | Ty | TypeRepresentable var.type |
| Param | Ty, Direction.names | TypeRepresentable param.type; all four Direction constructors |
| HeaderType | ordered Field list | every field representable |
| StructType | ordered Field list | every field representable |
| EnumType | ordered string list | True: all finite member lists |
| Method | ordered Param list, optional Ty | every param representable; present return type representable |
| ExternType | ordered constructor Param and Method lists | all members of both lists representable |
| ExternInstance | ordered Literal list | every argument LiteralRepresentable |

Every name may be empty, repeated or unresolved; lists may be empty, contain
duplicates and have arbitrary finite length. Header fields may contain
aggregate types even though semantic validation rejects them. Enum members
may be empty/duplicated and the enum may have no members. Constructor and
method parameters may use **any** actual Direction, including directionless
NONE and out/inout constructors. Extern arguments need not agree with an
extern declaration, arity or type. Optional method returns may name unresolved
headers/structs; `some (.bits 0)` differs from none. Zero widths/stack sizes,
uint32 maximum, huge decimal literal values and values outside their bit width
remain included, as in the existing leaf predicates.

Do not conflate `Direction.none` / `DIRECTION_NONE` with the protobuf sentinel
`DIRECTION_UNSPECIFIED`. The former is an actual constructor and is always
emitted; the latter has no Lean constructor. Missing/null/UNSPECIFIED direction
is rejected by actual `enumField`, not a directionless default. The shared
`Direction.names` table is used by both decoder and encoder (`protoName`), so
its consistency is insufficient to establish the intended wire mapping.

The actual validator separately requires unique/nonempty names, scalar header
fields, nonempty enums, in-only constructor parameters, method directions and
resolved extern arity/types (`python/p4blo/validator.py`, declaration checks).
**None** of those requirements belongs in the proposed wire predicates.

## Checked feasibility probe

The unregistered probe imports only actual `P4bloIR.CodecLaws`. Its four
named theorem roots compile without additional axioms:

1. `param_roundtrip`: every representable type, arbitrary name, all four
   directions. Finite direction cases reduce the actual enum table; no
   replacement enum encoder/decoder is defined.
2. `method_roundtrip`: every finite parameter list and optional return.
   The actual body reduces to actual Decode.array and optional Ty.decode;
   every list member is discharged by the Param theorem at every path.
3. `externType_roundtrip`: both ordered lists, using only those real member
   laws and the already-committed array theorem.
4. `unusual_roundtrip`: a nonvacuous kernel instance with duplicate/empty
   names, all four directions, unresolved types, zero-width/zero-size types,
   a max-width return and both some/none return cases.

The probe also checks a false representability premise for return-width
overflow, exact missing-direction rejection, null-return omission, and the
distinct error for present `{}` returns. It does **not** prove all nine laws
yet, register any default audit, change production decoders or establish
cross-language equivalence. The private one-line type-object lemma only
exposes the actual Ty encoder's constructor shape; it is not a second codec.

Fresh worktree-owned caches were used. With the IR package as the scoped
working directory, exact commands are:

```text
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.CodecLaws
nix develop -c lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true /Users/qobilidop/my/work/p4blo-program-codec-next/ir/DeclarationCodecProbe.lean
```

Dependency build exit 0: `/tmp/p4blo-program-codec-next-build.log`.
Final standalone probe exit 0:
`/tmp/p4blo-program-codec-next-probe-final.log`. All four roots report exactly
`[propext, Classical.choice, Quot.sound]`. Initial development failed at an
overcompressed functor/bind `change`, record syntax and ambiguous `UInt32`;
those unsuccessful attempts are not positive evidence. The final command
is run alone so a later shell command cannot mask its exit status.

Independent review may run the absolute probe through pinned `lake env lean`
using another checkout's already-built identical CodecLaws dependencies.
This does not rebuild or replace native executables, including main's running
full-gate consumers. No full Lean/Python/schema/oracle gate is claimed for this
planning-only task. No Docker operation or old evidence mutation occurred.

## Proposed implementation order and ownership

1. Extend the existing **test-only** codec endpoint with the nine declaration
   kinds and explicit record/constructor descriptors. Keep actual decode and
   encode functions as the implementation under test. Reuse independent type/
   literal descriptors, but add a direct four-case Direction descriptor; never
   observe direction via `protoName`, `Direction.names`, or encoded output.
   Add Python fixtures and known answers before proof work, capturing current
   raw responses as described below. No production endpoint/API addition.
2. Add a focused `ir/P4bloIR/DeclarationCodecLaws.lean` importing CodecLaws,
   or an equivalent narrow extension after root agrees file ownership. Keep
   predicates/laws in the existing CodecLaws namespace. Reuse the actual
   array theorem and existing type/literal laws; local finite object/default
   reductions are sufficient in the probe. **No Json.lean behavior change
   is expected or required.** A discovered codec defect is a separate scoped
   issue: stop, document old behavior and obtain a reviewed fix boundary.
3. Register the nine universal laws and a mixed nested extern witness in
   default CodecProofAudit. Cover all directions and invalid-but-representable
   declarations constructively, with explicit embedded-type/literal overflow
   negatives. Default native anchors remain independent of wire tables.
4. Run actual compiling faults, restore, replay, run both Lean packages
   before binary consumers, focused old/new codecs, required real-Lean
   discovery, lint/types and the ordinary integration gate. Freeze for
   independent review, then small coauthored commits through root.

Likely disjoint files: the new proof module; dedicated declaration test module
and `tests/test_codec_declarations.py`; narrowly appended existing endpoint/
native/export/audit registrations and CodecKind; a declaration evidence note.
No runtime Exec, interpreter, call modules, generated protobuf files or schema
changes. Avoid coupling this work to the concurrently developing action plan.

## Independent baseline and malformed matrix

Capture baseline transcripts from the current actual decoder with only the
test endpoint/fixtures added, before changing shared helpers or any codec.
If production remains byte-identical throughout, say so; do not invent an
old-versus-new refactor. Still source-pin the baseline and compare exact raw
stdin/stdout/stderr/status to catch unintended collateral changes. Store a
complete ordered request function, assert nonzero exact count and unique
requests, and fix that set before capture. Additional regressions belong in
a separate set, not a silently recaptured baseline. Pin old source hashes to
the reviewed baseline commit, then source-match requests/independent expected
answers separately against the final fixture. Never overwrite old artifacts.

Build independent wires/descriptors for all nine records and cover:

- Every Ty/Literal family where embedded, widths/sizes 0/max/overflow, huge
  decimal values, Boolean false, empty strings, Unicode/escaping. Include
  impossible semantic header fields, duplicate field/enum/parameter names,
  all directions, non-in constructor directions and unresolved extern calls.
- Distinct field names/types and list lengths, at least three unequal ordered
  fields/params/arguments, and an ExternType containing multiple unequal
  methods with both return-presence cases. A symmetric fixture cannot expose
  reversal or slot swapping. Observe full decoded names, directions, types,
  return presence and every member, not only the encoded JSON or list length.
- Non-object top-level; missing/null name; missing/null/nonobject/present-empty
  type message; missing/null/empty/nonarray repeated fields; null versus `{}`
  array elements; exact zero/later/nested first-error indices.
- Param direction missing/null/UNSPECIFIED, numeric value, unknown string,
  and each named valid value. Numeric enum acceptance differs from protobuf;
  preserve the actual Lean error without claiming general ProtoJSON parity.
- Optional returns absent/null versus `{}`/wrong type/overflow; names before
  types before directions; Method name before params before returns;
  ExternType name before constructor_params before methods; ExternInstance
  name before extern_type before args. Include simultaneous errors to anchor
  each ordered boundary, not only single-error inputs.
- Unknown keys remain actual ignored Lean input behavior. Canonical successful
  outputs must pass protobuf parsing; arbitrary malformed/unknown inputs are
  not expected to match Python's accepted language.

Canonical cross-language success uses the actual pb message plus public
`ir.dump_json`/`ir.load_json` with a minimal Program wrapper and no validator or
Index.build. Insert Field under a header, Var/Param under a block, Method under
an extern type, and other declarations under their corresponding top-level
lists. Observe the recovered selected protobuf message, not wrapper validity.
An invalid-but-representable header aggregate is deliberately allowed here.

Reuse strict `same_json`, duplicate-rejecting harness `loads`, shared
`lean_binary` discovery, `test_lean_agrees` naming and the existing process-
failure retention logic. Raw invalid declarations are codec artifacts, not
packet DRT bundles. Require nonempty source-matched live/restored replay sets
and exact type checks; do not execute command metadata from artifacts.

## Adversarial acceptance

1. One-sided actual HeaderType field reversal or ExternInstance argument
   reversal must compile the actual encoder, then fail the unchanged
   universal law (or independent runtime anchors, if buildable). Distinguish
   proof rejection from executable mismatch and from compiler/linter failure.
2. Swap IN/OUT values in actual shared `Direction.names`. Its encoder and
   decoder can remain mutually consistent, so roundtrip may pass. Require
   independent direct Direction descriptors, literal named-wire Python cases
   and native IO anchors to reject it. Keep known wire anchors out of any
   shared descriptor table; otherwise the paired wrong-model trap returns.
3. Pair the ExternInstance name/extern_type wire mappings in actual encoder
   and decoder. Roundtrip may survive after corresponding local proof-body
   path changes, but full independent abstract descriptors with asymmetric
   strings must fail even if encoded wire also round-trips unchanged.
4. Perturb a real decoder's field evaluation order (for example Param
   direction before type), or change a selected optional/default behavior.
   Exact simultaneous-error and absent/null/present-empty controls must
   reject it independently of successful representability laws. Preserve
   strict raw failure artifacts and replay live, then restore and replay.

Challenge Python fixture/observer coupling as well: a paired hand-authored
fixture remapping must not change the independent native literal-wire anchor.
Do not count a failure to compile as a runtime detection, and do not widen
production acceptance or hide a callback premise to make a mutant pass.

## Remaining route to full Program

After the nine declaration laws, the actual remaining graph is finite:

| Later slice | New dependencies / restrictions |
|---|---|
| Table declarations | Key: Expr + MatchKind; ActionCall: Literal list; Entry: KeyValue list + ActionCall + uint32 priority; Table: keys/actions/optional default/const entries + uint32 size |
| Parser syntax | Target: all constructors; KeySet: embedded Literals; SelectCase: sets + Target; Transition: Expr keys + cases; State: Stmt body + transition |
| Executable declaration assembly | Action: Param list + Stmt body; Block: kind, params, locals, actions, tables, states and body |
| Program closure | selected nine laws + Block + Export, arbitrary strings/errors; every list member covered |

The eventual Program predicate must cover **every** reachable uint32 (Ty,
Literal, Expr slice bounds, Stmt push/pop counts, KeyValue LPM prefix, Entry
priority, Table size), not just nominal declarations. Core error prefixes,
unique names, direction conventions, parser/control shape, table key/action
arity, valid transitions and resolved exports remain semantic validation, not
wire premises. Host TableEntries/Entries are outside Program and can later
reuse the table leaf laws; do not silently include them in a Program claim.

No text parser/serializer theorem, binary protobuf theorem, annotation/version
compatibility policy, safe unknown-field semantics, global validation,
runtime resource guarantee, execution correctness or universal Python
equivalence follows from these JSON-value roundtrips.
