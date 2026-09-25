"""CRC contracts, independently written P4 probes and full-pipeline DRT."""

from __future__ import annotations

import random
import subprocess
from pathlib import Path

import pytest

from p4blo import arch, ir
from p4blo.arch import assemble, externs, v1model
from p4blo.arch.externs import declarations as core_externs
from p4blo.arch.externs.crc import crc16, crc32
from p4blo.arch.externs.declarations import CRC16, CRC32
from p4blo.drt import state
from p4blo.drt.case import Case
from p4blo.drt.run import compare_program, run_python
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
from p4blo.interp import InterpError
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracle import run as spectec
from tests.oracle.bmv2 import run as bmv2

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


@pytest.mark.parametrize("warning", [False, True])
def test_known_spectec_classifier_accepts_only_recorded_diagnostic(warning: bool) -> None:
    spec = Path("/oracle/spec")
    mismatch = "error: expected (0) ABCD but got (0) 1234"
    diagnostic = mismatch + "\n\n  source: sim\n"
    if warning:
        diagnostic = spectec_sink_warning(spec) + diagnostic
    result = subprocess.CompletedProcess(["p4spectec"], 1, "", diagnostic)
    assert known_spectec_mismatch(result, spec, mismatch)
    for extra in ["Fatal error: crashed\n", "error: another error\n", "unexpected diagnostic\n"]:
        assert not known_spectec_mismatch(
            subprocess.CompletedProcess(["p4spectec"], 1, "", diagnostic + extra), spec, mismatch
        )
        assert not known_spectec_mismatch(
            subprocess.CompletedProcess(["p4spectec"], 1, "", extra + diagnostic), spec, mismatch
        )
    for exit_code in [0, 2, -11]:
        assert not known_spectec_mismatch(
            subprocess.CompletedProcess(["p4spectec"], exit_code, "", diagnostic), spec, mismatch
        )
    assert not known_spectec_mismatch(
        subprocess.CompletedProcess(["p4spectec"], 1, "unexpected output", diagnostic),
        spec,
        mismatch,
    )
    assert not known_spectec_mismatch(
        subprocess.CompletedProcess(["p4spectec"], 1, "", diagnostic.replace("1234", "1235")),
        spec,
        mismatch,
    )
    # A corrected oracle cannot enter the xfail branch; the surrounding
    # strict marker will turn the ordinary success path into an XPASS.
    assert not known_spectec_mismatch(
        subprocess.CompletedProcess(["p4spectec"], 0, "passed\n", spectec_sink_warning(spec)),
        spec,
        mismatch,
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


def typed_program() -> pb.Program:
    return assemble(
        BlockLibrary(TypedParser, TypedControl, TypedDeparser, externs=[typed16, typed32]),
        name="typed_crc",
        headers=TypedHeaders,
        metadata=TypedMetadata,
        exports={"parser": TypedParser, "control": TypedControl, "deparser": TypedDeparser},
    )


def test_typed_crc_authoring_executes() -> None:
    assert run_python(arch.reference.load(typed_program()), Case(pb.Entries(), 0, b""), 4) == [
        (0, bytes.fromhex("4040ff000000"))
    ]


def test_lean_agrees_on_typed_crc_authoring(lean_binary: Path) -> None:
    report = compare_program(typed_program(), [Case(pb.Entries(), 0, b"")], 4, [lean_binary])
    assert report.passed, (report.summary(), report.divergences)


def program(payloads: list[bytes]) -> pb.Program:
    p = core.Program("crc_probe")
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
    p.export("control", control)
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


@pytest.mark.parametrize("data,c16,c32", KNOWN)
def test_known_answers(data: bytes, c16: int, c32: int) -> None:
    assert crc16(data) == c16
    assert crc32(data) == c32


def test_dynamic_authoring_execution_and_observation() -> None:
    loaded = arch.reference.load(program([data for data, _, _ in KNOWN]))
    before = state.snapshot(loaded)
    assert len(before) == 2 * len(KNOWN)
    assert {item.kind for item in before} == {"crc16", "crc32"}
    for _ in range(2):
        assert run_python(loaded, Case(pb.Entries(), 0, PACKET), 4) == [(0, EXPECTED + PACKET)]
        assert state.snapshot(loaded) == before
    assert state.decode(state.encode(before)) == before


@pytest.mark.parametrize("kind", ["crc16", "crc32"])
def test_stateless_observer_rejects_cells(kind: str) -> None:
    with pytest.raises(ValueError, match="invalid extern state"):
        state.decode({"crc": {"kind": kind, "values": []}})


@pytest.mark.parametrize("width", [0, 1, 7, 9, 15, 17, 103, 105])
def test_unsupported_input_widths_fail_binding_and_printing(width: int) -> None:
    p = program([b"x"])
    p.extern_types[0].methods[0].params[0].type.bits = width
    index = ir.Index.build(p)
    with pytest.raises(externs.BindError, match="positive multiple of 8"):
        externs.supplied_registry().bind(index)
    with pytest.raises(v1model.PrintError, match="positive multiple of 8"):
        v1model.print_program(p)


@pytest.mark.parametrize("width", [16, 32])
def test_wrong_bound_argument_width_is_not_padded(width: int) -> None:
    loaded = arch.reference.load(program([b"x"]))
    bound = loaded.externs[f"crc{width}_0"]
    with pytest.raises(InterpError, match="bound width"):
        bound.call("compute", [Bits(16, 1)])


@pytest.mark.parametrize("index", [0, 1], ids=["crc16", "crc32"])
def test_crc_extra_constructor_arguments_are_not_ignored(index: int) -> None:
    p = program([b"x"])
    p.extern_instances[index].args.add(bits=pb.BitsLiteral(width=8, value="1"))
    with pytest.raises(externs.BindError, match="constructor takes no arguments"):
        externs.supplied_registry().bind(ir.Index.build(p))
    with pytest.raises(v1model.PrintError, match="constructor takes no arguments"):
        v1model.print_program(p)


@pytest.mark.parametrize("bad", ["return", "direction", "constructor", "method"])
def test_malformed_crc_shapes_are_rejected(bad: str) -> None:
    p = program([b"x"])
    decl = p.extern_types[0]
    if bad == "return":
        decl.methods[0].returns.bits = 32
    elif bad == "direction":
        decl.methods[0].params[0].direction = pb.DIRECTION_OUT
    elif bad == "constructor":
        decl.constructor_params.add(name="x", type=pb.Type(bits=8), direction=pb.DIRECTION_IN)
    else:
        decl.methods[0].name = "not_compute"
    with pytest.raises(externs.BindError):
        externs.supplied_registry().bind(ir.Index.build(p))
    with pytest.raises(v1model.PrintError, match="wrong shape"):
        v1model.print_program(p)


def test_lean_agrees_on_crc_known_answers(lean_binary: Path) -> None:
    report = compare_program(
        program([data for data, _, _ in KNOWN]),
        [Case(pb.Entries(), 0, PACKET)] * 3,
        4,
        [lean_binary],
    )
    assert report.passed, (report.summary(), report.divergences)


def test_lean_agrees_on_crc_generated_byte_strings(lean_binary: Path) -> None:
    rng = random.Random(0xC16C32)
    payloads = [rng.randbytes(n) for n in range(1, 65)]
    report = compare_program(program(payloads), [Case(pb.Entries(), 0, PACKET)], 4, [lean_binary])
    assert report.passed, (report.summary(), report.divergences)


@pytest.mark.parametrize("printed", [False, True], ids=["original-p4", "printed-ir"])
@pytest.mark.xfail(
    strict=True,
    raises=KnownSpecTecCRCDisagreement,
    reason="pinned SpecTec prepends zero to odd-byte CRC input; docs/assurance.md",
)
def test_crc_known_answers_on_spectec(tmp_path: Path, printed: bool) -> None:
    oracle = spectec.find_oracle()
    if oracle is None:
        pytest.skip("P4-SpecTec not built")
    assert oracle.missing() is None
    source = tmp_path / "crc.p4"
    source.write_text(
        v1model.print_program(program([d for d, _, _ in KNOWN])) if printed else original_p4()
    )
    vector = tmp_path / "crc.stf"
    vector.write_text(f"packet 0 {PACKET.hex()}\nexpect 0 {(EXPECTED + PACKET).hex()}$\n")
    result = subprocess.run(
        [
            str(oracle.binary),
            "sim",
            str(oracle.spec),
            "-arch",
            "v1model",
            "-i",
            str(oracle.include),
            "-p",
            str(source),
            "-stf",
            str(vector),
        ],
        cwd=oracle.root,
        capture_output=True,
        text=True,
        timeout=600,
    )
    observed = (
        b"".join(
            c16.to_bytes(2, "big") + c32.to_bytes(4, "big")
            for (_, c16, _), c32 in zip(KNOWN, SPECTEC_CRC32, strict=True)
        )
        + PACKET
    )
    known_error = (
        f"error: expected (0) {(EXPECTED + PACKET).hex().upper()} "
        f"but got (0) {observed.hex().upper()}"
    )
    if known_spectec_mismatch(result, oracle.spec, known_error):
        raise KnownSpecTecCRCDisagreement(known_error)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1:] == ["passed"], result.stdout + result.stderr


