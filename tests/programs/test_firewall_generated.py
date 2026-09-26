"""tcp-flow-policy-v1: independent Bloom model over shrinking flow sequences."""

from __future__ import annotations

import hashlib
import json
import os
import random
import zlib
from dataclasses import dataclass
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo import stf
from p4blo.arch import v1model
from p4blo.arch.bindings import BoundIndex
from p4blo.drt.case import Case
from p4blo.drt.replay import load, save
from p4blo.drt.run import (
    ProtocolError,
    Report,
    compare_program,
    python_outcome,
    request_json,
)
from p4blo.drt.state import Observation, Snapshot
from p4blo.v0 import p4blo_pb2 as pb
from tests.corpus.tutorial_firewall.tutorial_firewall import build
from tests.oracle import firewall as original
from tests.oracle.bmv2 import run as bmv2
from tests.programs.test_firewall import (
    CONFIGURATION,
    INDICES,
    SENTINEL_OUTPUT,
    Step,
    assert_original_observations,
    forwarded,
    observation_plan,
    packet,
)


def crc16_reference(data: bytes) -> int:
    """Polynomial remainder, not either production engine's CRC loop/table."""
    reflected = bytes(int(f"{byte:08b}"[::-1], 2) for byte in data)
    dividend = int.from_bytes(reflected, "big") << 16
    while dividend.bit_length() > 16:
        dividend ^= 0x18005 << (dividend.bit_length() - 17)
    return int(f"{dividend:016b}"[::-1], 2)


def indices(port: int, reverse: bool = False) -> tuple[int, int]:
    """The independent network-order 104-bit tuple, optionally reversed."""
    a, b, sport, dport = (2, 1, 80, port) if reverse else (1, 2, port, 80)
    data = bytes([10, 0, 0, a, 10, 0, 0, b])
    data += sport.to_bytes(2, "big") + dport.to_bytes(2, "big") + b"\x06"
    return crc16_reference(data) % 4096, zlib.crc32(data) % 4096


def check_hash_reference() -> None:
    assert crc16_reference(b"123456789") == 0xBB3D
    assert zlib.crc32(b"123456789") == 0xCBF43926
    assert crc16_reference(bytes(13)) == 0
    for port, expected in INDICES.items():
        assert indices(port) == expected


@dataclass(frozen=True)
class Policy:
    outbound: int | None = 0
    inbound: int | None = 1

    def __post_init__(self) -> None:
        assert self.outbound in (None, 0, 1) and self.inbound in (None, 0, 1)


@dataclass(frozen=True)
class Event:
    port: int
    inbound: bool = False
    flags: int = 0x10
    policy: Policy = Policy()

    def __post_init__(self) -> None:
        assert 0 <= self.port <= 65535 and 0 <= self.flags <= 255


def entries(policy: Policy) -> pb.Entries:
    lines: list[str] = list(CONFIGURATION[:2])
    for ingress, egress, direction in [(1, 2, policy.outbound), (2, 1, policy.inbound)]:
        if direction is not None:
            lines.append(
                f"add check_ports meta.ingress_port:{ingress} meta.egress_spec:{egress} "
                f"set_direction(dir:{direction})"
            )
    return stf.to_entries(BoundIndex.build(build()), stf.parse("\n".join(lines)))


def complete_state(ones: tuple[set[int], set[int]]) -> Snapshot:
    return (
        Observation("bloom_filter_1", "register", 1, tuple(int(i in ones[0]) for i in range(4096))),
        Observation("bloom_filter_2", "register", 1, tuple(int(i in ones[1]) for i in range(4096))),
        Observation("csum", "checksum16"),
        Observation("hash16", "crc16"),
        Observation("hash32", "crc32"),
    )


