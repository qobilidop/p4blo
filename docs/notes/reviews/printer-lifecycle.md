# Owned printer container lifecycle review

Final review: clear for this narrow test-infrastructure fix.

2026-09-23. Independently read `tests/test_printer.py`, the new lifecycle tests
and evidence note in `p4blo-printer-probe`. No candidate edits, Docker builds,
real container mutations or daemon operations were performed by this review.
The earlier actual hang diagnosis is retained separately in
`printer-probe-hang.md`.

The helper creates a fresh UUID-owned name and passes it explicitly to Docker.
Every execution exit, startup error and timeout enters bounded cleanup of only
that name. The exact anchored-name listing is attempted after a removal client
exception as well as after normal/nonzero removal. Normal `--rm` may legitimately
make removal return nonzero; a successful empty exact listing establishes
absence instead of assuming removal's exit code is authoritative.

Survivors, failed/timed-out absence queries and removal-client exceptions raise
the separate PrinterCleanupError. Availability's OSError/TimeoutExpired handler
does not swallow that class, so uncertain cleanup is never silently converted
to an optional compiler skip. When cleanup succeeds, original execution results
and startup/timeout errors are preserved. Simultaneous execution and cleanup
failure correctly reports the latter while retaining exception context.

Warm-image inspection is bounded at fifteen seconds and selects the shorter
thirty-second version probe. A missing-image/nonzero inspection retains the
previous six-hundred-second implicit-pull allowance, explicitly documented rather
than called an offline check. Compilation retains its old six-hundred-second
budget and error policy; compiler rejection/timeout do not become availability
skips. No image pin, printer behavior, mount policy or security setting changes.

Independent checks:

- All **15 deterministic lifecycle tests passed**, exit 0, 0.10 seconds.
- An extra scoped mock probe confirmed a KeyboardInterrupt during the run
  still attempts owned removal and exact listing before propagating.
- A compound client timeout plus removal-startup failure remains a visible
  PrinterCleanupError with the removal exception as cause, even when the
  later absence query succeeds.
- An unavailable cleaned-up version timeout is cached: two availability calls
  invoke the mocked probe once. The cache was cleared in that isolated review
  process; no shared test/process state changed.

Inspected the owner log reporting the full actual pinned-image printer suite
plus regressions: **71 passed**, no skips, exit 0. That real-container run and
owner Ruff/format/Pyright checks are attributed, not rerun by this reviewer.
The new deterministic tests verify exact commands, ownership filters and all
requested bounded failure branches.

No remaining blocker. The fix bounds and reports lifecycle failure; it does
not diagnose or guarantee recovery from the underlying Docker/containerd
inconsistency. The thirty-second warm budget is reasonably recorded as a
revisitable operational choice. Main integration owns its full-suite gate.
