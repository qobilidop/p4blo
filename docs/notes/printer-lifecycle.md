# Owned p4test container lifecycle

2026-09-23. A full integration gate stalled on its own immutable p4c image's
version probe. The Docker client already had a 600-second timeout, but its
container remained marked running after printing the successful version with
no processes and no mounts. Matching the exact image, command and start time
established ownership. Removing only that container released the probe;
listing the exact ID then confirmed absence. The full gate passed all printer
goldens. No daemon restart, prune, image rebuild or unrelated cleanup occurred.
The underlying Docker/containerd cause remains unproved.

`run_p4test` now assigns an unpredictable owned name and always performs bounded
removal followed by an exact anchored-name absence check. The run retains its
own bounded timeout. Normal `--rm` completion can make removal return nonzero;
absence, not that exit code, decides whether anything remains. A removal client
exception, failed/timed-out absence query or survivor raises PrinterCleanupError.
Availability handling does not catch this class: cleanup uncertainty is a
failure, never an optional skip. The final listing is attempted even after a
removal client exception. Cleanup does not promise recovery from an unavailable
daemon; it fails visibly with the exact owned name for later investigation.

A local immutable-image inspect has a 15-second budget. If present, its version
probe gets 30 seconds; if absent, the prior 600-second run budget is retained
for Docker's implicit pull plus probe. Each cleanup command gets 15 seconds.
Compiler invocations keep their previous 600-second budget and failure policy.
No image builds or new security-setting changes are introduced. Cold pull
remains possible just as before; this is not an offline availability check.
Confidence: high in bounded owned cleanup and fail-closed diagnostics; medium
in the warm-probe budget. Revisit with measured slow-host failures rather than
silently broadening compiler skips. The independent XDP helper is unchanged;
a shared abstraction is deferred until policies actually converge.

Fifteen deterministic tests cover successful/nonzero execution, client startup
and timeout, removal startup/timeout, surviving containers, failed/timed-out
listing, warm/cold budgets, cleanup-error propagation through availability,
and compiler failure/timeout/cleanup propagation. Exact commands and owned-name
filters are asserted. They never operate on real containers. The complete
printer suite plus these regressions passes **71 tests**, exit 0, against the
existing pinned image, with no skips. Ruff format/check and Pyright pass.
Log: `/tmp/p4blo-printer-owned-focused.log`. Independent review is clear in
`reviews/printer-lifecycle.md`, including extra interruption, compound failure
and cache probes. The merged full gate remains the integrator's obligation.
