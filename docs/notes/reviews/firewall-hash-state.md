# Firewall hash-state campaign review

Independent read-only review, 2026-09-23, of the report-only campaign in
`p4blo-firewall-adversarial` based on `8328127`. No blocking finding.

Inspected both exact XOR-one patches, the tracked-input reconstruction
recipe, actual baseline/mutant/restoration logs and saved bundles. The final
worktree has only the new campaign report; both Python and Lean CRC source
files have no diff. Intentional faults are not part of the final change.

The log evidence supports the distinction the report makes:

- Python's six ordinary firewall corpus checks survive, while 14 numeric,
  index and complete-state assertions fail at runtime.
- The Lean mutation builds both packages and default proof audits before
  three numeric/state tests fail. This is not a compilation failure being
  mislabeled as a semantic-test kill.
- Both connection probes and live mutant replays report one agreed and
  three diverged requests, without shared errors. Packet bytes/ports match;
  only CRC32-backed register state differs (cell 1986 versus 1987), while
  CRC16 remains at 1990. The packet-only Lean control passes all four cases.
- Restoration logs show both Lean gates and 110 focused tests passing,
  with external-oracle cases explicitly deselected rather than counted as
  successes. No full or external-oracle rerun is claimed for this campaign.

Independently verified both bundle files and the integrator's handoff copy
are **76,260 bytes**, SHA-256
`c547f2999038dae030dfd93402e7e26a73782f0424384fda9633a5ee7e886103`.
Loaded both bundles and checked their program exactly equals the tracked
typed firewall and their four requests exactly equal `connection()`;
ports/seed are 4/0. Independently replayed both against the restored Python
implementation and restored compiled Lean binary: each returned **four
agreed, zero diverged, zero shared errors**, and the command exited zero.
No implementation-worktree rebuild, source mutation or oracle-image change
was performed by this reviewer. Mutant runs themselves are inspected
campaign evidence, not a second independently repeated mutation campaign.

The conclusion is appropriately limited: selected weak packet-only gates
survive a consistent index permutation, while existing full-state/known-
answer gates detect it. Passing Lean audits under the wrong CRC highlights
the absence of an independent CRC refinement theorem, not a kernel flaw.
The report correctly avoids claiming universal equivalence or mutation
adequacy. Exact patches, source fixtures and complete commands are durable;
the ignored local bundles/logs are supplemental, not the only way to resume.
