# Status

Current checkpoint, 2026-09-26. No active implementation work.

## Current scope and evidence

The user requested one repository-maintenance skill. `tend-repo` now owns the
compaction procedure and preservation safeguards; AGENTS routes to it. The
separate skill and its optional link-rewrite helper are retired. This changes
maintenance instructions, not runtime behavior or the deferred research scope.

Metadata validation and independent preservation/scenario review passed with
no findings. Required-Lean `scripts/check.sh` exited 0: 5,007 tests passed in
96.07 seconds, no skips/expected failures, plus lint/types/schema/generation/
workflow checks. [Repository stewardship](notes/repository-stewardship.md) records
the exact reviewed patch and limits. The publishing commit's Actions runs own
its remote verdict; verify the exact SHA before treating publication as complete.
No further skill changes are planned; select a new bounded scope after publication.

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
