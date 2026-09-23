# Authoring replay retention review

Reviewed the integrator's pending `tests/test_lean_edsl.py` change on
2026-09-23, independently and read-only. No production code changes.

## Assessment

Clear for integration. Differential comparison and replay saving now precede
the independent known-answer assertion. This closes a real evidence-loss
path without replacing known answers with interpreter agreement. Protocol
errors carrying a report retain that report; errors without one still raise.

The new regression changes actual Python `Env.read`, rather than fabricating
a report. It requires the saved exact program, request, four-port setting
and seed, then replays Python `07` versus Lean `13` while the fault is live.
The scoped patch restores even on an assertion failure; replaying the same
bundle after restoration must agree. The other regression substitutes a
valid read-y program for read-x, establishes both-engine agreement, and still
requires independent expected-output rejection. No differential artifact is
claimed for a shared wrong answer.

## Independently executed evidence

Using the existing stable main binaries and the review worktree's Python
environment, directly invoked the default-target check, all 21 authored
examples, and both new regressions: **24 checks passed**, process exit 0.
Temporary bundles were isolated outside the implementation worktree. No
build, source edit or implementation-worktree cache write was performed.

Also inspected `/tmp/p4blo-edsl-replay-before.log`: the pre-fix regression
failed at the genuine `07` versus `13` known-answer assertion before reaching
save-on-failure, not at setup or an import error. That log is attributed
integrator evidence, not an independently repeated pre-fix run.

This is a replay-retention improvement for this gate, not proof of Python
correctness or a general guarantee that every failure is serializable.
