"""Independent wire and state expectations for the homepage's complete example."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from p4blo import stf
from p4blo.arch import v1model
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import LeanRunner, Outcome, ProtocolError, compare_cases, python_outcome
from p4blo.drt.state import Observation
from p4blo.v0 import p4blo_pb2 as pb
from tests.corpus.vlan_gateway.vlan_gateway import build

ROOT = Path(__file__).resolve().parents[2]
MACS = bytes.fromhex("000000000002000000000001")
PAYLOAD = bytes.fromhex("4500001400010000401166d60a0000010a000002")
UNTAGGED = MACS + bytes.fromhex("0800") + PAYLOAD


def frame(vid: int = 42, *, flags: int = 0, inner: int = 0x0800, payload: bytes = PAYLOAD):
    return (
        MACS
        + bytes.fromhex("8100")
        + (flags | vid).to_bytes(2, "big")
        + inner.to_bytes(2, "big")
        + payload
    )


def policy(vid: int = 42, port: int = 2) -> pb.Entries:
    return stf.to_entries(
        BoundIndex.build(build()),
        stf.parse(
            f"add access meta.ingress_port:1 hdr.vlan.vid:{vid} "
            f"hdr.ethernet.dst:0x000000000002 deliver(port:{port})"
        ),
    )


def sequence() -> tuple[list[Case], list[Outcome]]:
    """One persistent switch: include matching policies for every guard boundary."""
    cases: list[Case] = []
    expected: list[Outcome] = []
    counts = [0] * 512

    def add(
        packet: bytes,
        *,
        ingress: int = 1,
        vid: int = 42,
        port: int = 2,
        output: bytes | None = None,
        admitted: bool = False,
        empty_policy: bool = False,
    ) -> None:
        cases.append(Case(pb.Entries() if empty_policy else policy(vid, port), ingress, packet))
        if admitted:
            counts[port] += 1
        expected.append(
            Outcome(
                outputs=() if output is None else ((port, output),),
                diagnostic=f"egress_spec {port} is not a configured v1model port"
                if admitted and 4 <= port < 511
                else None,
                state=(Observation("admissions", "counter", values=tuple(counts)),),
            )
        )

    add(frame(), output=UNTAGGED, admitted=True)
    add(frame(), empty_policy=True)
    add(frame(43))
    add(frame(), ingress=0)
    add(bytes.fromhex("000000000003") + frame()[6:])
    add(UNTAGGED, vid=0)
    add(frame(0), vid=0)
    add(frame(4095), vid=4095)
    add(frame(inner=0x8100, payload=bytes.fromhex("00010800") + PAYLOAD))
    add(frame(inner=0x88A8, payload=bytes.fromhex("00010800") + PAYLOAD))
    add(MACS + bytes.fromhex("88a8") + frame()[14:])
    for length in range(18):
        add(frame()[:length], vid=0)
    for flags in range(16):
        add(frame(flags=flags << 12), output=UNTAGGED, admitted=True)
    for vid in (1, 4094):
        add(frame(vid), vid=vid, port=3, output=UNTAGGED, admitted=True)
    for payload in (b"", bytes(range(256))):
        add(
            frame(inner=0x86DD, payload=payload), output=MACS + b"\x86\xdd" + payload, admitted=True
        )
    # Architecture validation happens after the action: these admissions still count.
    for port in (4, 511):
        add(frame(), port=port, admitted=True)
    add(frame(), port=0, output=UNTAGGED, admitted=True)
    add(frame(), output=UNTAGGED, admitted=True)
    return cases, expected


def test_gateway_independent_packets_and_persistent_admissions() -> None:
    loaded = v1model.load(build())
    cases, expected = sequence()
    for number, (case, answer) in enumerate(zip(cases, expected, strict=True)):
        assert python_outcome(loaded, case, 4) == answer, number


def test_lean_agrees_gateway_packets_and_persistent_admissions(
    lean_binary: Path, tmp_path: Path
) -> None:
    (ROOT / ".artifacts/drt").mkdir(parents=True, exist_ok=True)
    program = build()
    source = tmp_path / "gateway.json"
    source.write_text(arch_wire.dump_json(program))
    cases, expected = sequence()
    observations: list[Outcome] = []
    with LeanRunner([lean_binary], source, 4) as runner:

        def observe(case: Case) -> Outcome:
            answer = runner.run(case)
            observations.append(answer)
            return answer

        try:
            report = compare_cases(program.name, v1model.load(program), cases, 4, observe)
        except ProtocolError as error:
            if error.report is not None:
                save(error.report, ROOT / ".artifacts/drt/vlan-gateway-protocol.json")
            raise
    if not report.passed or observations != expected:
        save(report, ROOT / ".artifacts/drt/vlan-gateway.json")
    assert report.passed, report.divergences
    assert observations == expected


def test_gateway_demo_output() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "tests.corpus.vlan_gateway.demo"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "VLAN 42: port 2, 34 bytes, tag removed; admissions[2] = 1\n"
        "VLAN 43: drop; admissions[2] = 1\n"
        "VLAN 42: port 2, 34 bytes, tag removed; admissions[2] = 2\n"
    )
    assert result.stderr == ""