def model(events: list[Event]) -> list[Step]:
    """Independent application specification: monotone Bloom bits, not exact flows."""
    check_hash_reference()
    ones: tuple[set[int], set[int]] = (set(), set())
    result = []
    for sequence, event in enumerate(events, 2000):
        data = packet(event.port, inbound=event.inbound, flags=event.flags, seq=sequence)
        direction = event.policy.inbound if event.inbound else event.policy.outbound
        allowed = True
        if direction is not None:
            i, j = indices(event.port, reverse=event.inbound != (direction == 1))
            if direction == 1:
                allowed = i in ones[0] and j in ones[1]
            elif event.flags & 2:
                ones[0].add(i)
                ones[1].add(j)
        ingress, egress = (2, 1) if event.inbound else (1, 2)
        outputs = ((egress, forwarded(data, egress)),) if allowed else ()
        result.append(
            Step(Case(entries(event.policy), ingress, data), outputs, complete_state(ones))
        )
    return result


def failure_path(report: Report, directory: Path) -> Path:
    assert report.program_ir is not None
    digest = hashlib.sha256(report.program_ir.SerializeToString(deterministic=True))
    for case in report.inputs:
        digest.update(request_json(case).encode())
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"firewall-generated-{digest.hexdigest()[:24]}.json"


def check_python(sequence: list[Step]) -> None:
    loaded = v1model.load(build())
    for item in sequence:
        actual = python_outcome(loaded, item.case, 4)
        assert actual.error is None and actual.diagnostic is None
        assert actual.outputs == item.outputs
        assert actual.state == item.state


def check_lean(events: list[Event], lean_binary: Path) -> None:
    sequence = model(events)
    try:
        report = compare_program(build(), [item.case for item in sequence], 4, [lean_binary])
    except ProtocolError as error:
        assert error.report is not None
        report = error.report
    if not report.passed:
        directory = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        bundle = failure_path(report, directory)
        save(report, bundle)
        pytest.fail(f"{report.summary()}; replay {bundle}; protocol={report.protocol_error}")
    assert report.cases == len(sequence)
    # Compare/save first. Equal wrong outcomes still fail independent known answers.
    check_python(sequence)


def targeted() -> dict[str, list[Event]]:
    absent = Policy(None, None)
    swapped = Policy(1, 0)
    return {
        "missing-direction-syn": [Event(0, flags=2, policy=absent)],
        "host-policy-changes": [
            Event(65535, flags=0x12, policy=absent),
            Event(65535, inbound=True),
            Event(65535, flags=0x12),
            Event(65535, inbound=True, flags=1, policy=absent),
            Event(65535, inbound=True, flags=4),
            Event(65535, inbound=True, flags=2, policy=swapped),
            Event(65535, policy=swapped),
            Event(0, inbound=True),
        ],
        "bloom-false-positive": [
            Event(12346, inbound=True),
            Event(749, flags=2),
            Event(12346, inbound=True),
            Event(13602, flags=2),
            Event(12346, inbound=True),
        ],
    }


@st.composite
def campaigns(draw: st.DrawFn) -> list[Event]:
    ports = draw(st.lists(st.integers(0, 65535), min_size=1, max_size=3, unique=True))
    direction = st.sampled_from([None, 0, 1])
    policy = st.builds(Policy, direction, direction)
    flags = st.one_of(st.sampled_from([0, 2, 0x10, 0x12, 1, 4, 255]), st.integers(0, 255))
    event = st.builds(Event, st.sampled_from(ports), st.booleans(), flags, policy)
    return draw(st.lists(event, min_size=1, max_size=10))


def test_reference_hash_known_answers() -> None:
    check_hash_reference()


def test_model_named_witnesses() -> None:
    scenarios = targeted()
    assert [bool(item.outputs) for item in model(scenarios["bloom-false-positive"])] == [
        False,
        True,
        False,
        True,
        True,
    ]
    changes = model(scenarios["host-policy-changes"])
    assert [bool(item.outputs) for item in changes] == [
        True,
        False,
        True,
        True,
        True,
        True,
        True,
        False,
    ]
    assert [sum(sum(obs.values) for obs in item.state) for item in changes] == [
        0,
        0,
        2,
        2,
        2,
        4,
        4,
        4,
    ]
    missing = model(scenarios["missing-direction-syn"])[0]
    assert missing.outputs and missing.state == complete_state((set(), set()))


