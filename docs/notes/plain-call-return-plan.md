# Next bounded bridge: normal plain-root return

2026-09-23. Read-only design and disposable feasibility probe at `ac69759`.
No production implementation, runtime mutation or commit in this checkpoint.

## Recommended contract

Prove one actual `Execution.dispatch (.blockReturn caller params args)` and
its normal, fault-free machine transition. Reuse the committed
`PlainCallEntry.params` and `args`, not another call profile. The actual
return arm captures the current callee frame, restores the saved caller,
then calls actual `copyBack`. That loop skips the input-only route and writes
the three `inout` roots in parameter order:

| Callee read | Original caller destination |
|---|---|
| hdr | source_hdr |
| meta | source_meta |
| observer | hdr |

Let `returnedFrame caller h m o` be the closed result expression
`caller` with its vars map updated by these three ordered inserts. This is
the theorem's result, not a second executable copyback implementation.
The proposed exact equation is:

```text
(dispatch (blockReturn caller PlainCallEntry.params PlainCallEntry.args)).run run
  = (ok [], {run with frame := returnedFrame caller h m o})
```

Here `run` is the **current callee-after Run**, not the old entry Run.
Preserve all of its non-frame state, including any legitimate effects of
the intervening body/observer. Only the originally captured caller *frame*
is restored. In particular do not reset packet, emitter, entries, externs,
visits or Index to a historical entry snapshot.

Explicit sufficient premises:

- `BlockFrame caller`: both original caller action fields are absent.
- Three existing original caller bindings: `caller.read? "source_hdr"`,
  `"source_meta"`, `"hdr"` return some old values. Under BlockFrame these
  are operationally writable map entries. No runtime declaration/permission
  check or global typing judgment is silently inferred from their presence.
- Three current callee lookups: `run.frame.read? "hdr" = some h`,
  `"meta" = some m`, `"observer" = some o`.

Values may be arbitrary `Value`s. The runtime neither checks parameter
types nor consults Index for these plain-root writes. A later source-typed
corollary can specialize the values; do not add a whole-copyback correctness
callback. The current raw callee reads use actual `Frame.read?`; this does
not prove action compatibility. No callee route/scratch/unrelated read is
needed. No source_route binding, zeroability, lookup or arity premise is
needed: the two lists are fixed and equal length, and return does not
revalidate them or initialize a frame.

Derive exact final target lookups, original caller scope and BlockFrame,
and lookup preservation for every name outside the three destinations.
This includes caller source_route and caller scratch/unrelated when present,
and preserves absence when absent. Callee route/scratch/unrelated are not
copied. Lift the equation to exactly one actual step and `Steps` with
arbitrary continuation K:

```text
{work := blockReturn caller params args :: K, run, fault := none}
  → {work := K, run := {run with frame := returnedFrame ...}, fault := none}
```

Leave K pending, including a deliberately faulting continuation. A future
observer-prefix proof can supply the three callee reads at this boundary.
This theorem does not show that entry/body/observer reached the boundary.

## Feasibility already checked

Fresh-cache pinned build of committed `P4bloIR.PlainCallEntry` passed
(14 dependency jobs; the entry module took about 23 s). A disposable
`ReturnProbe.lean` then checked the following two universal lemmas, with
exactly `[propext, Classical.choice, Quot.sound]` each. No native reduction,
new axiom or production edit was used. Probe compile exited 0.

```lean
open P4bloIR P4bloIR.PlainCallEntry P4bloIR.ScalarTyping
open P4bloIR.ScalarStatements

theorem copyBack_three (callee : Frame) (hdr metadata observer : Value)
    (hh : callee.read? "hdr" = some hdr)
    (hm : callee.read? "meta" = some metadata)
    (ho : callee.read? "observer" = some observer) :
    copyBack params args callee = (do
      writeVar "source_hdr" hdr
      writeVar "source_meta" metadata
      writeVar "hdr" observer) := by
  have io : (Direction.inout == Direction.out) = false := rfl
  have ii : (Direction.inout == Direction.inout) = true := rfl
  have ni : (Direction.in == Direction.inout) = false := rfl
  have no : (Direction.in == Direction.out) = false := rfl
  simp [copyBack, params, args, hh, hm, ho, writeLValue, io, ii, ni, no]

theorem restored_write (run : Run) (caller : Frame) (old value : Value)
    (hb : BlockFrame caller) (found : caller.read? "source_hdr" = some old) :
    (do setFrame caller; writeVar "source_hdr" value).run run =
      (.ok (), { run with frame :=
        { caller with vars := caller.vars.insert "source_hdr" value } }) := by
  have hw := writeVar_block (value := value) { run with frame := caller } hb found
  have hs : (setFrame caller).run run = (.ok (), { run with frame := caller }) := rfl
  simpa only [run_bind, hs] using hw
```

