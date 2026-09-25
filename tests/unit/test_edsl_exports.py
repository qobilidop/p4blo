"""Block libraries compile without an architecture; assembly adds roles."""

from __future__ import annotations

import pytest

from p4blo import arch
from p4blo.arch import validator
from p4blo.edsl import (
    BlockLibrary,
    Control,
    Deparser,
    EdslError,
    Enum,
    Header,
    In,
    InOut,
    Parser,
    Struct,
    Transition,
    bit8,
    state,
)
from p4blo.edsl.externs import Extern
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


class Scalar(Control):
    value: InOut[bit8]

    def apply(self) -> None:
        self.assign(self.value, self.value + 1)


class LocalHeader(Header):
    value: bit8


class Local(Struct):
    header: LocalHeader


class Color(Enum):
    RED: Color
    BLUE: Color


class ScalarWithLocals(Control):
    value: InOut[bit8]
    scratch: Local
    shade: Color


class PolicyWithLocals(Control[Headers, Metadata]):
    scratch: Local


class Shared(Control[Headers, Metadata]):
    pass


class Caller(Control[Headers, Metadata]):
    def apply(self) -> None:
        self.call(Shared, self.hdr, self.meta)
        signal.touch(bit8(1))


class AnotherCaller(Control[Headers, Metadata]):
    def apply(self) -> None:
        self.call(Shared, self.hdr, self.meta)
        signal.touch(bit8(2))


class Signal(Extern):
    def touch(self, value: In[bit8]) -> None:
        raise NotImplementedError


signal = Signal("signal")


def test_scalar_block_compiles_without_program_roots_or_exports() -> None:
    compiled = BlockLibrary(Scalar).compile()
    assert [(block.name, block.kind) for block in compiled.blocks] == [
        ("Scalar", pb.BLOCK_KIND_CONTROL)
    ]
    assert [(p.name, p.direction) for p in compiled.blocks[0].params] == [
        ("value", pb.DIRECTION_INOUT)
    ]
    assert compiled.struct_types == ()
    assert not hasattr(compiled, "headers")
    assert not hasattr(compiled, "metadata")
    assert not hasattr(compiled, "exports")


def test_standalone_block_registers_local_type_closure() -> None:
    compiled = BlockLibrary(ScalarWithLocals).compile()
    assert [(local.name, local.type.WhichOneof("kind")) for local in compiled.blocks[0].locals] == [
        ("scratch", "struct"),
        ("shade", "enum_type"),
    ]
    assert [decl.name for decl in compiled.header_types] == ["LocalHeader"]
    assert [decl.name for decl in compiled.struct_types] == ["Local"]
    assert [decl.name for decl in compiled.enum_types] == ["Color"]
    assert not hasattr(compiled, "headers")
    assert not hasattr(compiled, "metadata")
    assert not hasattr(compiled, "exports")


def test_assembled_block_registers_local_type_closure() -> None:
    program = arch.assemble(
        BlockLibrary(PolicyWithLocals),
        name="local_types",
        headers=Headers,
        metadata=Metadata,
        exports={"policy": PolicyWithLocals},
    )
    validator.check(program)
    assert [decl.name for decl in program.header_types] == ["LocalHeader"]
    assert [decl.name for decl in program.struct_types] == ["Headers", "Metadata", "Local"]


def test_shared_subblock_and_extern_are_declared_once() -> None:
    library = BlockLibrary(Caller, AnotherCaller, externs=[signal])
    first = library.compile()
    assert first == library.compile()
    assert [block.name for block in first.blocks] == ["Shared", "Caller", "AnotherCaller"]
    assert [item.name for item in first.extern_instances] == ["signal"]
    assert [item.name for item in first.extern_types] == ["Signal"]


def test_architecture_selects_named_exports_from_library() -> None:
    library = BlockLibrary(Parse, Apply, AlsoApply, Emit)
    program = arch.assemble(
        library,
        name="named_exports",
        headers=Headers,
        metadata=Metadata,
        exports={"first": Parse, "ingress": Apply, "egress": AlsoApply, "emit": Emit},
    )
    validator.check(program)
    assert [(e.role, e.block) for e in program.exports] == [
        ("first", "Parse"),
        ("ingress", "Apply"),
        ("egress", "AlsoApply"),
        ("emit", "Emit"),
    ]
    assert [block.name for block in library.compile().blocks] == [
        block.name for block in program.blocks
    ]


def test_reference_assembly_keeps_conventional_role_order() -> None:
    program = arch.reference.assemble(
        BlockLibrary(Parse, Apply, Emit),
        name="reference",
        headers=Headers,
        metadata=Metadata,
        parser=Parse,
        control=Apply,
        deparser=Emit,
    )
    validator.check(program)
    assert [(e.role, e.block) for e in program.exports] == [
        ("parser", "Parse"),
        ("control", "Apply"),
        ("deparser", "Emit"),
    ]


def test_export_requires_library_member_identity() -> None:
    class SameName(Control[Headers, Metadata], name="Apply"):
        pass

    with pytest.raises(EdslError, match="must name a block in this BlockLibrary"):
        arch.assemble(
            BlockLibrary(Apply),
            name="wrong_export",
            headers=Headers,
            metadata=Metadata,
            exports={"policy": SameName},
        )


@pytest.mark.parametrize("members", [(), (object,)])
def test_library_rejects_missing_or_invalid_blocks(members: tuple[object, ...]) -> None:
    with pytest.raises(EdslError, match="BlockLibrary"):
        BlockLibrary(*members)  # type: ignore[arg-type]
