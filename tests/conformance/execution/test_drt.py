"""Real Lean execution conformance."""

from __future__ import annotations

from pathlib import Path

import pytest

from p4blo.arch import validator
from p4blo.arch.bindings import BoundIndex
from p4blo.drt import (
    Case,
    case_to_stf,
    compare,
)
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.drt import CORPUS, PORTS, PROGRAMS, fate_program, golden, lean_report

# ---------------------------------------------------------------------------
# The real thing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("program_dir", PROGRAMS, ids=lambda p: p.name)
def test_lean_agrees_with_python(program_dir: Path, lean_binary: Path) -> None:
    report = compare(program_dir, 42, 200, PORTS, [lean_binary])
    assert report.cases == 200
    index = BoundIndex.build(golden(program_dir))
    shown = "\n".join(
        case_to_stf(index, d.case, comments={"python": str(d.python), "lean": str(d.lean)})
        for d in report.divergences[:3]
    )
    assert report.divergences == [], f"{report.summary()}\n{shown}"
    # The generator promises installable entries and in-range ports, so an
    # error on both sides, even for the same reason, is a bug somewhere.
    assert report.both_errored == 0, report.summary()


def test_lean_agrees_on_error_reasons(lean_binary: Path, tmp_path: Path) -> None:
    """Both sides refuse an lpm prefix wider than the key and an ingress
    port that is not the switch's, in the same words."""
    program = golden(CORPUS / "forwarder")
    bad_width = pb.Entries()
    te = bad_width.tables.add(block="MyIngress", table="ipv4_lpm")
    entry = te.entries.add()
    entry.keys.add(lpm=pb.LpmValue(value="1", prefix_len=40))
    entry.action.action = "drop"
    cases = [Case(bad_width, 0, bytes(34)), Case(pb.Entries(), 600, bytes(34))]
    lean = lean_report(program, cases, lean_binary, tmp_path)
    assert [o.error for o in lean] == [
        "prefix length 40 exceeds width 32",
        "ingress_port 600 is not a configured v1model port",
    ]


def test_lean_agrees_on_drop_redirection_and_the_port_rules(
    lean_binary: Path, tmp_path: Path
) -> None:
    program = fate_program()
    assert validator.validate(program) == []
    cases = [
        Case(pb.Entries(), ingress, bytes([redirect, drop, port >> 8, port & 0xFF]))
        for ingress, redirect, drop, port in [
            (6, 1, 0, 0),  # egress assignment cannot redirect selected port0
            (0, 1, 0, 0),
            (7, 1, 1, 3),  # ingress drop suppresses egress
            (0, 0, 0, 511),  # reserved drop port: no diagnostic
            (0, 0, 0, 9),  # beyond the count
            (0, 0, 0, 7),  # the last port
            (2, 0, 0, 4),
        ]
    ]
    cases.append(Case(pb.Entries(), 300, bytes(4)))  # ingress beyond the count: both error
    cases.append(Case(pb.Entries(), 512, bytes(4)))  # ingress beyond bit<9>: both error
    lean = lean_report(program, cases, lean_binary, tmp_path, ports=8)
    assert [o.diagnostic for o in lean[:7]] == [
        None,
        None,
        None,
        None,
        "egress_spec 9 is not a configured v1model port",
        None,
        None,
    ]
    assert lean[5].outputs == ((7, bytes([0, 0, 0, 0])),)
    assert [o.error for o in lean[7:]] == [
        "ingress_port 300 is not a configured v1model port",
        "ingress_port 512 is not a configured v1model port",
    ]
