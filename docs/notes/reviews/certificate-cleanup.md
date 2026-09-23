# Certificate subprocess cleanup review

2026-09-23. Independent read-only review of `work/certificate-cleanup`,
based on `45fe743`. Result: clear for the scoped correction and subsequent
integrated gates.

The CI trace establishes that a second group kill masked an already-raised
timeout error. It does not establish why the operating system denied that
kill. The change guards the cleanup attempt before signalling, including
when signalling itself fails, and retains cleanup on normal peer exit.
It does not accept the peer's JSON when that cleanup fails.

Timeout and exchange-error branches retain bounded follow-up operations.
They distinguish cleanup/reaping failure and a leader that has not exited
from the original exchange failure. No process-group identity guarantee or
cleanup of escaped descendants follows from these tests. The implementation
does not change the certificate's semantic acceptance rules.

Reviewed all production changes, six new deterministic cases and both live
descendant tests. The doubles never signal their dummy PID: both process
creation and the group-kill helper are replaced. Tests require one cleanup
attempt, bounded waits, preserved original diagnostics, and rejection even
of an otherwise accepted response when cleanup is denied. The successful
live peer test independently checks its descendant's process state.

Independently ran the complete certificate test module in the candidate:
18 passed, 43 explicitly skipped, exit 0. This worktree has no Lean binary;
the skips are not evidence of certificate/Lean agreement. The implementer's
ten repeated focused runs and full Python/schema gate are separately
attributed in `../certificate-cleanup.md`. Its old-function injection
demonstration covers the first five deterministic additions; the sixth
case was added later, not retrospectively claimed as an old-fail run.

Integration must rerun the certificate module against the built Lean peer,
the required Lean conformance gate, and the full gate. A newly successful
remote macOS run, not retrying the old failure alone, is the CI closure.

At integrated `5871da8`, the complete certificate module passes all 61
cases against the existing built Lean peer, with no skips, exit 0. Required
real-Lean conformance also passes: 597 cases, no skips, exit 0. No Lean
source changed in this correction; its binaries were not rebuilt while
these consumers ran. The full integration gate and new remote run remain
separate checks recorded in the checkpoint status.

Remote closure: fresh macOS CI run `35924868471` passes at pushed `c59878f`.
All five workflows at that commit pass, including Lean and both P4 oracles.
The earlier failing run remains recorded; it was not hidden by retrying it.
