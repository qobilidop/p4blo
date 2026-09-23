# Next bounded bridge: observer-free guarded control call

2026-09-23. Read-only plan based on main's reviewed normal-return laws and
the uncommitted GuardedCallPrefix candidate at `21410b6`. No implementation,
build or mutation was performed for this plan. Recheck the prefix interface
after it is committed and independently cleared; its tests were deliberately
not reviewed as part of this planning task.

## Recommended smallest contract

Add a separately named `GuardedControlCall` module. Reuse the four existing
plain-root params/args and the actual body-bearing declaration family:

```text
body = CallInitializers.body ++ guardedForward.lower
program = CallEntry.WithBody.program body
index = CallEntry.WithBody.index body
```

Prove `body = GuardedCallPrefix.body []`, not an unchecked substitution of
the old empty-body index. The observer-free name means **no observer
assignments**: keep the existing H observer parameter as a pass-through
inout value. Removing that parameter would require a different call profile
and is unnecessary for this increment. The two initializers still run.

Let `s = CallInitializers.bodyStore hdr meta route`, and
`s' = ForwardPolicy.restore (GuardedForwardPolicy.policy
(ForwardPolicy.observe s))`. Use independent source-data projections for the
output hdr and metadata: top-level Record.get at the literal hdr/meta slots
is sufficient; do not use authored field accessors or command denotation.
Let `h'`, `m'` be those Data values. Define the exact result expression:

```text
result = { initial with frame :=
  PlainCallReturn.returnedFrame initial.frame h'.toValue m'.toValue observer }
```

Main theorem: for arbitrary source hdr/meta/route data, arbitrary operational
observer Value, caller Run and continuation K, under the current prefix's
explicit premises:

- `initial.index = index` (real body-bearing Index.build witness);
- BlockFrame initial.frame;
- actual caller reads source_hdr=hdr.toValue, source_meta=meta.toValue,
  source_route=route.toValue and hdr=observer;

prove actual `Steps` from `block RewriteBody args :: K` to exactly `K`, fault
none, Run=result. Derive `callBlock RewriteBody args` returning `.ok ()` and
that Run for K=[], using actual Steps/Finishes soundness. Do not assume K
terminates or execute it in the arbitrary-K theorem. No callback asserting
whole-call correctness and no second evaluator are needed.

## Composition and minimal bridge lemmas

1. Apply committed `GuardedCallPrefix.source_prefix` with empty suffix.
   Its endpoint is `statements [] :: blockReturn originalCaller ... :: K`;
   it is **not yet a completed call**.
2. Pop that empty statements item with exactly one actual step.
3. From returned FrameMatches, specialize at the two literal top-level Slots
   to obtain actual callee hdr/meta reads of h'/m'. Use the prefix's separate
   observer-preservation equation for the third read. The prefix's scope/type
   results need no new global declaration assumptions.
4. Apply PlainCallReturn.return_step/return_steps using the saved original
   caller frame and its original three binding witnesses. Preserve the
   current callee-after Run's non-frame fields. Rewrite that Run using the
   prefix's exact record equation; do not restore an arbitrary historical Run.
5. Compose traces and derive the public literal caller lookups, exact original
   scope/action state, ChangesOnlyVars relative to the original caller Run,
   and preservation of every caller name outside source_hdr/source_meta/hdr.

If helper lemmas are worthwhile, keep them small: FrameMatches projection
at the concrete hdr/meta slots and source-policy preservation of route,
scratch and both validity bits. The latter follow from independent Snapshot
record policy/restore definitions. There is no need for a new generic caller
store, expression language, evaluator, permissions interface or binder.

Important caller/callee distinction: source_route is unchanged because input
is not copied back. Caller scratch/unrelated, if present, stay at their old
values; callee scratch19 and unrelated165 do not escape. Caller hdr receives
the unchanged observer value, so it is unchanged observationally. Keep the
existing exact three-insert returnedFrame expression; proving redundant
same-value map insertion equal to the original internal HashMap is optional.
Literal lookup preservation suffices and avoids unnecessary map-extensionality
work. Unlike the intermediate call-entry prefix, the completed call restores
the original scope, so ChangesOnlyVars from the original Run is now valid.

## Constructive and independent acceptance

