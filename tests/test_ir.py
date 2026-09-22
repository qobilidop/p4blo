import pytest

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb


def tiny() -> pb.Program:
    return ir.load_text(
        """
        name: "tiny"
        errors: "NoError"
        header_types { id: 1 name: "h" fields { name: "f" type { bits: 8 } } }
        struct_types { id: 2 name: "H" fields { name: "h" type { header: 1 } } }
        struct_types { id: 3 name: "M" }
        headers: 2
        metadata: 3
        blocks {
          id: 4 name: "p" kind: BLOCK_KIND_PARSER
          params { id: 5 name: "hdr" type { struct: 2 } direction: DIRECTION_OUT }
          params { id: 6 name: "meta" type { struct: 3 } direction: DIRECTION_INOUT }
          states { id: 7 name: "start" transition { direct { accept {} } } }
          start_state: 7
        }
        exports { role: "parser" block: 4 }
        """
    )


def test_text_roundtrip() -> None:
    program = tiny()
    assert ir.load_text(ir.dump_text(program)) == program


def test_binary_and_json_roundtrip() -> None:
    program = tiny()
    assert ir.load_binary(ir.dump_binary(program)) == program
    assert ir.load_json(ir.dump_json(program)) == program


def test_index() -> None:
    index = ir.Index.build(tiny())
    assert set(index.all) == {1, 2, 3, 4, 5, 6, 7}
    assert index.owner[5] == 4
    assert index.owner[7] == 4
    assert index.exported("parser").name == "p"


def test_index_rejects_duplicate_ids() -> None:
    program = tiny()
    program.struct_types[1].id = 2
    with pytest.raises(ir.DuplicateId):
        ir.Index.build(program)


def test_index_rejects_zero_id() -> None:
    program = tiny()
    program.blocks[0].states[0].id = 0
    with pytest.raises(ir.DuplicateId):
        ir.Index.build(program)
