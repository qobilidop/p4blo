# Next bounded codec: total statement decoding

2026-09-23. Planning baseline `fddab8e1d4ab01fe051ffb5f9b7a1ab46a079549`.
Read-only production inspection plus an isolated, unregistered Lean probe;
no production decoder, encoder, tests, audit registration or runtime changed.
Implementation awaits root review and an explicit implementation contract.

## Recommended slice

Make the **existing** `Stmt.decode` total by well-founded descent on finite
`Lean.Json` values. Preserve its public signature, all fourteen constructors,
recognized-case order, accepted/default behavior and exact diagnostic order.
Then prove its old-body unfolding law and universal representable statement
roundtrip through actual `Stmt.toJson`/`Stmt.decode`. No parallel recursive
decoder, fuel parameter, semantic validator or new production protocol.

This is still the third recursive codec slice, after Expr and LValue, but the
old planning notes' remaining barriers must be read against current code:

| Actual current dependency | Work needed in this slice |
|---|---|
| Expr.decode, LValue.decode | Already total, with checked old-body unfolding and roundtrip laws; reuse unchanged |
| Arg.decode | Already nonrecursive and proved; reuse unchanged |
| oneofBounded, msgFieldBounded | Existing generic erasure/descent laws; reuse unchanged |
| Stmt.conditional then/otherwise | The only recursive Stmt calls; need bounded repeated-field traversal |
| callAction/callBlock/callExtern args | Ordinary arrays of already-total Arg; no recursive bound needed |
| apply.hit/callExtern.result | Existing optional LValue helper; no recursive bound needed |
| State/Action/Block/Program decoders | Ordinary callers of Stmt; no recursion refactor required and no new roundtrip claim |

There is **no mutual JSON-decoder recursion**. Source Stmt's generated
induction principle does have both Stmt and List Stmt motives; that is a
nested-source induction concern, not a reason to introduce mutually recursive
Expr/LValue/Stmt decoders.

Confidence: high in the missing helper/descent feasibility after the checked
probe below; medium-high in the fourteen-constructor roundtrip proof cost.
Revisit only if actual statement induction/object normalization proves costly;
first finish helper erasure and actual unfolding as a reviewable sub-checkpoint,
never silently replace the universal roundtrip with examples.

## Checked missing helper, not an assumed library theorem

`ir/StmtCodecProbe.lean` imports the actual current CodecLaws/Json modules.
Its six named theorem roots compile with only standard axioms or subsets:

1. `mapIdxM_map`: indexed Except traversal commutes with a pure input map.
   A short induction over actual `List.mapIdxM.go`, generalized over its
   accumulator, preserves the accumulator-derived indices and first error.
2. `array_attach_erasure`: converting the result of `xs.attach.mapIdxM` to
   a list equals the actual `xs.mapIdxM` traversal with proofs erased, for
   arbitrary callbacks/results/errors. Uses pinned `Array.toList_mapIdxM`
   and `Array.attach_map_subtype_val`, not an invented member/index equality.
3. `array_mem_lt`: a genuine array member has smaller structural size than
   `Json.arr xs`, using `Array.sizeOf_lt_of_mem` and the Json constructor.
4. `arrayBounded_erasure`: the candidate bound-carrying array helper equals
   actual `Decode.array` on every input with the enclosing bound, including
   non-array errors and all callback errors.
5. `listFieldBounded_erasure`: the candidate repeated-field helper equals
   actual `Decode.listField`, including non-object payloads, missing/null
   fields, non-array fields and first-error traversal.
6. `array_encoded_roundtrip`: actual `Decode.array` decodes a list's encoded
   array under per-member, every-path decoder laws. This generic helper is
   discharged by the real Arg law or statement induction in the final theorem;
   it is not a whole-statement correctness callback premise for clients.

The array helper uses genuine membership supplied by `xs.attach`; do not use
`mapFinIdxM`'s separately supplied element as though it were definitionally
`xs[i]`. No new pinned TreeMap-internals lemma is needed: current
`Decode.get_some_lt` already supplies the actual field bound. The chain is
`child < array field < conditional payload < outer statement`. Arrays have
no synthesized message fallback: absent/null repeated fields return `[]`
without invoking the decoder. The old synthetic `{}` behavior of condition
and other message fields remains in the existing ordinary helpers.

