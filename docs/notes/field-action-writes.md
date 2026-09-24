# Field writes under an active action layer

2026-09-23. First prerequisite of `forwarder-action-next.md`, built against
committed `f1493d8`, including the reviewed authoritative root-write laws.

`P4blo.FieldActionWrites` adds operational correspondence lemmas; it does not
change `Fields`, `CmdWith`, the interpreter or the forwarder Program. The new
`Ref.write_unshadowed` lifts the committed `writeVar_block_unshadowed` through
the existing recursive `Path.writeLValue` reconstruction law. The result is
the exact original Run with only the selected block-map root inserted.
Action name, action parameter map, scope and all shared state survive.

`FrameMatches.set_unshadowed` requires absence of **only the written root**
from the actual action map. Other modeled roots may still be action-shadowed;
the proof preserves their action-first values. `Ref.write_matches_unshadowed`
combines exact runtime execution, updated independent source-store agreement,
`ChangesOnlyVars` and unchanged unrelated block names. None of these laws
claims declaration/permission checking, global validity or `BlockFrame` for
the active frame. Existing block-only APIs and proofs remain unchanged.

The constructive witness builds a real nominal `Box` index and writes its
scalar member through an installed action frame. The source also models
`shadow=7` from the action layer, while its block-map decoy remains 99. The
holder becomes 2, the action map/sentinel and unrelated block/shared values
stay unchanged. Kernel examples establish that the frame is *not* BlockFrame
and that the other modeled root is indeed shadowed. A complementary actual
shadowed write must update only the action value and retain the block decoy.
These artificial storage bindings are operational evidence, not a claim that
the witness is a validator-accepted declared control program. The subsequent
real-action theorem must supply the actual forwarder scope and initialized
frame independently.

Confidence: high in the precise nonshadowing contract and leaf-law reuse;
medium in retaining these named operational adapters as the long-term user
API. Revisit when a second verified action needs parameter writes or when
action-aware source typing is introduced. Do not remove the old command
theorems' BlockFrame premise to accommodate this example.

All four new default audit roots use exactly `propext`, `Classical.choice`,
`Quot.sound`, with no new axioms or native proof escapes. The native witness
checks selected explicit sentinels; preservation of every Run field is the
universal theorem's conclusion, not a claim of exhaustive native projection.

## Checks and adversarial boundary

From this worktree, both commands completed with exit 0:

```sh
nix develop -c /Users/qobilidop/my/work/p4blo-forwarder-action/scripts/check-lean.sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees -q
```

The first includes both packages, default audits and all native tests. Logs:
`/tmp/p4blo-field-action-writes-lean.log` and
`/tmp/p4blo-field-action-writes-required.log`. The required differential gate
reported 867 passed and 1570 deselected, with no skip.

An isolated copy of `FieldActionWrites.lean` changed only the result frame in
`FrameMatches.set_unshadowed` to also set `actionVars := none`. The candidate
source and binaries were never changed. Checking this copy with the pinned
Lean compiler exits 1: the other-root case supplies an action-first lookup
agreement, but the false conclusion demands block-only agreement. This is a
rejected **theorem-conclusion mutation**, not a compiling runtime fault or a
new differential input. The semantic mismatch, not the accompanying unused
simp warning, is the kill. The witness's action value 7 versus block decoy 99
illustrates exactly why the stronger claim is false.

To reproduce, copy the module into a scratch Lean file and change the unique
conclusion line
`{ frame with vars := frame.vars.insert root.name value.toValue }` to
`{ frame with vars := frame.vars.insert root.name value.toValue, actionVars := none }`.
Run `nix develop -c lake +leanprover/lean4:v4.34.0 env lean /absolute/scratch.lean`
from the `lean/` package. The recorded scratch file is
`/tmp/p4blo-field-action-mutant.hNvNJP/ForgetActionLayer.lean`; log:
`/tmp/p4blo-field-action-forget-layer-kill.log`.

The selected-action milestone still owes its planned real runtime mutation,
complete saved packet mismatch, live replay and restored agreement. This
prerequisite does not claim that work is complete. Independent read-only
review is CLEAR: the reviewer checked the structural argument, all four
exact axiom sets, fresh mixed-witness execution, compiled full user tests,
and the scratch mutation/gate evidence. See
`docs/notes/reviews/field-action-writes.md` (integrator-owned report).
