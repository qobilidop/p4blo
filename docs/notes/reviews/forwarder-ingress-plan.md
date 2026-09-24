# Forwarder ingress-prefix plan review

Plan review: CLEAR for the scoped checkpoint. No implementation, proof build,
or completed test evidence is claimed here.

Read `docs/notes/forwarder-ingress.md` against actual `Forwarder.ingress`,
`ForwarderProof.invalid_guard`, `ForwarderApply.source_steps`, and actual
Execution.dispatch in the isolated ingress worktree at 9a12253.

The proposed boundary is exact and useful: begin at the complete real ingress
body, finish with the full second checksum conditional still pending ahead of
arbitrary K. That pending statement must include the actual left-associated
144-bit input and output lvalue, not a reduced checksum placeholder. The
selected branch's empty-list pop is included; the pending checksum guard is
not evaluated. A next machine step only expands that pending statement list;
tests must distinguish expansion from the subsequent guard evaluation.

The invalid premise is genuinely smaller than table readiness. Existing
invalid_guard already proves a whole-Run-preserving false read from actual
index plus an action-first header lookup, without requiring scope, entries,
metadata, BlockFrame or valid contents of unused fields. Reuse that fact, or
the equivalent typed HeaderRef specialization, without importing valid-branch
requirements into the separate invalid theorem. The independent source policy
must preserve prior drop and all fields on that branch. Ethernet validity and
TTL are not extra application guards.

On valid IPv4, the existing concrete table theorem supplies selection/action/
return semantics under actual scope, no active action, real installed family
and complete source agreement. A readiness implication conditional on source
IPv4 validity is a concrete state predicate, not an assumed successful
execution. The source-agreement premise must tie that source bit to the actual
read; state readiness must not be decided using an unrelated fixture Boolean.

The literal counts are consistent with actual dispatch: five administrative
steps surround table source_steps (list expansion, conditional selection,
selected-list expansion, statement-to-table dispatch and empty selected-list
pop), giving 18/12/10 for valid forward/drop/NoAction. Invalid requires three
steps. Treat these as native checks unless adding an indexed theorem. One-short
and pending-K controls should expose the otherwise easy-to-miss pop.

The two Python observation routes are complementary: normal execution of the
real first conditional, plus actual whole-body execution intercepted before
the second dispatch. The latter sentinel is not a successful full-body return;
require one exact stop and catch only its dedicated sentinel. Preserve all
unexpected exceptions. Freeze expected complete state before running, and
observe immediately after actual guard evaluation as proposed; otherwise a
valid branch could repair a guard side effect. Avoid counting snapshot reads
as authored reads.

For invalid cases explicitly include absent entries, a malformed but unused
installed state, unrelated/empty scope maps, and a matching action-shadowed
header with a disagreeing block decoy. These are operational theorem controls,
not validator-approved programs. Existing real initialized-frame instances
should remain separate nonvacuity evidence for valid configurations.

No plan blocker found. Confidence is high in reuse and scope; the conditional
readiness API is reasonably provisional. Revisit it at checksum composition,
not by weakening exact pending syntax or treating the synthetic stop as a
whole-control proof. Independent core/observer/campaign review is still required
before implementation clearance.
