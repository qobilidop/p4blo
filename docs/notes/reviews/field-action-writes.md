# Active-action field-write prerequisite review

Final review: clear. This is a small operational prerequisite, not an action
correctness theorem or action-aware source typing.

2026-09-23. Read-only review of `p4blo-forwarder-action` against `f1493d8`.
Read the two new modules, all registrations, the prerequisite note and the
committed root-write law. No candidate source edits or rebuilds performed.

`Ref.write_unshadowed` correctly composes the existing recursive
Path.writeLValue law with actual writeVar_block_unshadowed. Its premise is
absence of the written name from the actual optional action map, not absence
of the whole action layer or an assertion about declared action names.
FrameMatches and this absence establish a real existing block binding. The
conclusion is the exact original Run with one block-map insertion: action
name/map, scope and every non-frame component remain unchanged.

`FrameMatches.set_unshadowed` uses unique modeled root names and handles
other modeled roots using their original action-first read. It does not
silently require those other roots to be unshadowed. The combined Ref law
supplies updated independent source-store agreement, exact ChangesOnlyVars,
and preservation of every unmentioned block name. No opaque whole-command
callback, alternate evaluator, runtime mutation or weakened BlockFrame API
was introduced.

The constructive witness is nonvacuous: its nominal Box declaration comes
from actual Index.build; an active action stores shadow=7 while the block-map
decoy is 99; the written aggregate holder is absent only from the action map.
Kernel examples establish that this frame is not BlockFrame. The complementary
runtime shadow write updates the action binding, leaving the block decoy and
holder untouched. As documented, this is an operational storage witness, not
a validator-accepted declared control/action program.

Independent fresh pinned Lean queries of all four registered roots returned
exactly `[propext, Classical.choice, Quot.sound]`, exit 0. Fresh #eval of the
two runtime observations passed. Independently ran the frozen compiled full
userTests binary, exit 0, including these witnesses and all existing authored
examples. Native checks observe selected block/action/visit sentinels; the
theorem, rather than those finite checks, establishes complete Run preservation.

The public import, ordinary native test driver and default audit all include
the increment. No blocker found in its exact hypotheses or conclusions.
The concrete real forwarder action still owes actual declarations, initialized
scope/frame, directionless parameter bindings, source policy, action return
and full 11-step composition; these are not consequences claimed here.

## Final evidence closure

Read the final note and exact scratch source/log. The isolated change adds
`actionVars := none` only to the source-agreement lemma's output frame. The
first compiler error is genuinely semantic: action-first lookup agreement
for an unrelated modeled root cannot establish its block-only value. The
additional downstream mismatch and unused-simp warning are not counted as
the kill. This is accurately labeled a theorem-conclusion mutation, not a
compiled runtime fault or differential inconsistency. Candidate source and
binaries were never mutated, so no restoration claim is needed for this probe.

Inspected the owner's completed required gate: 867 passed, 1570 deselected,
no skips; the note records exit 0 for it and both full Lean packages/default
audits/native tests. The earlier independent fresh axiom/native checks remain
applicable because the final additions were evidence text only. The note
correctly limits native coverage to selected sentinels and reserves complete
Run preservation for the universal theorem. No remaining blocker found.