Supply an actual `WithBody.index_built body` witness, exact block lookup and
body identity. Retain the distinction between successful indexing and global
program validity. Instantiate the theorem with nonempty asymmetric caller
values and nontrivial packet/emitter/entries/register/visits, all header
validity pairs, route hit/miss, TTL 0/1/2/255 and both old drop values. Include
caller scratch/unrelated and a nonzero H/Result observer so leakage/reset is
visible. Arbitrary-source theorem must not collapse to those finite fixtures.

Expected application results should be independent named constructor values
or ordinary Boolean/Nat policy calculations, not source accessors or the
theorem's final frame expression. Retain old drop, header validity and invalid
stored fields in the rejection branches. No packet is emitted here.

Native step counts are the separately checked prefix counts plus **two**:
one empty-list pop and one return. The currently reported prefix branch
counts 11/14/17/20/23/31 suggest final 13/16/19/22/25/33; confirm independently
against the committed lowering rather than deriving expected counts from
the executor. At each bound assert exact restored caller and pending K.
One fewer step must leave blockReturn pending; a further pending write/fault
must be observable if K is executed. Include K=[] and nonempty/faulting K.
Do not call pending-continuation failure a failure of the successful call.

Python tests should call actual stmt.call_block to **normal completion**.
A delegating run_block wrapper may retain the real callee reference and freeze
its state after the actual body returns, but must not throw a sentinel to
stop execution: Python call_block's finally would still copy back, turning
that technique into a different fault-boundary experiment. Compare exact
caller results, retained callee, complete detached Index/scopes/action layers
and all shared contents. Use the reviewed strict JSON and recursive mutable
Header/Struct object/list isolation checks across all three copied values.
Actual member writes after return should cover Ethernet, IPv4, Metadata and
H.Result, and leave the retained callee unchanged. Immutable leaves may share.

Record copyback order with a spy delegating to the real writer and filtering
by `env is original_caller`; normal body writes occur in the distinct callee.
Final value equality alone cannot detect reversed distinct root writes.
An independent exact syntax anchor must compare the selected full block,
params/args/types, two initializing assignments and the guarded body, requiring
three top-level statements and **no observer suffix**. Construct this expected
Python block explicitly from the tracked declaration/initializer helpers and
the separately checked guarded command export. Do not silently take a prefix
of the candidate's own body to manufacture its expected syntax. A full packet
wrapper, parser, or the existing seventeen observer assignments is not needed.

## Adversarial acceptance and scope

Reuse earlier retained fault profiles but test the new composition boundary:

- Wrong index/body or omitting the empty-list pop must reject a genuine
  correspondence obligation or exact queue boundary, not just fail to parse.
- Wrong return target, skipped restoration/copyback, input-route copy or
  resetting current shared state must fail proof or independent full-return
  answers; distinguish proof rejection from executed runtime mismatches.
- Paired authored/policy changes and same-width wrong names can preserve
  correspondence. Retain independent source/syntax/closed policy anchors.
- Actual Python selective copy aliases, reversed copyback, shared state
  mutation and skipped observer pass-through must be rejected after complete
  actual call_block. In particular retain the three aliases missed by the
  first normal-return observer (Metadata, H.Result and IPv4).
- Wrong scratch/unrelated initialization should be observed inside the
  retained callee even though caller locals correctly remain unchanged.

These boundary inputs must be reconstructible from tracked fixtures. Do not
invent a packet-DRT replay claim for a direct call boundary. If a campaign
also exercises an existing packet profile, retain and live/restored replay
its actual complete packet-program input separately.

This would be a meaningful **whole normal control-call theorem for one exact
already-parsed, route-selected program**, not merely a body theorem. It would
still not prove caller construction/global validation, parsing, route lookup,
checksum repair, architecture drop/forward fate, observer encoding, arbitrary
calls/actions/lvalues, pending-fault unwind or full packet execution.

Confidence: high in the composition after the reviewed prefix interface is
committed; medium in keeping its exact four-argument fixture as the long-term
API. Revisit abstraction only for a second distinct call client. Main expected
proof friction is dependent Store projection/record rewriting, not a missing
semantic law. Keep the theorem and focused constructive/test increment small;
do not expand ownership into the unfinished prefix or return implementation.
