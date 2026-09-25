"""Application blocks compile before an architecture selects their roles."""

from __future__ import annotations

import pytest

from examples.firewall import program as firewall
from examples.load_balancer import program as load_balancer
from examples.router import program as router
from p4blo import arch, edsl, validator
from p4blo.arch import entry
from p4blo.arch.contract import Contract
from p4blo.arch.externs import Registry
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb


@pytest.mark.parametrize("application", [router, firewall, load_balancer])
def test_application_library_preserves_assembled_block_bodies(application) -> None:
    compiled = application.blocks.compile()
    assembled = application.build()
    assert list(compiled.blocks) == list(assembled.blocks)
    assert list(compiled.extern_instances) == list(assembled.extern_instances)
    assert list(compiled.extern_types) == list(assembled.extern_types)
    assert not hasattr(compiled, "exports")
    assert not hasattr(compiled, "headers")
    assert not hasattr(compiled, "metadata")
    assert isinstance(compiled, pb.BlockLibrary)
    validator.check(compiled)


def test_public_authoring_api_does_not_call_a_library_a_program() -> None:
    assert not hasattr(edsl, "Program")


class WitnessHeaders(edsl.Struct):
    pass


class WitnessMetadata(edsl.Struct):
    choice: edsl.bit8


class ParseLeft(edsl.Parser[WitnessHeaders, WitnessMetadata]):
    @edsl.state(start=True)
    def start(self) -> edsl.Transition:
        return self.accept


class ParseRight(edsl.Parser[WitnessHeaders, WitnessMetadata]):
    @edsl.state(start=True)
    def start(self) -> edsl.Transition:
        return self.accept


class ChooseLeft(edsl.Control[WitnessHeaders, WitnessMetadata]):
    def apply(self) -> None:
        self.assign(self.meta.choice, 1)


class ChooseRight(edsl.Control[WitnessHeaders, WitnessMetadata]):
    def apply(self) -> None:
        self.assign(self.meta.choice, 2)


class EmitLeft(edsl.Deparser[WitnessHeaders]):
    def apply(self) -> None:
        pass


class EmitRight(edsl.Deparser[WitnessHeaders]):
    def apply(self) -> None:
        pass


def test_multiple_blocks_per_kind_need_no_selected_pipeline() -> None:
    library = edsl.BlockLibrary(
        ParseLeft, ParseRight, ChooseLeft, ChooseRight, EmitLeft, EmitRight
    ).compile()
    assert isinstance(library, pb.BlockLibrary)
    assert not hasattr(library, "headers")
    assert not hasattr(library, "metadata")
    assert not hasattr(library, "exports")
    assert [block.kind for block in library.blocks].count(pb.BLOCK_KIND_PARSER) == 2
    assert [block.kind for block in library.blocks].count(pb.BLOCK_KIND_CONTROL) == 2
    assert [block.kind for block in library.blocks].count(pb.BLOCK_KIND_DEPARSER) == 2
    validator.check(library)

    bindings = apb.BlockBindings(
        headers="WitnessHeaders",
        metadata="WitnessMetadata",
        exports=[
            apb.Export(role="parse_left", block="ParseLeft"),
            apb.Export(role="parse_right", block="ParseRight"),
            apb.Export(role="choose_left", block="ChooseLeft"),
            apb.Export(role="choose_right", block="ChooseRight"),
            apb.Export(role="emit_left", block="EmitLeft"),
            apb.Export(role="emit_right", block="EmitRight"),
        ],
    )
    loaded = arch.load(
        library,
        bindings=bindings,
        registry=Registry(),
        contract=Contract(()),
        roles={
            "parse_left": pb.BLOCK_KIND_PARSER,
            "parse_right": pb.BLOCK_KIND_PARSER,
            "choose_left": pb.BLOCK_KIND_CONTROL,
            "choose_right": pb.BLOCK_KIND_CONTROL,
            "emit_left": pb.BLOCK_KIND_DEPARSER,
            "emit_right": pb.BLOCK_KIND_DEPARSER,
        },
    )
    assert set(loaded.blocks) == {export.role for export in bindings.exports}
    for parser_role, control_role, deparser_role, expected in (
        ("parse_left", "choose_left", "emit_left", 1),
        ("parse_right", "choose_right", "emit_right", 2),
    ):
        parsed = entry.run_parser(
            loaded.index, loaded.block(parser_role), b"", loaded.metadata.zero(), loaded.externs
        )
        assert parsed.accepted
        headers, metadata = entry.run_control(
            loaded.index,
            loaded.block(control_role),
            parsed.headers,
            parsed.metadata,
            loaded.entries(),
            loaded.externs,
        )
        choice = metadata.fields[0]
        assert isinstance(choice, Bits)
        assert choice.value == expected
        assert (
            entry.run_deparser(loaded.index, loaded.block(deparser_role), headers, loaded.externs)
            == b""
        )

    with pytest.raises(arch.LoadError, match="must be"):
        arch.load(
            library,
            bindings=bindings,
            registry=Registry(),
            contract=Contract(()),
            roles={"choose_left": pb.BLOCK_KIND_PARSER},
        )
