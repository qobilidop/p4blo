# Conformance corpus

The Lean semantics' answers on a fixed set of programs and requests, kept
as data. Each file under `fixtures/` is one fixture: a program, an ordered
sequence of requests sent from fresh extern state, and for each request
the reply `p4blo-lean run` gave. An implementation is checked against the
fixtures without a Lean process; Lean is checked against them by answering
the same requests again. This file specifies the format completely, so an
implementation in any language can consume it; the checks and the command
line are in `impl/python/p4blo/conformance.py`, the input set in
`inputs.py`.

## Format

A fixture is a JSON object with exactly these fields,
`"format": "p4blo.conformance"` and `"version": 2`:

- `name`: the file's stem.
- `source`: where the inputs came from, as provenance only. `stf` names a
  corpus or example golden and its STF vector, whose packets became the
  requests with the entries installed before each; `drt` names a golden
  and the seed and count of `p4blo.drt.generate.generate`; `family` names
  a seed of `tests/oracles/generated.py`'s `materialize`, its family and
  description; `contract` names a program and describes hand-written
  requests for the parts of the contract the others never reach.
- `lean`: what answered, as provenance only (see "Provenance" below):
  `sources`, a SHA-256 digest of the semantics sources; `commit`, the last
  commit that touched them; `binary`, a SHA-256 digest of the
  `p4blo-lean` executable.
- `ports`: the v1model profile's configured port count (1–511).
- `program`: the program in the protobuf JSON wire profile
  (`spec/ir/proto/p4blo/v0/p4blo.proto`, proto field names).
- `steps`: a nonempty array, one `{"request": ..., "reply": ...}` per
  request, in order.

A request has exactly three fields: `entries`, the table entries the host
installs, as a `p4blo.v0.Entries` message in protobuf JSON; `ingress_port`,
a nonnegative integer; and `packet`, the packet's bytes in hexadecimal.

A reply has exactly the fields `outputs`, `state` and `coverage`, plus
`diagnostic` when there is one, or exactly `error`, `state` and `coverage`:

- `outputs`: the packets that left, in order, each `[port, "<hex>"]`.
  The supported profile emits zero or one output; multicast is excluded.
- `diagnostic`: present when the switch dropped the packet for a reason
  the program did not decide (a parse that ends off a byte boundary, an
  egress port the switch does not have); a string whose text is not part
  of the contract.
- `error`: the request could not run (the host's entries do not install,
  or the ingress port is not a port of the switch); the reason as an
  English sentence.
- `state`: every extern instance of the program, by instance name, after
  the request, including after an error. Each value is an object with a
  `kind` and the kind's fields:
  - `register`: `width`, the cell width in bits; `size`, the number of
    cells; `nonzero`, the cells whose value is not zero, as
    `[index, "<hex>"]` pairs in increasing index order. Every other cell
    is zero. A value never exceeds `width` bits.
  - `counter`: `size` and `nonzero` as for a register. A cell is the
    number of times `count` was called with that index since load, an
    unbounded natural number.
  - `checksum16`, `crc16`, `crc32`: no further field; they are stateless.
  Every cell value is spelled in lowercase hexadecimal with a `0x` prefix
  and no leading zeros (`0x0` is zero, `0x00` is invalid), so each state has
  one spelling. A zero cell is never listed.
- `coverage`: the sorted rule tags of the Lean semantics the request
  exercised. It is the Lean machine's own measure; another implementation
  ignores it.

Apart from the sparse listing of cells, which saves most of the corpus's
size, a step is the request and reply lines of the pipe protocol that
`p4blo-lean run` speaks; the protocol writes a register's or counter's
cells out in full, as an array `values`, in place of `size` and
`nonzero`.

The text is canonical: sorted keys, compact values, the header one field
per line and each step one line, so a changed answer is a one-line diff and
a check can compare bytes.

## Consuming it

For each fixture, load the program under the scoped v1model architecture with
`ports` ports and fresh extern state, zero in every cell. Then for each
step in order, install the request's entries (each request replaces the
previous entries: the program's const entries and defaults first, then the
request's; extern state persists across requests, errors included) and run
the packet arriving on `ingress_port`. The stage, metadata, port and drop rules are in
[`docs/arch-supports.md`](../../docs/arch-supports.md), together with the
extern families' behavior.

A step agrees when the extern states are equal cell for cell, and either

- neither side reports an error, the outputs are equal as sequences of
  (port, bytes), and both sides or neither report a diagnostic, whatever
  its text; or
