"""The packet a parser reads and the buffer a deparser writes.

Both work in bits, most significant first, because headers need not be byte
aligned (docs/semantics.md, "Parsers" and "Deparsers").
"""

from __future__ import annotations

from p4blo.interp.errors import PACKET_TOO_SHORT, ParseError


class Packet:
    """A packet under a parser: bytes that never change and a cursor in bits."""

    __slots__ = ("_value", "cursor", "data")

    def __init__(self, data: bytes) -> None:
        self.data = data
        self._value = int.from_bytes(data, "big")
        self.cursor = 0

    @property
    def total_bits(self) -> int:
        return len(self.data) * 8

    @property
    def remaining_bits(self) -> int:
        return self.total_bits - self.cursor

    def peek(self, n: int) -> int:
        """The next `n` bits as an integer, without moving the cursor.

        Raises `PacketTooShort` when fewer than `n` bits remain.
        """
        if n > self.remaining_bits:
            raise ParseError(PACKET_TOO_SHORT)
        return (self._value >> (self.remaining_bits - n)) & ((1 << n) - 1)

    def read(self, n: int) -> int:
        """`peek(n)`, then move the cursor; on error the cursor stays."""
        value = self.peek(n)
        self.cursor += n
        return value

    def advance(self, n: int) -> None:
        """Move the cursor by `n` bits; past the end it stays and the error
        is `PacketTooShort`."""
        if n > self.remaining_bits:
            raise ParseError(PACKET_TOO_SHORT)
        self.cursor += n


class Emitter:
    """The output of a deparser: bits appended in order, padded to bytes."""

    __slots__ = ("value", "width")

    def __init__(self) -> None:
        self.value = 0
        self.width = 0

    def write(self, width: int, value: int) -> None:
        """Append `value` as `width` bits."""
        self.value = (self.value << width) | value
        self.width += width

    def to_bytes(self) -> bytes:
        """Every bit written so far, then zero bits up to a byte boundary."""
        padding = -self.width % 8
        return (self.value << padding).to_bytes((self.width + padding) // 8, "big")
