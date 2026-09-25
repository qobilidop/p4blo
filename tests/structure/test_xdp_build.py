"""Compile/metadata gate only: never load or attach a BPF program."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from uuid import uuid4

import pytest

from tests.oracle.xdp.check import metadata_json, sections


def run_offline(
    image: str, arguments: list[str], *, timeout: float = 120
) -> subprocess.CompletedProcess[str]:
    """Own one container across client errors/timeouts, not only normal exit."""
    name = f"p4blo-xdp-check-{uuid4().hex}"
    try:
        return subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--name",
                name,
                "--network",
                "none",
                "--read-only",
                "--user",
                "65534:65534",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,noexec,size=32m,mode=1777",
                "--pids-limit",
                "64",
                "--memory",
                "512m",
                image,
                *arguments,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    finally:
        # Killing the attached Docker client does not stop the daemon's
        # container. Target only our unpredictable, explicitly owned name.
        try:
            subprocess.run(
                ["docker", "rm", "--force", name], capture_output=True, text=True, timeout=15
            )
        finally:
            remaining = subprocess.run(
                ["docker", "ps", "--all", "--quiet", "--filter", f"name=^/{name}$"],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            assert not remaining.stdout.strip(), f"XDP check container survived cleanup: {name}"


@pytest.mark.parametrize(
    "failure", [None, "exit", "start", "timeout", "cleanup-timeout", "survivor", "daemon"]
)
def test_xdp_container_cleanup(monkeypatch: pytest.MonkeyPatch, failure: str | None) -> None:
    calls: list[list[str]] = []

    def command(argv: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert options["timeout"] in (0.1, 15)
        if argv[1] == "run":
            if failure == "start":
                raise OSError("client startup failed")
            if failure == "timeout":
                raise subprocess.TimeoutExpired(argv, 0.1)
            return subprocess.CompletedProcess(
                argv, 1 if failure == "exit" else 0, "runtime answer", ""
            )
        if argv[1] == "rm":
            if failure == "cleanup-timeout":
                raise subprocess.TimeoutExpired(argv, 15)
            # Normal --rm may already have removed it; absence is decided
            # by listing, never by the removal command's exit code.
            return subprocess.CompletedProcess(argv, 1, "", "already absent")
        assert argv[1] == "ps" and options["check"] is True
        if failure == "daemon":
            raise subprocess.CalledProcessError(1, argv)
        return subprocess.CompletedProcess(
            argv, 0, "container-id" if failure == "survivor" else "", ""
        )

    monkeypatch.setattr(subprocess, "run", command)
    if failure in (None, "exit"):
        result = run_offline("owned-image", ["inspect"], timeout=0.1)
        assert result.stdout == "runtime answer"
        assert result.returncode == (1 if failure == "exit" else 0)
    elif failure in ("timeout", "cleanup-timeout"):
        with pytest.raises(subprocess.TimeoutExpired):
            run_offline("owned-image", ["inspect"], timeout=0.1)
    elif failure == "start":
        with pytest.raises(OSError, match="client startup failed"):
            run_offline("owned-image", ["inspect"], timeout=0.1)
    elif failure == "daemon":
        with pytest.raises(subprocess.CalledProcessError):
            run_offline("owned-image", ["inspect"], timeout=0.1)
    else:
        with pytest.raises(AssertionError, match="survived cleanup"):
            run_offline("owned-image", ["inspect"], timeout=0.1)
    assert len(calls) == 3
    name = calls[0][calls[0].index("--name") + 1]
    assert name.startswith("p4blo-xdp-check-")
    assert calls[0] == [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--user",
        "65534:65534",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,noexec,size=32m,mode=1777",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "owned-image",
        "inspect",
    ]
    assert calls[1] == ["docker", "rm", "--force", name]
    assert calls[2][-1] == f"name=^/{name}$"


@pytest.mark.parametrize(
    "response",
    [
        "[]",
        '{"programs":1,"maps":2,"priority":10,"chain_pass":1,"loaded":0}',
        '{"programs":true,"maps":2,"priority":10,"chain_pass":1,"loaded":false}',
        '{"programs":1,"maps":2,"priority":10,"chain_pass":1,"loaded":false,"maps":2}',
        '{"programs":1,"maps":2,"priority":10,"chain_pass":1,"loaded":false,"extra":1}',
    ],
)
def test_xdp_inspector_rejects_ambiguous_metadata(response: str) -> None:
    with pytest.raises(ValueError):
        metadata_json(response)


def test_xdp_inspector_metadata_known_answer() -> None:
    expected = {"programs": 1, "maps": 2, "priority": 10, "chain_pass": 1, "loaded": False}
    assert metadata_json(json.dumps(expected)) == expected


@pytest.mark.parametrize("data", [b"", b"\x7fELF", bytes(64)])
def test_xdp_rejects_incomplete_elf(data: bytes) -> None:
    with pytest.raises(ValueError):
        sections(data)


def test_xdp_original_compiles_and_passes_offline_negative_checks() -> None:
    required = os.environ.get("P4BLO_REQUIRE_XDP_BUILD") == "1"
    image = os.environ.get("P4BLO_XDP_BUILD_IMAGE", "p4blo-xdp-build")
    if shutil.which("docker") is None:
        if required:
            pytest.fail("required XDP compile gate needs Docker")
        pytest.skip("Docker unavailable for optional XDP compile gate")
    available = subprocess.run(
        ["docker", "image", "inspect", image], capture_output=True, timeout=30
    )
    if available.returncode:
        if required:
            pytest.fail("required XDP compile image unavailable")
        pytest.skip("optional XDP compile image unavailable")
    result = run_offline(image, ["python3", "/opt/check_tests.py", "-v"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Ran 4 tests" in result.stderr and result.stderr.rstrip().endswith("OK")
