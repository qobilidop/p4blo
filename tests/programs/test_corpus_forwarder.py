"""The forwarder corpus program has the shape the tutorial gives it.

Its vectors replay in tests/programs/test_corpus.py with every other program."""

from __future__ import annotations

from pathlib import Path

import pytest

from p4blo import ir
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb

CORPUS = Path(__file__).resolve().parents[2] / "tests" / "corpus" / "forwarder"
PROGRAM = CORPUS / "forwarder.txtpb"


@pytest.fixture(scope="module")
def program() -> apb.BlockAssembly:
    return arch_wire.load_text(PROGRAM)


@pytest.fixture(scope="module")
def index(program: apb.BlockAssembly) -> ir.Index:
    return BoundIndex.build(program)


def test_errors_are_the_core_errors(program: apb.BlockAssembly) -> None:
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
    # The contract fields the forwarder uses (impl/python/p4blo/arch/contract.py).
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


def test_text_roundtrip(program: apb.BlockAssembly) -> None:
    assert arch_wire.load_text(arch_wire.dump_text(program)) == program
