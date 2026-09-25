"""The metadata contract (docs/design.md, "Metadata contract").

An architecture names the fields of `M` it needs, each with a type and a
direction: provided fields are written before the blocks run, consumed
fields are read afterwards. Every field is optional; a program declares the
ones it uses. At load the program's `M` is checked structurally, by field
name and type, and nothing else about `M` concerns anyone.

`CONTRACT` is the vocabulary the architectures in this repository share. A
`Metadata` view, built from a contract and a program, is how an
architecture reads and writes those fields without knowing where in `M`
they sit or whether they are there at all: a field the program does not
declare reads as its zero value and ignores writes.
"""

from __future__ import annotations

from dataclasses import dataclass

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.interp.values import Bits, ErrorValue, Struct, Value, zero
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


class ContractError(Exception):
    """A program's `M` declares a contract field with the wrong type."""


@dataclass(frozen=True)
class Field:
    name: str
    type: pb.Type
    # True when the architecture writes it before the blocks run; False when
    # the architecture reads it afterwards.
    provided: bool


@dataclass(frozen=True)
class Contract:
    fields: tuple[Field, ...]

    def field(self, name: str) -> Field:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)

    def present(self, index: Index, metadata: str) -> set[str]:
        """The contract fields the program's `M` declares."""
        declared = {f.name for f in index.fields(metadata)}
        return {f.name for f in self.fields if f.name in declared}

    def check(self, index: Index, metadata: str) -> None:
        """Raise `ContractError` on a declared contract field of the wrong type."""
        declared = {f.name: f.type for f in index.fields(metadata)}
        for f in self.fields:
            if f.name in declared and declared[f.name] != f.type:
                raise ContractError(
                    f"{metadata}.{f.name} must be {describe(f.type)}, "
                    f"got {describe(declared[f.name])}"
                )

    def view(self, index: Index, bindings: apb.BlockBindings) -> Metadata:
        """Check the program against the contract and return its view of `M`."""
        self.check(index, bindings.metadata)
        return Metadata(self, index, bindings.metadata)


def describe(type: pb.Type) -> str:
    match type.WhichOneof("kind"):
        case "bits":
            return f"bit<{type.bits}>"
        case "boolean":
            return "bool"
        case "error":
            return "error"
        case kind:
            return kind or "?"


class Metadata:
    """A contract's view of one program's `M`.

    `zero` is the initial metadata value; `number`, `flag`, `error` and
    `write` access contract fields by name. Reads of an undeclared field
    give the field's zero value and writes to one do nothing, so an
    architecture never asks what the program declared.
    """

    def __init__(self, contract: Contract, index: Index, metadata: str) -> None:
        self.contract = contract
        self.index = index
        self.type = pb.Type(struct=metadata)
        self.slots = {
            name: index.field_index(metadata, name) for name in contract.present(index, metadata)
        }

    def zero(self) -> Struct:
        value = zero(self.type, self.index)
        assert isinstance(value, Struct)
        return value

    def read(self, m: Struct, name: str) -> Value:
        slot = self.slots.get(name)
        if slot is None:
            return zero(self.contract.field(name).type, self.index)
        return m.fields[slot]

    def number(self, m: Struct, name: str) -> int:
        value = self.read(m, name)
        assert isinstance(value, Bits)
        return value.value

    def flag(self, m: Struct, name: str) -> bool:
        value = self.read(m, name)
        assert isinstance(value, bool)
        return value

    def error(self, m: Struct, name: str) -> ErrorValue:
        value = self.read(m, name)
        assert isinstance(value, ErrorValue)
        return value

    def write(self, m: Struct, name: str, value: int | bool | ErrorValue) -> None:
        """Store `value` into `m` if the field is declared; an `int` is the
        value of a `bit<N>` field and takes the contract's width."""
        slot = self.slots.get(name)
        if slot is None:
            return
        if isinstance(value, int) and not isinstance(value, bool):
            m.fields[slot] = Bits(self.contract.field(name).type.bits, value)
        else:
            m.fields[slot] = value


# The vocabulary of the architectures in this repository, as the table in
# docs/design.md gives it.
CONTRACT = Contract(
    (
        Field("ingress_port", pb.Type(bits=9), provided=True),
        Field("parser_error", pb.Type(error=pb.ErrorType()), provided=True),
        Field("egress_port", pb.Type(bits=9), provided=False),
        Field("drop", pb.Type(boolean=pb.BoolType()), provided=False),
        Field("flood", pb.Type(boolean=pb.BoolType()), provided=False),
    )
)
