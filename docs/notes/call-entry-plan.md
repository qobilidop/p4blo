# Next bounded bridge: actual plain-root subcontrol entry

2026-09-23. Read-only investigation against main's current field wrapper and
the frozen initialization worktree at `6c99835`. No production edit or build.

## Recommendation: separate entry from body-prefix composition

The next independently reviewable checkpoint should prove **actual entry of
the existing four-parameter RewriteBody call**, stopping with its `runBlock`
and `blockReturn` work items still pending. Do not include caller setup,
authored body, observer execution or copyback in this first implementation.
It removes a concrete assumption and is small enough to validate thoroughly.

Start with the exact actual dispatch equation, for arbitrary caller Run and
arbitrary source values, not only the fixed `store 64 true true true` example.
Use the actual `Execution.dispatch (.block name args)` and Frame.forBlock.
No competing executable binder, generalized call AST or whole-correctness
callback is needed. A closed four-insertion expression describing the final
frame is a theorem result, not another runtime interpreter.

## Actual code and exact proposed premises

`ir/P4bloIR/Exec.lean` does these operations in this order:

1. Lookup the actual block in `run.index.blocks` and check exact argument count.
2. Run actual Frame.forBlock against the selected block and index.
3. Iterate `block.params.zip args`, obtaining each argument in the **caller
   Run**, and insert its value into the local callee-frame accumulator.
4. Capture the caller frame, then install the completed callee frame.
5. Return `[.runBlock block, .blockReturn caller block.params args]`.

The callee is not installed during the binding loop. `argumentValue` zeroes
out parameters without evaluating their argument; other directions read the
expression or lvalue. This matters even though the first real wrapper has
no out parameter. Preserve exact argument-count checking instead of relying
on zip truncation.

The bounded wrapper's actual parameter/argument mapping is:

| Callee declaration | Actual argument | Entry value |
|---|---|---|
| hdr : Headers, inout | lvalue source_hdr | caller stored Headers |
| meta : Metadata, inout | lvalue source_meta | caller stored Metadata |
| route : Route, in | expression source_route | caller stored Route |
| observer : H, inout | lvalue hdr | caller stored observer container |

Writable caller roots are distinct. Retain an explicit BlockFrame premise
on the caller for this bounded API, although the raw readVar equations below
can use action-first lookup without it. Fresh initialization supplies the
callee's absent action and actionVars. This does not establish action-call
entry or general action-overlay compatibility.

For the first exact dispatch lemma, use explicit hypotheses:

- `run.index.blocks[name]? = some block`;
- the exact four declarations and four plain arguments above;
- the actual initializer equation `Frame.forBlock run.index block = .ok zero`;
- the four actual caller `Frame.read?` lookups returning the intended values;
- the caller action-free boundary where claiming the bounded wrapper contract.

The initializer equation is a legitimate lower-level composition premise,
not the final user theorem's assumed whole-call correctness. Its public
application corollary must obtain it from Layout.initialize/Frame's actual
initialization theorem, discharging all declarations and extras explicitly.
Exact value typing/declarations are separate from operational reading: actual
argumentValue does not check the read value against the parameter's type.

Define the theorem's result frame as `zero` with vars containing the four
ordered inserts under `hdr`, `meta`, `route`, `observer`. Prove:

```text
dispatch (.block name args) run
  = (ok [runBlock block, blockReturn run.frame block.params args],
     {run with frame := boundFrame})
```

This is exact whole-Run equality outside the newly installed frame, not just
packet equality. Packet, cursor, emitter, entries, externs, visits and Index
are preserved. The return item captures the original caller frame exactly.
Lift it to one actual successful `Execution.Steps` transition with an arbitrary
continuation K and no pending fault. Optionally cover the preceding
`.statement (.callBlock ...)` administrative step; this adds no new semantics.
Do not execute the return item.

## What must be instantiated honestly

The existing InitialFrameTests real Index.build witness is for the small
`FieldCommandExamples.program`, whose only block is `fields`. It is not the
Python wrapper's `RewriteBody`, and its extraScope observer `bit<65>` is not
the actual wrapper's `H`. Reusing that witness under renamed prose would be
incorrect.

For the useful call fixture, mirror the actual RewriteBody declarations and
nominal H/Result observer layout, and prove actual Index.build succeeds on
that concrete declaration program. Its modeled roots remain hdr/meta/route/
scratch; observer H and unrelated bit<8> are explicitly initialized extras.
After binding, observer has the caller's entire H value, not its initial zero.
Scratch and unrelated are still zero at the entry boundary.

To keep the first commit bounded, a call-declaration fixture with these exact
declarations is sufficient, but label it as such. Add a checked comparison
against the tracked Python wrapper's selected block/types/arguments (or later
use its exported wire with independent expected declarations). Do not claim
actual Python full-program identity or caller-initializer execution merely
because the declarations agree. Full Index.build on the complete wrapper can
be a subsequent constructive witness if its size makes this first one costly.

Independent source entry construction should take arbitrary Headers,
Metadata and Route data, and append **zero scratch**. The existing fixture
`store` instead supplies scratch 19; it becomes applicable only after the
actual local initializer assignment executes. Preserve exact observer value,
zero unrelated local, all stored fields and both header validities, including
invalid headers. State exact callee lookups, scope and BlockFrame; avoid
assuming equality to a separately built HashMap with another insertion order.

