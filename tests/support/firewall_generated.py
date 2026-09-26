"""Reusable firewall generated fixtures and independent expectations."""

from __future__ import annotations

import hashlib
import os
import random
import zlib
from dataclasses import dataclass
from pathlib import Path

import pytest
from hypothesis import strategies as st

from p4blo import stf
from p4blo.arch import v1model
from p4blo.arch.bindings import BoundIndex
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import (
    ProtocolError,
    Report,
    compare_program,
    python_outcome,
    request_json,
)
from p4blo.drt.state import Observation, Snapshot
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracles import firewall as original
from tests.oracles.bmv2 import run as bmv2
from tests.programs.corpus.tutorial_firewall.tutorial_firewall import build
from tests.support.firewall import (
    CONFIGURATION,
    INDICES,
    Step,
    forwarded,
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
