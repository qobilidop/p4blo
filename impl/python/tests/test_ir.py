import pytest

from p4blo import ir
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb


def tiny() -> apb.BlockAssembly:
    return arch_wire.load_text(
        """
        name: "tiny"
        errors: "NoError"
        header_types { name: "h" fields { name: "f" type { bits: 8 } } }
        struct_types { name: "H" fields { name: "h" type { header: "h" } } }
        struct_types { name: "M" }
        headers: "H"
        metadata: "M"
        blocks {
          name: "p" kind: BLOCK_KIND_PARSER
          params { name: "hdr" type { struct: "H" } direction: DIRECTION_OUT }
          params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
          states { name: "start" transition { direct { accept {} } } }
          start_state: "start"
        }
        exports { role: "parser" block: "p" }
        """
    )


def test_text_roundtrip() -> None:
    program = tiny()
    assert arch_wire.load_text(arch_wire.dump_text(program)) == program


def test_binary_and_json_roundtrip() -> None:
    program = tiny()
    assert arch_wire.load_binary(arch_wire.dump_binary(program)) == program
    assert arch_wire.load_json(arch_wire.dump_json(program)) == program


def test_index() -> None:
    index = BoundIndex.build(tiny())
    assert index.program_names == {"h", "H", "M", "p"}
    scope = index.scopes["p"]
    assert set(scope.vars) == {"hdr", "meta"}
    assert set(scope.states) == {"start"}
    assert index.exported("parser").name == "p"
    assert index.field_index("H", "h") == 0
    assert index.errors == {"NoError": 0}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.struct_types.add(name="H"),
        lambda p: p.blocks.add(name="H"),
        lambda p: p.blocks[0].params.add(name="hdr"),
        lambda p: p.blocks[0].locals.add(name="p"),
        lambda p: p.blocks[0].states.add(name="hdr"),
        lambda p: p.header_types.add(name=""),
        lambda p: p.errors.append("NoError"),
    ],
)
def test_index_rejects_name_clashes(mutate) -> None:
    program = tiny()
    mutate(program)
    with pytest.raises(ir.DuplicateName):
        BoundIndex.build(program)


def test_action_params_may_shadow_nothing() -> None:
    program = tiny()
    action = program.blocks[0].actions.add(name="a")
    action.params.add(name="hdr", type=pb.Type(bits=1), direction=pb.DIRECTION_NONE)
    with pytest.raises(ir.DuplicateName):
        BoundIndex.build(program)
