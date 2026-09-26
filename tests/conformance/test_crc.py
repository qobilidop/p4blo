"""Real Lean execution conformance."""

from __future__ import annotations

import random
from pathlib import Path

from p4blo.drt.case import Case
from p4blo.drt.run import compare_program
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.crc import KNOWN, PACKET, program, typed_program


def test_lean_agrees_on_typed_crc_authoring(lean_binary: Path) -> None:
    report = compare_program(typed_program(), [Case(pb.Entries(), 0, b"")], 4, [lean_binary])
    assert report.passed, (report.summary(), report.divergences)


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
