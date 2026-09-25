# Lean conformance tests

Does the Lean semantics give the same answer as the Python reference
interpreter, and do both match answers written independently of either?

These are the Lean half of layers 4 and 5 of the testing strategy in
[`docs/design.md`](../../docs/design.md#testing-strategy): the validity
checker against the Python validator, programs authored in Lean's typed
source language (`impl/lean/`) against hand-written expected states,
and the corpus's forwarder and firewall run step by step, from call entry
to whole pipelines, on both interpreters. Each file names in its
docstring the part of execution it observes and what it does not claim.

Build Lean first (`scripts/check-lean.sh`), then:

```
P4BLO_REQUIRE_LEAN=1 uv run pytest tests/lean
```

Without `P4BLO_REQUIRE_LEAN=1`, the `lean_binary` fixture in
`tests/conftest.py` skips these when the executable is missing. The
required Lean CI gate selects every test whose name starts with
`test_lean_agrees`, wherever it lives (`uv run pytest tests -k
lean_agrees`), so new conformance tests need no file list.