## Proof feasibility and small probe

The fixed four-element binding loop avoids a new general list specification.
Unfold dispatch, rewrite block lookup/count and actual initialization, then
reduce its `forIn` over four pairs. Plain root reads preserve the entire Run,
so every pair still reads the same original caller; only the local callee
accumulator changes. Finish by the actual setFrame definition.

A pinned stdin probe against frozen existing libraries successfully checked
three universal argumentValue lemmas, all with exactly
`[propext, Classical.choice, Quot.sound]`:

```lean
-- Given run.frame.read? name = some value:
change (readVar name).run run = _
simp [readVar, P4bloIR.ScalarTyping.run_bind, h]
-- This proves both in + expr(var name) and inout + lvalue(var name).

-- For arbitrary arg, given Value.zero ty run.index = .ok value:
change (P4bloIR.liftExcept (Value.zero ty run.index)).run run = _
rw [h]
rfl
-- This proves out ignores the actual argument entirely.
```

The actual statements quantify arbitrary Run, names, type and Value; no
source evaluator is assumed. The final probe exited 0 and produced no
artifact in an implementation tree. Earlier exploratory invocations failed
on an unreduced Direction BEq guard and then redundant trailing rfl tactics;
those failures are not proof evidence. No four-binding dispatch or list-suffix
composition theorem was attempted or claimed by this feasibility probe.

If a general reusable binder lemma proves cheaper, keep it narrowly about
the actual `forIn` loop and per-argument read/zero facts. Do not generalize to
side-effecting argument expressions, member/index lvalues, actions or copyback
in this checkpoint.

## Follow-up: actual body prefix, without reshaping the wrapper

After entry, `.runBlock` for a control produces one work item containing the
**whole flat body**: scratch := 19; unrelated := 165; authored command;
observer suffix. Existing Cmd.steps instead starts with a work item containing
only cmd.lower and keeps a separately queued continuation. These are related,
but are not definitionally the same machine state. Do not silently split the
actual wrapper, insert a conditional wrapper, or assume that relation.

Add a narrowly strengthened generic prefix lemma (or a checked machine
statement-list concatenation lemma):

```text
Steps
  {work := statements (cmd.lower ++ suffix) :: K, run := start}
  {work := statements suffix :: K, run := final}
```

It should retain the existing exact source/Run/target conclusions and leaf
assumptions. A proof-only strengthening of the existing command induction is
plausible: done leaves the suffix without stepping, assignment carries it
through the tail, and a branch runs its selected branch with the remaining
command-plus-suffix queued beneath it. Derive the former theorem by choosing
an empty suffix and consuming the administrative empty-statements step.
This does not require another AST, denotation, lowerer or interpreter.

Then execute the two actual local assignments using checked writeVar facts,
establish FrameMatches with scratch 19, and apply the existing body theorem
through the strengthened prefix. Endpoint work is exactly:

```text
statements observerSuffix :: blockReturn originalCaller params args :: K
```

Show all non-frame Run components unchanged; preserve observer and unrelated
callee bindings through the typed body using target bounds. Lift the existing
independent ForwardPolicy (or separately reviewed guarded policy) only for
the authored command selected. Observer serialization, blockReturn, caller
copyback, failure unwinding and eventual packet fate remain unexecuted.

## Acceptance and independent faults

- Native/kernel anchors with arbitrary source theorem plus asymmetric
  concrete hdr/meta/route/observer values and both header validities; scratch
  and unrelated zero at entry, later 19/165 only after real assignments.
- Check caller frame captured exactly and all non-frame Run sentinels survive;
  nonempty arbitrary continuation and a faulting continuation that remains
  pending demonstrate this is a prefix, not an assumed completion theorem.
- Negative actual unknown-block and wrong-arity outcomes; a declaration-only
  scope missing an extra zeroability fact cannot silently qualify.
- Narrow out-argument law plus independent out example: nonzero caller value,
  zero callee entry, and an otherwise unreadable argument are useful runtime
  boundaries. The unreadable argument is not a claim of semantically valid
  source syntax; full-program valid out/copyback remains separate.
- Actual faults: swap unequal parameter destinations; bind observer from
  source_hdr; install the callee before all caller reads; skip binding; copy
  caller contents for out; or change a non-frame Run field. The actual-code
  correspondence should reject these. A paired fixture/name remapping can
  still require an independent expected lookup test to expose wrong intent.
- For subsequent body-prefix work, omit scratch/unrelated initialization,
  run the observer too early, consume a continuation, or drop blockReturn.
  Separate proof rejection from compiled Python/Lean mismatches and retain
  complete live/restored replay inputs whenever runtime mismatches occur.

Confidence: high in fixed four-root entry and exact Run/queue boundary; medium
in the cheapest proof for the monadic for-loop and suffix composition. Revisit
the fixed-arity helper after a second actual call profile needs it. If generic
list plumbing expands, ship the real four-argument theorem first rather than
broaden into a general call framework. Body-prefix composition is the next
checkpoint, not a prerequisite for accepting the narrowly useful entry result.
