"""Execute the documented authoring/running paths, not a parallel demo API."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from p4blo import stf
from p4blo.arch import v1model
from p4blo.edsl import EdslError, bit8
from p4blo.interp.tables import InstallError
from p4blo.v0 import p4blo_pb2 as pb
from tests.corpus.forwarder.forwarder import build

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs/quickstart.md"
OUTPUT = "forwarder: output ports [[2]]\ntutorial_firewall: output ports [[], [2], [1], []]\n"


def snippet(name: str) -> str:
    text = DOCUMENT.read_text()
    marker = f"<!-- quickstart: {name} -->\n```sh\n"
    assert text.count(marker) == 1
    block = text.split(marker)[1].split("\n```", 1)[0]
    header, source = block.split("\n", 1)
    assert header == "uv run python - <<'PY'"
    delimiter = "PY"
    assert source.endswith("\n" + delimiter)
    return source.removesuffix("\n" + delimiter) + "\n"


def python_demo(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", snippet(name)],
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


def test_python_quickstart_diagnostics() -> None:
    with pytest.raises(EdslError, match="no truth value"):
        bool(bit8(1) == bit8(1))
    loaded = v1model.load(build())
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
    switch = v1model.V1Model(ports=4)
    assert switch.run(loaded, loaded.entries(entries), packet.port, packet.data) == []
    assert switch.diagnostics == ["egress_spec 5 is not a configured v1model port"]
