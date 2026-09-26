# Retired application proof drafts

The core-only assurance decision (2026-09-25) retires these extensions.
Their unique committed content remains on the branches below for recovery;
retaining history does not make these drafts a work queue.

2026-09-23, converted to branches 2026-09-24. The user-approved finite
[milestone 1](../../docs/assurance.md) does not require these additional
application proofs. Nothing on these branches is evidence for a landed
claim; do not resume them without a new scope. All are pushed to
`origin`. Each predates the 2026-09-24 layout (`spec/ir`, `spec/arch`,
`impl/lean`) and the generic extern state, so each needs rebasing, with
its extern constructions moved to `P4bloArch`, before it can build.

| Branch | Tip | What it holds | What it lacks |
|---|---|---|---|
| `work/firewall-readback` | `75fdcf6` | the actual two-read prefix before the Bloom decision in Lean: copy-back, exact remaining queue, preservation of unrelated state; compiles standalone, theorem queries clean; a Python test draft | registration in the package and audits; the Python test was never run and uses wrong protobuf accessors; review; fault campaign. Plan: `docs/notes/firewall-readback-next.md` at commit `9e8f7d47`; its review is on `work/parked-reviews` |
| `work/forwarder-ingress` | `231e981` | actual table application composed with the first ingress guard, checksum pending; owner-reported Lean checks; Python and export drafts; its plan `docs/notes/forwarder-ingress.md` | the Python gates never ran and Pyright reports a wrong field name in the test; review; the checksum step; not a complete forwarding proof |
| `work/parked-reviews` | `d18436b` | the reviews of the two drafts above and eight variant review versions whose final forms are archived | nothing; reference only |

The review worktree's other 74 files were identical to notes at the
archive commit and were not duplicated. Two further branches from the same
cleanup, `work/firewall-adversarial` and `work/program-codec-next`, held
only content byte-identical to what `main` had already integrated and
were deleted on 2026-09-24. Recovery archives of the 86
worktrees removed on 2026-09-24 remain local; see
[worktree-cleanup.md](worktree-cleanup.md).
