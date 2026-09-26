"""Tutorial firewall: independent packets, known indices and complete state."""

from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from p4blo.arch import v1model
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.externs.crc import crc16, crc32
from p4blo.drt.run import LeanRunner, run_python
from p4blo.drt.state import snapshot
from tests.oracles import firewall as original
from tests.oracles import run as spectec
from tests.oracles.bmv2 import run as bmv2
from tests.programs.corpus.tutorial_firewall.tutorial_firewall import build
from tests.support.crc import known_spectec_mismatch
from tests.support.firewall import (
    CONFIGURATION,
    CORPUS,
    INDICES,
    MUTATIONS,
    SENTINEL,
    SENTINEL_OUTPUT,
    KnownSpecTecTableMaskDisagreement,
    Step,
    assert_original_observations,
    bypass,
    collision,
    connection,
    edges,
    expected_state,
    forwarded,
    mutant,
    observation_plan,
    shapes,
    vector,
)
from tests.support.firewall import (
    original_bmv2 as original_bmv2,
)


def test_original_smoke_inputs_and_expected_bytes_are_preserved() -> None:
    old = original.plan().phases[0]
    steps = connection()
    assert [(s.case.ingress_port, s.case.packet) for s in steps] == [
        (p.port, p.data) for p in old.packets
    ]
    assert [output for s in steps for output in s.outputs] == [
        (p.port, p.data) for p in old.expects
    ]
    assert (CORPUS / "connection.stf").read_text() == vector(steps)
    assert (CORPUS / "collisions.stf").read_text() == vector(collision())


@pytest.mark.parametrize("port", INDICES)
def test_independent_crc_indices(port: int) -> None:
    key = bytes.fromhex("0a0000010a000002") + port.to_bytes(2, "big") + bytes.fromhex("005006")
    assert (crc16(key) & 4095, crc32(key) & 4095) == INDICES[port]


@pytest.mark.parametrize(
    "sequence",
    [connection(), collision(), collision(reverse=True), shapes(), bypass(), edges()],
    ids=[
        "connection",
        "collision-first-crc16",
        "collision-first-crc32",
        "shapes",
        "bypass",
        "edges",
    ],
)
def test_known_packets_and_complete_state(sequence: list[Step]) -> None:
    loaded = v1model.load(build())
    assert snapshot(loaded) == expected_state(set())
    for item in sequence:
        assert tuple(run_python(loaded, item.case, 4)) == item.outputs
        assert snapshot(loaded) == item.state


@pytest.mark.parametrize(
    "sequence",
    [connection(), collision(), collision(reverse=True), shapes(), bypass(), edges()],
    ids=[
        "connection",
        "collision-first-crc16",
        "collision-first-crc32",
        "shapes",
        "bypass",
        "edges",
    ],
)
def test_lean_agrees_with_independent_firewall_expectations(
    lean_binary: Path, tmp_path: Path, sequence: list[Step]
) -> None:
    program_json = tmp_path / "firewall.json"
    program_json.write_text(arch_wire.dump_json(build()))
    with LeanRunner([lean_binary], program_json, 4) as runner:
        for item in sequence:
            result = runner.run(item.case)
            assert result.error is None and result.diagnostic is None
            assert result.outputs == item.outputs
            assert result.state == item.state


@pytest.mark.parametrize(
    "sequence,directions",
    [
        (connection(), True),
        (collision(), True),
        (collision(reverse=True), True),
        (shapes()[:6], True),
        (bypass(), False),
        (edges(), True),
    ],
    ids=[
        "connection",
        "collision-crc16-first",
        "collision-crc32-first",
        "shapes",
        "bypass",
        "edges",
    ],
)
def test_original_firewall_prefix_state_on_bmv2(
    original_bmv2: tuple[str, bmv2.Compiled], sequence: list[Step], directions: bool
) -> None:
    image, compiled = original_bmv2
    plan = observation_plan(sequence, directions=directions)
    request = plan.request(compiled)
    for phase in request["phases"]:
        phase["post_commands"] = [
            "register_read MyIngress.bloom_filter_1",
            "register_read MyIngress.bloom_filter_2",
        ]
        phase["completion_packet"] = {"port": 2, "data": SENTINEL_OUTPUT.hex()}
    reply = bmv2._driver(image, "replay", json.dumps(request))
    assert_original_observations(sequence, plan, reply)


@pytest.mark.parametrize(
    "sequence,directions",
    [
        (connection(), True),
        (collision(), True),
        (collision(reverse=True), True),
        (shapes()[:6], True),
        (bypass(), False),
        (edges()[1:], True),  # Route miss has its own exact discrepancy test below.
    ],
    ids=[
        "connection",
        "collision-crc16-first",
        "collision-crc32-first",
        "shapes",
        "bypass",
        "edges",
    ],
)
def test_original_firewall_packets_on_spectec(
    tmp_path: Path, sequence: list[Step], directions: bool
) -> None:
    oracle = spectec.find_oracle()
    if oracle is None:
        pytest.skip("P4-SpecTec not built")
    assert oracle.missing() is None
    original.source()
    lines: list[str] = list(original.CONFIGURATION if directions else original.CONFIGURATION[:2])
    lines.extend(vector(sequence).splitlines()[4:])
    path = tmp_path / "firewall.stf"
    path.write_text("\n".join(lines) + "\n")
    result = subprocess.run(
        [
            str(oracle.binary),
            "sim",
            str(oracle.spec),
            "-arch",
            "v1model",
            "-i",
            str(oracle.include),
            "-p",
            str(original.SOURCE),
            "-stf",
            str(path),
        ],
        cwd=oracle.root,
        capture_output=True,
        text=True,
        timeout=spectec.TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1:] == ["passed"], result.stdout + result.stderr


