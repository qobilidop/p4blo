# Status

Current checkpoint, 2026-09-26. No active implementation work.

## Current scope and evidence

The approved documentation refactor is implemented: short public README,
policy-focused AGENTS, topic-owned rationale/reviews, a small current checkpoint,
and current assurance separated from historical release evidence. No implementation,
schemas, test inputs, pins or proof premises changed. Unique parked branches and
local-only recovery snapshots remain retained.

Independent review compared all 68 decision entries and found no confirmed losses
or stronger claims. Both skill validators passed. Required-Lean `scripts/check.sh`
exited 0: 5,007 passed in 95.72 seconds, no skips/expected failures, plus all
lint/type/schema/generation/workflow checks. [Repository stewardship](notes/repository-stewardship.md)
records exact slice revisions, reviewed patch, preservation checks and limits.
The publishing commit's Actions runs own the remote result; check the exact SHA
before treating publication as complete. Baseline CI below is separate evidence.

After confirming publication, select a new bounded scope with the user. No feature
work follows from this refactor; [Roadmap](roadmap.md) remains deferred research.

## Checked baseline and archive

Pre-refactor archive: `de6aa7d9437ffc65c413b0adda7d3f8c558f84f6`.
Its exact-main runs all passed; no specialist job skipped:
[Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36272145887),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36272146053),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36272146195), and
[BMv2/p4c](https://github.com/qobilidop/p4blo/actions/runs/36272146069).
These results validate the baseline; the publishing revision needs its own CI.

## Retained boundaries and next scope

Current guarantees and exact assumptions belong in [assurance](../docs/assurance.md).
Only architecture-free core IR receives formal assurance; independent core blocks
and scoped v1model remain. Protobuf wire syntax plus its JSON profile for Lean
remain one IR. Retired architecture/application proofs are not continuation work.

[Roadmap](roadmap.md) retains deferred proofs, interchange questions, the joint
P4-SpecTec-to-Lean milestone and unresolved observations. [Validation evidence](notes/validation-evidence.md)
preserves exact finite experiments and completed-scope identities.
[Recovery](notes/recovery.md) owns earlier archive commits, parked branch gaps,
local-only refs and snapshot instructions. None is authorization to resume them.