def test_replay_identity_preserves_policy_and_sequence(tmp_path: Path) -> None:
    program = build()
    events = targeted()["host-policy-changes"]
    cases = tuple(item.case for item in model(events))
    report = Report(program.name, 0, 4, inputs=cases, program_ir=program)
    path = failure_path(report, tmp_path)
    save(report, path)
    restored, inputs, ports, seed = load(path)
    assert restored == program and inputs == list(cases) and (ports, seed) == (4, 0)
    shorter = Report(program.name, 0, 4, inputs=cases[:-1], program_ir=program)
    assert failure_path(shorter, tmp_path) != path
    # Same packet bytes/ports, different host snapshot: a distinct experiment.
    changed = list(cases)
    changed[0] = Case(entries(Policy()), cases[0].ingress_port, cases[0].packet)
    changed_report = Report(program.name, 0, 4, inputs=tuple(changed), program_ir=program)
    assert failure_path(changed_report, tmp_path) != path


@pytest.mark.parametrize("events", targeted().values(), ids=targeted())
def test_generated_profile_known_answers(events: list[Event]) -> None:
    check_python(model(events))


@settings(max_examples=40, deadline=None, derandomize=True)
@given(events=campaigns())
def test_generated_profile_shrinks_valid_configurations(events: list[Event]) -> None:
    check_python(model(events))


@pytest.mark.parametrize("events", targeted().values(), ids=targeted())
def test_lean_agrees_on_targeted_flow_policies(lean_binary: Path, events: list[Event]) -> None:
    check_lean(events, lean_binary)


@settings(max_examples=40, deadline=None, derandomize=True)
@given(events=campaigns())
def test_lean_agrees_on_shrinking_flow_policies(lean_binary: Path, events: list[Event]) -> None:
    check_lean(events, lean_binary)


def oracle_sample(seed: int, swapped: bool) -> list[Event]:
    port = random.Random(seed).randrange(65536)
    policy = Policy(1, 0) if swapped else Policy()
    return [
        Event(port, inbound=not swapped, policy=policy),
        Event(port, inbound=swapped, flags=0x12, policy=policy),
        Event(port, inbound=not swapped, policy=policy),
        Event(port, inbound=swapped, flags=1, policy=policy),
        Event(port, inbound=not swapped, flags=4, policy=policy),
    ]


@pytest.fixture(scope="module")
def original_bmv2() -> tuple[str, bmv2.Compiled]:
    image = bmv2.default_image()
    unavailable = bmv2.unavailable(image)
    if unavailable:
        pytest.skip(unavailable)
    return image, bmv2.compile_program(image, original.source())


@pytest.mark.parametrize(
    "events",
    [
        oracle_sample(20260923, False),
        oracle_sample(20260924, True),
        targeted()["missing-direction-syn"],
    ],
    ids=["seed-20260923", "seed-20260924-swapped", "missing-direction-syn"],
)
def test_generated_original_prefixes_on_bmv2(
    original_bmv2: tuple[str, bmv2.Compiled], events: list[Event]
) -> None:
    image, compiled = original_bmv2
    sequence = model(events)
    policy = events[0].policy
    assert all(event.policy == policy for event in events)
    commands = list(original.COMMANDS[:2])
    for ingress, egress, direction in [(1, 2, policy.outbound), (2, 1, policy.inbound)]:
        if direction is not None:
            commands.append(
                f"table_add MyIngress.check_ports MyIngress.set_direction {ingress} {egress} "
                f"=> {direction}"
            )
    plan = observation_plan(sequence)
    for phase in plan.phases:
        phase.commands = commands
    request = plan.request(compiled)
    for phase in request["phases"]:
        phase["post_commands"] = [
            "register_read MyIngress.bloom_filter_1",
            "register_read MyIngress.bloom_filter_2",
        ]
        phase["completion_packet"] = {"port": 2, "data": SENTINEL_OUTPUT.hex()}
    reply = bmv2._driver(image, "replay", json.dumps(request))
    assert_original_observations(sequence, plan, reply)
