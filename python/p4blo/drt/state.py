"""Immutable, representation-independent observations of builtin externs.

Only logical state crosses the pipe, not Python objects or Lean hash-map
layout. Hexadecimal strings carry unbounded naturals without JSON precision
loss or Python's decimal-conversion limit. An unsupported extern must get
an explicit adapter, never disappear silently from the comparison.
"""

from __future__ import annotations

from dataclasses import dataclass

from p4blo.arch import Loaded
from p4blo.externs.checksum import Checksum16
from p4blo.externs.counter import Counter
from p4blo.externs.crc import CRC
from p4blo.externs.register import Register


@dataclass(frozen=True)
class Observation:
    name: str
    kind: str
    width: int | None = None
    values: tuple[int, ...] = ()


type Snapshot = tuple[Observation, ...]


def snapshot(loaded: Loaded) -> Snapshot:
    observed: list[Observation] = []
    for name, extern in sorted(loaded.externs.items()):
        if isinstance(extern, Register):
            if any(cell.width != extern.width for cell in extern.cells):
                raise ValueError(f"register {name!r} has inconsistent cell widths")
            observed.append(
                Observation(name, "register", extern.width, tuple(c.value for c in extern.cells))
            )
        elif isinstance(extern, Counter):
            observed.append(Observation(name, "counter", values=tuple(extern.counts)))
        elif isinstance(extern, Checksum16):
            observed.append(Observation(name, "checksum16"))
        elif isinstance(extern, CRC):
            observed.append(Observation(name, f"crc{extern.output_width}"))
        else:
            raise TypeError(f"no differential state adapter for extern {name!r}")
    return tuple(observed)


def encode(state: Snapshot) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for item in state:
        fields: dict[str, object] = {"kind": item.kind}
        if item.kind == "register":
            fields["width"] = item.width
        if item.kind not in ("checksum16", "crc16", "crc32"):
            fields["values"] = [hex(v) for v in item.values]
        result[item.name] = fields
    return result


def decode(raw: object) -> Snapshot:
    if not isinstance(raw, dict):
        raise ValueError("extern state must be an object")
    observed: list[Observation] = []
    for name, fields in raw.items():
        if not isinstance(name, str) or not isinstance(fields, dict):
            raise ValueError("extern state must map instance names to objects")
        kind = fields.get("kind")
        expected = {
            "register": {"kind", "width", "values"},
            "counter": {"kind", "values"},
            "checksum16": {"kind"},
            "crc16": {"kind"},
            "crc32": {"kind"},
        }
        if not isinstance(kind, str) or kind not in expected or set(fields) != expected[kind]:
            raise ValueError(f"invalid extern state for {name!r}")
        width = fields.get("width")
        if kind == "register" and (type(width) is not int or width <= 0):
            raise ValueError("register width must be a positive integer")
        values = fields.get("values", [])
        if not isinstance(values, list):
            raise ValueError("extern values must be an array")
        numbers: list[int] = []
        for value in values:
            if not isinstance(value, str) or not value.startswith("0x"):
                raise ValueError("extern values must be hexadecimal natural-number strings")
            number = int(value, 16)
            if number < 0 or hex(number) != value:
                raise ValueError("extern values must use canonical hexadecimal spelling")
            if isinstance(width, int) and number.bit_length() > width:
                raise ValueError("register value exceeds its width")
            numbers.append(number)
        observed.append(Observation(name, kind, width, tuple(numbers)))
    return tuple(sorted(observed, key=lambda item: item.name))
