# Milestone usability review

2026-09-23. Independent integrator review of the isolated
`work/milestone-usability` candidate based on `169a2c9`. **CLEAR** for the
bounded authoring/run guide, corrected claims and executable snippet tests.
This is not final milestone or whole-repository gate acceptance.

Read the complete quickstart, six collected tests, evidence note and four
README diffs. Both complete examples are built from their independent
sources, with expected packet bytes checked against tracked STF vectors.
The Python path keeps one loaded object per sequence; the Lean path keeps
one actual fixed-program server per sequence. Python resolves configuration
but does not execute packets in that Lean path. Returned errors/diagnostics,
reply count and process failures are checked rather than equating process
exit zero with correct packet behavior.

The guide labels complete raw IR assembly separately from verified typed
fragments, explains build-time Python versus recorded branches, and uses the
existing public APIs/executables without adding a second demonstration runner.
Its checked Lean example instantiates the actual lowering theorem. Tests
execute the exact marked source snippets and exercise actual symbolic-bool,
host-installation, output-port, usage and per-request error diagnostics.
No application source, golden, runtime, proof or wire protocol changed.

Requested one portability/shell-discipline correction: resolve the repository
root once inside both Python heredocs, then use absolute paths. The owner
applied it and reran the final six tests. The integrator independently ran
`P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_quickstart.py -q`
against stable candidate binaries: **6 passed**, exit 0, no skips. No rebuild
occurred during this review. The owner's earlier 240-test application/corpus
gate is correctly distinguished from the final snippet rerun.

No remaining blocker found. The longer Lean-server snippet is a documented UX
tradeoff, not reason to add a new CLI in this milestone. Main still owns the
combined required/full gates and clean-checkout release evidence.

## Integration cache diagnosis

The first main snippet run passed five cases but failed the public Lean import.
Main retained `ir/.lake/build/lib/lean/P4blo.olean` from the earlier namespace
migration; the old dependency module shadowed the actual user package during
the standalone import. The fresh candidate had no such artifact.

With no main binary consumers running, the integrator moved only the two owned
build directories to `/tmp/p4blo-main-cache.BVXsJp`, verified their absence,
and rebuilt both packages/default audits/native tests successfully. The old
IR-side module is now absent, while the user-side module exists. All six
integrated quickstart cases pass, exit 0. The backup is recoverable; no source
or runtime behavior changed. This strengthens the reason for final acceptance
from a fresh checkout rather than relying on the historical main cache.
