"""The Internet checksum over a bit string, as in RFC 1071.

    extern checksum16 {
        checksum16();
        bit<16> compute(in bit<D> data);
    }

Elaborated to one extern type per data width `D`. `data` is the fields to
sum, concatenated in order, which is how the frontend elaborates v1model's
field list; a width that is not a multiple of 16 is zero-padded at the end.
The result is the one's complement of the one's-complement sum, so a header
whose checksum field holds the result sums to all ones.
"""

from __future__ import annotations

from collections.abc import Sequence

from p4blo.externs import Bindings, Implementation, MethodShape, ParamShape, Shape
from p4blo.interp import ExternBinding, ExternResult
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb

SHAPE = Shape(
    constructor=(),
    methods={"compute": MethodShape((ParamShape(pb.DIRECTION_IN, "D"),), returns=16)},
)


def internet_checksum(data: bytes) -> int:
    """RFC 1071 over `data`, odd lengths padded with a zero byte."""
    if len(data) % 2:
        data += b"\x00"
    total = sum(int.from_bytes(data[i : i + 2], "big") for i in range(0, len(data), 2))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


class Checksum16(ExternBinding):
    def call(self, method: str, args: list[Value]) -> ExternResult:
        data = args[0]
        assert method == "compute" and isinstance(data, Bits)
        padded_width = -(-data.width // 16) * 16
        payload = (data.value << (padded_width - data.width)).to_bytes(padded_width // 8, "big")
        return ExternResult(returns=Bits(16, internet_checksum(payload)))


def make(decl: pb.ExternType, bindings: Bindings, args: Sequence[Value]) -> ExternBinding:
    return Checksum16()


IMPLEMENTATION = Implementation("checksum16", SHAPE, make)