- both sides report an error with the same sentence. The sentences are
  the reference interpreter's messages, which Lean copies word for word;
  an implementation's own error class name followed by `: ` at the start
  of its message is ignored, so `InstallError: table 't' has 2 keys`
  matches `table 't' has 2 keys`.

Coverage is not compared. This is how the Python interpreter is checked,
and a third implementation consumes the fixtures the same way.

## Checking and writing

```
uv run python -m p4blo.conformance check-python   # Python against the fixtures, no Lean
uv run python -m p4blo.conformance check-lean     # Lean answers again, byte for byte
uv run python -m p4blo.conformance refresh        # Lean answers the tracked requests again
uv run python -m p4blo.conformance export         # answer inputs.py on Lean, rewrite fixtures/
```

`tests/conformance/test_fixtures.py` runs the first per fixture in `scripts/check.sh`
and the second in the `lean_agrees` gate, and fails when a fixture is
missing, has no input, or has another number of steps than its input has
requests. `check-lean`, `refresh` and `export` need the Lean executable
that `scripts/check-lean.sh` builds.

Two commands write fixtures, so that a diff says what kind of change it
is:

- `refresh` answers each fixture's recorded requests again and rewrites
  the replies and the header, never a program or a request, and runs no
  generator. A fixture whose replies and recorded sources are unchanged is
  left byte for byte. After a semantics change that alters an answer,
  first written in `docs/ir-semantics.md` or `docs/arch-supports.md`,
  refresh from committed Lean sources and review the diff: every changed
  step line is a changed answer, and the header lines name what answered.
- `export` runs `inputs.py`, the one place a generator runs, and rewrites
  the whole set; it removes only files that declare themselves fixtures.
  Use it in a commit of its own to add or change inputs: a new corpus
  program, example or vector fails the membership test until then. The
  fixtures hold concrete inputs, so a change to a generator, or to a
  golden or STF vector already exported, changes no check; it changes
  only what the next export writes.

## Provenance

The header's `sources` digest covers the files whose content decides an
answer, found by a rule rather than a list: start at the endpoint,
`spec/arch/Main.lean`, and follow its `import` lines through `spec/ir`
and `spec/arch`. A proof module, one whose name ends in `Laws`, `Audit`,
`Probe` or `Theorems`, and anything under `P4bloIRTest/` or `P4bloArchTest/`, is
neither followed nor digested, since it changes no answer. A file of
imports alone, such as the `P4bloIR.lean` umbrella, is followed but not
digested, so adding a proof module to it is no change either. Each
package's `lean-toolchain` is digested. The proof-support modules the
umbrella imports under other names (such as typing) stay in: a
change there costs a needless note, never a missed one.

The header is informative; the byte comparison is the check. When the
sources change and no answer does, every fixture stays byte identical and
`check-lean` passes with a note naming the recorded and current digests.
It also notes a binary whose digest differs from the recorded one, which a
rebuild or another platform explains. Neither is a failure; `refresh`
records the current sources.

A binary built before the sources it is meant to answer for would make
`check-lean` pass falsely and `refresh` record stale answers. So
`check-lean`, `refresh` and `export` refuse to run when the executable is
older than the newest digested source, and say which. The required CI gate
builds Lean immediately before the tests, so this guard is for local use;
the per-fixture pytest checks do not repeat it.

## Mutants

Deliberate faults the corpus catches. The Python ones are in `mutants.py`
(`uv run python -m tests.conformance.mutants`), each applied in-process
to one function of the reference interpreter, and
`tests/conformance/test_fixtures.py` requires each to be caught. The current fixtures kill all four Python faults:

| Mutant | Fault | Caught by |
|---|---|---|
| `sub-off-by-one` | `bit<N>` subtraction subtracts one more (`p4blo.interp.expr.bits_binary`) | 8 fixtures, including `stf-corpus-forwarder-forward` and `family-seed21` |
| `count-twice` | a counter's `count` adds two (`Counter.call`) | 10 fixtures, among them `stf-corpus-stateful-persist`, on state alone |
| `unicast-to-ingress` | unicast leaves on ingress instead of selected egress (`V1Model.run`) | 69 fixtures, including `contract-fate` |
| `lpm-unchecked` | an LPM value with bits outside its prefix installs (`tables.check_key_value`) | `contract-forwarder-install` only |

The former flood mutant belongs to the retired custom architecture. Its
record and source remain in revision `14e6f44`; it is not a current gate.
Current isolated Python and Lean architecture faults test six-stage ordering
against independently expected bytes, alongside the core/codec/observer faults
described in [assurance](../../docs/assurance.md#adversarial-checks).
