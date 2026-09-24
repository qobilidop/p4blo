# Load-balancer application review — 2026-09-24

Independent read-only review of candidate `46e6216`, followed by the requested
regression `195f3b5`. Program SHA-256:
`a360d12b7e576f2cd596388dd1abb5528064e8e1568540a876875acc1748382b`.
No confirmed correctness or usability defects remain.

The reviewer confirmed exact service selection, group-scoped backend lookup,
flow affinity, Ethernet rewriting, TTL decrement and checksum repair. Extra
packets varied TTL, DSCP, identification and payload while preserving affinity
and transport bytes. The documented bucket-one configuration edit redirects
only its intended flows. Review edits were in-memory, not canonical changes.

Review identified a useful regression gap: a service miss with a configured
group-zero backend must drop. Current code passed the independent manual
check; the author added it to the persistent known-answer sequence, bringing
that sequence to 111 requests (37 forwarded, two invalid-port diagnostics).
All three application tests pass, including actual Lean execution. Before
that test-only addition, six generic/oracle tests passed, including generated
Lean cases and both real P4 oracles. Full Pyright and Ruff passed.

The integrator reran fault sensitivity with the 111-request suite. Constant
bucket selection, omission of source port from the hash, a service-guard bypass
and stale output checksum each fail both independent-answer tests. Baseline and
restored runs pass both tests. The new group-zero regression specifically
challenges the guard's purpose. Recipe: `notes/mutations/example-programs.py`;
local evidence: `.artifacts/examples-mutations/load_balancer/`.

The independent combined review passed 19 non-Lean application/layout tests
(7 deselected) and full Pyright. Final integration evidence is in `docs/status.md`.
This is a request-only UDP dispatcher with a documented direct-server-return
deployment assumption, not NAT, health checking or consistent hashing.