Suggested production placement: add the array membership bound to the small
`JsonBounds` module, the two bounded helpers and their erasure facts beside
the existing Decode helpers, and narrowly replace only Stmt's oneof call and
two conditional listField calls. All other statement callbacks keep ordinary
helpers and their original sequencing. The current public `Decode.array` and
`listField` remain unchanged as proof-erased references for other callers.

The probe also establishes a kernel-checked missing-list example. Four
`#eval` observations use the **unchanged partial production Stmt decoder**:
first malformed then element reports `[0]`, a valid first element followed
by a malformed second reports `[1]` before a bad otherwise field, a bad
condition wins over both malformed arrays, and null branches become empty.
Those evaluations are concrete compatibility observations, not kernel
theorems about old partial Stmt or a new total statement implementation.

## Implementation and proof obligations

Keep `Stmt.decode path j` as the sole production entry point. As in Expr,
define its recursive callback with an explicit `sizeOf child < sizeOf j`
argument, use `oneofBounded`, and finish with `termination_by sizeOf j`.
Conditional still decodes condition first, then the whole then list, then
the otherwise list. Every other callback retains its old field order.

Prove `Stmt.decode_unfold` equals the **original recurrence body**, written
with ordinary `oneof`, `msgField`, `listField` and `optField`, by the actual
generated equation and generic erasure facts. This is not equality against
the former opaque partial constant. Capture old native transcripts before
the production refactor and compare exact stdout/stderr/status afterward.
Together these give a reviewed logical recurrence and finite executable
compatibility evidence, not a universal raw-text equivalence theorem.

Define only wire representability, recursively:

| Statement | Required predicates |
|---|---|
| assign | target LValue, value Expr |
| conditional | condition Expr; every statement in both branch lists |
| apply | optional hit LValue when present |
| callAction, callBlock | every Arg |
| callExtern | every Arg; optional result LValue when present |
| setValid, setInvalid, extract | target/header LValue |
| push, pop | stack LValue and count `< 2^32` |
| advance, verify, emit | contained Expr |

All names/error strings may be empty/unresolved; all list lengths are finite
but mathematically unbounded. Embedded predicates retain zero widths, huge
decimal values, invalid operators' operand types and reversed slices. No
positive count, stack size, block kind, direction, name resolution, permission,
call arity or whole-program validity premise belongs here. Uint32 overflow
inside any nested expression or push/pop must remain an explicit negative.

Prove `∀ path statement, StmtRepresentable statement →
Stmt.decode path statement.toJson = .ok statement`. Use generated nested
Stmt/List induction (the probe prints its exact signature), the actual list
roundtrip helper, existing Expr/LValue/Arg laws, and small optional-field
normalization lemmas. Empty strings/lists, optional none/some, and count zero
need distinct omission cases. Default-audit actual Stmt.decode, unfolding,
new helper erasure roots, universal statement roundtrip and an advertised
nontrivial nested constructive witness. No native decision escape.

## Independent baseline and accepted-input matrix

Before changing Stmt.decode, extend only the registered **test-only**
`codec-leaves` endpoint/`Tests.CodecLaws` with kind `stmt`, an explicit
constructor-matching recursive descriptor, and native controls. Existing
descriptor functions for Expr/LValue/Arg already avoid production operator
name tables. Reuse them; do not derive statement tags or branch order from
Stmt.toJson. Add `stmt` to the shared Python CodecKind type and a dedicated
`tests/test_codec_stmt.py` using `assert_leaf`, `same_json`, shared
`lean_binary`, and `test_lean_agrees` discovery. No new executable/default
target should be needed: current endpoint and CodecProofAudit are defaults.

Hand-build canonical wires and expected constructor descriptors for every
statement, optional none/some, empty/nonempty argument lists, count 0/max,
unequal nested branches of different lengths, several distinct array elements,
empty/unicode names, and semantically invalid but representable combinations.
Use a nested conditional in both branches, not only a linear chain. Send
actual Lean output to Python protobuf Stmt parsing and the public Program
JSON adapter with a minimal body wrapper, without invoking validation.
Assert independent decoded constructors, canonical field/default presence,
array order and strict JSON types, not merely encode/decode agreement.

Malformed and normalization anchors must include:

- Non-object statement/payload; no recognized kind; unknown-only object;
  null selected kind; two recognized kinds in reversed textual order. The
  more-than-one diagnostic uses the fixed fourteen-case list, not map order,
  and is raised before decoding either malformed payload.
