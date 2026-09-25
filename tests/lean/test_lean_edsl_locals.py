"""A local declared in a state or an action starts afresh at every entry.

The typed eDSL hoists such a local to the block and writes its zero value
where the declaration stands (docs/ir-semantics.md, "State-local
variables"). These programs mirror the IL bridge review's `statelocal` and
`actlocal` probes: a looping state, and an action called twice, each
declaring a scalar and a header local. The expected bytes are written by
hand from P4's fresh scope per entry, which P4-SpecTec gives; a hoisted
local that kept its value would count up instead. Both interpreters are
held to them.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from p4blo import arch
from p4blo.arch import assemble, validator
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.edsl import (
    BlockLibrary,
    Control,
    Deparser,
    Header,
    L,
    Parser,
    Stack,
    Struct,
    Transition,
    action,
    bit8,
    state,
)
from p4blo.v0 import p4blo_pb2 as pb


class out_t(Header):
    cnt: bit8
    seen: bit8


class elem_t(Header):
    more: bit8


class headers(Struct):
    out: out_t
    elems: Stack[elem_t, L[3]]


class metadata(Struct):
    """Empty: the switch delivers every packet to port 0."""


class StateLocalParser(Parser[headers, metadata]):
    """`statelocal`: `loop` declares `cnt` and `tmp`, bumps `cnt`, counts
    `tmp.isValid()` into `out.seen`, sets `tmp` valid and records `cnt` in
    `out.cnt`, once per stack element."""

    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.hdr.out)
        return self.goto(self.loop)

    @state
    def loop(self) -> Transition:
        out = self.hdr.out
        cnt = self.local("cnt", bit8)
        self.assign(cnt, cnt + 1)
        tmp = self.local("tmp", elem_t)
        with self.if_(tmp.is_valid()):
            self.assign(out.seen, out.seen + 1)
        self.set_valid(tmp)
        self.assign(out.cnt, cnt)
        self.extract(self.hdr.elems.next)
        return self.select(self.hdr.elems.last.more, {1: self.loop}, default=self.accept)


class ExtractParser(Parser[headers, metadata]):
    @state
    def start(self) -> Transition:
        self.extract(self.hdr.out)
        return self.accept


class PassControl(Control[headers, metadata]):
    pass


class ActionLocalControl(Control[headers, metadata]):
    """`actlocal`: `bump` declares `c` and `tmp`, adds `c + 1` to `out.cnt`,
    counts `tmp.isValid()` into `out.seen` and sets `tmp` valid; it is
    called twice."""

    @action
    def bump(self) -> None:
        out = self.hdr.out
        c = self.local("c", bit8)
        self.assign(c, c + 1)
        self.assign(out.cnt, out.cnt + c)
        tmp = self.local("tmp", elem_t)
        with self.if_(tmp.is_valid()):
            self.assign(out.seen, out.seen + 1)
        self.set_valid(tmp)

    def apply(self) -> None:
        self.bump()
        self.bump()


class Emit(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.out)
        self.emit(self.hdr.elems)


def statelocal() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(StateLocalParser, PassControl, Emit),
        name="edsl_statelocal",
        headers=headers,
        metadata=metadata,
        exports={"parser": StateLocalParser, "control": PassControl, "deparser": Emit},
    )


def actlocal() -> apb.BlockAssembly:
    return assemble(
        BlockLibrary(ExtractParser, ActionLocalControl, Emit),
        name="edsl_actlocal",
        headers=headers,
        metadata=metadata,
        exports={"parser": ExtractParser, "control": ActionLocalControl, "deparser": Emit},
    )


# name: (program, input packet, the one output packet on port 0). The state
# runs three times and the action twice; each entry sees `cnt`/`c` at 0 and
# `tmp` invalid. A stale local would give `03 02` and `03 01` instead.
CASES: dict[str, tuple[apb.BlockAssembly, bytes, bytes]] = {
    "statelocal": (statelocal(), b"\x00\x00\x01\x01\x00", b"\x01\x00\x01\x01\x00"),
    "actlocal": (actlocal(), b"\x00\x00", b"\x02\x00"),
}


@pytest.mark.parametrize("name", CASES)
def test_the_programs_validate(name: str) -> None:
    assert validator.validate(CASES[name][0]) == []


@pytest.mark.parametrize("name", CASES)
def test_python_sees_a_fresh_local_at_every_entry(name: str) -> None:
    program, packet, expected = CASES[name]
    assert run_python(arch.reference.load(program), Case(pb.Entries(), 0, packet), 4) == [
        (0, expected)
    ]


@pytest.mark.parametrize("name", CASES)
def test_lean_agrees_on_edsl_locals_at_every_entry(name: str, lean_binary: Path) -> None:
    program, packet, expected = CASES[name]
    case = Case(pb.Entries(), 0, packet)
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        artifacts = Path(os.environ.get("P4BLO_ARTIFACTS", ".artifacts"))
        bundle = artifacts / "lean-edsl-locals" / name
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    assert report.agreed == 1
    assert run_python(arch.reference.load(program), case, 4) == [(0, expected)]
