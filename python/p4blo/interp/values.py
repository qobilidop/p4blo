"""Run-time values.

A value carries everything the semantics needs: a `Bits` knows its width, a
`Header` its validity, a `Stack` its next index. See docs/semantics.md,
"Values", for the rules these types implement.
"""

from __future__ import annotations

from dataclasses import dataclass

from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


@dataclass(frozen=True, slots=True)
class Bits:
    """An unsigned value of `width` bits; invariant `0 <= value < 2**width`."""

    width: int
    value: int

    def __post_init__(self) -> None:
        if self.width < 1:
            raise ValueError(f"width must be at least 1, got {self.width}")
        if not 0 <= self.value < (1 << self.width):
            raise ValueError(f"{self.value} does not fit in {self.width} bits")

    @classmethod
    def wrap(cls, width: int, value: int) -> Bits:
        """Reduce `value` modulo 2**width."""
        return cls(width, value & ((1 << width) - 1))


@dataclass(frozen=True, slots=True)
class EnumValue:
    enum_type: int
    member: int


@dataclass(frozen=True, slots=True)
class ErrorValue:
    """Index into Program.errors; 0 is NoError."""

    index: int


@dataclass(slots=True)
class Header:
    type_id: int
    valid: bool
    fields: list[Value]


@dataclass(slots=True)
class Struct:
    type_id: int
    fields: list[Value]


@dataclass(slots=True)
class Stack:
    header_type: int
    elements: list[Header]
    next_index: int


type Value = Bits | bool | EnumValue | ErrorValue | Header | Struct | Stack


def zero(type: pb.Type, index: Index) -> Value:
    """The initial value of a type: zero bits, false, member 0, invalid headers."""
    match type.WhichOneof("kind"):
        case "bits":
            return Bits(type.bits, 0)
        case "boolean":
            return False
        case "header":
            decl = index.header_types[type.header]
            return Header(decl.id, False, [zero(f.type, index) for f in decl.fields])
        case "struct":
            decl = index.struct_types[type.struct]
            return Struct(decl.id, [zero(f.type, index) for f in decl.fields])
        case "enum_type":
            return EnumValue(type.enum_type, 0)
        case "error":
            return ErrorValue(0)
        case "stack":
            header = pb.Type(header=type.stack.header)
            elements = [zero(header, index) for _ in range(type.stack.size)]
            return Stack(type.stack.header, elements, 0)  # type: ignore[arg-type]
        case _:
            raise ValueError("type has no kind")


def copy(value: Value) -> Value:
    """A deep copy; immutable values are returned as they are."""
    match value:
        case Header(type_id, valid, fields):
            return Header(type_id, valid, [copy(f) for f in fields])
        case Struct(type_id, fields):
            return Struct(type_id, [copy(f) for f in fields])
        case Stack(header_type, elements, next_index):
            return Stack(header_type, [copy(e) for e in elements], next_index)  # type: ignore[misc]
        case _:
            return value


def equal(a: Value, b: Value) -> bool:
    """Equality as docs/semantics.md defines it for every type."""
    match a, b:
        case Header(_, va, fa), Header(_, vb, fb):
            if va != vb:
                return False
            if not va:
                return True
            return all(equal(x, y) for x, y in zip(fa, fb, strict=True))
        case Struct(_, fa), Struct(_, fb):
            return all(equal(x, y) for x, y in zip(fa, fb, strict=True))
        case Stack(_, ea, _), Stack(_, eb, _):
            return all(equal(x, y) for x, y in zip(ea, eb, strict=True))
        case _:
            return a == b


def assign(target: Value, source: Value) -> Value:
    """The value stored by `target = source`: a copy of `source`."""
    return copy(source)
