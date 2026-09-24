"""Full CRC-16/ARC and CRC-32/ISO-HDLC over positive byte-aligned bits.

See the Externs section of docs/semantics.md. The reflected byte-table implementation is
independent of Lean's forward-polynomial, explicitly reflected bit fold.
"""

from __future__ import annotations

from collections.abc import Sequence

from p4blo.externs import BindError, Bindings, Implementation, MethodShape, ParamShape, Shape
from p4blo.interp import ExternBinding, ExternResult, InterpError
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb


def _table(polynomial: int) -> tuple[int, ...]:
    result: list[int] = []
    for byte in range(256):
        for _ in range(8):
            byte = (byte >> 1) ^ (polynomial if byte & 1 else 0)
        result.append(byte)
    return tuple(result)


_CRC16 = _table(0xA001)
_CRC32 = _table(0xEDB88320)


def crc16(data: bytes) -> int:
    """CRC-16/ARC over bytes, including leading zero bytes."""
    result = 0
    for byte in data:
        result = (result >> 8) ^ _CRC16[(result ^ byte) & 0xFF]
    return result


def crc32(data: bytes) -> int:
    """CRC-32/ISO-HDLC over bytes; does not use a native runtime module."""
    result = 0xFFFFFFFF
    for byte in data:
        result = (result >> 8) ^ _CRC32[(result ^ byte) & 0xFF]
    return result ^ 0xFFFFFFFF


class CRC(ExternBinding):
    def __init__(self, output_width: int, data_width: int) -> None:
        self.output_width = output_width
        self.data_width = data_width

    def call(self, method: str, args: list[Value]) -> ExternResult:
        if (
            method != "compute"
            or len(args) != 1
            or not isinstance(args[0], Bits)
            or args[0].width != self.data_width
        ):
            raise InterpError(f"crc{self.output_width}: call does not fit bound width")
        payload = args[0].value.to_bytes(self.data_width // 8, "big")
        result = crc16(payload) if self.output_width == 16 else crc32(payload)
        return ExternResult(returns=Bits(self.output_width, result))


def _implementation(output_width: int) -> Implementation:
    name = f"crc{output_width}"

    def make(decl: pb.ExternType, bindings: Bindings, args: Sequence[Value]) -> ExternBinding:
        if args:
            raise BindError(f"{name}: constructor takes no arguments")
        width = bindings.widths["D"]
        if width <= 0 or width % 8:
            raise BindError(f"{name}: data width must be a positive multiple of 8")
        return CRC(output_width, width)

    shape = Shape(
        constructor=(),
        methods={"compute": MethodShape((ParamShape(pb.DIRECTION_IN, "D"),), returns=output_width)},
    )
    return Implementation(name, shape, make)


CRC16_IMPLEMENTATION = _implementation(16)
CRC32_IMPLEMENTATION = _implementation(32)
