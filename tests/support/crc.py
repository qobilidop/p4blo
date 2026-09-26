"""Shared crc fixtures and campaign helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from p4blo.arch import assemble
from p4blo.arch.builder import AssemblyBuilder
from p4blo.arch.externs import declarations as core_externs
from p4blo.arch.externs.declarations import CRC16, CRC32
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.edsl import (
    BlockLibrary,
    Control,
    Deparser,
    Header,
    Parser,
    Struct,
    Transition,
    bit8,
    bit16,
    bit32,
    core,
)
from p4blo.edsl import state as parser_state

# Literal answers checked on BMv2 by the independent hand-written probe
# below. SpecTec's odd-byte padding divergence is recorded separately.
KNOWN = [
    (bytes.fromhex("0a0000010a0000023039005006"), 0x17C6, 0x7DD597C3),
    (bytes(13), 0, 0x0F744682),
    (bytes([255]) * 13, 0x7F01, 0xF2D6F3C1),
    (b"123456789", 0xBB3D, 0xCBF43926),
    (b"\x00", 0, 0xD202EF8D),
    (b"\xff", 0x4040, 0xFF000000),
    (b"\x00\x01", 0xC0C1, 0x36DE2269),
    (b"\x01", 0xC0C1, 0xA505DF1B),
    (b"\x00\x00", 0, 0x41D912FF),
]

PACKET = bytes(60)

EXPECTED = b"".join(c16.to_bytes(2, "big") + c32.to_bytes(4, "big") for _, c16, c32 in KNOWN)

SPECTEC_CRC32 = [
    0xA31AA886,
    0xD1BB79C7,
    0x2C19CC84,
    0xCE7745FE,
    0x41D912FF,
    0x6CDBFD72,
    0x36DE2269,
    0x36DE2269,
    0x41D912FF,
]


class KnownSpecTecCRCDisagreement(Exception):
    """Only the exact recorded odd-byte padding mismatch earns an xfail."""


def spectec_sink_warning(spec: Path) -> str:
    return (
        "warning[elab/dec-missing-clauses]: function `sink` has no clauses defined\n"
        f"  --> {spec}/4-p4-ir/4.5-ir-to-surface.watsup:1:1\n"
        "  |\n1 | dec $sink<T>() : T\n  | ^^^^^^^^^^^^^^^^^^\n"
    )


def known_spectec_mismatch(
    result: subprocess.CompletedProcess[str], spec: Path, mismatch: str
) -> bool:
    """Whitelist the complete diagnostic, not merely a matching error line."""
    diagnostic = mismatch + "\n\n  source: sim\n"
    return (
        result.returncode == 1
        and result.stdout == ""
        and result.stderr in (diagnostic, spectec_sink_warning(spec) + diagnostic)
    )


class TypedResult(Header):
    c16: bit16
    c32: bit32


class TypedHeaders(Struct):
    result: TypedResult


class TypedMetadata(Struct):
    pass


typed16 = CRC16[bit8]("typed16")

typed32 = CRC32[bit8]("typed32")


class TypedParser(Parser[TypedHeaders, TypedMetadata]):
    @parser_state
    def start(self) -> Transition:
        return self.accept


class TypedControl(Control[TypedHeaders, TypedMetadata]):
    def apply(self) -> None:
        self.set_valid(self.hdr.result)
        self.assign(self.hdr.result.c16, typed16.compute(bit8(255)))
        self.assign(self.hdr.result.c32, typed32.compute(bit8(255)))


class TypedDeparser(Deparser[TypedHeaders]):
    def apply(self) -> None:
        self.emit(self.hdr.result)


def typed_program() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(TypedParser, TypedControl, TypedDeparser, externs=[typed16, typed32]),
        name="typed_crc",
        headers=TypedHeaders,
        metadata=TypedMetadata,
        exports={"parser": TypedParser, "ingress": TypedControl, "deparser": TypedDeparser},
    )


def program(payloads: list[bytes]) -> apb.BlockAssembly:
    p = AssemblyBuilder("crc_probe")
    fields = {f"c{width}_{i}": core.bit(width) for i in range(len(payloads)) for width in (16, 32)}
    result = p.header("Result", **fields)
    p.headers = p.struct("H", result=result)
    p.metadata = p.struct("M")
    instances = []
    for i, data in enumerate(payloads):
        pair = []
        for width, declare in ((16, core_externs.crc16), (32, core_externs.crc32)):
            decl = declare(p, core.bit(len(data) * 8), name=f"crc{width}.sample{i}")
            pair.append(p.extern_instance(f"crc{width}_{i}", decl))
        instances.append(pair)
    with p.parser("P") as parser:
        with parser.state("start") as body:
            body.accept()
    with p.control("C") as control:
        with control.body() as body:
            body.set_valid(control.hdr.result)
            for i, data in enumerate(payloads):
                for j, width in enumerate((16, 32)):
                    body.call(
                        instances[i][j],
                        "compute",
                        int.from_bytes(data, "big"),
                        result=getattr(control.hdr.result, f"c{width}_{i}"),
                    )
    with p.deparser("D") as deparser:
        with deparser.body() as body:
            body.emit(deparser.hdr.result)
    p.export("parser", parser)
    p.export("ingress", control)
    p.export("deparser", deparser)
    return p.build()


def original_p4(
    vectors: list[tuple[bytes, int, int]] = KNOWN,
    widths: tuple[int, ...] = (16, 32),
) -> str:
    """A standalone P4 probe: no printer or IR syntax is consulted."""
    fields = "\n".join(f"bit<{w}> c{w}_{i};" for i in range(len(vectors)) for w in widths)
    calls = "\n".join(
        f"hash(hdr.result.c{w}_{i}, HashAlgorithm.crc{w}, {w}w0, "
        f"{{ {len(data) * 8}w0x{data.hex()} }}, 64w{2**w});"
        for i, (data, _, _) in enumerate(vectors)
        for w in widths
    )
    return f"""
#include <core.p4>
#include <v1model.p4>
header Result {{ {fields} }}
struct H {{ Result result; }}
struct M {{ }}
parser P(packet_in packet, out H hdr, inout M meta,
         inout standard_metadata_t sm) {{ state start {{ transition accept; }} }}
control Verify(inout H hdr, inout M meta) {{ apply {{ }} }}
control C(inout H hdr, inout M meta, inout standard_metadata_t sm) {{
  apply {{ hdr.result.setValid(); {calls} sm.egress_spec = 0; }}
}}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) {{ apply {{ }} }}
control Checksum(inout H hdr, inout M meta) {{ apply {{ }} }}
control D(packet_out packet, in H hdr) {{ apply {{ packet.emit(hdr.result); }} }}
V1Switch(P(), Verify(), C(), E(), Checksum(), D()) main;
"""
