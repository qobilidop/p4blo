"""Characterize exact pinned oracle disagreements using standalone P4 inputs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from p4blo import ir, stf
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracle import run as spectec
from tests.oracle.bmv2 import run as bmv2

CASES = Path(__file__).resolve().parents[1] / "oracle" / "discrepancies"
NAMES = ("crc32_odd", "register_bounds", "table_mask", "const_priority")
pytestmark = pytest.mark.oracle


@pytest.mark.parametrize("name", NAMES)
def test_same_inputs_distinct_recorded_answers(name: str) -> None:
    """Expectation differences must never change source, setup or packets."""
    vectors = [
        (CASES / f"{name}.{oracle}.stf").read_text().splitlines() for oracle in ("bmv2", "spectec")
    ]
    inputs = [[line for line in lines if not line.startswith("expect ")] for lines in vectors]
    assert inputs[0] == inputs[1]
    assert vectors[0] != vectors[1]
    assert any(line.startswith("packet ") for line in inputs[0])


@pytest.mark.parametrize("name", NAMES)
def test_pinned_spectec_answer(name: str) -> None:
    oracle = spectec.find_oracle()
    if oracle is None:
        pytest.skip("P4-SpecTec not built")
    assert oracle.missing() is None
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
            str(CASES / f"{name}.p4"),
            "-stf",
            str(CASES / f"{name}.spectec.stf"),
        ],
        cwd=oracle.root,
        capture_output=True,
        text=True,
        timeout=spectec.TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1:] == ["passed"], result.stdout + result.stderr


@pytest.mark.parametrize("name", NAMES)
def test_pinned_bmv2_answer(name: str) -> None:
    image = bmv2.default_image()
    if reason := bmv2.unavailable(image):
        pytest.skip(reason)
    compiled = bmv2.compile_program(image, (CASES / f"{name}.p4").read_text())
    # These probes configure their tables in P4 and need no IR-dependent
    # STF name or width translation. The source itself goes to p4c unchanged.
    index = ir.Index.build(pb.BlockLibrary(name="packet_only"))
    vector = CASES / f"{name}.bmv2.stf"
    statements = stf.parse(vector.read_text())
    if name == "table_mask":
        assert vector.read_text().splitlines()[0] == "add I.route 1 hdr.h.key:0x0a I.hit()"
        table = compiled.find_table("I", "route")
        action = compiled.find_action(table, "I", "hit")
        phase = bmv2.Phase(
            commands=[f"table_add {table['name']} {action} 0x0a&&&0xff => 9999"],
            packets=[s for s in statements if isinstance(s, stf.Packet)],
            expects=[s for s in statements if isinstance(s, stf.Expect)],
        )
        plan = bmv2.Plan([phase], [0, 1, 2], [])
        reply = bmv2._driver(image, "replay", json.dumps(plan.request(compiled)))
        status, detail = bmv2.judge(plan, reply)
        assert status == "pass", detail
    else:
        assert all(isinstance(item, stf.Packet | stf.Expect) for item in statements)
        verdict = bmv2.run_vector(image, index, compiled, vector)
        assert verdict.status == "pass", verdict
