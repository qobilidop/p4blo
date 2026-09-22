"""Declarations of the externs the corpus implements.

Each helper declares, on a program, the monomorphic extern type that
`p4blo.externs` binds: the same constructor and method signatures, with the
width parameter fixed. The IR knows nothing of these; they save retyping
the signature that the implementation checks against.
"""

from __future__ import annotations

from p4blo.edsl.program import Program
from p4blo.edsl.types import ExternType, TypeLike, bit, method


def register(program: Program, width: TypeLike, name: str = "register") -> ExternType:
    """`register<T>` at width `T`: `read(out T result, in bit<32> index)`
    and `write(in bit<32> index, in T value)`, constructed with a size.

    A program with two widths names the second `register.<suffix>`; the
    family before the dot is what binds it (see `ir.extern_family`)."""
    return program.extern_type(
        name,
        constructor=[("size", bit(32))],
        methods={
            "read": [("result", "out", width), ("index", "in", bit(32))],
            "write": [("index", "in", bit(32)), ("value", "in", width)],
        },
    )


def counter(program: Program, name: str = "counter") -> ExternType:
    """A packet counter array: `count(in bit<32> index)`, constructed with a size."""
    return program.extern_type(
        name,
        constructor=[("size", bit(32))],
        methods={"count": [("index", "in", bit(32))]},
    )


def checksum16(program: Program, data_width: TypeLike, name: str = "checksum16") -> ExternType:
    """The Internet checksum: `bit<16> compute(in bit<D> data)`."""
    return program.extern_type(
        name,
        methods={"compute": method([("data", "in", data_width)], returns=bit(16))},
    )
