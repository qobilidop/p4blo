# Differential and generated tests

Do the Python and Lean interpreters agree on generated programs and
request sequences, and would these tests notice a wrong implementation?

These suites exercise typed generation, shrinking, retained replays,
coverage-guided families, complete extern state and deliberate semantic
faults. `test_drt_coverage.py` checks the adequacy criterion that every
Lean rule tag is hit, with the retained
[unhit-tag ledger](../coverage/unhit-tags.json). The witness-table and
ledger consistency checks also stay here because they describe this
conformance evidence.

Pure generation, replay, state-decoding and fake-peer protocol checks live
beside the Python package in
[`impl/python/tests/drt/`](../../../impl/python/tests/drt/). They require
neither Lean nor a native P4 oracle. Shared constructors and campaign
helpers live in [`tests/support/`](../../support/); suites never import
another test module.

```
uv run pytest tests/conformance/execution
uv run pytest impl/python/tests/drt
```

The real-Lean cases skip when it is not built; set `P4BLO_REQUIRE_LEAN=1`
after `scripts/check-lean.sh` to require them. The broader
[conformance suite](../README.md) retains fixed semantic fixtures and
assurance fault campaigns.
