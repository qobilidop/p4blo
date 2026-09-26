"""Package checks without native oracle dependencies."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from p4blo.arch import externs, v1model
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.externs.crc import crc16, crc32
from p4blo.drt import state
from p4blo.drt.case import Case
from p4blo.drt.run import run_python
from p4blo.interp import InterpError
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.crc import (
    EXPECTED,
    KNOWN,
    PACKET,
    known_spectec_mismatch,
    program,
    spectec_sink_warning,
    typed_program,
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


def test_typed_crc_authoring_executes() -> None:
    assert run_python(v1model.load(typed_program()), Case(pb.Entries(), 0, b""), 4) == [
        (0, bytes.fromhex("4040ff000000"))
    ]


@pytest.mark.parametrize("data,c16,c32", KNOWN)
def test_known_answers(data: bytes, c16: int, c32: int) -> None:
    assert crc16(data) == c16
    assert crc32(data) == c32


def test_dynamic_authoring_execution_and_observation() -> None:
    loaded = v1model.load(program([data for data, _, _ in KNOWN]))
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
    index = BoundIndex.build(p)
    with pytest.raises(externs.BindError, match="positive multiple of 8"):
        externs.supplied_registry().bind(index)
    with pytest.raises(v1model.PrintError, match="positive multiple of 8"):
        v1model.print_program(p)


@pytest.mark.parametrize("width", [16, 32])
def test_wrong_bound_argument_width_is_not_padded(width: int) -> None:
    loaded = v1model.load(program([b"x"]))
    bound = loaded.externs[f"crc{width}_0"]
    with pytest.raises(InterpError, match="bound width"):
        bound.call("compute", [Bits(16, 1)])


@pytest.mark.parametrize("index", [0, 1], ids=["crc16", "crc32"])
def test_crc_extra_constructor_arguments_are_not_ignored(index: int) -> None:
    p = program([b"x"])
    p.extern_instances[index].args.add(bits=pb.BitsLiteral(width=8, value="1"))
    with pytest.raises(externs.BindError, match="constructor takes no arguments"):
        externs.supplied_registry().bind(BoundIndex.build(p))
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
        externs.supplied_registry().bind(BoundIndex.build(p))
    message = "has no method" if bad == "method" else "wrong shape"
    with pytest.raises(v1model.PrintError, match=message):
        v1model.print_program(p)
