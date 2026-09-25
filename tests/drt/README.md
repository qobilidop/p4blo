# Differential and generated tests

Do the Python and Lean interpreters agree on programs and packets
nobody wrote by hand, and would the tests notice if one of them were
wrong?

These are layers 5 and 6 of the testing strategy in
[`docs/design.md`](../../docs/design.md#testing-strategy). The
`test_drt*` files drive the differential loop of `p4blo.drt`: typed
generated programs and request sequences with complete extern state,
shrinking, retained replays, the coverage-guided families, the adequacy
criterion that every Lean rule tag is hit (`test_drt_coverage.py`, with
[`../drt-unhit-tags.json`](../drt-unhit-tags.json)), the pipe protocol
that must fail rather than hang, and the execution certificate. The
fault side checks that a wrong implementation is caught:
`test_conformance.py` requires every mutant of
[`../conformance/`](../conformance/README.md) to be killed, and
`test_assurance.py` checks the fail-closed orchestration of
`scripts/check-assurance.py`, whose expensive campaign stays opt-in.

```
uv run pytest tests/drt
```

The suites that talk to Lean skip when it is not built; set
`P4BLO_REQUIRE_LEAN=1` after `scripts/check-lean.sh` to require them.
