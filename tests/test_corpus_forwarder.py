"""The forwarder corpus program: it loads, and its vectors replay."""

from __future__ import annotations

from pathlib import Path

import pytest

from p4blo import arch, ir, stf
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
    # The contract fields the forwarder uses (python/p4blo/arch/contract.py).
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
# The forwarder runs under the switch architecture (python/p4blo/arch), which
# is what the vectors describe: the deparser's bytes with the payload behind
# them, dropped on meta.drop, otherwise sent to meta.egress_port. The filter
# architecture runs it too, in tests/test_arch.py.


@pytest.fixture(scope="module")
def loaded(program: pb.Program) -> arch.Loaded:
    return arch.load(program)


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
def test_vector(loaded: arch.Loaded, vector: Path) -> None:
    statements = stf.parse(vector.read_text())
    stf.assert_replay(loaded.index, statements, arch.stf_driver(arch.Switch(ports=4), loaded))
