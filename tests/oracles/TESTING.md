# External oracle tests

These suites compare with P4-SpecTec and BMv2, check printed P4 with p4c, and
exercise the adapters that make those comparisons. Drivers, pinned original
sources, patches and inventories live here too. [The driver reference](README.md)
explains setup and exact oracle boundaries.

```
uv run pytest -m spectec
uv run pytest -m bmv2
uv run pytest -m p4c
uv run pytest tests/oracles -m 'not oracle'
```

External tests explicitly declare their dependency. Pure translator,
classifier, catalog and readback-parser checks run without external tools,
even when their names mention an oracle. Program-specific comparisons may stay
beside their assets under `tests/programs/`; the marker selects them too.

`P4BLO_REQUIRE_IL_EXPORT=1` and `P4BLO_REQUIRE_SPECTEC_COVERAGE=1` make missing
export/coverage tooling fail instead of skip. Oracle characterization requires
exact recorded answers; known discrepancies use narrow, strict expected
failures. See [the test guide](../README.md) and
[discrepancies](../../docs/oracle-discrepancies.md).
