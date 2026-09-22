"""The reference interpreter.

Three entry points, one per block kind, with the calling convention from
docs/design.md:

    parse    : Packet x M            -> H x M x consumed x error
    control  : H x M x Entries       -> H x M
    deparse  : H                     -> Packet

None of them mutates its arguments; each returns fresh values. Externs are
the only state a block can touch, and they are passed in by the caller.
Everything the interpreter decides is written down in docs/semantics.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits, Struct, Value
from p4blo.ir import Index


@dataclass(frozen=True, slots=True)
class ExternResult:
    """What an extern method call produced: one value per out or inout
    parameter, in parameter order, and the return value if any."""

    outs: tuple[Value, ...] = ()
    returns: Value | None = None


class ExternBinding(Protocol):
    """A Python implementation bound to one extern instance.

    `method` is the index into the extern type's methods; `args` holds one
    value per parameter in order, with the current value for out and inout
    parameters. The binding is called after the registry has checked arity
    and widths, so it may trust its inputs.
    """

    def call(self, method: int, args: list[Value]) -> ExternResult: ...


type Externs = Mapping[int, ExternBinding]


@dataclass(slots=True)
class ParseOutcome:
    headers: Struct
    metadata: Struct
    consumed_bits: int
    # Index into Program.errors; 0 is NoError and means the parser accepted.
    error: int

    @property
    def accepted(self) -> bool:
        return self.error == 0


class InterpError(Exception):
    """The interpreter met a program it should never have been given.

    Raised only on inputs the validator rejects; a validated program never
    triggers it.
    """


def run_parser(
    index: Index,
    block: int,
    packet: bytes,
    metadata: Struct,
    externs: Externs,
) -> ParseOutcome:
    """Run parser `block` over `packet` with an initial metadata value.

    The headers value starts as the zero value of the program's headers type.
    """
    raise NotImplementedError


def run_control(
    index: Index,
    block: int,
    headers: Struct,
    metadata: Struct,
    entries: InstalledEntries,
    externs: Externs,
) -> tuple[Struct, Struct]:
    """Run control `block` and return the new headers and metadata."""
    raise NotImplementedError


def run_deparser(
    index: Index,
    block: int,
    headers: Struct,
    externs: Externs,
) -> bytes:
    """Run deparser `block` and return the emitted bytes, zero-padded to a
    byte boundary."""
    raise NotImplementedError


__all__ = [
    "Bits",
    "ExternBinding",
    "ExternResult",
    "Externs",
    "InstalledEntries",
    "InterpError",
    "ParseOutcome",
    "run_control",
    "run_deparser",
    "run_parser",
]
