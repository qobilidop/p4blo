# Engineering-practice review

Independent, read-only AI-agent review on 2026-09-25, in the isolated
`/private/tmp/p4blo-practices-review` worktree. Base: `045f3de`.
Initial staged patch SHA-256:
`5c0fe5d3d2bb510f2d698c249e9d176642a7a8de6cc1a9cf9f27c645ffffef77`.
The artifact-guard implementation is committed as `cd04ba2`; the policy
changes and review correction are carried by
[PR #1](https://github.com/qobilidop/p4blo/pull/1).

## Confirmed finding and resolution

**P2: active compaction procedure conflicted with PR-default integration.**
Following `.agents/skills/compact-agent-state/SKILL.md` literally started
on clean `main` (step 1), committed (step 7), and pushed (step 9), without
a PR or final-revision remote CI. This bypassed the new substantive-change
workflow. Reproducer: follow those three instructions in sequence.

Corrected the skill to name the committed pre-compaction archive point,
require a PR branch before editing, and use the final-revision review/CI
and head-SHA verification in `AGENTS.md` before merge. Also replaced the
same-day date heuristic with an explicit unfinished-compaction condition.
The reviewer confirmed closure and no further findings; correction diff
SHA-256: `7f61b5c71b68767164d85e1c0ca83f5a0220c39494044684863f98d9ef0b1163`.

## Evidence and limits

- Targeted `tests/structure/test_file_sizes.py` and `test_generated.py`:
  18 passed, using the integrator's Python environment in the review tree.
- Standalone file-size guard and staged whitespace check: exit 0.
- Read-only inspection covered fresh generation isolation, inventories,
  index/working-copy comparisons, size handling, negative tests, local/CI
  wiring and policy consistency. No other confirmed defect was found.
- Reviewer did not run real Buf, the full gate, Lean or external oracles.
  The integrator ran real Buf and the full local gate; current results
  are in `../status.md`. Remote CI remains separately visible on the PR.
- No source files were edited by the reviewer. This was AI-agent review,
  not human approval or proof that no defects remain.
