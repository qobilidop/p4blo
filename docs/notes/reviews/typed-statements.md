# Typed scalar statement review

Independent structural and completed-candidate review on 2026-09-23 of
`p4blo-typed-statements`. **Clear for integration**, with no unresolved
correctness finding. Stable binaries were executed read-only; no rebuilds
or implementation edits were performed. Merged-main gates remain the
integrator's responsibility.

## Core semantics and proof boundary

No blocker found in the inspected core. `Env.set` updates the positional
heterogeneous Fin/Bool source environment. `Cmd.denote` interprets writes,
conditionals and explicit tails directly over that environment, using the
previous independent expression semantics. Neither source function calls
IR execution, lowering or runtime frame operations. Shared scalar types
and direction tags do not make this semantic definition circular.

`Place` combines a typed reference with source write permission. `Modes`
distinguishes locals and parameter directions; `Modes.Agrees` connects every
source binding to an exact name/type/direction declaration in actual block
scope. `canAssign` additionally rejects malformed contexts, absent/mismatched
declarations and read-only input/directionless parameters. This is a scoped
typing/permission boundary, not a claim that runtime writes enforce those
permissions, nor a whole-program validity decision procedure.

Operational theorems separately require `FrameMatches` for exact values and
`BlockFrame` for absence of both active action and action-value storage.
That restriction matches the block-map insertion proof and prevents a hidden
action shadowing layer from invalidating it. Read-only permissions are not
smuggled into operational lookup: the typing premise and runtime-storage
premise serve different purposes.

`Modes.scope_agrees` and `Modes.frame_matches` construct concrete witnesses
for arbitrary well-formed contexts/environments. The scope constructor
builds corresponding parameter/local lists and a declaration map. This
demonstrates nonvacuity without claiming a proved bridge from global index
validation or `Frame.forBlock` initialization. Current tests exercise the
latter implementation path independently; its general proof remains absent.

## Exactness and continuation

`Cmd.steps` follows the existing `Execution.step`, not a replacement machine.
Its endpoint retains the arbitrary continuation verbatim and unexecuted.
Finite-step composition feeds the existing `Finishes.sound` connection to
production `execute` when the continuation is empty. No claim is made that
an arbitrary continuation itself terminates or succeeds.

`FrameMatches (cmd.denote env)` specifies exact final values for all source
bindings, not just their types. `ChangesOnlyVars` is whole-record equality
allowing only the frame value map to change, preserving scope, action,
packet, emitter, entries, externs, visits and index. `PreservesOutside`
additionally fixes every map lookup outside the syntactic possible-target
set, including previously absent unrelated names. The combined statement
avoids overstating hash-map representation equality while giving exact
observable source-variable updates and unrelated-state preservation.

## Completed acceptance review

All preliminary acceptance suggestions were addressed: public theorem and
witness audits are default targets; actual out/inout assignments run on
`Index.build` / `Frame.forBlock` frames; a kernel example leaves a genuinely
faulting continuation untouched, with a runtime test that confirms the fault
if executed; and ASSURANCE bounds the unproved global-construction bridge.

The exporter supplies syntax and inputs, never answers. Python independently
checks all nine fixture IDs and exact input types/values, builds the wrapper,
and observes every source binding plus an unrelated sentinel. Its independent
expected bytes cover order-dependent updates, wraparound, both branches,
skip and boolean assignment. DRT comparison/save precedes known answers,
so agreement cannot excuse a valid but unintended source term. The wrapper
is correctly labeled outside the lowering proof.

Independently executed evidence:

- Ten statement-focused checks directly invoked against the stable candidate
  (nine examples plus default-target guard): exit 0.
- Existing user-test executable: exit 0 with 21 contextual scalar answers,
  nine command/noninterference cases, negative elaboration and API checks,
  actual parameter writes and faulting-continuation runtime checks. An initial
  invocation from the review directory hit the existing relative fixture path
  after the new checks had passed; rerunning from the required `lean/` working
  directory succeeded. No build was needed.
- Independent `#print axioms` via pinned Lean and existing libraries confirmed
  scope/frame witnesses, lowering typing, prefix/execution correctness and
  `Steps.execute` use only `[propext, Classical.choice, Quot.sound]`.
  `Env.get_set` / `Cmd.denote_seq` have no axioms; `Cmd.lower_seq` uses
  `[propext]`. No sorry/custom axiom or native-decision assumption surfaced.
- Saved production-write mutant bundle exactly equals the tracked
  `update-dependent` wrapper and empty request, with four ports and seed 0.
  Independently restored replay: one agreement, no divergences/errors, exit 0.

Bundle: 9,888 bytes, SHA-256
`1f806e5de1c788cc573182229b9a6b6a240226e77c49729728d22aedb77cf313`.

Inspected the separate mutant logs rather than repeating destructive edits:
reverse source ordering breaks sequencing/exact-value proofs; wrong lowered
target breaks typing and execution; omitted write with adjusted typing breaks
the actual step equality; swapped if branches with adjusted typing breaks the
chosen transition. Their logs contain real proof failures, even where unused
simp warnings also appear. They are correctly labeled proof/build rejection,
not executable conformance kills.

The same-width x-to-y source place alteration builds with audits, then fails
source and independent Python known answers after DRT agreement (`031000a5`
versus `040b00a5`). The actual Python skip-x-write defect produces a retained
runtime mismatch (`000701a5` versus `040b00a5`), live replay failure, and same-
bundle restored agreement. The affected Python source has zero tracked diff.
ASSURANCE records exact edits, tracked reconstruction and replay commands;
it does not rely on a temporary helper or overstate universal adequacy.

Implementer-attributed full evidence: both Lean package gates, 184 required
DRT, and 1190 Python/schema checks with five existing strict discrepancies
and no skips; the final IR root-export-only addition was followed by both
Lean gates and 32 combined focused checks. These are not independent full
suite or clean-worktree build claims, and integration must rerun merged gates.
