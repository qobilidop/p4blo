# Author and run the two examples

Run every command from the repository root. These examples need no Docker,
P4 compiler or external oracle. Nix supplies the pinned development tools:

```sh
nix develop -c uv sync --locked
nix develop -c scripts/check-lean.sh
```

The second command builds **both** Lean packages, checks proof audits and runs
native tests; the first build takes longer. Without Nix, `uv sync --locked`
is enough for the Python section, but does not install the pinned Lean or
schema tools. The current Lean toolchain is recorded in `lean/lean-toolchain`.

## What to edit

| Application | Python authoring | Lean authoring | First vector |
|---|---|---|---|
| IPv4 forwarder | [forwarder.py](../tests/corpus/forwarder/forwarder.py) | [Forwarder.lean](../lean/P4blo/Forwarder.lean) | [forward.stf](../tests/corpus/forwarder/forward.stf) |
| Stateful Bloom firewall | [tutorial_firewall.py](../tests/corpus/tutorial_firewall/tutorial_firewall.py) | [TutorialFirewall.lean](../lean/P4blo/TutorialFirewall.lean) | [connection.stf](../tests/corpus/tutorial_firewall/connection.stf) |

These are complete independently authored programs, not wrappers that read
the goldens. Python `build()` and Lean `program` each construct an IR Program.
Read the declarations, parser, actions, tables and final Program assembly in
those files. For example, the forwarder's `ipv4_forward` action deliberately
assigns the **old destination** MAC to the source before changing destination.
The table's route data comes from the STF `add` commands, not a hardcoded route.

For a small authoring change, make a separate copy of an example and change
its action or table default; rebuild and update your own packet expectations.
The committed examples intentionally remain byte-identical to their goldens.
Their tests should fail if you change behavior without changing its contract.

Python uses the typed `p4blo.edsl` API. Ordinary Python executes **at build
time**; `with self.if_(condition):` records a runtime IR branch. Do not use
Python `if` on a symbolic eDSL expression. Width/name checks are partly static
(Pyright) and partly build-time/validator checks, not a correctness proof.

Lean's checked `Ref.named`, scalar expressions and command fragments have
documented scoped proofs. Complete parser/table/action/extern declarations in
these examples also use ordinary `P4bloIR` constructors. That explicit raw
assembly is **not** a verified complete frontend. Complete execution is tested;
only the individual properties listed in [the assurance notes](../lean/ASSURANCE.md)
are proved. The [milestone](milestone-1.md) does not require a whole-pipeline
proof or universal Python correctness.

## Run the Python-authored programs

This builds from the Python sources, validates through `arch.load`, and checks
the independent STF packet expectations. Keep one `Loaded` object for an
entire sequence: its externs hold the firewall's persistent registers.

<!-- quickstart: python-run -->
```sh
nix develop -c uv run python - <<'PY'
from pathlib import Path
from p4blo import arch, stf
from tests.corpus.forwarder.forwarder import build as forwarder
from tests.corpus.tutorial_firewall.tutorial_firewall import build as firewall

root = Path.cwd().resolve()
for name, build, vector in [
    ("forwarder", forwarder, "forward.stf"),
    ("tutorial_firewall", firewall, "connection.stf"),
]:
    loaded = arch.load(build())
    switch = arch.Switch(ports=4)
    driver = arch.stf_driver(switch, loaded)
    ports = []
    def run(entries, port, packet):
        output = driver(entries, port, packet)
        ports.append([p for p, _ in output])
        return output
    path = root / "tests/corpus" / name / vector
    stf.assert_replay(loaded.index, stf.parse(path.read_text()), run)
    assert not switch.diagnostics, switch.diagnostics
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
Recreating `arch.load(...)` for each packet resets that state. Table entries
are installed from the vector's current configuration for each packet;
they are separate from persistent extern state.

## Run the Lean-authored programs

After editing either Lean source, rebuild its existing executable:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d lean build leanForwarder leanTutorialFirewall
```

With no arguments each executable exports its authored Program as JSON.
With `run`, it executes that **compiled in-memory Program** and accepts one
snake_case JSON request per line: `entries`, `ingress_port`, and hex `packet`.
The servers have four ports. Returned extern state persists within one server
process; starting a new process resets it. Requests do not accept a replacement
Program. The following script resolves STF host entries using the exported
syntax, then sends the whole sequence to one server and checks the same STF
expectations—Python does not execute the packets in this section.

