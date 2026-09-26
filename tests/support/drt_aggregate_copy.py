"""Shared drt aggregate copy fixtures and campaign helpers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Literal

import pytest

from p4blo.arch import v1model
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.programs import bits, scalar_program
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.v0 import p4blo_pb2 as pb

CopyKind = Literal["header", "struct"]

WIDTHS = (8, 9, 16, 65)


def read(*path: str) -> pb.Expr:
    result = pb.Expr(var=path[0])
    for field in path[1:]:
        result = pb.Expr(member=pb.Member(base=result, field=field))
    return result


def place(*path: str) -> pb.LValue:
    result = pb.LValue(var=path[0])
    for field in path[1:]:
        result = pb.LValue(member=pb.LMember(base=result, field=field))
    return result


def copy_program(
    kind: CopyKind, width: int, valid: bool, a: int, b: int, changed: int, other: int
) -> tuple[apb.BlockAssembly, bytes]:
    program = scalar_program(bits(8, 0), 8)
    program.name = f"aggregate-copy-{kind}"
    header = program.header_types.add(name="Packet")
    for name in ("left", "right"):
        header.fields.add(name=name, type=pb.Type(bits=width))
    record = program.struct_types.add(name="Record")
    record.fields.add(name="packet", type=pb.Type(header="Packet"))
    record.fields.add(name="tag", type=pb.Type(bits=8))
    control = program.blocks[1]
    del control.body[1:]

    def assign(path: tuple[str, ...], value: pb.Expr) -> None:
        control.body.add(assign=pb.Assign(target=place(*path), value=value))

    def validity(root: str, value: bool) -> None:
        statement = control.body.add()
        target = statement.set_valid if value else statement.set_invalid
        target.header.CopyFrom(place(root, "packet"))

    for root, left, right, is_valid, tag in (
        ("source", a, b, valid, 13),
        ("target", 0, 0, not valid, 29),
        ("unrelated", 7, 11, False, 165),
    ):
        control.locals.add(name=root, type=pb.Type(struct="Record"))
        assign((root, "packet", "left"), bits(width, left))
        assign((root, "packet", "right"), bits(width, right))
        assign((root, "tag"), bits(8, tag))
        validity(root, is_valid)
    if kind == "header":
        assign(("target", "packet"), read("source", "packet"))
    else:
        assign(("target",), read("source"))
    # Mutate both sides after copying; unequal sentinels expose either alias.
    assign(("source", "packet", "left"), bits(width, changed))
    assign(("source", "tag"), bits(8, 73))
    validity("source", not valid)
    assign(("target", "packet", "right"), bits(width, other))

    fields = program.header_types[0].fields
    del fields[:]
    expected = bytearray()
    padded = ((width + 7) // 8) * 8
    # Snapshot every stored field and validity after the tested operations.
    # Invalid headers are observed through a separate valid Result header.
    for root, left, right, is_valid, tag in (
        ("source", changed, b, not valid, 73),
        ("target", a, other, valid, 13 if kind == "struct" else 29),
        ("unrelated", 7, 11, False, 165),
    ):
        for label, value, result_width, number in (
            ("left", read(root, "packet", "left"), padded, left),
            ("right", read(root, "packet", "right"), padded, right),
            (
                "valid",
                pb.Expr(
                    cast=pb.Cast(
                        to=pb.Type(bits=1),
                        operand=pb.Expr(is_valid=pb.IsValid(header=read(root, "packet"))),
                    )
                ),
                8,
                int(is_valid),
            ),
            ("tag", read(root, "tag"), 8, tag),
        ):
            name = f"{root}_{label}"
            fields.add(name=name, type=pb.Type(bits=result_width))
            assign(
                ("hdr", "result", name),
                pb.Expr(cast=pb.Cast(to=pb.Type(bits=result_width), operand=value)),
            )
            expected.extend(number.to_bytes(result_width // 8, "big"))
    return program, bytes(expected)


def check_copy(program: apb.BlockAssembly, expected: bytes, lean_binary: Path) -> None:
    case = Case(pb.Entries(), 0, b"")
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        assert error.report is not None
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(program.SerializeToString()).hexdigest()[:24]
        bundle = directory / f"aggregate-copy-{digest}.json"
        save(report, bundle)
        pytest.fail(f"{report.summary()}; replay {bundle}; {report.protocol_error}")
    assert run_python(v1model.load(program), case, 4) == [(0, expected)]
