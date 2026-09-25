# External oracle tests

Does p4blo agree with the P4 tools it does not control: the P4-SpecTec
simulator, the P4-SpecTec IL export, and BMv2's `simple_switch`?

These are the oracle half of layer 4 of the testing strategy in
[`docs/design.md`](../../docs/design.md#testing-strategy), and the
evidence for claim 2. Every corpus and example vector replays on
P4-SpecTec through the v1model shim (`test_oracle.py`) and through the
block architecture (`test_oracle_block.py`), and on BMv2
(`test_oracle_bmv2.py`, `test_bmv2_readback.py`); generated programs run
on P4-SpecTec at CI size (`test_oracle_generated.py`); real P4 comes
back through the IL bridge (`test_frontend_spectec.py`); every in-scope
P4-SpecTec rule is exercised or excluded with a reason
(`test_spectec_coverage.py`); and the pinned rule inventory resolves the
ledger's `SpecTec:` citations (`test_spectec_rules.py`).

The drivers, patches and pinned inventories these tests use live in
[`../oracle/`](../oracle/README.md), which says how to build each
oracle. `tests/conftest.py` marks every module here but
`test_spectec_rules.py` `oracle` by file stem, so `scripts/check.sh`
deselects them and the oracle workflows run them.
With the oracles built:

```
P4BLO_REQUIRE_IL_EXPORT=1 uv run pytest -m oracle -k "not bmv2"
uv run pytest tests/external/test_oracle_bmv2.py
```

Each suite skips when its oracle is missing;
`P4BLO_REQUIRE_IL_EXPORT=1` and `P4BLO_REQUIRE_SPECTEC_COVERAGE=1` turn
the IL-export and coverage skips into failures.