<!-- quickstart: lean-run -->
```sh
nix develop -c uv run python - <<'PY'
import json
import subprocess
from pathlib import Path
from google.protobuf.json_format import MessageToDict
from p4blo import ir, stf

root = Path.cwd().resolve()
for name, executable, vector in [
    ("forwarder", "leanForwarder", "forward.stf"),
    ("tutorial_firewall", "leanTutorialFirewall", "connection.stf"),
]:
    command = [str(root / "lean/.lake/build/bin" / executable)]
    exported = subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
    assert not exported.stderr, exported.stderr
    index = ir.Index.build(ir.load_json(exported.stdout))
    statements = stf.parse((root / "tests/corpus" / name / vector).read_text())
    installed, requests = [], []
    for statement in statements:
        if isinstance(statement, stf.Add | stf.SetDefault):
            installed.append(statement)
        elif isinstance(statement, stf.Packet):
            requests.append(json.dumps({
                "entries": MessageToDict(stf.to_entries(index, installed), preserving_proto_field_name=True),
                "ingress_port": statement.port,
                "packet": statement.data.hex(),
            }))
    assert requests, "vector has no packets"
    result = subprocess.run(command + ["run"], input="\n".join(requests) + "\n",
                            check=True, capture_output=True, text=True, timeout=30)
    assert not result.stderr, result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == len(requests), "expected one reply per request"
    replies, ports = iter(lines), []
    def run(entries, port, packet):
        reply = json.loads(next(replies))
        assert "error" not in reply and "diagnostic" not in reply, reply
        output = [(p, bytes.fromhex(data)) for p, data in reply["outputs"]]
        ports.append([p for p, _ in output])
        return output
    stf.assert_replay(index, statements, run)
    print(f"{name}: output ports {ports}")
PY
```

Expected output is identical to the Python section. The firewall reply also
contains the full persistent extern snapshot under `state`; dedicated tests
check all 8,192 Bloom cells, not just these four packets. Bloom false positives
remain intentional: this is not exact connection tracking, has no timeout or
FIN deletion, and does not verify transport checksums.

## A checked Lean fragment

This is the smaller authoring layer with a proved lowering contract, distinct
from complete raw IR assembly. It wraps 8-bit addition, then lowers the same
expression to the IR. `import P4blo` is the user package; `P4bloIR` names the
authoritative IR/specification.

<!-- quickstart: lean-fragment -->
```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d lean env lean --stdin <<'LEAN'
import P4blo
open P4blo.Scalar
open scoped P4blo.Scalar

def wrapped : Expr (.bits 8) := bits[8, 255] + bits[8, 1]
#eval (denote wrapped).val
example (run : P4bloIR.Run) :
    (P4bloIR.evaluate (lower wrapped)).run run =
      (.ok (toValue (denote wrapped)), run) := evaluate_lower_run wrapped run

#check P4blo.Forwarder.program
#check P4blo.TutorialFirewall.program
#check P4blo.prepareSwitch
#check P4blo.runSwitch
LEAN
```

The evaluated value is `0`. `bits[8, 256]` is rejected during elaboration;
wrapping is an arithmetic operation, not permission for an overflowing literal.
For a direct Lean application, `prepareSwitch` returns `(switch, externs)`;
pass the extern state returned by `runSwitch` into the next call.
`prepareSwitch` performs indexing, extern binding and architecture checks,
**not the Python validator's complete set of checks**. `P4blo` interpreter
entry points reuse the reference semantics; they are not another optimized
engine with a separate correctness claim.

## Diagnostics and checks

Python construction may raise `EdslError` with a source location; `arch.load`
can reject validation, extern binding, missing exports or architecture-contract
mismatches. Bad host entries are rejected by `loaded.entries(...)` before
`Switch.run` starts. Runtime errors are separate from an ordinary drop.
`Switch.diagnostics` records conditions such as an out-of-range output port;
check it as well as the returned packets. It accumulates on that Switch object.

A Lean server's process exit 0 means its input stream was handled; inspect
**every reply**. `error` is a request/execution error; optional `diagnostic`
can accompany a dropped packet. The scripts above reject both for these
known-good vectors. Do not infer transactional rollback after every possible
execution error; the state/error boundary is documented separately.

To check these exact documented snippets after building Lean:

```sh
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest tests/test_quickstart.py -q
```

For broader application coverage, run `tests/test_lean_forwarder.py` and
`tests/test_lean_firewall.py`; for release gates and optional external oracle
setup see [workflows](workflows.md). Forwarder semantics deliberately include
TTL 0 wrapping to 255, old-destination-to-source MAC assignment, and checksum
recalculation after a table action even if it drops. The parser supports the
documented fixed-width headers, not arbitrary IPv4/TCP options or full P4.
