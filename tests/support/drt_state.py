"""Shared drt state fixtures and campaign helpers."""

from __future__ import annotations

from pathlib import Path

from p4blo.arch import v1model
from p4blo.arch import wire as arch_wire
from p4blo.drt.case import Case
from p4blo.drt.run import (
    LeanRunner,
    compare_cases,
)
from p4blo.drt.state import snapshot
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]


def wide_register_roundtrip(tmp_path: Path, command: list[str | Path]) -> None:
    program = arch_wire.load_text(
        ROOT / "tests/programs/corpus/register_bounds/register_bounds.txtpb"
    )
    for field in program.header_types[0].fields:
        field.type.bits = 16384
    program.extern_types[0].methods[0].params[0].type.bits = 16384
    program.extern_types[0].methods[1].params[1].type.bits = 16384
    program.blocks[1].locals[0].type.bits = 16384
    loaded = v1model.load(program)  # Includes validation of the widened program.
    packet = bytes(2048) + b"\x80" + bytes(2047) + bytes(2048)
    program_json = tmp_path / "wide.json"
    program_json.write_text(arch_wire.dump_json(program))
    with LeanRunner(command, program_json, 4) as runner:
        report = compare_cases("wide", loaded, [Case(pb.Entries(), 0, packet)], 4, runner.run)
    assert report.passed, report.divergences
    assert snapshot(loaded)[0].values[0].bit_length() == 16384
