"""Run-time values: zero, copy and equality per docs/semantics.md, "Values"."""

from __future__ import annotations

import pytest

from p4blo import ir
from p4blo.interp import values
from p4blo.interp.values import NO_ERROR, Bits, EnumValue, ErrorValue, Header, Stack, Struct
from p4blo.v0 import p4blo_pb2 as pb


def index() -> ir.Index:
    return ir.Index.build(
        ir.load_text(
            """
            errors: "NoError"
            header_types {
              name: "h"
              fields { name: "f" type { bits: 8 } }
              fields { name: "b" type { boolean {} } }
            }
            struct_types {
              name: "S"
              fields { name: "h" type { header: "h" } }
              fields { name: "hs" type { stack { header: "h" size: 2 } } }
              fields { name: "c" type { enum_type: "color" } }
              fields { name: "e" type { error {} } }
            }
            enum_types { name: "color" members: "red" members: "blue" }
            """
        )
    )


def test_bits_invariant() -> None:
    assert Bits.wrap(8, 300) == Bits(8, 44)
    with pytest.raises(ValueError):
        Bits(8, 256)
    with pytest.raises(ValueError):
        Bits(0, 0)


def test_zero_is_recursive_with_invalid_headers_and_first_members() -> None:
    s = values.zero(pb.Type(struct="S"), index())
    assert s == Struct(
        "S",
        [
            Header("h", False, [Bits(8, 0), False]),
            Stack("h", [Header("h", False, [Bits(8, 0), False]) for _ in range(2)], 0),
            EnumValue("color", "red"),
            NO_ERROR,
        ],
    )


def test_copy_is_deep() -> None:
    s = values.zero(pb.Type(struct="S"), index())
    assert isinstance(s, Struct)
    c = values.copy(s)
    assert c == s
    assert isinstance(c, Struct)
    header = c.fields[0]
    assert isinstance(header, Header)
    header.valid = True
    header.fields[0] = Bits(8, 1)
    assert s.fields[0] == Header("h", False, [Bits(8, 0), False])


def test_header_equality_by_validity_then_fields() -> None:
    a = Header("h", False, [Bits(8, 1), True])
    b = Header("h", False, [Bits(8, 2), False])
    assert values.equal(a, b)  # two invalid headers are equal whatever their fields
    a.valid = True
    assert not values.equal(a, b)  # one valid, one invalid
    b.valid = True
    assert not values.equal(a, b)
    b.fields = [Bits(8, 1), True]
    assert values.equal(a, b)


def test_struct_and_stack_equality_are_elementwise() -> None:
    idx = index()
    a = values.zero(pb.Type(struct="S"), idx)
    b = values.zero(pb.Type(struct="S"), idx)
    assert values.equal(a, b)
    assert isinstance(b, Struct)
    stack = b.fields[1]
    assert isinstance(stack, Stack)
    stack.elements[1].valid = True
    assert not values.equal(a, b)


def test_scalar_equality_is_by_value_and_name() -> None:
    assert values.equal(Bits(8, 3), Bits(8, 3))
    assert not values.equal(Bits(8, 3), Bits(16, 3))
    assert values.equal(EnumValue("color", "red"), EnumValue("color", "red"))
    assert not values.equal(EnumValue("color", "red"), EnumValue("color", "blue"))
    assert values.equal(ErrorValue("NoError"), NO_ERROR)
    assert not values.equal(True, False)
