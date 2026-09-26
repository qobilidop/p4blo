# Author in Python and compare with Lean

Run commands from the repository root after the
[Python setup](../README.md#getting-started). No Docker, P4 compiler or external
oracle is needed. Start with the [router demo](../examples/router/README.md),
then the [firewall and load balancer](../examples/README.md). Each combines a
complete typed eDSL program, host configuration and independent expectations.
The [authoring guide](python-edsl.md) explains blocks and externs.

The two corpus examples below preserve the upstream behaviors covered by
their packet and state observations. Their authored stateless checksum
computation runs in ingress; their READMEs explain this schedule and the
limits of original-source comparison:

| Program | Python source | First vector |
|---|---|---|
| IPv4 forwarder | [forwarder.py](../tests/corpus/forwarder/forwarder.py) | [forward.stf](../tests/corpus/forwarder/forward.stf) |
| Stateful Bloom firewall | [tutorial_firewall.py](../tests/corpus/tutorial_firewall/tutorial_firewall.py) | [connection.stf](../tests/corpus/tutorial_firewall/connection.stf) |

Their `build()` functions construct architecture assemblies from IR blocks.
Read the declarations, parser, actions, tables and final assembly together.
Route data comes from STF `add` commands. For a small authoring change, copy
an example, change an action or table default, and update your packet
expectations. Committed examples must continue to reproduce their goldens.

Ordinary Python executes at build time; `with self.if_(condition):` records
a runtime IR branch. Do not use Python `if` on a symbolic eDSL expression.
Width/name checks are partly static (Pyright) and partly build-time or
validator checks. The eDSL is tested, not a verified frontend.

## Run the Python-authored programs

This builds from the Python sources, validates through `v1model.load`, and checks
the independent STF packet expectations. Keep one `Loaded` object for an
entire sequence: its externs hold the firewall's persistent registers.

<!-- quickstart: python-run -->
```sh
uv run python - <<'PY'
from pathlib import Path
from p4blo import arch, stf
from p4blo.arch import v1model
from tests.corpus.forwarder.forwarder import build as forwarder
from tests.corpus.tutorial_firewall.tutorial_firewall import build as firewall

root = Path.cwd().resolve()
for name, build, vector in [
    ("forwarder", forwarder, "forward.stf"),
    ("tutorial_firewall", firewall, "connection.stf"),
]:
    loaded = v1model.load(build())
    pipeline = v1model.V1Model(ports=4)
    driver = arch.stf_driver(pipeline, loaded)
    ports = []
    def run(entries, port, packet):
        output = driver(entries, port, packet)
        ports.append([p for p, _ in output])
        return output
    path = root / "tests/corpus" / name / vector
    stf.assert_replay(loaded.index, stf.parse(path.read_text()), run)
    assert not pipeline.diagnostics, pipeline.diagnostics
    print(f"{name}: output ports {ports}")
PY
```

Expected output:

```text
forwarder: output ports [[2]]
tutorial_firewall: output ports [[], [2], [1], []]
```

The firewall first drops an unsolicited reply, then an outbound SYN sets its
two Bloom cells, the corresponding reply passes, and another unsolicited
reply drops. `[]` means no output packet, **not necessarily an error**.
Recreating `v1model.load(...)` for each packet resets that state. Table entries
are installed from the vector's current configuration for each packet;
they are separate from persistent extern state.

## Compare execution with Lean

For this optional section, install the Lean tools from the
[development setup](../README.md#development), then run:

```sh
scripts/check-lean.sh
```

This builds both Lean packages, runs the core proof audits and native tests.
The matching `lean-toolchain` files in `spec/ir/` and `spec/arch/` select the
compiler. `uv` does not install Lean.

The same Python-authored IR is serialized and executed by `p4blo-lean`.
Python supplies the inputs and checks STF expectations; Lean executes the
packets. One process per program preserves extern state across its sequence.

<!-- quickstart: lean-run -->
```sh
uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from p4blo import arch, stf
from p4blo.arch import v1model, wire
from p4blo.drt import Case, LeanRunner
from tests.corpus.forwarder.forwarder import build as forwarder
from tests.corpus.tutorial_firewall.tutorial_firewall import build as firewall

root = Path.cwd().resolve()
for name, build, vector in [
    ("forwarder", forwarder, "forward.stf"),
    ("tutorial_firewall", firewall, "connection.stf"),
]:
    program = build()
    loaded = v1model.load(program)
    statements = stf.parse((root / "tests/corpus" / name / vector).read_text())
    ports = []
    with TemporaryDirectory() as directory:
        path = Path(directory) / "program.json"
        path.write_text(wire.dump_json(program))
        with LeanRunner([root / "spec/arch/.lake/build/bin/p4blo-lean"], path, ports=4) as runner:
            def run(entries, port, packet):
                reply = runner.run(Case(entries, port, packet))
                assert reply.error is None and reply.diagnostic is None, reply
                assert reply.outputs is not None, reply
                ports.append([p for p, _ in reply.outputs])
                return reply.outputs
            stf.assert_replay(loaded.index, statements, run)
    print(f"{name}: output ports {ports}")
PY
```

Expected output is identical to the Python section. The runner also returns
persistent extern state; dedicated firewall tests check all 8,192 Bloom
cells. Bloom false positives remain intentional: this is not exact connection
tracking, has no timeout or FIN deletion, and does not verify transport
checksums.

Formal verification covers the architecture-free IR, including soundness of
its validity checker and progress under explicit extern, installation and
entry assumptions. The v1model adapter and concrete extern families are tested
executable adapters. Neither they nor these applications have a formal
correctness guarantee; see [assurance](assurance.md#what-is-proved).

## Diagnostics and checks

Python construction may raise `EdslError` with a source location; `v1model.load`
can reject validation, extern binding, missing exports or unsupported profile
behavior. Bad host entries are rejected by `loaded.entries(...)` before
`V1Model.run` starts. Runtime errors are separate from an ordinary drop.
`V1Model.diagnostics` records conditions such as an out-of-range output port;
check it as well as the returned packets. It accumulates on the pipeline object.

A Lean server's process exit 0 means its input stream was handled; inspect
**every reply**. `error` is a request/execution error; optional `diagnostic`
can accompany a dropped packet. The scripts above reject both for these
known-good vectors. Do not infer transactional rollback after every possible
execution error; the state/error boundary is documented separately.

To check these exact documented snippets after building Lean:

```sh
P4BLO_REQUIRE_LEAN=1 uv run pytest tests/structure/test_quickstart.py -q
```

For broader application coverage, run `uv run pytest tests/examples`; for
release gates and optional external oracle setup see [workflows](workflows.md).
Forwarder semantics deliberately include TTL 0 wrapping to 255, old-destination-to-source MAC assignment, and checksum
recalculation after a table action even if it drops. The parser supports the
documented fixed-width headers, not arbitrary IPv4/TCP options or full P4.
