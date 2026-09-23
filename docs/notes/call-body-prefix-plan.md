# Actual call entry through the guarded body prefix

2026-09-23. Read-only design investigation. Inspected committed main
`5871da8` including flat-prefix proof `45fe743`, and the uncommitted, separately
reviewed `p4blo-plain-call-entry` candidate based on `ad746c5`. No production
source edits, builds or proof probes were performed. Candidate interface names
below must be checked against their eventual committed integration before
implementation. This plan is not a claim that the composition already checks.

## Smallest useful result

Prove a finite prefix of the **actual** execution machine, starting at the
four-argument `RewriteBody` call and stopping before its observer and return.
The selected block must contain the real flat body:

```text
scratch := bits8(19)
unrelated := bits8(165)
guardedForward.lower
observerSuffix
```

The endpoint is exactly:

```text
statements observerSuffix ::
blockReturn originalCaller actualBlock.params PlainCallEntry.args :: K
```

Both endpoints have no pending fault. `K` and `observerSuffix` are arbitrary
and remain unexecuted, even if either would fail. Do not add a synthetic
conditional or turn the flat list into separately queued command lists.
Do not conclude `execute`/`call_block` completion from this finite prefix:
the suffix and copyback are still pending.

The independent initial source state is `entryStore hdr meta route` with
scratch zero. After the actual local assignments, define a constructor-based
`bodyStore hdr meta route` with the same arbitrary three aggregate values and
scratch **19**. The final modeled store is exactly:

```text
ForwardPolicy.restore
  (GuardedForwardPolicy.policy (ForwardPolicy.observe (bodyStore hdr meta route)))
```

Observer is a separately preserved arbitrary IR Value; its typing is not
inferred from binding it to an H parameter. Unrelated is an extra declared
bit8 local: zero after entry, **165** before and after the authored body.

The guarded policy's "invalid input changes only drop" refers to the modeled
bodyStore. It must not be described as the entire call prefix changing only
drop: this prefix also installs a callee frame and initializes scratch and
unrelated. Invalid-header stored fields and validity bits are still preserved.

## Close the actual block identity gap first

`CallEntry.index` currently comes from an actual `Index.build`, but its only
block has an empty body. Its scopes also retain that empty block. Merely
setting the work item to a different `runBlock`, or saying the declarations
agree, would not prove actual dispatch of the body-bearing call.

Recommended small prerequisite: parameterize the selected declaration fixture
by the **entire body list**, keeping the existing empty-body names as aliases
or their original compatible specializations:

```text
blockWithBody body   = { existing declaration block with body := body }
programWithBody body = { existing declaration program with
                        blocks := [blockWithBody body] }
indexWithBody body   = (Index.build (programWithBody body)).toOption.getD default
scopeWithBody body   = (indexWithBody body).scopes["RewriteBody"]?.getD default
```

Preserve the existing declaration-program name unless there is a separate
reason to rename it: a different name contributes no proof strength and would
break old known answers. A new module may call the family `CallBodyDeclarations`
without claiming that the original empty program had this body.

Required kernel equations, for arbitrary body:

1. Actual `Index.build` succeeds, actual block lookup returns exactly
   `blockWithBody body`, and actual scope lookup returns `scopeWithBody body`.
2. The built scope's block equals that same body-bearing block. Params,
   locals, scope vars/action maps and nominal declarations retain their exact
   prior values; the Index's program/blocks/scopes are **not** unchanged.
3. Actual nominal agreement, root Modes.Agrees, production zero-fuel bound
   and extra zeroability hold for this built Index/scope. Obtain actual
   Frame.forBlock initialization from `Layout.initialize` again.

`Index.build`/its private buildScope inspect declaration names/parameters/
locals/actions/tables/states, not statement bodies; the body is retained in
the stored Block and scope.block. Thus symbolic-body equations should reduce
without inspecting the suffix. This is a source inspection, not a checked
feasibility lemma. Avoid requiring a decidable test over arbitrary statements.

Prefer generalizing the existing declarations/proofs once and deriving the
empty specializations, rather than copying the entire CallEntry proof.
If that creates excessive compatibility churn, a narrow body-bearing sibling
family with proved unchanged type maps and declaration maps is acceptable:
reuse existing root/observer zero laws after transporting their real inputs,
and reuse `Layout.initialize`. Do not manually construct an Index and leave
`Index.build` as an assumption in the application result.

