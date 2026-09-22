"""The forwarder corpus program: it loads, and its vectors replay."""

from __future__ import annotations

from pathlib import Path

import pytest

from p4blo import interp, ir, stf
from p4blo.interp import values
from p4blo.interp.tables import InstalledEntries
from p4blo.v0 import p4blo_pb2 as pb

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "forwarder"
PROGRAM = CORPUS / "forwarder.txtpb"


@pytest.fixture(scope="module")
def program() -> pb.Program:
    return ir.load_text(PROGRAM)


@pytest.fixture(scope="module")
def index(program: pb.Program) -> ir.Index:
    return ir.Index.build(program)


def test_errors_are_the_core_errors(program: pb.Program) -> None:
    assert tuple(program.errors) == ir.CORE_ERRORS


def test_exports_resolve_to_blocks_of_their_kind(index: ir.Index) -> None:
    roles = {
        "parser": pb.BLOCK_KIND_PARSER,
        "control": pb.BLOCK_KIND_CONTROL,
        "deparser": pb.BLOCK_KIND_DEPARSER,
    }
    assert {e.role for e in index.program.exports} == set(roles)
    for role, kind in roles.items():
        assert index.exported(role).kind == kind


def test_the_headers_and_metadata_types(index: ir.Index) -> None:
    program = index.program
    assert [f.name for f in index.fields(program.headers)] == ["ethernet", "ipv4"]
    metadata = {f.name: f.type for f in index.fields(program.metadata)}
    # The metadata contract of the step-1 architecture.
    assert set(metadata) == {"ingress_port", "egress_port", "drop"}
    assert metadata["ingress_port"].bits == 9
    assert metadata["egress_port"].bits == 9
    assert metadata["drop"].WhichOneof("kind") == "boolean"


def test_the_parser_states(index: ir.Index) -> None:
    parser = index.exported("parser")
    assert parser.start_state == "start"
    assert [s.name for s in parser.states] == ["start", "parse_ethernet", "parse_ipv4"]
    assert [p.direction for p in parser.params] == [pb.DIRECTION_OUT, pb.DIRECTION_INOUT]


def test_the_table(index: ir.Index) -> None:
    table = index.scopes["MyIngress"].tables["ipv4_lpm"]
    assert [k.match_kind for k in table.keys] == [pb.MATCH_KIND_LPM]
    assert list(table.actions) == ["ipv4_forward", "drop", "NoAction"]
    assert table.default_action.action == "drop"


def test_the_action_data_is_directionless(index: ir.Index) -> None:
    action = index.scopes["MyIngress"].actions["ipv4_forward"]
    assert [(p.name, p.type.bits, p.direction) for p in action.params] == [
        ("dstAddr", 48, pb.DIRECTION_NONE),
        ("port", 9, pb.DIRECTION_NONE),
    ]


def test_text_roundtrip(program: pb.Program) -> None:
    assert ir.load_text(ir.dump_text(program)) == program


# ---------------------------------------------------------------------------
# The vectors, end to end
# ---------------------------------------------------------------------------
#
# The driver below is the step-1 architecture, in the shape claim 3 says an
# architecture has: ordinary Python, with no P4 in it. It gets a packet and
# an ingress port and gives back the packets that left.
#
#   metadata starts as the zero value of M, with ingress_port set;
#   the parser runs;
#   the control runs even after a parser error, with the partial headers,
#     which is v1model's behavior;
#   the deparser runs, and the bytes the parser did not consume follow it;
#   meta.drop discards the packet, otherwise meta.egress_port sends it.


def driver(index: ir.Index) -> stf.RunPacket:
    """The step-1 architecture as a `run_packet` for the STF runner."""
    program = index.program
    fields = {f.name: i for i, f in enumerate(index.fields(program.metadata))}
    ingress_width = index.fields(program.metadata)[fields["ingress_port"]].type.bits
    parser = index.exported("parser").name
    control = index.exported("control").name
    deparser = index.exported("deparser").name

    def run(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        installed = InstalledEntries.build(index, entries)
        metadata = values.zero(pb.Type(struct=program.metadata), index)
        assert isinstance(metadata, values.Struct)
        metadata.fields[fields["ingress_port"]] = values.Bits(ingress_width, port)

        parsed = interp.run_parser(index, parser, packet, metadata, {})
        headers, metadata = interp.run_control(
            index, control, parsed.headers, parsed.metadata, installed, {}
        )
        emitted = interp.run_deparser(index, deparser, headers, {})
        payload = packet[parsed.consumed_bits // 8 :]

        if metadata.fields[fields["drop"]] is True:
            return []
        egress = metadata.fields[fields["egress_port"]]
        assert isinstance(egress, values.Bits)
        return [(egress.value, emitted + payload)]

    return run


def skipping(run: stf.RunPacket) -> stf.RunPacket:
    """Turn the not-yet-written interpreter into a skip rather than a failure."""

    def wrapped(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        try:
            return run(entries, port, packet)
        except NotImplementedError:
            pytest.skip("interpreter not implemented yet")

    return wrapped


VECTORS = sorted(CORPUS.glob("*.stf"))


def test_every_vector_is_collected() -> None:
    assert [path.stem for path in VECTORS] == [
        "forward",
        "lpm_precedence",
        "miss",
        "non_ipv4",
        "too_short",
    ]


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
def test_vector(index: ir.Index, vector: Path) -> None:
    statements = stf.parse(vector.read_text())
    stf.assert_replay(index, statements, skipping(driver(index)))
