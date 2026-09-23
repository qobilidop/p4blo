# Original firewall oracle review

Reviewed 2026-09-23: the integrator's uncommitted original-source fixture
and oracle tests against `4b64497`. Read-only review from an independent
worktree. This is an oracle-feasibility checkpoint, not a completed firewall
port or proof of firewall equivalence.

## Findings

No blocking semantic defect found in the current fixed experiment.

- Recommended hardening: `firewall.plan()` currently filters out the STF
  configuration and uses separately written BMv2 `COMMANDS`. Those commands
  match the current STF by inspection, but a later change to an `add`,
  `setdefault` or interleaved configuration could be silently ignored by
  BMv2 while changing SpecTec's experiment. Assert the exact supported
  configuration, or explicitly translate it and reject unsupported shapes.
- The promotion note said four focused tests, while the current increment
  contains five (three fixture/observer tests and two actual oracle tests).
  Keep its recorded count aligned with the executed selection.

## Source and experiment integrity

- Independently fetched the file at upstream commit
  `098ce0b7ae486f5b747a6b53ad1585f0d977b42e`; its SHA-256 and the local vendored
  source both equal
  `5e1286ddbbc583d00fb5cbbb7c5f7a07076b4c200b0e9ed931c58e6b03230b19`.
  Both network-fetch and hash commands succeeded. The source preserves its
  Stephen Ibanez/Apache-2.0 SPDX notices, and the repository has Apache-2.0
  license text. No printer-generated replacement is being checked instead.
- SpecTec consumes the hash-checked original file directly. BMv2 compiles
  that same checked source text directly. Neither path invokes the p4blo
  printer or depends on a not-yet-implemented firewall IR translation.
- The four packets are exactly 54 bytes: 14-byte Ethernet, 20-byte IPv4,
  20-byte TCP. IPv4 length 40 and TCP data offset 5 agree. Expected output
  changes MAC addresses, decrements TTL 64 to 63, and adjusts IPv4 checksum
  from `66ce` to `67ce`; both expected headers have a valid checksum.
  TCP checksums are zero and unverified by the original source, not a claim
  of valid end-host TCP traffic.
- Requests are: inbound ACK before state; outbound SYN; same inbound
  five-tuple afterward; different inbound destination TCP port. Sequence
  numbers 1–4 distinguish every packet without entering the source hash.
  Only SYN and the established-flow ACK are expected to leave, with exact
  byte/length matches. The changed-flow rejection is a concrete case, not
  a claim that Bloom collisions cannot permit other flows.
- The single BMv2 phase preserves register state. Its existing driver
  writes increasing capture timestamps in input order, which preserves
  ordering across input ports. The two route/direction configurations match
  the original source's keys and actions under the declared two-port setup.
- Existing oracle CI jobs run the complete two test files, so the new
  original-source tests are discovered without a new filename list. They
  retain existing unavailable-oracle skip policies; missing infrastructure
  must still be reported as untested, not a successful semantic check.

## Observer checks and remaining limits

The observer regression replaces the expected established ACK with the
distinct premature ACK. The judge rejects it; packet identity no longer
allows those requests to substitute for one another in aggregate queues.
Exact expected output count/bytes and unexpected-output checks remain intact.
The BMv2 test also rejects missing/extra phases, driver errors and CLI errors.

This does not establish per-request completion, register contents, all CRC
indices, malformed-packet behavior, collision coverage, or table updates
during a persistent run. Per-port output queues and the existing BMv2
completion heuristic remain trust boundaries. Only the configured ports are
observed. Keep these as limitations of this preflight; the actual application
milestone requires stronger state and observer evidence.

## Independently executed checks

With bytecode writing disabled and no main-worktree writes, invoked the
source-pin test, vector-distinction/length/checksum test and premature-ACK
observer test: **all three passed**. `git diff --check` passed. Actual
SpecTec/BMv2 executions and the full suite are the integrator's reported
checks, not independently rerun by this reviewer. Only this report was
written in the review worktree; no implementation edits or commits.

## Integration follow-up

The integrator implemented the configuration-drift hardening: the fixed
STF setup must match its reviewed header exactly, and only packet/expect
statements may follow it. Tests reject changed direction rules and late
configuration writes instead of silently dropping them. Six focused
original-firewall tests, including both real oracles, pass after this change;
format/lint/typecheck pass. This follow-up is integrator evidence, not a
new independent execution claim. The preflight report count is corrected.
