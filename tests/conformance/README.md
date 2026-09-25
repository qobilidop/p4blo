# Conformance corpus

The Lean semantics' answers on a fixed set of programs and requests, kept
as data. Each file under `fixtures/` is one fixture: a program, an ordered
sequence of requests sent from fresh extern state, and for each request
the reply `p4blo-lean run` gave. An implementation is checked against the
fixtures without a Lean process; Lean is checked against them by answering
the same requests again. The format, the checks and the command line are
in `impl/python/p4blo/conformance.py`; the input set is `inputs.py`.

## Format

A fixture is a JSON object, `"format": "p4blo.conformance"`, `"version": 1`:

- `name`: the file's stem.
- `source`: where the inputs came from. `stf` names a corpus or example
  golden and its STF vector, whose packets became the requests with the
  entries installed before each; `drt` names a golden and the seed and
  count of `p4blo.drt.generate.generate`; `family` names a seed of
  `tests/oracle/generated.py`'s `materialize`, its family and description.
- `lean`: the last commit that touched `spec/ir` or `spec/arch` when the
  fixture was answered, and a SHA-256 digest of the files the endpoint is
  built from. Informative only; see below.
- `ports`: the switch's port count, the `--ports` of `p4blo-lean run`.
- `program`: the program in the protobuf JSON wire profile
  (`p4blo.ir.dump_json`, proto field names).
- `steps`: one object per request, in order, `{"request": ..., "reply": ...}`,
  each exactly a line of the pipe protocol of `p4blo.drt.run`: the request's
  `entries` (protobuf JSON), `ingress_port` and `packet` (hex); the reply's
  `outputs` as `[port, hex]` pairs with an optional `diagnostic`, or an
  `error`, and always `state` (every extern's logical state, values as
  hexadecimal strings) and `coverage` (the Lean rule tags the request
  exercised).

The text is canonical: sorted keys, compact values, the header one field
per line and each step one line, so a changed answer is a one-line diff and
a check can compare bytes.

## Consuming it

For each fixture, load the program under the switch architecture with
`ports` ports and fresh extern state, then for each step in order install
the request's entries (each request replaces the previous entries; extern
state persists) and run the packet. The step agrees when the extern states
are equal and either the outputs are equal as (port, bytes) sequences with
a diagnostic on both sides or neither, or both sides report an error for
the same reason. Diagnostic texts and `coverage` are not compared: coverage
is the Lean machine's own measure. This is how the Python interpreter is
checked, and a third implementation consumes the fixtures the same way.

## Checking and regenerating

```
uv run python -m p4blo.conformance check-python   # Python against the fixtures, no Lean
uv run python -m p4blo.conformance check-lean     # Lean answers again, byte for byte
uv run python -m p4blo.conformance export         # answer inputs.py on Lean, rewrite fixtures/
```

`tests/test_conformance.py` runs the first per fixture in `scripts/check.sh`
and the second in the `lean_agrees` gate. `check-lean` and `export` need
the Lean executable that `scripts/check-lean.sh` builds.

A change to the semantics that alters an answer fails `check-lean` (and,
until Python follows, `check-python`) until the fixtures are re-exported.
Re-export deliberately, after the changed behavior is written in
`docs/ir-semantics.md` or `docs/arch-supports.md`, from committed Lean
sources, and review the diff: every changed line is a changed answer. A
change to the Lean sources that alters no answer leaves every fixture byte
identical; the header then names an older commit, which the tests report
as a warning and do not fail on. The fixtures hold concrete inputs, so a
change to a generator changes no check; it changes what the next export
writes. Adding a corpus program, example or vector fails
`test_the_fixture_set_is_the_input_set` until the next export.
