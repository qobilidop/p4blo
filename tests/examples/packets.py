"""Independent wire construction for application tests; no eDSL imports."""

from __future__ import annotations

import struct


def internet_checksum(data: bytes) -> int:
    padded = data + b"\x00" * (len(data) % 2)
    total = sum(int.from_bytes(padded[i : i + 2], "big") for i in range(0, len(padded), 2))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def ipv4_frame(
    *,
    src: int = 0x0A000001,
    dst: int = 0x0A000201,
    ttl: int = 64,
    protocol: int = 17,
    payload: bytes = b"hello",
    version_ihl: int = 0x45,
    flags_fragment: int = 0x4000,
    total_length: int | None = None,
    src_mac: int = 1,
    dst_mac: int = 2,
) -> bytes:
    length = 20 + len(payload) if total_length is None else total_length
    header = struct.pack(
        "!BBHHHBBHII",
        version_ihl,
        0,
        length,
        123,
        flags_fragment,
        ttl,
        protocol,
        0,
        src,
        dst,
    )
    header = header[:10] + internet_checksum(header).to_bytes(2, "big") + header[12:]
    return dst_mac.to_bytes(6, "big") + src_mac.to_bytes(6, "big") + b"\x08\x00" + header + payload
