# Next codec slice: table declarations

2026-09-23. Proposed after the foundational declaration slice; feasibility
work is isolated at `77b9890`. This does not close Program roundtrip or add a
new runtime guarantee. No production encoder/decoder changes are proposed.

## Contract and minimal scope

Add four actual-code roundtrip laws: Key, ActionCall, Entry and Table, in
`ir/P4bloIR/TableCodecLaws.lean`, reusing the existing KeyValue law. Keep the
public predicates/laws in `P4bloIR.CodecLaws`; splitting files is for proof
maintenance, not another IR or package. Existing Expr/Literal/KeyValue/list
laws are sufficient dependencies; the declaration-law branch is not needed.

| Message | Wire-only premise |
|---|---|
| Key | ExprRepresentable for its expression; all three MatchKind values |
| ActionCall | LiteralRepresentable for every argument, preserving order |
| Entry | KeyValueRepresentable for each key; ActionCallRepresentable; uint32 priority |
| Table | KeyRepresentable for every key; optional ActionCallRepresentable; EntryRepresentable for every const entry; uint32 size |

Keep empty/duplicate/unresolved names, arbitrary string order, all combinations
of const-default flag and default presence, no keys, unequal key arity, mixed
match kinds, noncanonical key values/masks and zero widths/sizes. Neither
entry priority nor size is required to be positive. The laws must not hide
semantic validation in wire predicates. Decimal key/literal values are
unbounded naturals; nested widths, slice bounds and LPM prefixes retain their
existing uint32 restrictions. A bool needs no representability restriction.

The theorem shape is `decode path value.toJson = .ok value` at **every** path.
The production decoders are already total. Do not refactor them merely to
ease proofs, substitute a proof-only decoder, or prove only a new wrapper.
Text/binary protobuf parsing and universal Python equivalence are not claimed.
Host TableEntries/Entries, parser syntax, Action/Block and Program remain
separate slices, even though host entries can eventually reuse these laws.

## Checked feasibility and remaining risk

Unregistered `ir/TableCodecProbe.lean` proves actual Key, ActionCall and Entry
roundtrips, an invalid-but-wire-representable ordered witness, and overflow
exclusions. It uses existing Expr/Literal/KeyValue laws and the real array
traversal, with no decoder replacement. Four printed roots have exactly
`propext`, `Classical.choice`, `Quot.sound`. It is not imported by a public
module, default audit or test target and does not count as integrated codec
coverage. The Table law has **not** been proved by this probe.

The probe's first attempt failed because `UInt32` in simp lists was ambiguous
with Lean's machine type; qualifying `CodecLaws.UInt32` resolved it. This is
ordinary development, not an adversarial kill or a production bug.

Commands, both exit 0:

```sh
nix develop /Users/qobilidop/my/work/p4blo-table-codec-next -c lake +leanprover/lean4:v4.34.0 build P4bloIR.CodecLaws
nix develop /Users/qobilidop/my/work/p4blo-table-codec-next -c lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true /Users/qobilidop/my/work/p4blo-table-codec-next/ir/TableCodecProbe.lean
```

Run from that worktree's `ir/` package. Logs are
`/tmp/p4blo-table-codec-probe-build.log` and
`/tmp/p4blo-table-codec-probe.log`. Paths are local evidence, not prerequisites
for future sessions: the checked source and pinned toolchain reproduce them.

Confidence: high for the first three laws; medium-high for the complete Table
composition. Its seven fields introduce optional nested messages, a defaulted
bool and several arrays, but no new recursion. Prefer factoring small generic
omission/object lemmas if brute-force case splitting becomes expensive; do
not weaken the predicate or hide behind larger global heartbeat limits.
Confidence is medium in the lasting file split. Revisit when composing Block
and Program, preserving public names rather than multiplying packages.

## Freeze independent behavior first