@pytest.mark.parametrize("printed", [False, True], ids=["original-p4", "printed-ir"])
def test_crc_known_answers_on_bmv2(tmp_path: Path, printed: bool) -> None:
    image = bmv2.default_image()
    unavailable = bmv2.unavailable(image)
    if unavailable:
        pytest.skip(unavailable)
    p = program([d for d, _, _ in KNOWN])
    compiled = bmv2.compile_program(image, v1model.print_program(p) if printed else original_p4())
    vector = tmp_path / "crc.stf"
    vector.write_text(f"packet 0 {PACKET.hex()}\nexpect 0 {(EXPECTED + PACKET).hex()}$\n")
    verdict = bmv2.run_vector(image, ir.Index.build(p), compiled, vector)
    assert verdict.status == "pass", verdict


@pytest.mark.parametrize("control", ["crc16-all", "crc32-even", "crc32-explicit-leading-zero"])
def test_crc_passing_controls_on_spectec(tmp_path: Path, control: str) -> None:
    oracle = spectec.find_oracle()
    if oracle is None:
        pytest.skip("P4-SpecTec not built")
    assert oracle.missing() is None
    widths = (16,) if control == "crc16-all" else (32,)
    vectors = KNOWN if widths == (16,) else [v for v in KNOWN if len(v[0]) % 2 == 0]
    if control == "crc32-explicit-leading-zero":
        vectors = [
            (b"\x00" + data, c16, observed)
            for (data, c16, _), observed in zip(KNOWN, SPECTEC_CRC32, strict=True)
            if len(data) % 2
        ]
    expected = (
        b"".join(
            (c16 if width == 16 else c32).to_bytes(width // 8, "big")
            for _, c16, c32 in vectors
            for width in widths
        )
        + PACKET
    )
    source = tmp_path / "control.p4"
    source.write_text(original_p4(vectors, widths))
    vector = tmp_path / "control.stf"
    vector.write_text(f"packet 0 {PACKET.hex()}\nexpect 0 {expected.hex()}$\n")
    result = subprocess.run(
        [
            str(oracle.binary),
            "sim",
            str(oracle.spec),
            "-arch",
            "v1model",
            "-i",
            str(oracle.include),
            "-p",
            str(source),
            "-stf",
            str(vector),
        ],
        cwd=oracle.root,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1:] == ["passed"], result.stdout + result.stderr
