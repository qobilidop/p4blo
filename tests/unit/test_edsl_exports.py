"""Typed programs export named blocks without choosing a packet pipeline."""

from __future__ import annotations

import pytest

from p4blo import validator
from p4blo.edsl import Control, Deparser, EdslError, Parser, Program, Struct, Transition, state
from p4blo.v0 import p4blo_pb2 as pb


class Headers(Struct):
    pass


class Metadata(Struct):
    pass


class Parse(Parser[Headers, Metadata]):
    @state
    def start(self) -> Transition:
        return self.accept


class Apply(Control[Headers, Metadata]):
    pass


class AlsoApply(Control[Headers, Metadata]):
    pass


class Emit(Deparser[Headers]):
    pass


def test_control_only_program_has_one_named_export() -> None:
    source = Program(
        "single_control", headers=Headers, metadata=Metadata, exports={"policy": Apply}
    )
    program = source.build()
    validator.check(program)
    assert [(e.role, e.block) for e in program.exports] == [("policy", "Apply")]
    assert [(b.name, b.kind) for b in program.blocks] == [("Apply", pb.BLOCK_KIND_CONTROL)]
    assert source.build() == program


def test_arbitrary_export_names_preserve_order_and_kind() -> None:
    program = Program(
        "named_exports",
        headers=Headers,
        metadata=Metadata,
        exports={"first": Parse, "ingress": Apply, "egress": AlsoApply, "emit": Emit},
    ).build()
    validator.check(program)
    assert [(e.role, e.block) for e in program.exports] == [
        ("first", "Parse"),
        ("ingress", "Apply"),
        ("egress", "AlsoApply"),
        ("emit", "Emit"),
    ]


@pytest.mark.parametrize("exports", [{"": Apply}, {"policy": object}])
def test_invalid_export_is_reported(exports: dict[str, object]) -> None:
    with pytest.raises(EdslError, match="export|role"):
        Program(
            "invalid",
            headers=Headers,
            metadata=Metadata,
            exports=exports,  # type: ignore[arg-type]
        )
