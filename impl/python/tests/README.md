# Unit tests

Does each piece of the Python implementation do what
[`docs/ir-semantics.md`](../../../docs/ir-semantics.md) and
[`docs/arch-supports.md`](../../../docs/arch-supports.md) say, taken one at a
time?

These are layers 1 and 2 of the testing strategy in
[`docs/design.md`](../../../docs/design.md#testing-strategy): unit and
property tests on the primitives (values, expressions, parsers, controls,
deparsers, tables, externs, CRC, the STF reader), and one tiny malformed
program per validator rule. The printer, the eDSL (including its
pyright-checked static guarantees), the IR text form, the expression
typer and the two architectures are checked here too, each against
hand-computed answers.

```
uv run pytest impl/python/tests
```

`test_crc.py` also holds probes that run on the external oracles; they
skip when an oracle is not built, and the oracle workflows select them
with `-k spectec` and `-k bmv2`.
