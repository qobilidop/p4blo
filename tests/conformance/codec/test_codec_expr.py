"""Independent bounded expression codec vectors and exact decoder diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest
from google.protobuf import json_format

from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.codec_expr import (
    Expression,
    expressions,
    malformed,
    normalized,
)
from tests.support.codec_leaves import assert_leaf, same_json


@pytest.mark.parametrize("expr", expressions())
def test_expr_protobuf_known_answers(expr: Expression) -> None:
    value = json_format.ParseDict(expr.wire, pb.Expr())
    program = apb.BlockAssembly()
    program.blocks.add().body.add().emit.value.CopyFrom(value)
    recovered = arch_wire.load_json(arch_wire.dump_json(program)).blocks[0].body[0].emit.value
    assert recovered == value
    encoded = json_format.MessageToDict(value, preserving_proto_field_name=True)
    assert same_json(encoded, expr.wire)


@pytest.mark.parametrize("expr", expressions())
@pytest.mark.lean
def test_lean_agrees_expr_known_answers(lean_binary: Path, expr: Expression) -> None:
    actual = assert_leaf(
        lean_binary, "expr", expr.wire, {"value": expr.value, "encoded": expr.wire}
    )
    # Decode the actual Lean-produced payload using the public Python codec.
    actual_wire = actual["encoded"]
    assert isinstance(actual_wire, dict)
    value = json_format.ParseDict(actual_wire, pb.Expr())
    program = apb.BlockAssembly()
    program.blocks.add().body.add().emit.value.CopyFrom(value)
    recovered = arch_wire.load_json(arch_wire.dump_json(program)).blocks[0].body[0].emit.value
    assert recovered == json_format.ParseDict(expr.wire, pb.Expr())


@pytest.mark.parametrize("wire,message", malformed())
@pytest.mark.lean
def test_lean_agrees_expr_exact_errors(lean_binary: Path, wire: object, message: str) -> None:
    assert_leaf(lean_binary, "expr", wire, {"error": message})


@pytest.mark.parametrize("wire,expr", normalized())
@pytest.mark.lean
def test_lean_agrees_expr_normalization(lean_binary: Path, wire: object, expr: Expression) -> None:
    assert_leaf(lean_binary, "expr", wire, {"value": expr.value, "encoded": expr.wire})