@pytest.mark.parametrize("printed", [False, True], ids=["original", "printed"])
@pytest.mark.xfail(
    strict=True,
    raises=KnownSpecTecTableMaskDisagreement,
    reason="pinned SpecTec table adapter casts base as mask; docs/assurance.md",
)
def test_firewall_route_miss_on_spectec(tmp_path: Path, printed: bool) -> None:
    oracle = spectec.find_oracle()
    if oracle is None:
        pytest.skip("P4-SpecTec not built")
    assert oracle.missing() is None
    original.source()
    route_miss = edges()[0].case.packet
    packets = (
        f"packet 1 {route_miss.hex()}\npacket 1 {SENTINEL.hex()}\n"
        f"expect 2 {SENTINEL_OUTPUT.hex()}$\n"
    )
    if printed:
        source = tmp_path / "printed.p4"
        source.write_text(v1model.print_program(build()))
        translated, _ = spectec.translate(
            "\n".join(CONFIGURATION) + "\n" + packets, BoundIndex.build(build())
        )
    else:
        source = original.SOURCE
        translated = "\n".join(original.CONFIGURATION) + "\n" + packets
    path = tmp_path / "route-miss.stf"
    path.write_text(translated)
    result = subprocess.run(
        [
            str(oracle.binary),
            "sim",
            str(oracle.spec),
            "-arch",
            "v1model",
            "-i",
            str(oracle.include),
            "-p",
            str(source),
            "-stf",
            str(path),
        ],
        cwd=oracle.root,
        capture_output=True,
        text=True,
        timeout=spectec.TIMEOUT_SECONDS,
    )
    mismatch = (
        f"error: expected (2) {SENTINEL_OUTPUT.hex().upper()} "
        f"but got (2) {forwarded(route_miss, 2).hex().upper()}"
    )
    if known_spectec_mismatch(result, oracle.spec, mismatch):
        raise KnownSpecTecTableMaskDisagreement(mismatch)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1:] == ["passed"], result.stdout + result.stderr


def test_original_state_observer_rejects_partial_wrong_or_stale_results() -> None:
    sequence = connection()
    plan = observation_plan(sequence)
    phases = []
    for item, phase in zip(sequence, plan.phases, strict=True):
        phases.append(
            {
                "error": None,
                "outputs": {
                    str(port): [e.data.hex() for e in phase.expects if e.port == port]
                    for port in [1, 2]
                },
                "registers": {
                    "MyIngress." + obs.name: list(obs.values)
                    for obs in item.state
                    if obs.kind == "register"
                },
            }
        )
    good = {"phases": phases}
    assert_original_observations(sequence, plan, good)
    mutants = []
    for kind in [
        "missing",
        "truncated",
        "touched-only",
        "extra-cell",
        "wrong-index",
        "stale",
        "error",
        "missing-sentinel",
        "duplicate-sentinel",
        "wrong-sentinel",
        "premature-ack",
    ]:
        bad = deepcopy(good)
        phase = bad["phases"][1]
        registers = phase["registers"]
        name = "MyIngress.bloom_filter_2"
        if kind == "missing":
            del registers[name]
        elif kind == "truncated":
            registers[name].pop()
        elif kind == "touched-only":
            registers[name] = [1]
        elif kind == "extra-cell":
            registers[name].append(0)
        elif kind == "wrong-index":
            registers[name][1987], registers[name][2182] = 0, 1
        elif kind == "stale":
            registers[name] = [0] * 4096
        elif kind == "error":
            phase["error"] = "switch crashed"
        elif kind == "missing-sentinel":
            phase["outputs"]["2"].pop()
        elif kind == "duplicate-sentinel":
            phase["outputs"]["2"].append(SENTINEL_OUTPUT.hex())
        elif kind == "wrong-sentinel":
            phase["outputs"]["2"][-1] = SENTINEL.hex()
        else:
            bad["phases"][0]["outputs"]["1"] = [forwarded(sequence[0].case.packet, 1).hex()]
        mutants.append(bad)
    for bad in mutants:
        with pytest.raises(AssertionError):
            assert_original_observations(sequence, plan, bad)


@pytest.mark.parametrize("name", MUTATIONS)
def test_firewall_known_answers_kill_valid_semantic_mutations(name: str) -> None:
    program, sequence = mutant(name)
    loaded = v1model.load(program)
    detected = False
    for item in sequence:
        outputs = tuple(run_python(loaded, item.case, 4))
        detected |= outputs != item.outputs or snapshot(loaded) != item.state
    assert detected, f"surviving valid port mutant: {name}"


@pytest.mark.parametrize("name", MUTATIONS)
def test_lean_agrees_on_firewall_mutant_detection(
    lean_binary: Path, tmp_path: Path, name: str
) -> None:
    program, sequence = mutant(name)
    path = tmp_path / "mutant.json"
    path.write_text(arch_wire.dump_json(program))
    detected = False
    with LeanRunner([lean_binary], path, 4) as runner:
        for item in sequence:
            result = runner.run(item.case)
            assert result.error is None and result.diagnostic is None
            detected |= result.outputs != item.outputs or result.state != item.state
    assert detected, f"surviving valid port mutant on Lean: {name}"
