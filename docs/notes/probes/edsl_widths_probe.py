"""Can pyright check bit widths statically? Widths as Literal type args."""
from __future__ import annotations
from typing import Any, Generic, Literal, TypeVar, overload, Self

W = TypeVar("W", bound=int)
W2 = TypeVar("W2", bound=int)

class Bits(Generic[W]):
    width: int
    def __init__(self, width: W) -> None: self.width = width
    def __add__(self, other: Bits[W] | int) -> Bits[W]: ...
    def __sub__(self, other: Bits[W] | int) -> Bits[W]: ...
    def __eq__(self, other: Bits[W] | int) -> Bool: ...  # type: ignore[override]
    def __lshift__(self, other: Bits[Any] | int) -> Bits[W]: ...
    def cast(self, to: type[Bits[W2]]) -> Bits[W2]: ...

class Bool: ...

def concat(a: Bits[Any], b: Bits[Any]) -> Bits[int]: ...

u8 = Bits[Literal[8]]
u16 = Bits[Literal[16]]

# Headers as classes with annotated fields, statically visible.
class Header:
    def __init_subclass__(cls) -> None: ...
    def is_valid(self) -> Bool: ...

class ipv4_t(Header):
    version: Bits[Literal[4]]
    ttl: Bits[Literal[8]]
    hdrChecksum: Bits[Literal[16]]
    dstAddr: Bits[Literal[32]]

class ethernet_t(Header):
    etherType: Bits[Literal[16]]

class headers:
    ethernet: ethernet_t
    ipv4: ipv4_t

def assign(target: Bits[W], value: Bits[W] | int) -> None: ...

hdr = headers()
assign(hdr.ipv4.ttl, hdr.ipv4.ttl - 1)          # ok
assign(hdr.ipv4.ttl, hdr.ipv4.hdrChecksum)      # ERROR expected: 8 vs 16
x = hdr.ipv4.ttl + hdr.ipv4.hdrChecksum          # ERROR expected
y = hdr.ipv4.ttl + 1                             # ok
z = hdr.ethernet.etherType == 0x800              # ok
w = hdr.ipv4.hdrChecksum.cast(u8)                # ok: Bits[Literal[8]]
assign(hdr.ipv4.ttl, w)                          # ok
assign(hdr.ipv4.ttl, hdr.ipv4.hdrChecksum.cast(u16))  # ERROR expected
v = concat(hdr.ipv4.ttl, hdr.ipv4.version)       # Bits[int]
assign(hdr.ipv4.ttl, v)                          # is this an error? Bits[int] vs Bits[Literal[8]]
hdr.ipv4.tt1                                     # ERROR expected: typo caught statically
reveal_type(hdr.ipv4.ttl)
reveal_type(v)
