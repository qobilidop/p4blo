# Milestone 1 release-plan review

Final disposition: **CLEAR** for the finite release plan. The one concrete
expected-failure classification issue found below has a checked narrow fix.
This is a plan review, not a declaration that the milestone is complete.

Reviewed `docs/profile.md`, `docs/evidence.md`, `docs/milestone-1.md`, the
pending `AGENTS.md` / `docs/workflows.md` assurance-command additions, the
quickstart entry points, and relevant CI/oracle selection and exception code.
No production edits or builds were made in the integrator's worktree.

## Clear scope and acceptance

- The profile consistently distinguishes canonical wire representation,
  invalid-but-decodable IR, validated execution, typed-fragment theorems and
  independent application intent. Unknown fields, noncanonical ProtoJSON,
  resource limits, custom externs and unproved validators are not hidden.
- Rejected host configuration is explicitly a **pre-execution** preservation
  claim, not rollback after a running program has mutated state. The strict
  configuration fix and its separately reviewed tests must be integrated
  before the release revision is selected.
- A fresh worktree, locked sync, both package/audit/native builds, full ordinary
  tests with retained JUnit, required real-Lean conformance, then the finite
  assurance command on frozen sources is sufficient for the proposed bounded
  claim. There is no need to resume the parked application proof drafts.
- All required oracle availability must be demonstrated. Verifying the only
  ordinary skip is the named optional local XDP-image check prevents silent
  P4/printer/oracle skips. The four P4/Python/Lean CI workflows must succeed;
  inspect and record the fifth XDP workflow separately, without calling an
  external snapshot failure a pass or making kernel execution a milestone.
- The command additions accurately describe current runner behavior and its
  intentionally demonstrated weak-observer survivor. Build errors, skipped
  selected tests or incomplete source restoration do not count as kills.

## Concrete issue found: broad BMv2 xfail

`test_vector_passes_on_bmv2[register_bounds/bounds.stf]` was marked strict
xfail without `raises=`. Both an ordinary divergence and `ORACLE ERROR` used
`pytest.fail`, so even exact node/count checking could accept a crash or setup
failure as the known register discrepancy. The four SpecTec exceptions already
have dedicated precise exception classifiers; this fifth one did not.

Root authorized a narrow test-only fix, owned in the isolated
`p4blo-milestone-adversarial` worktree, with exact two-packet mismatch matching,
dedicated exception/raises marker, actual-pytest error/XPASS controls and a live
immutable-image replay. The pre-fix new regression genuinely demonstrated the
problem: the inner oracle-error test exited zero with one xfail, so its outer
expectation of a real failure failed. This review does **not** substitute for
root's independent review of that implementation. Final release verification
must use the fixed, checked revision and retain the actual five failure
identities/reasons, not just a count of five.

## Final documentation bookkeeping (not new engineering scope)

After the concrete gates pass, update the matrix's pending Program/Entries
row/closeout list and the corresponding milestone checkboxes with exact
evidence. Retain the named code-gate revision, fresh-worktree provenance,
commands, JUnit/skip/xfail inventory and CI run links. A subsequent docs-only
completion commit may cite that exact code revision; do not relabel earlier
logs as tests of the newer commit. The remaining optional proof exclusions
are appropriate and should not expand automatically.

No other claim or acceptance blocker found in this review.

## Finding resolution

Root independently reviewed the isolated test-only fix and ran all 15 new
deterministic classifier/actual-pytest wiring regressions successfully, then
separately ran the real known BMv2 vector: one precisely classified xfail,
no skips, exit 0. Owner full BMv2 module result was 36 passed / one exact
xfail / no skips. Root cleared the fix for integration. This code review is
attributed to root, not presented as independent review by its implementer.
The final release plan is therefore clear once that checked fix joins the
selected frozen code revision. Final gate execution and milestone completion
remain the integrator's explicit next actions, not completed by this report.
