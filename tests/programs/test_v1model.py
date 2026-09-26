"""Six-stage architecture acceptance on Python, Lean and two external oracles."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from p4blo import arch, stf
from p4blo.arch import v1model
from p4blo.drt.case import Case
from p4blo.drt.run import compare_program
from p4blo.drt.state import encode, snapshot
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracle import run as spectec
from tests.oracle.bmv2 import run as bmv2
from tests.oracle.v1model_disagreements import ACTUAL, KnownV1ModelDisagreement, known
from tests.programs.v1model_fixtures import stages

PROBES = Path(__file__).resolve().parents[1] / "frontend" / "probes"
NATIVE = ("v1model_stages", "v1model_portable", "dropgate", "undrop", "egressspec", "readspec")


def test_stage_order_and_drop_state() -> None:
    loaded = v1model.load(stages())
    vector = (PROBES / "v1model_stages.stf").read_text()
    stf.assert_replay(loaded.index, stf.parse(vector), arch.stf_driver(v1model.V1Model(4), loaded))
    assert encode(snapshot(loaded)) == {
        "egress_count": {"kind": "register", "width": 8, "values": ["0x6"]},
        "compute_count": {"kind": "register", "width": 8, "values": ["0x5"]},
        "deparser_count": {"kind": "register", "width": 8, "values": ["0x5"]},
    }


def test_lean_agrees_on_six_stage_state(lean_binary: Path) -> None:
    packets = [
        s
        for s in stf.parse((PROBES / "v1model_stages.stf").read_text())
        if isinstance(s, stf.Packet)
    ]
    cases = [Case(pb.Entries(), p.port, p.data) for p in packets]
    report = compare_program(stages(), cases, 4, [lean_binary])
    assert report.passed, report.summary()
    test_stage_order_and_drop_state()


def run_spectec(source: Path, vector: Path) -> subprocess.CompletedProcess[str]:
    oracle = spectec.find_oracle()
    if oracle is None:
        pytest.skip("P4-SpecTec oracle is not built")
    assert oracle.missing() is None
    return subprocess.run(
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
            str(vector),
        ],
        cwd=oracle.root,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )


def run_bmv2(source: str, vector: Path) -> None:
    image = bmv2.default_image()
    reason = bmv2.unavailable(image)
    if reason is not None:
        pytest.skip(reason)
    compiled = bmv2.compile_program(image, source)
    statements = stf.parse(vector.read_text())
    phase = bmv2.Phase(
        packets=[s for s in statements if isinstance(s, stf.Packet)],
        expects=[s for s in statements if isinstance(s, stf.Expect)],
        no_packets=[s for s in statements if isinstance(s, stf.NoPacket)],
    )
    plan = bmv2.Plan([phase], [0, 1, 2, 3], [])
    reply = bmv2._driver(image, "replay", json.dumps(plan.request(compiled)))
    verdict, detail = bmv2.judge(plan, reply)
    assert verdict == "pass", detail


@pytest.mark.oracle
@pytest.mark.parametrize("name", NATIVE)
def test_spectec_native_stage_profiles(name: str) -> None:
    done = run_spectec(PROBES / f"{name}.p4", PROBES / f"{name}.stf")
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.oracle
@pytest.mark.parametrize("name", (*(n for n in NATIVE if n != "v1model_stages"), *ACTUAL))
def test_bmv2_native_stage_profiles(name: str) -> None:
    run_bmv2((PROBES / f"{name}.p4").read_text(), PROBES / f"{name}.stf")


@pytest.mark.oracle
def test_spectec_printed_stage_profile(tmp_path: Path) -> None:
    source = tmp_path / "stages.p4"
    source.write_text(v1model.print_program(stages()))
    done = run_spectec(source, PROBES / "v1model_stages.stf")
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.oracle
@pytest.mark.parametrize("name", ACTUAL)
@pytest.mark.xfail(
    strict=True,
    raises=KnownV1ModelDisagreement,
    reason="Pinned P4-SpecTec egress behavior; docs/oracle-discrepancies.md",
)
def test_spectec_native_egress_disagreement(name: str) -> None:
    done = run_spectec(PROBES / f"{name}.p4", PROBES / f"{name}.stf")
    if known(name, done):
        raise KnownV1ModelDisagreement(done.stderr)
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize("name", ACTUAL)
def test_disagreement_classifier_rejects_unrelated_failures(name: str) -> None:
    port, data = ACTUAL[name]
    stderr = (
        f"error: [FAIL] Remaining packets to be matched:\n({port}) {data}"
        "[FAIL] Expected packets to be output:\n(2) 0002\n\n  source: sim\n"
    )
    if name == "v1model_egress_spec_read":
        stderr = "error: expected (2) 0002 but got (2) 0202\n\n  source: sim\n"
    result = subprocess.CompletedProcess([], 1, "", stderr)
    assert known(name, result)
    for changed in (
        subprocess.CompletedProcess([], 2, "", stderr),
        subprocess.CompletedProcess([], 1, "unexpected", stderr),
        subprocess.CompletedProcess([], 1, "", stderr.replace(data, "ffff", 1)),
        subprocess.CompletedProcess([], 1, "", "error: build failed\n" + stderr),
        subprocess.CompletedProcess([], 1, "", stderr + "another failure\n"),
    ):
        assert not known(name, changed)


@pytest.mark.parametrize("role", ["egress", "compute_checksum"])
def test_egress_spec_is_reset_before_egress(role: str) -> None:
    from tests.unit.test_v1model import assign, block, path, program, read, run

    model = program()
    if role == "compute_checksum":
        exports = [e for e in model.exports if e.role != "egress"]
        del model.exports[:]
        model.exports.extend(exports)
    block(model, role).body.append(
        assign(
            path("hdr", "h", "value"),
            pb.Expr(cast=pb.Cast(to=pb.Type(bits=8), operand=read("meta", "egress_spec"))),
        )
    )
    assert run(model) == [(1, b"\x00payload")]


@pytest.mark.parametrize("role", ["verify_checksum", "ingress", "egress", "compute_checksum"])
def test_block_runner_selects_one_control_stage(role: str) -> None:
    from p4blo.arch import spectec_block

    model = stages()
    selected = next(e.block for e in model.exports if e.role == role)
    printed = spectec_block.print_program(model, control_role=role)
    assert printed.rstrip().endswith(f"P4blo(Parse(), {selected}(), Emit()) main;")
    assert "standard_metadata" not in printed
    for name in ("Verify", "Ingress", "Egress", "Compute"):
        assert f"control {name}(" in printed
    with pytest.raises(spectec_block.PrintError, match="not a control"):
        spectec_block.print_program(model, control_role="parser")
    with pytest.raises(spectec_block.PrintError, match="no block exported"):
        spectec_block.print_program(model, control_role="missing")
