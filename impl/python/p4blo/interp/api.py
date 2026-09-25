"""The types a caller exchanges with the interpreter.

They live here rather than in `__init__` so that every module of the package
can import them without a cycle; `p4blo.interp` re-exports them unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from p4blo.interp.values import Value


@dataclass(frozen=True, slots=True)
class ExternResult:
    """What an extern method call produced: one value per out or inout
    parameter, in parameter order, and the return value if any."""

    outs: tuple[Value, ...] = ()
    returns: Value | None = None


class ExternBinding(Protocol):
    """A Python implementation bound to one extern instance.

    `method` is the method's name in the extern type; `args` holds one value
    per parameter in order: the argument's value for `in` and `inout`, and
    the zero value of the parameter's type for `out`, which is uninitialized
    in P4 (docs/ir-semantics.md, "Externs"). The binding is called after the
    registry has checked arity and widths, so it may trust its inputs; the
    values it returns are copied back, so it never aliases program storage.
    """

    def call(self, method: str, args: list[Value]) -> ExternResult: ...


type Externs = Mapping[str, ExternBinding]
"""Bindings by extern instance name."""


class InterpError(Exception):
    """The interpreter met a program it should never have been given.

    Raised only on inputs the validator rejects; a validated program never
    triggers it.
    """