The fixed-arity `PlainCallEntry.dispatch_entry`/`entry_steps` already accept an
arbitrary looked-up block with the exact params, so they require no change.
Factor the existing source-entry frame-value argument into a small
`boundFrame_matches` lemma or a body-parametric `source_entry_with_body`;
retain the current `source_entry` as the empty instance. A low-level lemma
may consume a real initializer equation/zero facts, but the final application
theorem must discharge them with the actual-built body witness, not an
unconstrained whole-call correctness callback.

## Composition and exact obligations

Let `body suffix` be the two literal assignments followed by
`guardedForward.lower ++ suffix`. The final theorem takes an arbitrary caller
Run, arbitrary hdr/meta/route Data, observer Value, suffix and continuation.
Its entry premises are:

- `run.index = indexWithBody (body suffix)`;
- caller BlockFrame (retaining the reviewed bounded call scope);
- the four actual caller Frame.read? equations for source_hdr, source_meta,
  source_route and hdr (the observer actual argument).

Compose these existing mechanisms with small exact lemmas:

1. **Call entry.** Apply the body-parametric concrete entry witness. Preserve
   the exact original caller frame inside blockReturn, not a later frame.
2. **Control expansion.** One `Steps.next` using actual dispatch `.runBlock`
   and actual `block.kind = .control` produces `.statements (body suffix)`.
   This step changes no Run field. It is not the parser `.states` arm.
3. **Scratch assignment.** Use the existing field command
   `Cmd.assign FieldCommandExamples.scratch bits[8,19]` with `steps_prefix`;
   its suffix is the unrelated assignment followed by guarded body/suffix.
   Prove its exact one-statement lowering by rfl, and its source result equals
   constructor-based bodyStore. The singleton command consumes the actual
   list-head/assignment transitions but leaves the flat residual list.
4. **Unrelated assignment.** Keep this extra outside the modeled root layout.
   Reduce actual `.assign (.var "unrelated") (.literal (.bits 8 165))` using
   `ScalarStatements.writeVar_block`, the real zero lookup and BlockFrame.
   Take its two actual successful steps. Prove exact insertion, preserve
   FrameMatches bodyStore by the four root names being different from
   unrelated, and preserve observer. Its actual local bit8 declaration gives
   a separate scoped writable-path/type witness; do not infer permission
   from the runtime map insertion, whose implementation checks existence only.
5. **Authored body.** Apply concrete `guardedForward.steps_prefix` with the
   actual remaining suffix and return-plus-K continuation. Transport modes,
   frame, Index and BlockFrame through the initializer transitions.
6. **Policy and preservation.** Rewrite exact final source values with
   `GuardedForwardPolicy.source_policy`. Show observer and unrelated are absent
   from `guardedForward.targets`, then use PreservesOutside. The modeled
   scratch19 is part of the full policy snapshot, so no extra assumption is
   needed that the policy leaves it unchanged.

State a full final Run equality of the form
`final = { initialCallerRun with frame := finalCalleeFrame }` plus exact
callee scope/action-layer/value facts. **Do not** use ChangesOnlyVars from
caller to final: call entry changes scope/frame identity, not just vars.
ChangesOnlyVars applies only from the installed callee through its local/body
updates. Compose the exact entry equality with these narrower guarantees.
Packet/cursor, emitter, entries, externs, visits and Index then remain exactly
those of the arbitrary caller Run; all caller-frame contents remain captured
verbatim in the pending return item. No independently rebuilt HashMap equality
is needed for semantic contents.

Provide the `.block "RewriteBody" args :: K` theorem first. The preceding
`.statement (.callBlock ...)` administrative transition is a cheap explicit
corollary if useful; do not silently conflate these start configurations.

## Honest connection to the tracked wrapper

Instantiate suffix with the actual selected wrapper's observation statements.
Export the complete selected block/declaration family and compare against
`guarded_program(..., guardedForward.lower)` in the tracked Python tests.
Unlike the earlier entry-only test, compare **the entire selected body**;
project away neither initializers nor suffix. In particular the validity
observer uses the current test-only identity mux, while the authored guards
use member-shaped reads. Keep both spellings exact.

An executable check may identify the suffix by proving the first two actual
assignments and guarded lower list form an exact prefix, then compare every
remaining statement. It must reject extra/missing/reordered statements and
cannot silently substitute a convenient observer. This establishes selected
block syntax identity in tests, not a kernel wire-codec/full-program theorem.
The constructed program still contains only selected declarations/block;
caller initialization, its surrounding parser/deparser and architecture remain
outside the proof. Generalize to the full wrapper Index only in a later slice.

