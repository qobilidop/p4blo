"""The fixed input set of the exported conformance corpus.

`python -m p4blo.conformance export` answers these on Lean and writes one
fixture per input under `fixtures/`. Three kinds, each named in the
fixture's `source` header:

- `stf`: every corpus program and public example with each of its STF
  vectors, one fixture per vector file, its packets as requests in order
  with the entries installed before each, as the vector replays them.
- `drt`: every corpus program and example with the DRT's generated host
  entries and packets, `p4blo.drt.generate.generate` at fixed seeds.
- `family`: the generated program families of `tests/oracle/generated.py`
  at fixed seeds, through its `materialize`, with the switch it uses there.
- `contract`: hand-written requests for the parts of the reply contract
  the other kinds never reach: installs the host rejects, an ingress port
  the switch does not have (both error replies), drop, unicast, and egress redirection attempts.

The fixtures hold the concrete programs and requests, so a later change to
a generator changes no check; it changes what the next export writes.
"""

from __future__ import annotations

from pathlib import Path

from google.protobuf import json_format

from p4blo import stf
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.builder import AssemblyBuilder
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.conformance import Input
from p4blo.drt.case import Case
from p4blo.drt.generate import generate
from p4blo.edsl.core import bit
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]
PORTS = 4
# Two seeds of eight cases per program: enough to cross every program's
# tables and parser with generated entries, small enough to read.
DRT_SEEDS = (1, 2)
DRT_COUNT = 8
# `materialize` picks the family by the seed modulo the number of
# families, so consecutive seeds spread over all of them; how many each
# family gets follows from `generated.FAMILIES`, not from this range.
FAMILY_SEEDS = range(36)


