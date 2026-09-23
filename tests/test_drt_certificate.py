"""The fixed execution claim binds Python's actual state to Lean's checker."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from p4blo.drt import certificate
from p4blo.externs.counter import Counter
from p4blo.interp.api import ExternResult
from p4blo.interp.values import Value


@pytest.mark.parametrize("register", [0, 41, 255])
def test_lean_agrees_on_python_execution_claim(register: int, lean_binary: Path) -> None:
    artifact = certificate.create_example_certificate(register, 9, lean_binary=lean_binary)
    assert artifact["format"] == certificate.FORMAT
    assert artifact["example"] == certificate.EXAMPLE
    assert artifact["initial"] == [hex(register), "0x9"]
    assert artifact["claim"] == {
        "completion": {"kind": "success"},
        "register": [8, [hex((register + 1) & 255)]],
        "counter": ["0xa"],
        "local": [8, hex((register + 1) & 255)],
    }
    assert certificate.verify_example_certificate(artifact, lean_binary=lean_binary) == "accepted"


def test_lean_agrees_on_large_hex_counter(lean_binary: Path) -> None:
    counter = int("f" * 5000, 16)
    artifact = certificate.create_example_certificate(255, counter, lean_binary=lean_binary)
    assert artifact["initial"][1] == hex(counter)
    assert artifact["claim"]["counter"] == [hex(counter + 1)]
    assert certificate.verify_example_certificate(artifact, lean_binary=lean_binary) == "accepted"


def test_lean_agrees_on_exported_zero_literal_spelling(lean_binary: Path) -> None:
    program = certificate.export_example_program(lean_binary=lean_binary)
    first = program.blocks[0].body[0].call_extern.args[1].expr.literal.bits
    final = program.blocks[0].body[3].call_extern.args[0].expr.literal.bits
    assert first.width == final.width == 32
    assert first.value == final.value == "0"
    artifact = certificate.create_example_certificate(0, 0, lean_binary=lean_binary)
    wire: dict[str, Any] = artifact["program"]
    body: list[dict[str, Any]] = wire["blocks"][0]["body"]
    assert body[0]["call_extern"]["args"][1]["expr"]["literal"]["bits"]["value"] == "0"


@pytest.mark.parametrize(
    "change",
    [
        "completion_kind",
        "completion_message",
        "register_width",
        "register_cell",
        "register_absent",
        "counter_cell",
        "counter_absent",
        "local_width",
        "local_value",
        "local_absent",
    ],
)
def test_lean_agrees_on_claim_corruption(change: str, lean_binary: Path) -> None:
    artifact = certificate.create_example_certificate(41, 9, lean_binary=lean_binary)
    raw: dict[str, Any] = json.loads(json.dumps(artifact))
    claim: dict[str, Any] = raw["claim"]
    match change:
        case "completion_kind":
            claim["completion"] = {"kind": "parse", "message": "PacketTooShort"}
        case "completion_message":
            claim["completion"] = {"kind": "interp", "message": "fabricated"}
        case "register_width":
            claim["register"][0] = 7
        case "register_cell":
            claim["register"][1][0] = "0x2b"
        case "register_absent":
            claim["register"] = None
        case "counter_cell":
            claim["counter"][0] = "0xb"
        case "counter_absent":
            claim["counter"] = None
        case "local_width":
            claim["local"][0] = 7
        case "local_value":
            claim["local"][1] = "0x2b"
        case "local_absent":
            claim["local"] = None
        case _:
            raise AssertionError(change)
    assert certificate.verify_example_certificate(json.dumps(raw), lean_binary=lean_binary) == (
        "mismatch"
    )


@pytest.mark.parametrize("change", ["register", "counter"])
def test_lean_agrees_on_changed_initial_value(change: str, lean_binary: Path) -> None:
    artifact = certificate.create_example_certificate(41, 9, lean_binary=lean_binary)
    raw: dict[str, Any] = json.loads(json.dumps(artifact))
    raw["initial"][0 if change == "register" else 1] = "0x8"
    assert certificate.verify_example_certificate(json.dumps(raw), lean_binary=lean_binary) == (
        "mismatch"
    )


def test_lean_agrees_on_budget_exhaustion(lean_binary: Path) -> None:
    artifact = certificate.create_example_certificate(41, 9, fuel=9, lean_binary=lean_binary)
    assert artifact["claim"]["completion"] == {"kind": "success"}
    assert certificate.verify_example_certificate(artifact, lean_binary=lean_binary) == "exhausted"
    artifact["fuel"] = 10
    assert certificate.verify_example_certificate(artifact, lean_binary=lean_binary) == "accepted"


@pytest.mark.parametrize(
    "change",
    [
        "program",
        "arithmetic",
        "constructor",
        "format",
        "version",
        "example",
        "missing_claim",
        "missing_completion",
        "missing_register",
        "missing_counter",
        "missing_local",
        "noncanonical",
        "out_of_width",
        "negative_fuel",
        "string_fuel",
    ],
)
def test_lean_agrees_on_invalid_artifact(change: str, lean_binary: Path) -> None:
    artifact = certificate.create_example_certificate(41, 9, lean_binary=lean_binary)
    raw: dict[str, Any] = json.loads(json.dumps(artifact))
    match change:
        case "program":
            raw["program"]["name"] = "changed"
        case "arithmetic":
            raw["program"]["blocks"][0]["body"][1]["assign"]["value"]["binary"]["op"] = (
                "BINARY_OP_SUB"
            )
        case "constructor":
            raw["program"]["extern_instances"][0]["args"][0]["bits"]["value"] = "2"
        case "format":
            raw["format"] = "unknown"
        case "version":
            raw["version"] = 2
        case "example":
            raw["example"] = "unknown"
        case "missing_claim":
            raw.pop("claim")
        case "missing_completion":
            raw["claim"].pop("completion")
        case "missing_register":
            raw["claim"].pop("register")
        case "missing_counter":
            raw["claim"].pop("counter")
        case "missing_local":
            raw["claim"].pop("local")
        case "noncanonical":
            raw["initial"][0] = "0x029"
        case "out_of_width":
            raw["initial"][0] = "0x100"
        case "negative_fuel":
            raw["fuel"] = -1
        case "string_fuel":
            raw["fuel"] = "10"
        case _:
            raise AssertionError(change)
    with pytest.raises(certificate.InvalidCertificate):
        certificate.verify_example_certificate(json.dumps(raw), lean_binary=lean_binary)


def test_lean_agrees_on_missing_python_counter_increment(
    lean_binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def omit_increment(self: Counter, method: str, args: list[Value]) -> ExternResult:
        assert method == "count"
        return ExternResult()

    monkeypatch.setattr(Counter, "call", omit_increment)
    artifact = certificate.create_example_certificate(41, 9, lean_binary=lean_binary)
    assert artifact["claim"]["counter"] == ["0x9"]
    assert certificate.verify_example_certificate(artifact, lean_binary=lean_binary) == "mismatch"


def test_lean_agrees_on_certificate_cli(tmp_path: Path, lean_binary: Path) -> None:
    path = tmp_path / "claim.json"
    created = subprocess.run(
        [
            sys.executable,
            "-m",
            "p4blo.drt.certificate",
            "create",
            "--register",
            "0x29",
            "--counter",
            "0x9",
            "--lean",
            str(lean_binary),
            "-o",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert created.returncode == 0, created.stdout + created.stderr
    artifact = json.loads(path.read_text())
    assert artifact["program"]["name"] == "execution-certificate"
    checked = subprocess.run(
        [
            sys.executable,
            "-m",
            "p4blo.drt.certificate",
            "verify",
            str(path),
            "--lean",
            str(lean_binary),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert checked.returncode == 0
    assert json.loads(checked.stdout) == {"verdict": "accepted"}


@pytest.mark.parametrize(
    ("change", "exit_code", "response"),
    [
        ("claim", 1, {"verdict": "mismatch"}),
        ("fuel", 1, {"verdict": "exhausted"}),
        ("program", 2, {"error": "certificate program is not the fixed example"}),
    ],
)
def test_lean_agrees_on_cli_verifier_exit_codes(
    tmp_path: Path,
    lean_binary: Path,
    capsys: pytest.CaptureFixture[str],
    change: str,
    exit_code: int,
    response: dict[str, str],
) -> None:
    artifact = certificate.create_example_certificate(41, 9, lean_binary=lean_binary)
    raw: dict[str, Any] = json.loads(json.dumps(artifact))
    match change:
        case "claim":
            raw["claim"]["counter"][0] = "0xb"
        case "fuel":
            raw["fuel"] = 9
        case "program":
            raw["program"]["name"] = "changed"
        case _:
            raise AssertionError(change)
    path = tmp_path / "claim.json"
    path.write_text(json.dumps(raw))
    assert certificate.main(["verify", str(path), "--lean", str(lean_binary)]) == exit_code
    assert json.loads(capsys.readouterr().out) == response


@pytest.mark.parametrize(
    ("reply", "exit_code"),
    [
        ("{}", 0),
        ('{"verdict":"accepted"}', 1),
        ('{"verdict":"mismatch"}', 0),
        ('{"verdict":"other"}', 0),
        ("not JSON", 0),
    ],
)
def test_checker_rejects_missing_malformed_or_exit_mismatched_verdict(
    tmp_path: Path, reply: str, exit_code: int
) -> None:
    peer = tmp_path / "peer.py"
    peer.write_text(
        f"#!/usr/bin/env python3\nimport sys\nprint({reply!r})\nsys.exit({exit_code})\n"
    )
    peer.chmod(0o755)
    with pytest.raises(certificate.CertificateError):
        certificate.verify_example_certificate("{}", lean_binary=peer)


def test_unencodable_request_fails_before_starting_peer(tmp_path: Path) -> None:
    with pytest.raises(certificate.CertificateError, match="not UTF-8"):
        certificate.verify_example_certificate('"\ud800"', lean_binary=tmp_path / "missing")


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cleanup")
def test_certificate_timeout_reaps_descendant_held_pipes(tmp_path: Path) -> None:
    peer = tmp_path / "peer.py"
    peer.write_text("#!/usr/bin/env python3\nimport os, time\nos.fork()\ntime.sleep(60)\n")
    peer.chmod(0o755)
    started = time.monotonic()
    with pytest.raises(certificate.CertificateError, match="timed out"):
        certificate.verify_example_certificate("{}", lean_binary=peer, timeout=0.2)
    assert time.monotonic() - started < 5


@pytest.mark.parametrize("register", [-1, 256, True])
def test_create_refuses_invalid_register_without_running_lean(register: int) -> None:
    with pytest.raises(ValueError, match="register"):
        certificate.create_example_certificate(register, 0)