## Independent runtime and adversarial acceptance

Native prefix tests step actual Execution.step with literal independently
derived branch counts, not a new executor/fuel semantics. Include every
validity pair, both hits, TTL 0/1/2/255 and both prior drop values. Check entry
scratch/unrelated 0/0, post-initializer 19/165, policy full roots, observer
asymmetric nonzero bytes, exact captured caller and complete queue. Preserve
all non-frame sentinels, including whole Index/program/maps, entry/default
contents and extern cells. Test empty and nonempty suffixes, nonempty K, and
a faulting suffix/continuation. The suffix should visibly overwrite scratch
or observer if advanced: a premature suffix cannot be observationally inert.

Hand-derived candidate counts from the `.block` start (not executed or checked
in this investigation) are 11 for Ethernet-invalid, 14 for Ethernet-valid/
IPv4-invalid, 17 for both valid/miss, 20 for both valid/hit/TTL0, 23 for both
valid/hit/TTL1 and 31 for both valid/hit/TTL2-or-255. Entry/control expansion
contribute two steps; the two initializers contribute four; each taken
conditional requires its real branch-list administrative step. Confirm these
literal counts against actual step during implementation; do not silently
replace them with a computed cost from the command being tested. An empty
suffix still ends with `.statements []` pending, not with return at the head.

Python can run the actual call_block/run_block/execute path and intercept
`execute_one` immediately before the first uniquely identified observer
statement. Snapshot before delegating that statement, then stop with a test
sentinel. **call_block has a finally copy_back**, so raising a sentinel still
runs copyback afterward. Assert the frozen caller/shared contents inside the
snapshot callback before unwinding, never treat post-exception caller state
as the prefix state. Do not disable or replace the production binder/body
executor to manufacture a prefix. For an empty suffix, a separately labeled
snapshot at copy_back entry can observe the pre-return boundary. No Python
queue-equivalence theorem follows from these test hooks.

Use the reviewed call-entry snapshot discipline: detached deep copies and
immutable serializations, not aliases/object identity; strict JSON bool/int
and full key/case-set validation. Compare both runtimes independently to
separately written complete prefix answers. Hooks need exact one-hit evidence.

Required challenges in isolated restored worktrees:

- skip either initializer; write 19 to unrelated/165 to scratch; reorder a
  dependent initializer/body; end before the wrong assignment;
- use an empty-body lookup index with a body-bearing runBlock work item;
- consume the first observer statement or the pending return/K; discard
  blockReturn; capture the installed callee instead of original caller;
- mutate actual runBlock dispatch to omit/reorder the flat list;
- a valid compiled wrapper-prefix/export mutation caught by independent
  exact block identity or snapshot answers, despite generic proofs;
- a real Python local-write or call-state fault observed at the prefix.

Classify proof rejection, syntax/known-answer rejection and genuine runtime
divergence separately. If a fault also produces packet-level DRT disagreement,
save the complete input before assertions, replay live, then restored. Prefix
snapshots themselves are not packet DRT bundles: retain their complete tracked
input/hook/frozen-answer recipe and do not claim the packet replay checks an
internal queue boundary. No mocked Lean. Standard default axiom audits and
both Lean/required real-Lean/focused gates plus independent review apply.

## Risk and delivery sequence

Confidence high: actual fixed-arity entry already supplies the right pending
queue; runBlock expansion is a direct equation; committed steps_prefix has
exactly the required flat suffix; scratch/extra writes are ordinary reviewed
runtime operations. Confidence medium: cheapest reuse of the built-index/
initialization family without unfolding huge concrete declarations. Try
symbolic body parameterization first; if reduction becomes expensive, prove
small type/declaration-map transport lemmas instead of duplicating the binder.
Revisit the fixed family when a second real call signature is needed.

Recommended two independently reviewed checkpoints: (1) actual-built
body-parametric declarations/entry with old empty API preserved and full-body
identity tests; (2) initializer/control/body-prefix composition, exact policy
boundary and adversarial native/Python snapshots. Neither needs new syntax,
source semantics, a runtime fuel bound, validity writes, parser, observer
correctness, copyback correctness, exception-unwinding correctness, route/
checksum handling, packet fate or universal Python equivalence.
