"""Deparsers: emit of headers, structs and stacks, and bit padding, per
docs/ir-semantics.md, "Deparsers"."""

from __future__ import annotations

from p4blo import interp
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.interp import values
from p4blo.interp.values import Bits, Header, Stack, Struct
from p4blo.v0 import p4blo_pb2 as pb

TEMPLATE = """
errors: "NoError"
header_types { name: "h4" fields { name: "f" type { bits: 4 } } }
header_types { name: "h8" fields { name: "f" type { bits: 8 } } }
struct_types { name: "S" fields { name: "x" type { header: "h8" } } }
struct_types {
  name: "H"
  fields { name: "a" type { header: "h4" } }
  fields { name: "b" type { header: "h4" } }
  fields { name: "e" type { header: "h8" } }
  fields { name: "hs" type { stack { header: "h8" size: 2 } } }
  fields { name: "s" type { struct: "S" } }
}
struct_types { name: "M" }
headers: "H"
metadata: "M"
blocks {
  name: "D" kind: BLOCK_KIND_DEPARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_IN }
  @BODY@
}
"""


def emit(*fields: str) -> str:
    """A body that emits `hdr.<field>` for each name, or `hdr` itself for ""."""
    stmts = []
    for f in fields:
        value = 'var: "hdr"' if f == "" else f'member {{ base {{ var: "hdr" }} field: "{f}" }}'
        stmts.append(f"body {{ emit {{ value {{ {value} }} }} }}")
    return "\n".join(stmts)


def run(body: str, headers: Struct) -> bytes:
    index = BoundIndex.build(arch_wire.load_text(TEMPLATE.replace("@BODY@", body)))
    return interp.run_deparser(index, "D", headers, {})


def headers() -> Struct:
    """Every header valid with a distinct value; tests invalidate as needed."""
    return Struct(
        "H",
        [
            Header("h4", True, [Bits(4, 0xA)]),
            Header("h4", True, [Bits(4, 0xB)]),
            Header("h8", True, [Bits(8, 0xCD)]),
            Stack(
                "h8", [Header("h8", True, [Bits(8, 0x11)]), Header("h8", True, [Bits(8, 0x22)])], 2
            ),
            Struct("S", [Header("h8", True, [Bits(8, 0xEE)])]),
        ],
    )


def test_valid_header_emits_its_fields_and_invalid_emits_nothing() -> None:
    h = headers()
    assert run(emit("e"), h) == b"\xcd"
    h.fields[2] = Header("h8", False, [Bits(8, 0xCD)])
    assert run(emit("e"), h) == b""


def test_struct_emits_its_fields_in_declaration_order() -> None:
    assert run(emit(""), headers()) == b"\xab\xcd\x11\x22\xee"
    assert run(emit("s"), headers()) == b"\xee"


def test_stack_emits_elements_in_order_skipping_invalid_ones() -> None:
    h = headers()
    stack = h.fields[3]
    assert isinstance(stack, Stack)
    stack.elements[0].valid = False
    assert run(emit("hs"), h) == b"\x22"
    stack.elements[0].valid = True
    stack.elements[1].valid = False
    assert run(emit("hs"), h) == b"\x11"


def test_bits_are_concatenated_and_padded_to_a_byte_at_the_end() -> None:
    assert run(emit("a"), headers()) == b"\xa0"
    assert run(emit("a", "b"), headers()) == b"\xab"
    assert run(emit("a", "e"), headers()) == b"\xac\xd0"
    assert run(emit("e", "a"), headers()) == b"\xcd\xa0"


def test_nothing_emitted_is_no_bytes() -> None:
    assert run("", headers()) == b""


def test_the_zero_headers_emit_nothing() -> None:
    index = BoundIndex.build(arch_wire.load_text(TEMPLATE.replace("@BODY@", emit(""))))
    zero = values.zero(pb.Type(struct="H"), index)
    assert isinstance(zero, Struct)
    assert interp.run_deparser(index, "D", zero, {}) == b""
