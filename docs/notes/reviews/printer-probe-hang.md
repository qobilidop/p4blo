# Printer availability probe hang diagnosis

Disposition: diagnosed a container/client completion stall, not evidence of a
p4test compilation hang. No process or container was stopped by this reviewer.

2026-09-23. Read-only inspection of main's `tests/test_printer.py`, the owning
process tree and bounded Docker diagnostics. Every Docker diagnostic used an
eight-second subprocess timeout; none timed out. No image builds, daemon
restart, cleanup or unrelated-worktree mutations were performed.

## Observed ownership and state

Main `scripts/check.sh` PID 56874 owns pytest PID 56985, which owns Docker client
PID 69034. The latter had run approximately six minutes with the exact command
`docker run --rm <pinned-p4c-image> p4test --version`. The integration output
was waiting around 84%, not showing a test failure.

The exact matching container is
`8d98e4e64d913c309295a04f9634a7711a4296ed45094fa7970a0ea84490ab21`
(`keen_buck`). Read-only observations:

- Inspect reports running, no pause/restart/dead/OOM flag, no error and a start
  time of `2026-09-24T02:24:34.483801937Z`.
- `docker top` returns only its header: no process rows.
- `docker stats --no-stream` reports zero PIDs, zero CPU and about 132 KiB.
- Its logs already contain `p4test` and
  `Version 1.2.5.15 (SHA: 325e90e BUILD: Release)`.
- The pinned arm64 Linux image is present. Docker info/image/list/inspect
  commands respond promptly. Host disk has approximately 512 GiB available;
  this does not establish the Docker VM's free space.

Thus p4test has at least produced its expected version, and no compiler process
is visible. The evidence points to stale daemon/container lifecycle completion
or an attached-client wait after program exit, rather than active compiler
work, a missing-image pull, daemon-wide unresponsiveness or observed OOM. These
checks do not establish the precise containerd/Docker internal cause.

## Existing timeout and lifecycle gap

`p4test_available` already has `timeout=600` and catches TimeoutExpired to return
a cached unavailable reason. The problem is not an absent timeout: the probe
permits a ten-minute stall and killing the client need not remove a daemon-owned
container. It has no explicit owned name or finally cleanup/absence check.
The actual compilation command separately uses 600 seconds and has the same
container lifecycle gap; its timeout is currently a test failure rather than
an availability skip. Preserve that distinction deliberately.

The XDP test helper already documents and tests this client-versus-container
problem. A narrow printer helper can follow the same ownership pattern without
changing printer semantics or introducing global cleanup: unique owned name,
bounded client command, bounded finally removal of only that name, and exact
absence verification. Cleanup failure/survival must remain visible, not be
silently converted into an optional-image skip by a broad exception handler.
Separate a short availability budget from the compiler budget; for example a
30-second version check and the existing longer compile limit. Decide/document
whether availability may pull missing images rather than accidentally treating
slow registry access as compiler work.

## Proposed safe immediate action and regressions

After the integrator records evidence, re-resolve the exact container ID above
and confirm image/command/ownership. Remove or stop only that task-owned target,
then verify it is absent by an exact-ID listing; observe the owning client and
test exit. Do not restart the daemon, prune resources or touch unrelated stopped
development containers. An interrupted availability probe or ensuing skip is
not a successful compiler gate; rerun the bounded pinned compiler check after
the lifecycle fix or record it unavailable.

Permanent deterministic tests should cover normal exit, startup failure,
nonzero Docker failure, client timeout, cleanup timeout, surviving container
and failed absence query. Assert exact ownership/cleanup arguments and bounded
timeouts; assert version-probe caching does not rerun a known unavailable probe.
Keep real compiler rejection distinct from Docker unavailability and verify
compiler timeouts still fail instead of silently skipping. A narrowly owned
live success/timeout test is useful only after the integrator authorizes it and
must prove exact absence on both paths. This review did not create such a test
container or implement the helper.
