# Parked application proof drafts

2026-09-23. The user-approved finite [milestone 1](../milestone-1.md)
does not require these additional application proofs. Preserve the drafts;
do not resume them automatically or present them as landed guarantees.
The tracked plans describe the intended mathematics independently of these
local worktrees. No release result depends on either tree or temporary logs.

## Firewall readback

Tree: `/Users/qobilidop/my/work/p4blo-firewall-readback`, branch
`work/firewall-readback`, HEAD `b3defb4` (plan only, already integrated).
Untracked files: `lean/P4blo/TutorialFirewallReadback.lean`,
`lean/P4blo/TutorialFirewallReadbackTests.lean`, and
`tests/test_lean_firewall_readback.py`.

The standalone core compiles at default limits: actual two register calls,
copyback, exact remaining queue and preservation of unrelated state/layers.
Standalone native observations pass 337 profiles (56 noncanonical native-only
profiles). Seventeen fresh theorem queries pass: `cell_answer` has no axioms;
the other sixteen use only the standard three audited axioms. These modules
are not public/default-registered. No final independent acceptance review or
fault campaign has been completed.

The Python draft has not been formatted or tested. Suspected draft protobuf
access mistakes include `.else_`, `WhichOneof("stmt")` instead of `"kind"`,
and a CallAction field name. Native success does not establish that this draft
works. Do not count proposed 280 canonical Python profiles as executed tests.
Future work, only under a new scope: repair/review the draft, integrate actual
audits, independently challenge observers and semantics, then run full gates.
The reviewed mathematical plan is `firewall-readback-next.md`.

## Guarded forwarding ingress

Tree: `/Users/qobilidop/my/work/p4blo-forwarder-ingress`, branch
`work/forwarder-ingress`, base/HEAD `9a12253`, uncommitted draft.
The owner reports both Lean packages/default checks, eleven audit roots,
540 native prefixes, 1620 queue boundaries and twelve invalid controls pass.
The draft combines actual table application with the first ingress guard,
leaving the checksum pending; it is not a complete forwarding proof.

Python/export drafts exist but focused, required and full Python gates and
adversarial campaigns have not run. Ruff formatting/checking passed; Pyright
still reports `InstalledEntries.defaults` at line 484 of
`tests/test_lean_forwarder_ingress.py` (the actual field is `default_actions`).
There is no final independent review. Do not count draft Python cases or the
unmerged proof as accepted evidence. The local plan is
`docs/notes/forwarder-ingress.md`; landed application prerequisites and their
scope are documented in `forwarder-apply.md` on main.
