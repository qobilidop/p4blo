"""A packet counter array, the packets-only case of v1model's counter.

    extern counter {
        counter(bit<32> size);
        void count(in bit<32> index);
    }

`size` cells, each a count of how often `count` was called with that index.
A count at or beyond `size` is ignored. The counts are host-readable state,
exposed here for tests through `counts`.
"""

from __future__ import annotations

from collections.abc import Sequence

from p4blo.externs import Bindings, Implementation, MethodShape, ParamShape, Shape
from p4blo.interp import ExternBinding, ExternResult
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb

SHAPE = Shape(
    constructor=(32,),
    methods={"count": MethodShape((ParamShape(pb.DIRECTION_IN, 32),))},
)


class Counter(ExternBinding):
    def __init__(self, size: int) -> None:
        self.counts = [0] * size

    def call(self, method: str, args: list[Value]) -> ExternResult:
        index = args[0]
        assert method == "count" and isinstance(index, Bits)
        if index.value < len(self.counts):
            self.counts[index.value] += 1
        return ExternResult()


def make(decl: pb.ExternType, bindings: Bindings, args: Sequence[Value]) -> ExternBinding:
    size = args[0]
    assert isinstance(size, Bits)
    return Counter(size.value)


IMPLEMENTATION = Implementation("counter", SHAPE, make)
