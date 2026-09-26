# CI speed final-head review

Independent read-only Codex agent review of `f6c3a6e` through final PR #3
head `30c567c5e3e7d5e337d19cb7aa843c2042d64ba5`, in an isolated worktree.
The existing ci-speed review was checked against the final workflow and
documentation follow-ups. This is AI-agent review, not human review.

Confirmed defects: none. Final docs preserve the standalone-query limitation
and the separately dated cache decision's rationale and revisit trigger.
Cache restore/save keys and paths agree; only main saves; build/test steps
remain mandatory. Differential workers share read-only Lean executables;
probe JSON uses per-worker temporary directories and expensive fixtures
already have loadgroup markers.

Checks: `git diff --check f6c3a6e..30c567c`, exit 0; pinned-environment
`actionlint .github/workflows/lean.yml`, exit 0. Inspected check-lean.sh,
tests/conftest.py, package configurations, workflow and documentation diff.
Plain actionlint was absent outside Nix; the pinned rerun succeeded.
No Lake/pytest build, cache timing or stale-module experiment was repeated
by this reviewer. The earlier recorded experiments remain attributed to
the author and earlier reviewer. Remote CI was pending at review time;
the integrator must check final-head success before merging.

Closure prose follow-up: the reviewer confirmed that README's exclusion of
P4 source execution contradicted the documented frontend subset, and that
calling Lean normative contradicted the dated semantics decision. It also
found that same wording in docs/design.md's goals. Both pages now describe
independent semantics checked against P4-SpecTec, with no universal
Python equivalence claim; README links the frontend's bounded coverage.
