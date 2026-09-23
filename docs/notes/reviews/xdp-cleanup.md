# XDP compile gate container lifecycle review

Read-only implementation inspection and isolated runtime reproduction on
2026-09-23. **Confirmed cleanup defect** in the original
`tests/test_xdp_build.py` gate: a timeout kills the attached Docker client,
not necessarily the daemon-owned container. `--rm` removes a container
after it stops; it does not make a still-running container stop when the
client is killed. No implementation edits or image builds were performed.

## Independent reproduction and cleanup

Used the already-present `p4blo-bmv2` image, ID
`sha256:2b255b539b7c7dab31460422150d577990a2572c8caab253479839f27dc81b0d`.
The unique explicitly owned name was
`p4blo-review-xdp-timeout-6f82289d69384f8b8f2cc4edf2d96b67`.
An initial successful exact-name `docker ps -aq` query was empty.

Ran with `--rm --name EXACTNAME --network none --read-only --cap-drop ALL
--security-opt no-new-privileges --user 65534:65534 --pids-limit 16
--memory 64m --entrypoint /bin/sh`, executing only
`printf ready; sleep 8`. The Python caller used `subprocess.run` with
captured output and a two-second timeout.

Observed `TimeoutExpired(timeout=2)` with partial stdout `b'ready'`.
An immediate exact-name `docker inspect` succeeded and reported
`Running=true`, `Status=running`, no OOM/error/dead state. This demonstrates
the actual client/container lifetime mismatch, not a mock approximation.

A `finally` block issued `docker rm -f EXACTNAME`, which exited 0 and
returned that name. A subsequent **successful** exact-name
`docker ps -aq --filter name=^/EXACTNAME$` returned an empty string. The
complete probe exited 0; the owned container is gone. No other containers,
images, volumes, capabilities or network settings were modified.

## Smallest useful fix

Keep this inside XDP test infrastructure, not production Python or the
generic interpreter. A small helper should:

1. Generate a unique task-prefixed container name before starting Docker
   and pass it explicitly via `--name`. Never derive cleanup targets from
   broad filters, image names, daemon-wide listings or shared environment
   variables. Preserve all current runtime restrictions.
2. Enclose the Docker run in `try/finally`; clean up the exact owned name
   on success, nonzero exit, timeout and interruption. Success can already
   have auto-removed it; that case is expected.
3. Bound cleanup subprocesses separately. Attempt `docker rm -f NAME`,
   then use a successful exact-name listing to verify absence. A nonzero
   inspect/list command is not evidence of absence: it may mean the daemon
   is unreachable. If removal reports failure but a successful subsequent
   listing is empty, the `--rm` race is harmless.
4. Surface cleanup failures rather than silently passing a successful gate.
   Preserve useful original timeout/nonzero output as well as cleanup
   diagnostics; avoid replacing the real failure with an uninformative
   secondary exception. Do not report that cleanup succeeded when it could
   not be verified.

This handles ordinary exceptions and bounded cleanup failures, not host
power loss, interpreter SIGKILL or an unreachable Docker daemon. A remote
creation request still in flight when the client is killed is a subtler
race: prefer a separated create/start lifecycle if addressing that stronger
claim now, or explicitly avoid promising daemon-crash-proof reclamation.
Do not add privileged access, a global reaper, or shared-container pruning
to close this small gate defect.

## Regression requirements

Add deterministic ordinary Python tests that do not require Docker or the
optional image. Inject/mock the subprocess boundary rather than sleep in
the regular test suite. Assert exact-name cleanup and successful absence
verification for:

- normal exit 0 (including already auto-removed container);
- nonzero program exit, preserving the program output/result;
- `TimeoutExpired`, preserving that failure after cleanup;
- an ordinary launch exception/interruption handled by `finally`;
- failed removal with container still present: test must fail;
- daemon/listing failure: test must fail, not count nonzero as absence;
- failed removal followed by successful empty listing: harmless race.

Inspect the command construction in tests to ensure all safety flags remain
and unrelated names never enter cleanup. The already demonstrated real
daemon reproduction is enough motivation; after implementation, a second
tiny uniquely named live timeout run can check the helper actually removes
its container, with the same strict bounds and verified cleanup. Native XDP
compiler/ELF/BTF checks need not be rebuilt for this lifecycle-only change.

This review concerns observer resource cleanup only. It does not change the
compile-only assurance claim or add any kernel BPF load/attach behavior.

## Candidate implementation review

**Final disposition: clear for integration.**

Read-only review of `p4blo-xdp-cleanup/tests/test_xdp_build.py` finds the
small named-container helper sound for the scoped cleanup claim. UUID names
are generated internally; the helper passes the exact name to Docker and
to force removal. Nested `finally` executes a separately bounded exact-name
listing even when removal times out. Successful empty listing handles
normal auto-removal; listing/daemon failures and surviving containers are
errors. Normal success/nonzero results and runtime exceptions survive when
cleanup succeeds. The caller's native result/known-answer assertions remain
unchanged. All restrictions remain, with nonroot user now explicit in the
run command as well as the image.

Independently ran focused pure tests using the review environment from
`/tmp`, with bytecode/cache writes disabled: **15 passed, 1 Docker test
deselected**, exit 0. Candidate `git diff --check` also passed. Additional
read-only injected checks confirm startup `OSError` and `KeyboardInterrupt`
both preserve the original exception and still run exact cleanup/listing.
A simultaneous runtime timeout and removal timeout retains both through
Python exception chaining. Exact network/user/capabilities/security/tmpfs/
pids/memory/read-only command restrictions were also checked independently.

Suggested permanent startup-exception and safety-flag assertions augment
the six existing deterministic regression cases. Live post-fix helper
checks are being performed separately by the integrator; native XDP image
checks were not repeated by this reviewer. No implementation blocker found;
the startup creation race, daemon outage and forced-process-death limits
above still bound the assurance claim.

### Final delta and live-check evidence

Reviewed the final permanent startup-`OSError` case and exact complete argv
guard; the latter checks every runtime restriction as well as image and
arguments. Independently reran the final pure file selection: **16 passed,
1 Docker test deselected**, exit 0. This supersedes the earlier 15-test run.

The integrator additionally reports two actual calls through the new helper
using the existing BMv2 image, explicit nonroot user and dropped capabilities:
normal `printf` returns its original result, and a sleeper that prints
`ready` preserves `TimeoutExpired` after two seconds. In both cases the
helper removed its uniquely owned container and exact-name absence was
verified. These post-fix live checks are attributed integrator evidence;
the reviewer independently reproduced and cleaned up the pre-fix leak.
The integrator's full file gate reports 16 passes and one explicit missing
local XDP-image skip, not a native XDP rebuild/pass for this change.
