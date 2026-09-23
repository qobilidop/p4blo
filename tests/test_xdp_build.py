"""Compile/metadata gate only: never load or attach a BPF program."""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

from tests.oracle.xdp.check import metadata_json, sections


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
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
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
            "python3",
            "/opt/check_tests.py",
            "-v",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Ran 4 tests" in result.stderr and result.stderr.rstrip().endswith("OK")
