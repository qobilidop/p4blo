"""The exported conformance corpus (tests/conformance/README.md).

Without Lean, every fixture's requests run on the Python interpreter and
must agree with the recorded Lean replies, one test per fixture so that a
failure names it. With Lean, every fixture is answered again and must be
byte identical, so a semantics change on either side fails until the
fixtures are deliberately re-exported. Corrupted copies show that both
checks see a changed answer.
"""

from __future__ import annotations

import re
import shutil
import sys
import warnings
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from p4blo import conformance
from p4blo.conformance import Fixture, Step
from tests.conformance import inputs

FIXTURES = conformance.DEFAULT_DIR
PATHS = conformance.fixture_paths(FIXTURES)


def test_the_fixture_set_is_the_input_set() -> None:
    """A program or vector added without a re-export fails here."""
    assert sorted(p.stem for p in PATHS) == sorted(i.name for i in inputs.inputs())


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_python_agrees_with_fixture(path: Path) -> None:
    assert conformance.check_python_fixture(path) == []


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_lean_agrees_with_fixture(path: Path, lean_binary: Path) -> None:
    assert conformance.check_lean_fixture(path, [lean_binary]) == []


# ---------------------------------------------------------------------------
# Corrupted fixtures
# ---------------------------------------------------------------------------


def corrupted(
    tmp_path: Path, name: str, change: Callable[[dict[str, object]], dict[str, object]]
) -> tuple[Path, int]:
    """A canonical copy of a fixture with the first reply `change` alters,
    and the number of the request whose reply changed."""
    fixture = conformance.load(FIXTURES / f"{name}.json")
    steps = list(fixture.steps)
    for number, step in enumerate(steps):
        reply = change(dict(step.reply))
        if reply != step.reply:
            steps[number] = Step(step.request, reply)
            path = tmp_path / f"{name}.json"
            path.write_text(conformance.dumps(replace(fixture, steps=tuple(steps))))
            return path, number
    raise AssertionError(f"nothing to corrupt in {name}")


def flip_output_byte(reply: dict[str, object]) -> dict[str, object]:
    outputs = reply.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        return reply
    port, data = outputs[0]
    flipped = f"{int(data[:2], 16) ^ 0x01:02x}" + data[2:]
    return {**reply, "outputs": [[port, flipped], *outputs[1:]]}


def change_state_cell(reply: dict[str, object]) -> dict[str, object]:
    state = reply["state"]
    assert isinstance(state, dict)
    for name, cell in sorted(state.items()):
        if cell.get("kind") == "register" and any(v != "0x0" for v in cell["values"]):
            values = list(cell["values"])
            i = next(i for i, v in enumerate(values) if v != "0x0")
            values[i] = hex(int(values[i], 16) ^ 1)
            return {**reply, "state": {**state, name: {**cell, "values": values}}}
    return reply


def test_python_check_catches_a_flipped_output_byte(tmp_path: Path) -> None:
    path, number = corrupted(tmp_path, "stf-corpus-forwarder-forward", flip_output_byte)
    problems = conformance.check_python_fixture(path)
    assert len(problems) == 1
    assert problems[0].startswith(f"stf-corpus-forwarder-forward: case {number}: Python port ")
    assert "; fixture port " in problems[0]


def test_python_check_catches_a_changed_state_cell(tmp_path: Path) -> None:
    path, number = corrupted(tmp_path, "stf-corpus-stateful-persist", change_state_cell)
    problems = conformance.check_python_fixture(path)
    assert len(problems) == 1
    assert problems[0].startswith(f"stf-corpus-stateful-persist: case {number}: ")
    # Packets agree; the state line names the register and both values.
    assert re.search(r"\nstate \w+: Python \{.*\}; fixture \{.*\}$", problems[0])


def test_python_check_rejects_a_hand_formatted_fixture(tmp_path: Path) -> None:
    path = tmp_path / "reformatted.json"
    source = FIXTURES / "stf-corpus-forwarder-forward.json"
    path.write_text(source.read_text().replace('"ports": 4', '"ports":  4'))
    problems = conformance.check_python_fixture(path)
    assert problems == ["stf-corpus-forwarder-forward: the file is not in canonical form"]


def test_lean_agrees_check_catches_a_changed_answer(tmp_path: Path, lean_binary: Path) -> None:
    path, number = corrupted(tmp_path, "stf-corpus-forwarder-forward", flip_output_byte)
    assert conformance.check_lean_fixture(path, [lean_binary]) == [
        f"stf-corpus-forwarder-forward: request {number}: Lean's reply changed in outputs"
    ]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_one_committed_lean_source_answered_every_fixture() -> None:
    """An export from uncommitted Lean sources would name no commit anyone
    can check out; the header records the digest and the commit."""
    recorded = {conformance._compact(conformance.load(p).lean) for p in PATHS}
    assert len(recorded) == 1
    lean = conformance.load(PATHS[0]).lean
    assert set(lean) == {"commit", "sources"}
    assert re.fullmatch(r"[0-9a-f]{40}", str(lean["commit"]))
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", str(lean["sources"]))


def test_changed_lean_sources_are_reported_not_failed() -> None:
    """The commit is informative; the byte comparison is the check. When
    the sources moved on and every answer stayed, say so and pass."""
    drift = conformance.lean_drift(conformance.load(p) for p in PATHS)
    if drift is not None:
        warnings.warn(drift, stacklevel=1)


def test_drift_names_both_sources(tmp_path: Path) -> None:
    fixture: Fixture = conformance.load(PATHS[0])
    old = replace(fixture, lean={"commit": "0" * 40, "sources": "sha256:" + "0" * 64})
    drift = conformance.lean_drift([old])
    assert drift is not None
    current = conformance.lean_provenance()
    assert "0" * 40 in drift and str(current["sources"]) in drift
    assert "check-lean decides" in drift
    assert conformance.lean_drift([replace(fixture, lean=current)]) is None


def test_export_replaces_the_directory(tmp_path: Path) -> None:
    """A stale fixture goes; export is the only writer of the set. Python
    stands in for Lean through the DRT's fake endpoint."""
    shutil.copy(PATHS[0], tmp_path / "gone.json")
    chosen = [i for i in inputs.stf_inputs() if i.name == "stf-corpus-stateful-persist"]
    fake = [sys.executable, "-m", "p4blo.drt.fake_lean"]
    written = conformance.export(chosen, fake, tmp_path)
    assert [p.name for p in conformance.fixture_paths(tmp_path)] == [
        "stf-corpus-stateful-persist.json"
    ]
    assert conformance.check_python(tmp_path) == []
    assert written == conformance.fixture_paths(tmp_path)
