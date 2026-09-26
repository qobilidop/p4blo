"""Persistent execution of the Python-authored tutorial firewall.

The generic Lean endpoint checks serialized programs and request sequences
against Python and independent packet/state expectations.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings

from p4blo import arch, stf
from p4blo.arch import v1model
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.firewall import Step, bypass, collision, connection, edges, shapes
from tests.support.firewall_boundaries import persistence, truncated
from tests.support.firewall_generated import Event, campaigns, model, targeted
from tests.support.firewall_semantics import (
    VECTORS,
    check_sequence,
    compare_and_save,
)
from tests.support.firewall_semantics import (
    firewall as firewall,
)


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
@pytest.mark.lean
def test_lean_agrees_firewall_stf(
    firewall: apb.BlockAssembly, lean_binary: Path, vector: Path
) -> None:
    statements = stf.parse(vector.read_text())
    index = BoundIndex.build(firewall)
    cases: list[Case] = []

    def collect(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        cases.append(Case(entries, port, packet))
        return []

    stf.replay(index, statements, collect)
    assert cases
    compare_and_save(firewall, cases, lean_binary)
    stf.assert_replay(
        index, statements, arch.stf_driver(v1model.V1Model(ports=4), v1model.load(firewall))
    )


@pytest.mark.parametrize(
    "sequence",
    [connection(), collision(), collision(reverse=True), shapes(), bypass(), edges()],
    ids=["connection", "collision", "reverse-collision", "shapes", "bypass", "edges"],
)
@pytest.mark.lean
def test_lean_agrees_firewall_known_sequences(
    firewall: apb.BlockAssembly, lean_binary: Path, sequence: list[Step]
) -> None:
    check_sequence(firewall, sequence, lean_binary)


@pytest.mark.parametrize("length", range(55))
@pytest.mark.lean
def test_lean_agrees_firewall_packet_boundaries(
    firewall: apb.BlockAssembly, lean_binary: Path, length: int
) -> None:
    check_sequence(firewall, [truncated(length)], lean_binary)


@pytest.mark.parametrize("length", range(54))
@pytest.mark.lean
def test_lean_agrees_firewall_persistent_boundaries(
    firewall: apb.BlockAssembly, lean_binary: Path, length: int
) -> None:
    check_sequence(firewall, persistence(length), lean_binary)


@pytest.mark.parametrize("events", targeted().values(), ids=targeted().keys())
@pytest.mark.lean
def test_lean_agrees_firewall_host_policy(
    firewall: apb.BlockAssembly, lean_binary: Path, events: list[Event]
) -> None:
    check_sequence(firewall, model(events), lean_binary)


@settings(max_examples=40, derandomize=True, deadline=None)
@given(events=campaigns())
@pytest.mark.lean
def test_lean_agrees_firewall_generated(
    firewall: apb.BlockAssembly, lean_binary: Path, events: list[Event]
) -> None:
    check_sequence(firewall, model(events), lean_binary)
