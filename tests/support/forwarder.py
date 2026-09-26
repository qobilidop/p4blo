"""Reusable forwarder fixtures and independent expectations."""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Any

import pytest
from google.protobuf.message import Message

from p4blo import stf
from p4blo.arch import v1model, validator
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program
from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.values import Bits, Header, Struct
from p4blo.v0 import p4blo_pb2 as pb
from tests.programs.corpus.forwarder.forwarder import build

ROOT = Path(__file__).resolve().parents[2]


CORPUS = ROOT / "tests/programs/corpus/forwarder"


VECTORS = sorted(CORPUS.glob("*.stf"))


def assert_program_identity(program: apb.BlockAssembly) -> None:
    assert program == build(), "program differs from Python authoring"
    assert program == arch_wire.load_text(CORPUS / "forwarder.txtpb"), (
        "program differs from frozen golden"
    )
    assert validator.validate(program) == []


@pytest.fixture(scope="module")
def forwarder() -> apb.BlockAssembly:
    assert {"forward.stf", "miss.stf", "non_ipv4.stf", "lpm_precedence.stf", "too_short.stf"} <= {
        vector.name for vector in VECTORS
    }, "required forwarder STF vector is missing"
    program = arch_wire.load_text(CORPUS / "forwarder.txtpb")
    assert_program_identity(program)
    return program


def compare_and_save(
    program: apb.BlockAssembly, cases: list[Case], lean_binary: Path, label: str
) -> None:
    try:
        report = compare_program(program, cases, 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ROOT / ".artifacts/drt"))
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"lean-forwarder-{label}.json"
        save(report, destination)
        pytest.fail(f"complete mismatch saved to {destination}: {report}")
    assert report.agreed == len(cases)


def edge_case(ttl: int) -> tuple[Case, list[tuple[int, bytes]]]:
    index = BoundIndex.build(arch_wire.load_text(CORPUS / "forwarder.txtpb"))
    installed = stf.parse(
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 ipv4_forward(dstAddr:0x000000000202, port:2)"
    )
    packet = bytes.fromhex("00000000010100000000000108004500001a00010000")
    packet += bytes([ttl]) + bytes.fromhex("1100000a0001010a000202deadbeefcafe")
    # Literal answers are independent of authored field accessors and either
    # interpreter. Source is old destination 0x101, NOT old source 1/new dst0x202.
    ttl_checksum = {0: "ff11a4cf", 1: "0011a3d0"}[ttl]
    expected = bytes.fromhex(
        "00000000020200000000010108004500001a00010000"
        + ttl_checksum
        + "0a0001010a000202deadbeefcafe"
    )
    return Case(stf.to_entries(index, installed), 0, packet), [(2, expected)]


def freeze(value: Any) -> object:
    """Detached, exact-type contents of every field of this finite Env profile.

    Includes complete dataclasses/maps/protobufs, packet/emitter slots and
    extern-instance state; never retains a mutable object as the expected value.
    Unknown object forms fail closed instead of falling back to repr/equality.
    """
    kind = type(value)
    if value is None or kind in (str, bytes, int, bool, float):
        return kind, value
    if isinstance(value, Message):
        return kind, value.SerializeToString(deterministic=True)
    if isinstance(value, dict):
        return kind, tuple(sorted(((freeze(k), freeze(v)) for k, v in value.items()), key=repr))
    if isinstance(value, list | tuple):
        return kind, tuple(freeze(item) for item in value)
    if isinstance(value, set | frozenset):
        return kind, tuple(sorted((freeze(item) for item in value), key=repr))
    if dataclasses.is_dataclass(value):
        return kind, tuple(
            (field.name, freeze(getattr(value, field.name))) for field in dataclasses.fields(value)
        )
    slots = tuple(
        name
        for cls in kind.__mro__
        for name in getattr(cls, "__slots__", ())
        if name not in {"__dict__", "__weakref__"}
    )
    if slots or hasattr(value, "__dict__"):
        return (
            kind,
            tuple((name, freeze(getattr(value, name))) for name in slots),
            freeze(vars(value)) if hasattr(value, "__dict__") else None,
        )
    raise TypeError(f"unobserved runtime value {kind}")


def invalid_env(
    program: apb.BlockAssembly, valid: bool, sentinel: bool, port: int, ttl: int
) -> Env:
    loaded = v1model.load(program)
    installed = loaded.entries(edge_case(0)[0].entries)
    installed.default_actions[("MyIngress", "ipv4_lpm")] = pb.ActionCall(action="NoAction")
    loaded.externs["sentinel"] = Register(2, 8)
    loaded.externs["sentinel"].cells[:] = [Bits(8, 7), Bits(8, 9)]
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 3
    emitter = Emitter()
    emitter.value, emitter.width = 0x1234, 13
    env = Env.for_block(
        loaded.index,
        loaded.index.blocks["MyIngress"],
        loaded.externs,
        entries=installed,
        packet=packet,
        emitter=emitter,
        visits={("sentinel", "state"): 13},
    )
    env.vars["hdr"] = Struct(
        "headers",
        [
            Header("ethernet_t", valid, [Bits(48, 0x101), Bits(48, 1), Bits(16, 0x0800)]),
            Header(
                "ipv4_t",
                False,
                [
                    Bits(4, 4),
                    Bits(4, 5),
                    Bits(8, 17),
                    Bits(16, 26),
                    Bits(16, 1),
                    Bits(3, 0),
                    Bits(13, 0),
                    Bits(8, ttl),
                    Bits(8, 17),
                    Bits(16, 0x9876),
                    Bits(32, 0x0A000101),
                    Bits(32, 0x0A000202),
                ],
            ),
        ],
    )
    env.vars["meta"] = Struct("metadata", [Bits(9, 3), Bits(9, port)])
    # Retain unrelated boolean-state coverage independently of packet fate.
    env.vars["untouched_flag"] = sentinel
    return env


def observe_invalid_control(env: Env) -> None:
    before = freeze(env)
    stmt.execute(env.block.body, env)
    assert freeze(env) == before, "invalid IPv4 changed complete Python control state"