Before laws or source changes, commit a dedicated test/observer baseline,
following `declaration-codec.md`'s non-overwriting raw transcript recipe.
Use `ir/Tests/TableCodec.lean` and `tests/test_codec_tables.py`; extend the
shared codec endpoint's kind dispatch without changing existing replies.
The constructor observer must describe all fields, never reuse encoded JSON.
MatchKind must use direct constructor matching, not MatchKind.names or
protoName: both encoder and decoder share that table, so a paired permutation
can preserve roundtrip while violating the wire contract.

Include independently authored native literal anchors for all three match
kinds, exact ordered asymmetric lists, optional default presence and the
bool flag. Python expectations must not be generated from those Lean
fixtures or production enums. Pass successful encoded values through public
protobuf load/dump using minimal Program wrappers without Index.build or
validation; this intentionally preserves semantically invalid examples.

Cover all Expr/KeyValue/Literal families through representative nested cases;
zero/max/overflow at every newly introduced bound; large decimal values;
absent/null/present-empty default_action; absent/false/true bool plus wrong
types; omitted/empty/null repeated fields; duplicate actions and unequal
ordered keys/entries/arguments. In particular, a present empty ActionCall is
not absence: its fields default to empty name and no arguments. In contrast,
Entry's non-optional action has no presence requirement in the actual decoder:
missing, null and present-empty all decode as an empty ActionCall. Include
literal anchors for all three accepted Entry defaults, and for Table's
absent/null default (none) versus present-empty default (some empty call).
Check actual implementation behavior for each case instead of guessing from
protobuf's more permissive acceptance language.

Pin field-error precedence from actual code: Key expression before match
kind before name; ActionCall name before args; Entry keys before action
before priority; Table name, keys, actions, default action, const flag,
const entries, size. Include competing errors, later array indices and nested
paths. Unknown-field policy is observed only as current behavior, not a
new compatibility promise. Strict duplicate-rejecting/type-sensitive protocol
checks remain mandatory.

Capture ordered unique input/raw stdout/stderr/exit status, source identities,
and independent expected answers before proof work. Refuse changed production
bytes and an existing capture path; verify source hashes again after capture.
Record the resulting exact nonzero inventory and immutable baseline commit,
then compare future tests to that inventory and historical source hashes.
Do not silently recapture changed behavior or count repeated observations as
independent inputs.

## Proofs, challenges and acceptance

After the test-only checkpoint, add all four universal laws and default axiom
audits. Construct a Table witness containing all match kinds, all KeyValue
constructors, optional default data, both empty and nonempty nested lists,
maximum bounds and intentionally invalid names/arity. Add negative examples
for every propagated overflow, including the optional default and nested
const-entry arguments. Prove absence imposes no condition. Native tests and
raw observers must not require proof witnesses to be semantically valid.

At minimum challenge actual compiling code in isolated worktrees:

1. Reverse only an encoder list: unchanged universal laws must reject it.
2. Swap MatchKind names on both sides: roundtrip may pass; independent raw
   answers and direct native anchors must reject it. Corrupt the matching
   Python expectations separately to show the native anchors stay independent.
3. Invert const_default_action consistently in encoder and decoder: distinguish
   proof survival from independent wire/default failures. Include omitted
   false and explicitly true controls, not only presence checks.
4. Change decoder order or a nested error index with a multi-error input.
   Roundtrip may survive; exact path/first-error baselines must catch it.
5. Challenge absent versus present-empty default handling. Report whether
   the actual law or a raw known answer rejects the change; never count a
   parser/setup/linter failure as a semantic detection.

Compile the faulty production module before crediting a proof rejection.
For surviving proofs, retain exact live raw mismatches, source-match them to
tracked fixtures, replay live, restore actual source and replay clean. A
pytest preflight failure is setup evidence, not execution of scoped tests;
if needed, use the existing independently inspected raw runner and record
which actual test bodies were invoked. Require nonempty verified inventories.

Run both complete Lean packages/default audits/native tests before any
consumer, then focused codec tests, required all-suite Lean agreement and
the full repository gate. Replay every prior retained corpus and baseline
unchanged, with historical source hashes pinned to their own commits. Obtain
independent read-only review, update status/decisions, and push small logical
commits. No new P4 construct, runtime execution claim, table-selection theorem
or whole-Program codec theorem follows from this slice.
