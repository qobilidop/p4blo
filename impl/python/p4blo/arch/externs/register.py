"""A register array, as v1model and PSA declare it.

    extern register<T> {
        register(bit<32> size);
        void read(out T result, in bit<32> index);
        void write(in bit<32> index, in T value);
    }

Elaborated to one extern type per width `T`. Semantics: `size` cells of
width `T`, all zero at creation; `read` of an index at or beyond `size`
yields zero and `write` there does nothing, which is what BMv2 does. A
Lean model of the same lives under spec/ir/ and the two are pinned by vectors.
"""

from __future__ import annotations

from collections.abc import Sequence

from p4blo.arch.externs import (
    Bindings,
    Implementation,
    MethodShape,
    ParamShape,
    Shape,
)
from p4blo.interp import ExternBinding, ExternResult
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb

SHAPE = Shape(
    constructor=(32,),
    methods={
        "read": MethodShape((ParamShape(pb.DIRECTION_OUT, "T"), ParamShape(pb.DIRECTION_IN, 32))),
        "write": MethodShape((ParamShape(pb.DIRECTION_IN, 32), ParamShape(pb.DIRECTION_IN, "T"))),
    },
)


class Register(ExternBinding):
    def __init__(self, size: int, width: int) -> None:
        self.width = width
        self.cells = [Bits(width, 0) for _ in range(size)]

    def call(self, method: str, args: list[Value]) -> ExternResult:
        match method:
            case "read":
                index = args[1]
                assert isinstance(index, Bits)
                in_range = index.value < len(self.cells)
                value = self.cells[index.value] if in_range else Bits(self.width, 0)
                return ExternResult(outs=(value,))
            case "write":
                index, value = args
                assert isinstance(index, Bits) and isinstance(value, Bits)
                if index.value < len(self.cells):
                    self.cells[index.value] = value
                return ExternResult()
            case _:
                raise ValueError(method)


def make(decl: pb.ExternType, bindings: Bindings, args: Sequence[Value]) -> ExternBinding:
    size = args[0]
    assert isinstance(size, Bits)
    return Register(size.value, bindings.widths["T"])


IMPLEMENTATION = Implementation("register", SHAPE, make)
