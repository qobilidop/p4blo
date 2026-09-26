"""Real Lean execution conformance."""

from __future__ import annotations

from pathlib import Path

import pytest

from p4blo.arch.externs.crc import crc16
from p4blo.drt.case import Case
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.copyback import (
    CallKind,
    check,
    copyback_program,
    expected_copyback,
    extern_program,
)


@pytest.mark.parametrize("kind", ["action", "block"])
@pytest.mark.parametrize(("first", "second"), [(0, 1), (1, 0), (2, 0), (0, 2)])
@pytest.mark.lean
def test_lean_agrees_copyback_writes_the_element_resolved_at_copy_in(
    lean_binary: Path, kind: CallKind, first: int, second: int
) -> None:
    """The reproducer of the ledger review: `a(hdr.hs[t])` with the callee
    moving `t`. Writing `hs[second]` instead is the old re-resolution."""
    packet = bytes([0x05, 0x07, 0xDE, 0xAD])
    program = copyback_program(kind, first, second, overlap=False)
    check(
        program, Case(pb.Entries(), 0, packet), expected_copyback(first, packet, False), lean_binary
    )


@pytest.mark.parametrize("kind", ["action", "block"])
@pytest.mark.parametrize(("first", "second"), [(0, 1), (1, 0), (2, 1)])
@pytest.mark.lean
def test_lean_agrees_copyback_with_an_overlapping_in_argument(
    lean_binary: Path, kind: CallKind, first: int, second: int
) -> None:
    """`a(hdr.hs[t].f, hdr.hs[t])`: the `in` copy and the `inout` target
    both resolve before the body moves `t`."""
    packet = bytes([0x05, 0x07])
    program = copyback_program(kind, first, second, overlap=True)
    check(
        program, Case(pb.Entries(), 0, packet), expected_copyback(first, packet, True), lean_binary
    )


@pytest.mark.parametrize("first", [0, 1, 2])
@pytest.mark.lean
def test_lean_agrees_extern_out_and_result_through_computed_indices(
    lean_binary: Path, first: int
) -> None:
    packet = bytes([0x05, 0x07, 0x11, 0x22, 0x33, 0x44])
    hs = bytearray(packet[:2])
    ws = bytearray(packet[2:6])
    if first < 2:
        hs[first] = 0x5A
        # The crc reads hs[0] after the register read wrote it.
        ws[2 * first : 2 * first + 2] = crc16(bytes([hs[0]])).to_bytes(2, "big")
    check(extern_program(first), Case(pb.Entries(), 0, packet), bytes(hs + ws), lean_binary)
