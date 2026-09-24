"""Execute the documented authoring/running paths, not a parallel demo API."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from p4blo import arch, stf
from p4blo.edsl import EdslError, bit8
from p4blo.interp.tables import InstallError
from p4blo.v0 import p4blo_pb2 as pb
from tests.corpus.forwarder.forwarder import build

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/quickstart.md"
OUTPUT = "forwarder: output ports [[2]]\ntutorial_firewall: output ports [[], [2], [1], []]\n"


def snippet(name: str, language: str) -> str:
    text = DOCUMENT.read_text()
    marker = f"<!-- quickstart: {name} -->\n```sh\n"
    assert text.count(marker) == 1
    block = text.split(marker)[1].split("\n```", 1)[0]
    header, source = block.split("\n", 1)
    if language == "python":
        assert header == "nix develop -c uv run python - <<'PY'"
        delimiter = "PY"
    else:
        toolchain = (ROOT / "lean/lean-toolchain").read_text().strip()
        assert header == f"nix develop -c lake +{toolchain} -d lean env lean --stdin <<'LEAN'"
        delimiter = "LEAN"
    assert source.endswith("\n" + delimiter)
    return source.removesuffix("\n" + delimiter) + "\n"


def python_demo(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", snippet(name, "python")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_python_quickstart_sources_and_persistence() -> None:
    result = python_demo("python-run")
    assert result.returncode == 0, result.stderr
    assert result.stderr == "" and result.stdout == OUTPUT


def test_lean_agrees_quickstart_sources_and_persistence(lean_binary: Path) -> None:
    assert lean_binary.is_file()
    result = python_demo("lean-run")
    assert result.returncode == 0, result.stderr
    assert result.stderr == "" and result.stdout == OUTPUT


def lean_fragment(source: str) -> subprocess.CompletedProcess[str]:
    lake = shutil.which("lake")
    assert lake is not None, "the documented Lean snippet needs the pinned Lake toolchain"
    toolchain = (ROOT / "lean/lean-toolchain").read_text().strip()
    return subprocess.run(
        [lake, f"+{toolchain}", "-d", str(ROOT / "lean"), "env", "lean", "--stdin"],
        cwd=ROOT,
        input=source,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_lean_agrees_quickstart_fragment_and_imports(lean_binary: Path) -> None:
    assert lean_binary.is_file()
    source = snippet("lean-fragment", "lean")
    result = lean_fragment(source)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == "" and result.stdout.startswith("0\n")
    for name in ["Forwarder.program", "TutorialFirewall.program", "prepareSwitch", "runSwitch"]:
        assert f"P4blo.{name}" in result.stdout
    assert source.count("bits[8, 255]") == 1
    invalid = lean_fragment(source.replace("bits[8, 255]", "bits[8, 256]"))
    assert invalid.returncode != 0 and "error:" in invalid.stdout
    assert "256" in invalid.stdout, "literal diagnostic should identify the overflowing value"


def test_python_quickstart_diagnostics() -> None:
    with pytest.raises(EdslError, match="no truth value"):
        bool(bit8(1) == bit8(1))
    loaded = arch.load(build())
    with pytest.raises(InstallError, match="no table 'missing'"):
        loaded.entries(
            pb.Entries(
                tables=[
                    pb.TableEntries(
                        block="MyIngress",
                        table="missing",
                        default_action=pb.ActionCall(action="drop"),
                    )
                ]
            )
        )
    statements = stf.parse((ROOT / "tests/corpus/forwarder/forward.stf").read_text())
    entries = stf.to_entries(loaded.index, statements)
    entries.tables[0].entries[0].action.args[1].bits.value = "5"
    packet = next(statement for statement in statements if isinstance(statement, stf.Packet))
    switch = arch.Switch(ports=4)
    assert switch.run(loaded, loaded.entries(entries), packet.port, packet.data) == []
    assert switch.diagnostics == ["egress_port 5 is not a port of this switch"]


@pytest.mark.parametrize("name", ["leanForwarder", "leanTutorialFirewall"])
def test_lean_agrees_quickstart_server_errors(lean_binary: Path, name: str) -> None:
    assert lean_binary.is_file()
    command = [str(ROOT / "lean/.lake/build/bin" / name)]
    usage = subprocess.run(command + ["unknown"], capture_output=True, text=True, timeout=30)
    assert usage.returncode == 2 and usage.stdout == ""
    assert usage.stderr == f"usage: {name} [run]\n"
    stream = subprocess.run(
        command + ["run"],
        input='{"ingress_port":4,"packet":""}\n',
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert stream.returncode == 0 and stream.stderr == ""
    lines = stream.stdout.splitlines()
    assert len(lines) == 1
    reply = json.loads(lines[0])
    assert set(reply) == {"error", "state"}
    assert reply["error"] == "ingress_port 4 is not a port of this switch"
