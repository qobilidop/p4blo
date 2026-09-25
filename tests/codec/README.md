# Codec tests

Does the wire encoding carry every IR value there and back, and does the
decoder reject what it must, with the diagnostic it names?

These tests belong to layer 1 of the testing strategy in
[`docs/design.md`](../../docs/design.md#testing-strategy), applied to
the boundary between the protobuf wire syntax and the abstract syntax
that Lean owns. Each syntactic category (leaves, expressions, lvalues,
statements, declarations, tables, parsers, blocks, whole programs and
host entries) has its own file of independently written wire answers,
so a defect that survives a round trip is still caught. The same
answers are replayed against the Lean codecs where the executable is
built.

```
uv run pytest tests/codec
```

`test_codec_leaves.py` and `test_codec_expr.py` hold the generators and
helpers the other files import.
