# Classify the known BMv2 discrepancy narrowly

The milestone release review found a concrete false-pass risk in the old
`register_bounds/bounds.stf` expected-failure marker. It was strict, but had
no `raises=` restriction. The replay test uses `pytest.fail` for both semantic
disagreement and an oracle error, so an unavailable/broken execution reported
as `error` on that vector could be hidden as the one expected discrepancy.
Checking just the five expected-failure node identities would not catch it.

The new test-only classifier raises `KnownBMv2RegisterBoundsDisagreement`
only for this exact vector, `status == "fail"`, and the complete observed
two-line mismatch:

```text
line 46: expected 040700 $ on port 0, got 0407ff
line 52: expected ff0100 $ on port 0, got ff01ff
```

These are the two out-of-bounds reads whose input destination is `ff`; the
other seven outputs, including in-range accumulation and wrap, match. The
existing driver/judge reports all mismatches, so a missing, additional,
changed, reordered or differently formatted mismatch cannot silently earn
the exception. The marker is still strict and now restricts `raises=` to
that dedicated exception. A corrected result becomes strict XPASS; an oracle
error or other divergence is a real failure. An unavailable oracle still
skips and must separately fail the release's required-availability check.

No interpreter, printer, oracle driver, image, semantics or golden changed.
This narrows an existing documented exception; it does not add a sixth one.
Hardcoded line numbers deliberately fail closed if the vector or diagnostic
format changes and need a reviewed update, rather than a permissive regex.
Decision confidence: high for this pinned two-output discrepancy; no claim
that this classifier handles arbitrary future BMv2 divergences.

## Evidence and reproduction

Before the classifier change, the newly added actual-pytest wiring regression
for an `error` verdict failed: the inner test process returned **0 with one
xfail**, not the required real failure. Log:
`/tmp/p4blo-milestone-bmv2-before.log`. This was a genuine marker survivor, not
a compile/setup failure.

The actual existing BMv2 image was available. A direct unmarked run of
`tests/corpus/register_bounds/register_bounds.txtpb` and `bounds.stf` returned
exactly the two lines above, with `status='fail'`, not `error` or `skip`.
Log: `/tmp/p4blo-milestone-bmv2-known.log`. The local image identity inspected
during these checks was
`sha256:2b255b539b7c7dab31460422150d577990a2572c8caab253479839f27dc81b0d`;
no image was built or changed.

Permanent deterministic regressions cover ten rejected classifier variants,
the exact positive/marker contract, and actual isolated pytest outcomes for
the known mismatch, an oracle error, an extra mismatch, and corrected behavior.
They require genuine nonzero exits for error/change/strict XPASS and exactly
one xfail only for the known mismatch. No Docker is needed for those controls.

```sh
nix develop -c uv run pytest tests/test_oracle_bmv2.py -q -rxX
nix develop -c uv run ruff format --check tests/test_oracle_bmv2.py
nix develop -c uv run ruff check tests/test_oracle_bmv2.py
nix develop -c uv run pyright tests/test_oracle_bmv2.py
```

Final owner live module gate: **36 passed, one exactly classified expected
discrepancy, no skips**, exit 0 (51.92 seconds), recorded in
`/tmp/p4blo-milestone-bmv2-final.log`. Scoped Ruff, formatting and Pyright all
passed. Independent root review is **CLEAR**: all 15 new deterministic
regressions passed (1.09 seconds), and a separate actual pinned-image run of
the known vector produced the one classified xfail with no skips (2.94 seconds).
The source was frozen during both independent checks.

The final combined clean-checkout release gate belongs to the integrator;
the earlier full gate for the finite runner is not relabeled as covering
this later classification change.
