# Tend-repo skill review

Independent read-only AI-agent review, not human review, on 2026-09-26.
Reviewer: Codex agent `minimal_arch_review` in an isolated worktree.
Base: `405b73b8007fea238bb05cd24fdd33ca800f801b`.
Reviewed patch SHA-256:
`8cce68ec0df07e38b4073f7e276602d1d8f0312a77d79cb3d1caad9e7815e46b`.

The source procedure was p4-spectec-lean's `.agents/skills/tend-repo/SKILL.md`,
last changed at `bc60115baee2f300a872b186009ad4dfb7490ebd` in that repository.
The adaptation keeps consistency, compaction and learning, delegates policy
and compaction to p4blo's existing owners, and adds its evidence boundaries.

## Findings and scenarios

Approved, with no confirmed defects or conflicting policy. These were dry
runs; the reviewer neither edited files nor executed maintenance.

1. Review only, excluding spec/: inspect scoped evidence, report opportunities
   and proposed validation, make no edits and run no maintenance gates.
2. Completed scope with an oversized resume read, unresolved reviews and
   unique parked branches: preserve obligations, reviews and recovery refs;
   use the existing compaction procedure only when its prerequisites hold.
   Defer if unresolved findings mean active engineering. Actual state was
   738 resume Markdown lines, approved reviews and three unique parked branches;
   hypothetical facts did not replace observed state.
3. Stale test documentation, a native patch comment and duplicated website
   source: correct live documentation drift; retain the native patch because
   build stamps hash its contents, and the checked generated website copy
   because its renderer and tests enforce equality with canonical source.

## Checks and limits

The reviewer read the skill, AGENTS diff, compaction procedure, status,
parked inventory and current review findings; checked metadata and reference
paths; inspected native patch hashing and website generation/check consumers;
verified unique parked-branch differences and counted resume Markdown.
`git diff --check` passed. Heavy gates and native builds were not run by the
reviewer; final status evidence wording is the integrator's responsibility.

Integrator checks: skill-creator `quick_validate.py` passed using ephemeral
`uv run --with pyyaml` (no project dependency added). Required-Lean
`scripts/check.sh` passed 5,007 tests in 97.50 seconds, no skips or expected
failures, and lint/types/schema/generation/workflow checks passed. Runtime,
schema and test inputs are unchanged; native/Lean builds were not rerun locally.