def programs() -> list[tuple[str, Path]]:
    """Every corpus program and public example, as (label, golden)."""
    corpus = sorted((ROOT / "tests/corpus").glob("*/*.txtpb"))
    examples = sorted((ROOT / "tests/examples").glob("*/program.txtpb"))
    return [(f"corpus-{p.parent.name}", p) for p in corpus if p.stem == p.parent.name] + [
        (f"example-{p.parent.name}", p) for p in examples
    ]


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def stf_cases(program: apb.BlockAssembly, vector: Path) -> tuple[Case, ...]:
    cases: list[Case] = []

    def collect(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        cases.append(Case(entries, port, packet))
        return []

    # Replay only groups packets with the entries installed before them;
    # its expectation failures against the empty answers are irrelevant.
    stf.replay(BoundIndex.build(program), stf.parse(vector.read_text()), collect)
    return tuple(cases)


def stf_inputs() -> list[Input]:
    found: list[Input] = []
    for label, golden in programs():
        program = arch_wire.load_text(golden)
        for vector in sorted(golden.parent.glob("*.stf")):
            source = {"kind": "stf", "program": _relative(golden), "vector": _relative(vector)}
            cases = stf_cases(program, vector)
            found.append(Input(f"stf-{label}-{vector.stem}", source, program, cases, PORTS))
    return found


def drt_inputs() -> list[Input]:
    found: list[Input] = []
    for label, golden in programs():
        program = arch_wire.load_text(golden)
        index = BoundIndex.build(program)
        for seed in DRT_SEEDS:
            source = {
                "kind": "drt",
                "program": _relative(golden),
                "generator": "p4blo.drt.generate.generate",
                "seed": seed,
                "count": DRT_COUNT,
            }
            cases = tuple(generate(index, seed, DRT_COUNT, PORTS))
            found.append(Input(f"drt-{label}-seed{seed}", source, program, cases, PORTS))
    return found


def family_inputs() -> list[Input]:
    from tests.oracle import generated

    found: list[Input] = []
    for seed in FAMILY_SEEDS:
        g = generated.materialize(seed)
        source = {
            "kind": "family",
            "generator": "tests/oracle/generated.py materialize",
            "seed": seed,
            "family": g.family,
            "description": g.description,
        }
        name = f"family-seed{seed:02d}"
        found.append(Input(name, source, g.program, g.cases, generated.SWITCH_PORTS))
    return found


def _forwarder_entries(
    prefix_len: int = 24, keys: int = 1, table: str = "ipv4_lpm", port_width: int = 9
) -> pb.Entries:
    """One route of the forwarder's `ipv4_lpm`, 10.0.2.0/24 to port 2,
    with one part optionally made wrong."""
    key = {"lpm": {"prefix_len": prefix_len, "value": str(0x0A000200)}}
    action = {
        "action": "ipv4_forward",
        "args": [
            {"bits": {"value": "514", "width": 48}},
            {"bits": {"value": "2", "width": port_width}},
        ],
    }
    entry = {"keys": [key] * keys, "action": action}
    tables = {"tables": [{"block": "MyIngress", "table": table, "entries": [entry]}]}
    return json_format.ParseDict(tables, pb.Entries())


# An IPv4 packet to 10.0.2.2, which the route above matches.
_TO_10_0_2_2 = bytes.fromhex(
    "00000000010100000000000108004500001a00010000401100000a0001010a000202deadbeefcafe"
)


def fate_program() -> apb.BlockAssembly:
    """A packet selects unicast/drop and a later attempted redirection.

    The output echoes ingress so the selected destination is independently
    visible alongside the packet bytes.
    """
    p = AssemblyBuilder("fate")
    h = p.header("h_t", redirect=bit(8), drop=bit(8), port=bit(16))
    p.headers = p.struct("headers", h=h)
    p.metadata = p.struct("metadata", ingress_port=bit(9), egress_spec=bit(9))
    with p.parser("P") as ps:
        with ps.state("start") as s:
            s.extract(ps.hdr.h)
            s.accept()
    with p.control("C") as c:
        with c.body() as b:
            b.assign(c.meta.egress_spec, c.hdr.h.port.cast(bit(9)))
            with b.if_(c.hdr.h.drop != 0):
                b.assign(c.meta.egress_spec, 511)
            b.assign(c.hdr.h.port, c.meta.ingress_port.cast(bit(16)))
    with p.control("E") as e:
        with e.body() as b:
            with b.if_(e.hdr.h.redirect != 0):
                b.assign(e.meta.egress_spec, 1)
    p.export("egress", "E")
    with p.deparser("D") as d:
        with d.body() as b:
            b.emit(d.hdr.h)
    p.export("parser", "P")
    p.export("ingress", "C")
    p.export("deparser", "D")
    return p.build()


def contract_inputs() -> list[Input]:
    golden = ROOT / "tests/corpus/forwarder/forwarder.txtpb"
    rejected = [
        _forwarder_entries(prefix_len=8),  # value bits outside the prefix
        _forwarder_entries(keys=2),  # a key too many
        _forwarder_entries(table="no_such_table"),
        _forwarder_entries(port_width=16),  # an argument of the wrong width
    ]
    install = (
        Case(_forwarder_entries(), 0, _TO_10_0_2_2),
        *(Case(entries, 0, _TO_10_0_2_2) for entries in rejected),
        Case(_forwarder_entries(), 3, _TO_10_0_2_2),  # accepted again
        Case(_forwarder_entries(), 4, _TO_10_0_2_2),  # an ingress port beyond the four
    )
    fate_ports = 8
    fate = tuple(
        Case(pb.Entries(), ingress, bytes([redirect, drop, port >> 8, port & 0xFF]) + b"payload")
        for ingress, redirect, drop, port in [
            (6, 1, 0, 0),  # egress assignment cannot redirect selected port0
            (0, 1, 0, 5),  # egress assignment cannot redirect selected port5
            (7, 1, 1, 3),  # ingress drop suppresses egress
            (2, 0, 0, 4),  # unicast
            (0, 0, 0, 7),  # the last port
            (0, 0, 0, 511),  # reserved drop port: no diagnostic
            (0, 0, 0, 8),  # one beyond the count: a diagnostic
            (300, 0, 0, 1),  # an ingress port beyond the count: an error
            (512, 0, 0, 1),  # an ingress port beyond bit<9>: an error
        ]
    )
    return [
        Input(
            "contract-forwarder-install",
            {
                "kind": "contract",
                "program": _relative(golden),
                "description": "installs the host rejects between accepted ones, and an "
                "ingress port beyond the switch",
            },
            arch_wire.load_text(golden),
            install,
            PORTS,
        ),
        Input(
            "contract-fate",
            {
                "kind": "contract",
                "program": "tests/conformance/inputs.py fate_program",
                "description": "drop, unicast, redirection attempts and port rules",
            },
            fate_program(),
            fate,
            fate_ports,
        ),
    ]


def inputs() -> list[Input]:
    return [*stf_inputs(), *drt_inputs(), *family_inputs(), *contract_inputs()]
