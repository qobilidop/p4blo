# Lean conformance tests

Does the Lean semantics give the same answer as the Python reference
interpreter, and do both match answers written independently of either?

These are the Lean half of layers 4 and 5 of the testing strategy in
[`docs/design.md`](../../../docs/design.md#testing-strategy): the validity
checker against the Python validator, architecture-free libraries and
Python eDSL locals, and parser-error call copyback. Application packet,
action and state comparisons live under `tests/programs/`; generated
programs and sequences live under `tests/conformance/execution/`. Each file names in its
docstring the part of execution it observes and what it does not claim.
Formal proofs belong only to the core IR in `spec/ir/`; running a Lean
comparison does not prove an application or architecture property.

Build Lean first (`scripts/check-lean.sh`), then:

```
P4BLO_REQUIRE_LEAN=1 uv run pytest tests/conformance/semantics
```

Without `P4BLO_REQUIRE_LEAN=1`, the `lean_binary` fixture in
`conftest.py` skips these when the executable is missing. The
required Lean CI gate selects every test whose name starts with
`test_lean_agrees`, wherever it lives (`uv run pytest tests -k
lean_agrees`), so new conformance tests need no file list.
