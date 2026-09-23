"""The fixed execution claim binds Python's actual state to Lean's checker."""

from __future__ import annotations

import io
import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from p4blo.drt import certificate
from p4blo.externs.counter import Counter
from p4blo.externs.register import Register
from p4blo.interp.api import ExternResult
from p4blo.interp.env import Env
from p4blo.interp.stmt import execute
from p4blo.interp.values import Bits, Value
from p4blo.v0 import p4blo_pb2 as pb


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


@pytest.mark.parametrize("binding", ["r", "k"])
@pytest.mark.parametrize("change", ["replace", "delete"])
def test_lean_agrees_on_final_binding_changes(
    lean_binary: Path, monkeypatch: pytest.MonkeyPatch, binding: str, change: str
) -> None:
    def changed(stmts: Iterable[pb.Stmt], env: Env) -> None:
        execute(stmts, env)
        final = dict(env.externs)
        if change == "delete":
            del final[binding]
        else:
            final[binding] = Register(1, 8) if binding == "r" else Counter(1)
        env.externs = final

    monkeypatch.setattr(certificate, "execute", changed)
    artifact = certificate.create_example_certificate(41, 9, lean_binary=lean_binary)
    assert certificate.verify_example_certificate(artifact, lean_binary=lean_binary) == "mismatch"


def test_lean_agrees_on_rejecting_inconsistent_python_cell_width(
    lean_binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Register.call

    def corrupt(self: Register, method: str, args: list[Value]) -> ExternResult:
        result = original(self, method, args)
        if method == "write":
            self.cells[0] = Bits(7, self.cells[0].value)
        return result

    monkeypatch.setattr(Register, "call", corrupt)
    with pytest.raises(certificate.CertificateError, match="inconsistent register cell widths"):
        certificate.create_example_certificate(41, 9, lean_binary=lean_binary)


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
        ('{"verdict":"mismatch","verdict":"accepted"}', 0),
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


class _CleanupPeer:
    def __init__(self, outcome: str) -> None:
        self.pid = 12345
        self.returncode: int | None = None
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
        self.stderr = io.BytesIO()
        self.outcome = outcome
        self.communicate_timeouts: list[float] = []
        self.wait_timeouts: list[float] = []

    def communicate(
        self, input: bytes | None = None, timeout: float | None = None
    ) -> tuple[bytes, bytes]:
        assert timeout is not None
        self.communicate_timeouts.append(timeout)
        if self.outcome.startswith("timeout"):
            if len(self.communicate_timeouts) == 1 or self.outcome == "timeout_stubborn":
                raise subprocess.TimeoutExpired("peer", timeout)
            self.returncode = -9
            return b"", b""
        if self.outcome.startswith("exchange"):
            raise BrokenPipeError("broken pipe")
        self.returncode = 0
        return b'{"verdict":"accepted"}', b""

    def wait(self, timeout: float | None = None) -> int:
        assert timeout is not None
        self.wait_timeouts.append(timeout)
        if self.outcome in {"timeout_stubborn", "exchange_stubborn"}:
            raise subprocess.TimeoutExpired("peer", timeout)
        self.returncode = -9
        return -9


@pytest.mark.parametrize("outcome", ["timeout", "timeout_stubborn"])
def test_certificate_does_not_repeat_successful_group_cleanup(
    monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    peer = _CleanupPeer(outcome)
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: peer)
    kills = 0

    def kill_once(process: object) -> None:
        nonlocal kills
        assert process is peer
        kills += 1
        if kills > 1:
            raise PermissionError(1, "redundant kill denied")

    monkeypatch.setattr(certificate, "_kill_owned_process_group", kill_once)
    with pytest.raises(certificate.CertificateError, match="timed out after 0.2s"):
        certificate.verify_example_certificate("{}", lean_binary="peer", timeout=0.2)
    assert kills == 1
    assert peer.communicate_timeouts == [0.2, 1]
    if outcome == "timeout_stubborn":
        assert peer.wait_timeouts == [1]
        assert peer.stdin.closed and peer.stdout.closed and peer.stderr.closed


@pytest.mark.parametrize(
    "outcome", ["timeout_stubborn", "exchange", "exchange_stubborn", "success"]
)
def test_certificate_reports_first_group_cleanup_denial(
    monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    peer = _CleanupPeer(outcome)
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: peer)
    kills = 0

    def deny_kill(process: object) -> None:
        nonlocal kills
        assert process is peer
        kills += 1
        raise PermissionError(1, "first kill denied")

    monkeypatch.setattr(certificate, "_kill_owned_process_group", deny_kill)
    with pytest.raises(
        certificate.CertificateError, match="process-group cleanup failed"
    ) as caught:
        certificate.verify_example_certificate("{}", lean_binary="peer", timeout=0.2)
    assert kills == 1
    assert isinstance(caught.value.__cause__, PermissionError)
    if outcome == "timeout_stubborn":
        assert "timed out after 0.2s" in str(caught.value)
        assert peer.communicate_timeouts == [0.2, 1]
        assert peer.wait_timeouts == [1]
    elif outcome.startswith("exchange"):
        assert "exchange failed: broken pipe" in str(caught.value)
        assert peer.wait_timeouts == [1]
    else:
        assert peer.communicate_timeouts == [0.2]


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cleanup")
def test_certificate_timeout_reaps_descendant_held_pipes(tmp_path: Path) -> None:
    peer = tmp_path / "peer.py"
    peer.write_text("#!/usr/bin/env python3\nimport os, time\nos.fork()\ntime.sleep(60)\n")
    peer.chmod(0o755)
    started = time.monotonic()
    with pytest.raises(certificate.CertificateError, match="timed out"):
        certificate.verify_example_certificate("{}", lean_binary=peer, timeout=0.2)
    assert time.monotonic() - started < 5


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cleanup")
def test_successful_certificate_peer_cannot_leave_descendants(tmp_path: Path) -> None:
    pid_file = tmp_path / "child.pid"
    peer = tmp_path / "peer.py"
    peer.write_text(
        "#!/usr/bin/env python3\nimport os, pathlib, time\n"
        "child = os.fork()\n"
        "if child == 0:\n"
        "    for fd in (0, 1, 2): os.close(fd)\n"
        "    time.sleep(60)\n"
        "    os._exit(0)\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child))\n"
        'print(\'{"verdict":"accepted"}\', flush=True)\n'
    )
    peer.chmod(0o755)
    try:
        assert certificate.verify_example_certificate("{}", lean_binary=peer) == "accepted"
        child = int(pid_file.read_text())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(child)],
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            ).stdout.strip()
            if not status or status.startswith("Z"):
                break
            time.sleep(0.01)
        else:
            pytest.fail("successful invocation left its child running")
    finally:
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass


@pytest.mark.parametrize("register", [-1, 256, True])
def test_create_refuses_invalid_register_without_running_lean(register: int) -> None:
    with pytest.raises(ValueError, match="register"):
        certificate.create_example_certificate(register, 0)
