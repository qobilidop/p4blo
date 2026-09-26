# CI efficiency

Complete: [PR #5](https://github.com/qobilidop/p4blo/pull/5), merged as
`967e0a35bf1d0939c26eb4c8b4636259e886b14b`, based on `5de0d9e` (PR #4).
The implementation branch and both author worktrees are removed after checking
that their changes were integrated. The review worktree is temporary and is
removed after the closing documentation check.
The user asked to reduce CI time and delegated the choice of prose-only checks.
This scope preserves every existing semantic case and strict expected failure.

## Baseline

Final closure head `e5cf214` passed all seven checks. Its measured job times:
Python macOS 182 s (tests 28 s), Python Linux 143 s (tests 84 s), schema 53 s;
Lean warm build 50 s and differential tests 411 s; BMv2 393 s; XDP 125 s.
P4-SpecTec run 36204854146 spent 325 s in generated cases, 76 s in the
frontend and 44 s in coverage, 643 s overall.
Runs: [Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36204854147),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36204854144),
[BMv2](https://github.com/qobilidop/p4blo/actions/runs/36204854171),
[XDP](https://github.com/qobilidop/p4blo/actions/runs/36204854161).

## Accepted approach and ownership

- Root integrates workflow scope, PR cancellation, Lean matrix, docs and gates.
- Classifier author: `/private/tmp/p4blo-ci-scope`, base `5de0d9e`, owns
  `scripts/ci-scope.py` and its structure tests. Commit `771f9d0` passes 69
  tests, Ruff and Pyright; integrated as `5674288`. Follow-up owns
  `tests/conftest.py`, shard tests and the obsolete pytest marker declaration.
- Oracle author: `/private/tmp/p4blo-oracle-parallel`, same base, owns the
  two oracle workflows. Measures serial/2/4 workers with identical JUnit case
  inventories/statuses. Existing immutable simulator/image only; no rebuild.
- Independent reviewer: `/private/tmp/p4blo-ci-efficiency-review`, initially
  base `5de0d9e`, read-only. Reviews classifier, scheduling and final integration.

Classifier CLI: `python3 scripts/ci-scope.py --event-path PATH --event-name NAME
--github-output PATH`. Output `full=true|false`; any uncertainty requests full.
PRs compare merge-base to the complete PR head, pushes compare before/after.
Only regular non-executable Markdown in the narrow allowlist can skip heavy
jobs; executable/parsed quickstart, semantics and coverage docs remain full.
Python/schema always run. Missing scope output cannot skip specialist jobs.
Superseded PR runs cancel; main runs remain intact. No counts or seeds change.

Lean uses two stable node-ID hash shards; their disjoint union must equal the
unsharded collection, including after normal pytest selection. Each builds and
audits all packages before tests, and only shard 1 saves the main build cache.
Remove ineffective module grouping: xdist reads group marks before the existing
hook adds them; simply prioritizing that hook would serialize unrelated tests.
Use ordinary load scheduling. Keep failure artifacts separate by shard.

## Evidence and remaining work

Read-only xdist experiment reproduced absent groups with the existing hook;
prioritizing it activated groups, including cases without expensive fixtures.
Current grouping claims therefore overstate what the scheduler does.
Local serial/2/4-worker measurements, each with identical JUnit case identities
and outcomes:

| Suite | Serial / 2 / 4 workers (seconds) | Outcomes |
|---|---|---|
| P4-SpecTec generated | 243.50 / 127.19 / 68.14 | 179 passed, 4 xfailed |
| BMv2 corpus | 68.94 / 34.36 / 18.34 | 44 passed, 2 xfailed |
| BMv2 firewall | 70.69 / 40.86 / 27.32 | 6 passed |
| BMv2 boundaries | 98.74 / 53.87 / 28.30 | 20 passed |
| BMv2 generated | 27.31 / 16.00 / 13.67 | 3 passed |

Local host has 16 CPUs; Docker has 12. Remote measurements below differ from
these local speedups, so local ratios are not projected onto the full workflow.
The real Lean collection has 3,045 cases: shards contain 1,509 and 1,536;
independent collection verifies no overlap and an exact union. Classifier
independent review at `771f9d0` found no confirmed defect (69 tests passed).

Shard author commit `bc82cc8` (integrated `5c58bcc`) passed 14 focused tests,
Ruff and Pyright. Independent real-xdist execution also verified the complete,
disjoint sample inventory. Oracle author commit `391d577` passed actionlint,
Ruff and Pyright; all 15 local benchmark runs retained identical cases/statuses.
Integrated classifier/shard/boundary checks: 96 passed.

Independent [review](../reviews/ci-efficiency-2026-09-25.md) approved the
classifier, shards and integration after one guard correction: a failed scope
job cannot authorize a skip even if it already emitted `full=false`. Five
workflow-boundary tests cover the corrected guard and reject the unsafe form.
The final full required-Lean gate passed 5,289 tests, one optional local XDP
skip and four expected failures. Explicit workflow-test parameter IDs keep all
five guard checks out of the existing external-oracle name filter. Independent
review approved exact final head `e4c1d759549dfa3c8518184e2a9b4818993071fd`.
All eight validation jobs and four scope jobs passed on that head before merge.

## Remote result and limits

| Job | Baseline seconds | Final seconds | Final run |
|---|---:|---:|---|
| Lean, slowest shard after | 521 | 256 | [Lean](https://github.com/qobilidop/p4blo/actions/runs/36207118970) |
| BMv2 | 393 | 252 | [BMv2](https://github.com/qobilidop/p4blo/actions/runs/36207118971) |
| P4-SpecTec | 643 | 556 | [P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36207118915) |

These are job times, excluding the preceding 4–7 s scope job and queue time.
Lean differential stages took 171 and 142 s, with all 1,509/1,536 cases passing.
P4-SpecTec generated execution fell from 325 to 169 s (179 passes, four expected
failures), but unchanged serial stages ran slower on this runner: corpus 49 s,
blocks 81 s, frontend 98 s and coverage 55 s. It remains the critical path.
This is one observed comparison; machine and cache variability prevent a
latency guarantee. Serial-stage profiling is a possible later scope, not active
work. No case, seed or strict expected failure was removed.

The closing prose-only checkpoint exercises the policy's other route remotely:
Python/schema must pass, scope must succeed with `full=false`, and specialist
jobs must be explicitly skipped. Its attached CI is routing evidence, not an
additional execution of those specialist suites. The code-changing PR above
already proved that all specialist jobs still run for executable changes.