- Conditional missing/null condition, then, otherwise; valid condition with
  both lists absent/null/empty; present non-array branch; null element versus
  null field; malformed element zero versus later elements and nested paths.
- Multiple simultaneous errors: condition before then before otherwise;
  earlier then index before later then index; any then failure before an
  otherwise error. Keep exact bracket and dot path spelling.
- Assign target before value; apply table before optional hit; call action or
  block string before args; extern instance, method, args in order, then
  optional result; stack before count; verify condition before error string.
- Optional absent/null versus present `{}`; absent/null numeric count versus
  malformed count; max/overflow, numeric string normalization and malformed
  nested Expr/LValue/Arg. Existing unknown-field acceptance is frozen, not
  generalized into a compatibility policy.

Current shared subprocess observation already saves timeout/launch/crash/
empty/malformed/invalid-UTF8 results before failing; do not reopen the old
already-fixed timeout-retention task. Reuse its strict, nonempty raw-artifact
replay checks and tracked reconstruction fixtures. Capture the complete
pre-change selected request set and exact native transcripts, source-match
every row, and retain post-change comparison evidence.

## Adversarial acceptance after implementation authorization

1. A one-sided encoder then/otherwise swap or element reversal must compile
   actual Json, then reject the appropriate unchanged roundtrip proof. Count
   proof rejection separately from any runtime test; termination elaboration
   failure alone is not a semantic mutant detection.
2. Pair the wrong encoder/decoder branch mapping, including the deliberately
   changed unfolding statement. Roundtrip may still pass. Independent unequal
   branch descriptors and wire/constructor anchors must fail; retain exact raw
   request/expected/actual, replay live, restore, and replay successfully.
3. Change actual repeated-field traversal order or index numbering. Multi-error
   fixtures must detect first-error/path differences independently of ordinary
   successful roundtrip. Perturb missing/null to error separately; exact
   normalization controls must reject it.
4. Pair compatible statement tag mappings, e.g. set_valid/set_invalid or
   call_action/call_block. Independent constructor tags must expose the same
   wrong-model trap found in shared Expr operator tables. Keep a native anchor
   as well as Python checks, and challenge the observer if the fault survives.

Restore each compiling fault before the next. Preserve raw codec artifacts,
not a fictional packet DRT bundle for invalid raw statement messages. Freeze
before independent review; run both Lean packages/default audits/native tests,
focused old+new codec suites, required real-Lean discovery, and the ordinary
full gate. Build first, then run binary consumers; never rebuild concurrently.
No Docker rebuild or global cleanup is authorized by this plan.

## Reproduce the planning probe and its limits

Fresh worktree-owned caches were used. With the IR package as the scoped
working directory (no persistent shell directory assumptions), run:

```text
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.CodecLaws
nix develop -c lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true /Users/qobilidop/my/work/p4blo-stmt-codec-plan/ir/StmtCodecProbe.lean
```

Observed exits: baseline dependency build **0** (five jobs); final complete
probe **0**. Logs: `/tmp/p4blo-stmt-plan-baseline.log` and
`/tmp/p4blo-stmt-plan-probe-final.log` (the preceding complete probe3 also
passed). First attempts exposed only an unexpanded
Except pure and a match requiring simplification before rewrite; those
nonzero attempts are not evidence. Final six audit outputs contain only
propext/Quot.sound for map traversal facts, and standard three axioms for
descent/erasure/canonical-array facts. The probe is not a package target.

A reviewer can run the same absolute probe via `lake env lean` in another
checkout's IR package with already-built identical Json/CodecLaws dependencies;
this does not rebuild or replace that checkout's native executables. Root
owns the independent review and eventual plan/probe commit. No full Lean,
Python, schema, external-oracle or production semantic gate is claimed for
this planning-only checkpoint.

Trust/exclusions remain unchanged: these are finite in-memory Lean.Json
laws, not text parsing, duplicate textual keys, protobuf binary conversion,
general ProtoJSON acceptance, safe unknown semantic fields, version policy,
runtime stack/memory budgets, whole Program roundtrip/validity, statement
execution, or universal Python equivalence. Logical totality is not a physical
resource guarantee. The next implementation must preserve errors/defaults
even on syntax that the semantic validator would reject.
