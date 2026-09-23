# Certificate subprocess cleanup, 2026-09-23

CI run [35922311964](https://github.com/qobilidop/p4blo/actions/runs/35922311964)
failed on macOS in `test_certificate_timeout_reaps_descendant_held_pipes`.
The timeout branch raised `CertificateError` after killing the owned
process group and reaping its leader (`returncode: -9`). Its `finally`
then called `os.killpg` again; that call raised `PermissionError` (`EPERM`)
and replaced the intended timeout diagnostic. The trace establishes the
duplicate call and its effect, not why macOS returned `EPERM` on that call.

`_invoke` now attempts group cleanup once per invocation. Timeout and
exchange-error paths do bounded follow-up reaping; a first cleanup denial
is reported as `CertificateError` alongside the original timeout or
exchange diagnostic. A normal response remains untrusted when cleanup
fails. The normal path still attempts to signal the owned group after its
leader exits, including descendants that closed the pipes. This does not
prove that every descendant terminated.
If a signalled leader fails to terminate within the bounded waits, the
adapter reports that separately. The code does not claim to clean up
descendants that changed process groups, or to explain process-group ID
reuse and macOS permission behavior.

Confidence is high in the control-flow diagnosis and regression: tests
inject a successful first kill followed by a denied redundant kill and
check the timeout survives with exactly one kill. Loading the committed
`_invoke` function into the current module made the initial five new
deterministic cases fail (two redundant-kill cases and three first-kill-
denial cases); the patched function passed them. A fourth denial case
covers bounded exchange-error reaping. This is separate from the live CI
observation. Revisit the policy if a real run shows a first group kill
denied, a leader surviving a successful signal, or a descendant surviving
the normal-path test. Those outcomes need their own captured process-state
evidence before changing the cleanup guarantee.

Focused checks: `nix develop -c uv run pytest -q tests/test_drt_certificate.py
-k 'cleanup or descendant'` passed (8 cases); Ruff format/check and Pyright
on the two changed Python files passed. The live timeout and successful-peer
child tests are included in that selection. Ten consecutive repetitions of
the focused selection also passed (8 cases each). The full
`nix develop -c scripts/check.sh` gate exited 0: 1,425 passed, 598 skipped,
5 expected failures, plus formatting, lint, types, schema/no-drift and
workflow lint. This worktree has no built Lean executable, so the Lean
conformance cases were among the explicit skips; the required real-Lean
gate and external oracle gates were not rerun for this Python-only change.
Independent review is clear in [reviews/certificate-cleanup.md](reviews/certificate-cleanup.md);
the reviewer also ran the complete certificate test module (18 passed,
43 skipped because the Lean binary was unavailable).
