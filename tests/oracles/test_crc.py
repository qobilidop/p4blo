"""Package checks without native oracle dependencies."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from p4blo.arch import v1model
from p4blo.arch.bindings import BoundIndex
from tests.oracles import run as spectec
from tests.oracles.bmv2 import run as bmv2
from tests.support.crc import (
    EXPECTED,
    KNOWN,
    PACKET,
    SPECTEC_CRC32,
    KnownSpecTecCRCDisagreement,
    known_spectec_mismatch,
    original_p4,
    program,
)


@pytest.mark.parametrize("printed", [False, True], ids=["original-p4", "printed-ir"])
@pytest.mark.xfail(
    strict=True,
    raises=KnownSpecTecCRCDisagreement,
    reason="pinned SpecTec prepends zero to odd-byte CRC input; docs/assurance.md",
)
@pytest.mark.spectec
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
@pytest.mark.bmv2
def test_crc_known_answers_on_bmv2(tmp_path: Path, printed: bool) -> None:
    image = bmv2.default_image()
    unavailable = bmv2.unavailable(image)
    if unavailable:
        pytest.skip(unavailable)
    p = program([d for d, _, _ in KNOWN])
    compiled = bmv2.compile_program(image, v1model.print_program(p) if printed else original_p4())
    vector = tmp_path / "crc.stf"
    vector.write_text(f"packet 0 {PACKET.hex()}\nexpect 0 {(EXPECTED + PACKET).hex()}$\n")
    verdict = bmv2.run_vector(image, BoundIndex.build(p), compiled, vector)
    assert verdict.status == "pass", verdict


@pytest.mark.parametrize("control", ["crc16-all", "crc32-even", "crc32-explicit-leading-zero"])
@pytest.mark.spectec
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
