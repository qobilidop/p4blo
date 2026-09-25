# pyright: strict
"""Declarations for the extern families supplied by the reference architectures.

Import these names explicitly when a program uses these services. Declaring
an extern does not install its Python implementation: pass a registry to
``p4blo.arch.loader.load`` or use the reference architecture's convenience
loader. A different architecture may provide the same families, a subset,
or its own families without changing the eDSL or IR.

The typed classes serve ``p4blo.edsl.Program``. The lowercase helpers serve
``p4blo.edsl.core.Program``. Both produce identical IR declarations, which
the runtime registry checks against implementation shapes at load time.
"""

from __future__ import annotations

from typing import Any
from typing import Literal as L

from p4blo.arch.builder import AssemblyBuilder as Program
from p4blo.edsl.core.types import ExternType, TypeLike, bit, method
from p4blo.edsl.externs import Extern
from p4blo.edsl.values import Bits, Const, In, Out, Val, bit32


class Register[T: Bits[Any]](Extern, name="register"):
    """``register<T>`` with persistent cells, constructed with a size."""

    def __init__(self, name: str, size: Const[bit32], *, type_name: str = "") -> None:
        super().__init__(name, size, type_name=type_name)

    def read(self, result: Out[T], index: In[Val[bit32]]) -> None: ...

    def write(self, index: In[Val[bit32]], value: In[Val[T]]) -> None: ...


class Counter(Extern, name="counter"):
    """A persistent packet counter array, constructed with a size."""

    def __init__(self, name: str, size: Const[bit32], *, type_name: str = "") -> None:
        super().__init__(name, size, type_name=type_name)

    def count(self, index: In[Val[bit32]]) -> None: ...


class Checksum16[T: Bits[Any]](Extern, name="checksum16"):
    """The Internet checksum: ``bit<16> compute(in T data)``."""

    def __init__(self, name: str, *, type_name: str = "") -> None:
        super().__init__(name, type_name=type_name)

    def compute(self, data: In[Val[T]]) -> Bits[L[16]]: ...


class CRC16[T: Bits[Any]](Extern, name="crc16"):
    """Full CRC-16/ARC over positive, byte-aligned ``T``."""

    def __init__(self, name: str, *, type_name: str = "") -> None:
        super().__init__(name, type_name=type_name)

    def compute(self, data: In[Val[T]]) -> Bits[L[16]]: ...


class CRC32[T: Bits[Any]](Extern, name="crc32"):
    """Full CRC-32/ISO-HDLC over positive, byte-aligned ``T``."""

    def __init__(self, name: str, *, type_name: str = "") -> None:
        super().__init__(name, type_name=type_name)

    def compute(self, data: In[Val[T]]) -> Bits[L[32]]: ...


def register(program: Program, width: TypeLike, name: str = "register") -> ExternType:
    """Declare ``register<T>`` at ``width`` in the dynamic eDSL.

    Multiple widths use distinct type names such as ``register.8``. The
    runtime binds the family name before the first dot and still checks the
    complete declaration shape.
    """
    return program.extern_type(
        name,
        constructor=[("size", bit(32))],
        methods={
            "read": [("result", "out", width), ("index", "in", bit(32))],
            "write": [("index", "in", bit(32)), ("value", "in", width)],
        },
    )


def counter(program: Program, name: str = "counter") -> ExternType:
    """Declare a packet counter array in the dynamic eDSL."""
    return program.extern_type(
        name,
        constructor=[("size", bit(32))],
        methods={"count": [("index", "in", bit(32))]},
    )


def checksum16(program: Program, data_width: TypeLike, name: str = "checksum16") -> ExternType:
    """Declare the Internet checksum over ``data_width`` bits."""
    return program.extern_type(
        name,
        methods={"compute": method([("data", "in", data_width)], returns=bit(16))},
    )


def crc16(program: Program, data_width: TypeLike, name: str = "crc16") -> ExternType:
    """Declare CRC-16/ARC over positive, byte-aligned ``data_width`` bits."""
    return program.extern_type(
        name, methods={"compute": method([("data", "in", data_width)], returns=bit(16))}
    )


def crc32(program: Program, data_width: TypeLike, name: str = "crc32") -> ExternType:
    """Declare CRC-32/ISO-HDLC over positive, byte-aligned ``data_width`` bits."""
    return program.extern_type(
        name, methods={"compute": method([("data", "in", data_width)], returns=bit(32))}
    )


__all__ = [
    "CRC16",
    "CRC32",
    "Checksum16",
    "Counter",
    "Register",
    "checksum16",
    "counter",
    "crc16",
    "crc32",
    "register",
]