Command: `nix develop -c lake +leanprover/lean4:v4.34.0 env lean
-DwarningAsError=true /absolute/worktree/ir/ReturnProbe.lean`, run with the
IR package as working directory. The file imports `P4bloIR.PlainCallEntry`;
the snippet and two `#print axioms` queries reconstruct the probe. The
temporary file was removed; only this plan is proposed for retention.
First attempts left Direction BEq guards and setFrame's state transition
unreduced; the explicit facts above resolved them. Those failed attempts
are not proof evidence. No complete return theorem or runtime gate was
attempted in this planning task.

Implementation should compose the three existing `writeVar_block` laws,
using HashMap insertion lemmas to preserve subsequent root existence, then
unfold only the actual blockReturn arm. Confidence high in this fixed-profile
proof; revisit a generic list lemma only when a second real call profile
justifies it. Do not refactor runtime semantics to make the proof easier.

## Independent tests and adversarial acceptance

Use asymmetric old caller and new callee values, all four header-validity
pairs, and the actual H/Result observer layout from the committed declaration
fixture. Caller source_route must differ from callee route. Give caller and
callee different scratch/unrelated sentinels, different scopes, and decoy
callee destination names so skipped restoration cannot hide behind an early
unknown-variable failure. Also include a callee with no route binding at all:
normal copyback must succeed without reading it. Keep missing-destination or
missing-callee-read counterexamples separate from the successful theorem;
there is no rollback or fault-unwinding theorem here.

Observe actual `dispatch`/`step` on Lean and actual Python `stmt.copy_back`
on independently constructed caller/callee environments. Python has separate
Env objects, so direct copy_back tests do not independently establish Lean's
machine-level frame restoration; exact Lean scope/frame/queue observations
and the proof must cover it. Compare independently named expected full caller
values, unchanged callee values, detached complete Index and scope dataclasses,
action layers, and frozen packet/emitter/entries/extern/visits contents.
Retain identity checks only as additional evidence. Use strict `same_json`
for both engines' value observations and exact four unique Boolean validity
pairs, carrying forward the entry observer regressions. Check that a later
actual caller header write does not mutate the retained Python callee copy.

Distinct successful root writes commute observationally. The final-state
theorem alone therefore does **not** establish an order-sensitive external
trace. The proof follows the actual loop's ordered three-write reduction;
a test-only spy that delegates to actual Python `write_lvalue` should record
exactly source_hdr, source_meta, hdr. Do not call a reversed-loop survivor
under only final-state checks evidence that order was verified.

Planned actual faults: wrong destination, copy input route (including changing
its expression argument to a lvalue in the fault so a wrong write can succeed),
skip observer copy, omit caller restoration, read from restored caller rather
than captured callee, or reset a current non-frame field. Each compiling Lean
mutant must reject the scoped proof or exact observation; distinguish proof
rejection from runtime mismatches. Mutate actual Python copy_back separately
and retain live/restored entry-level reconstruction inputs, not a fictitious
whole-packet DRT claim. Challenge the observer with shared-state/index/scope
mutation and bool/int JSON aliases. A paired source-result destination/name
remapping may pass generic correspondence; independent literal caller-name
answers and the tracked wrapper params/args must reject that wrong intention.

## Proposed implementation ownership and exclusions

After root approval: new `ir/P4bloIR/PlainCallReturn.lean`, focused native
tests and append-only IR export/audit/test registration. If the existing
typed H/Result fixture is reused for cross-language tests, use new
`lean/P4blo/CallReturnTests.lean` and a dedicated exporter/default registration;
do not edit `CallEntry*`, which the body-family task owns. Add new
`tests/test_lean_call_return.py` with shared lean_binary fixture and required
`test_lean_agrees` discovery. Default-audit advertised generic and constructive
roots; require standard-three axioms, both Lean gates, focused/required tests,
fault restoration and independent review before commits.

No source adapter, full call composition, body/observer execution, parser,
action, overlapping writable arguments, arbitrary lvalues, or pending-fault
unwinding is authorized by this plan. No Docker or external-system changes.
The present deliverable is only this reviewable plan/probe evidence; root
reviews it before authorizing implementation.
