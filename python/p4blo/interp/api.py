"""The types a caller exchanges with the interpreter.

They live here rather than in `__init__` so that every module of the package
can import them without a cycle; `p4blo.interp` re-exports them unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from p4blo.interp.values import NO_ERROR, ErrorValue, Struct, Value


@dataclass(frozen=True, slots=True)
class ExternResult:
    """What an extern method call produced: one value per out or inout
    parameter, in parameter order, and the return value if any."""

    outs: tuple[Value, ...] = ()
    returns: Value | None = None


class ExternBinding(Protocol):
    """A Python implementation bound to one extern instance.

    `method` is the method's name in the extern type; `args` holds one value
    per parameter in order, with the current value for out and inout
    parameters. The binding is called after the registry has checked arity
    and widths, so it may trust its inputs.
    """

    def call(self, method: str, args: list[Value]) -> ExternResult: ...


type Externs = Mapping[str, ExternBinding]
"""Bindings by extern instance name."""


@dataclass(slots=True)
class ParseOutcome:
    """What a parser run produced (docs/semantics.md, "Parsers").

    Rejection and error are separate: `accept` gives `accepted` with
    `NoError`; an explicit `reject` gives not accepted with `NoError`; a
    raised error gives not accepted with that error.
    """

    headers: Struct
    metadata: Struct
    consumed_bits: int
    accepted: bool = True
    # A name from Program.errors.
    error: ErrorValue = NO_ERROR


class InterpError(Exception):
    """The interpreter met a program it should never have been given.

    Raised only on inputs the validator rejects; a validated program never
    triggers it.
    """
