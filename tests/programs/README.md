# Program tests

Program checks specify intended behavior independently of the interpreters.
`corpus/<program>/` keeps the eDSL source, golden IR, README, STF vectors and
specialized behavior tests together. `examples/<application>/` keeps verification
assets for canonical public sources under `examples/`.

`test_corpus.py` discovers each corpus program, checks that its source rebuilds
its golden, and replays its vectors. Other checks cover packet boundaries,
state persistence and application-specific intent. Shared builders and expected
answers live in `tests/support/`; tests never import one another.

```
uv run pytest tests/programs -m 'not lean and not oracle'
```

Tests that also compare with Lean or an external P4 tool declare `lean`,
`spectec` or `bmv2`. The specialist CI jobs find them here automatically by
marker. See [the test guide](../README.md).
