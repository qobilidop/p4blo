# Python package tests

Tests live beside `p4blo/`, outside the installed package, and follow its
components: `arch/`, `drt/`, `edsl/`, `interp/`, `printer/` and `validator/`.
Top-level modules cover the IR and STF APIs. `edsl/typing/` holds must-pass and
must-fail pyright inputs; printer goldens stay with printer tests.

```
uv run pytest impl/python/tests
```

These checks require no Lean executable, P4 simulator or Docker image. DRT
unit checks use fake peers to exercise protocol errors, timeouts and replay
handling. Actual Lean agreement belongs in `tests/conformance/`; native P4
checks belong in `tests/oracles/`. Shared test data and helpers come from
`tests/support/`, never another test module.

See [the test guide](../../../tests/README.md) for the complete organization.
