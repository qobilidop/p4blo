"""The exported conformance corpus (tests/conformance/README.md).

Without Lean, every fixture's requests run on the Python interpreter and
must agree with the recorded Lean replies, one test per fixture so that a
failure names it. With Lean, every fixture is answered again and must be
byte identical, so a semantics change on either side fails until the
fixtures are deliberately refreshed. Corrupted copies show that both
checks see a changed answer, and that the membership test sees a lost one.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from p4blo import conformance
from p4blo.conformance import Fixture, Step
from tests.conformance import inputs, mutants

FIXTURES = conformance.DEFAULT_DIR
PATHS = conformance.fixture_paths(FIXTURES)
FAKE_LEAN = [sys.executable, "-m", "p4blo.drt.fake_lean"]


def test_the_fixture_set_is_the_input_set() -> None:
    """A program or vector added without an export fails here, and so does
    a fixture that lost steps: neither check can see a missing request."""
    assert conformance.check_inputs(FIXTURES, inputs.inputs()) == []


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_python_agrees_with_fixture(path: Path) -> None:
    assert conformance.check_python_fixture(path) == []


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_lean_agrees_with_fixture(path: Path, lean_binary: Path) -> None:
    assert conformance.check_lean_fixture(path, [lean_binary]) == []


def test_the_contract_is_exercised() -> None:
    """Error replies and replies with several outputs are part of the
    contract a third implementation must meet; the corpus holds both."""
    replies = [s.reply for p in PATHS for s in conformance.load(p).steps]
    assert any("error" in r for r in replies)
    outputs = [r["outputs"] for r in replies if isinstance(r.get("outputs"), list)]
    assert any(len(o) > 1 for o in outputs if isinstance(o, list))
    assert any("diagnostic" in r for r in replies)


@pytest.mark.parametrize("name", mutants.MUTANTS)
def test_python_mutants_are_caught(name: str) -> None:
    """Each deliberate interpreter fault fails some fixture's check."""
    assert mutants.killers(name) != []


def test_the_corpus_stays_small() -> None:
    """A program with thousands of nonzero cells would multiply the size;
    the budget makes that a decision rather than an accident."""
    sizes = {p.stem: p.stat().st_size for p in PATHS}
    assert sum(sizes.values()) < 4_000_000
    assert max(sizes.values()) < 1_000_000


# ---------------------------------------------------------------------------
# Corrupted fixtures
# ---------------------------------------------------------------------------


def write(path: Path, fixture: Fixture) -> Path:
    path.write_text(conformance.dumps(fixture))
    return path


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
            path = write(tmp_path / f"{name}.json", replace(fixture, steps=tuple(steps)))
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
        if cell.get("kind") == "register" and cell["nonzero"]:
            [index, value], *rest = cell["nonzero"]
            nonzero = [[index, hex(int(value, 16) ^ 1)], *rest]
            return {**reply, "state": {**state, name: {**cell, "nonzero": nonzero}}}
    return reply


def reword_error(reply: dict[str, object]) -> dict[str, object]:
    if "error" not in reply:
        return reply
    return {**reply, "error": "Lean rejects this install"}


def test_python_check_catches_a_flipped_output_byte(tmp_path: Path) -> None:
    path, number = corrupted(tmp_path, "stf-corpus-forwarder-forward", flip_output_byte)
    problems = conformance.check_python_fixture(path)
    assert len(problems) == 1
    assert problems[0].startswith(f"stf-corpus-forwarder-forward: request {number}: Python port ")
    assert "; fixture port " in problems[0]


def test_python_check_catches_a_changed_state_cell(tmp_path: Path) -> None:
    path, number = corrupted(tmp_path, "stf-corpus-stateful-persist", change_state_cell)
    problems = conformance.check_python_fixture(path)
    assert len(problems) == 1
    assert problems[0].startswith(f"stf-corpus-stateful-persist: request {number}: ")
    # Packets agree; the state line names the register and both values.
    assert re.search(r"\nstate \w+: Python \{.*\}; fixture \{.*\}$", problems[0])


def test_python_check_names_the_sides_without_rewriting_texts(tmp_path: Path) -> None:
    """The side labels are built into the message, so a recorded text that
    says "Lean" is quoted as it is."""
    path, number = corrupted(tmp_path, "contract-forwarder-install", reword_error)
    problems = conformance.check_python_fixture(path)
    assert problems == [
        f"contract-forwarder-install: request {number}: Python error: InstallError: lpm value "
        "'167772672' has bits outside its prefix; fixture error: Lean rejects this install"
    ]


def test_python_check_rejects_a_hand_formatted_fixture(tmp_path: Path) -> None:
    path = tmp_path / "stf-corpus-forwarder-forward.json"
    source = FIXTURES / "stf-corpus-forwarder-forward.json"
    path.write_text(source.read_text().replace('"ports": 4', '"ports":  4'))
    problems = conformance.check_python_fixture(path)
    assert problems == ["stf-corpus-forwarder-forward: the file is not in canonical form"]


def test_lean_agrees_check_catches_a_changed_answer(tmp_path: Path, lean_binary: Path) -> None:
    path, number = corrupted(tmp_path, "stf-corpus-forwarder-forward", flip_output_byte)
    assert conformance.check_lean_fixture(path, [lean_binary]) == [
        f"stf-corpus-forwarder-forward: request {number}: Lean's reply changed in outputs"
    ]


def test_a_truncated_fixture_fails_the_membership_test(tmp_path: Path) -> None:
    """Both checks answer only the requests that are there; the count
    against the input set is what sees one dropped."""
    name = "stf-corpus-stateful-persist"
    fixture = conformance.load(FIXTURES / f"{name}.json")
    assert len(fixture.steps) > 1
    write(tmp_path / f"{name}.json", replace(fixture, steps=fixture.steps[:-1]))
    chosen = [i for i in inputs.stf_inputs() if i.name == name]
    assert conformance.check_inputs(tmp_path, chosen) == [
        f"{name}: {len(fixture.steps) - 1} steps, but its input has {len(fixture.steps)} requests"
    ]
    assert conformance.check_inputs(tmp_path, []) == [f"{name}: a fixture with no input"]


def test_a_fixture_without_steps_is_rejected(tmp_path: Path) -> None:
    fixture = conformance.load(FIXTURES / "stf-corpus-forwarder-forward.json")
    path = write(tmp_path / "stf-corpus-forwarder-forward.json", replace(fixture, steps=()))
    with pytest.raises(ValueError, match="steps must be a nonempty array"):
        conformance.load(path)
    assert conformance.check_python_fixture(path) == [
        "stf-corpus-forwarder-forward: stf-corpus-forwarder-forward.json: "
        "fixture steps must be a nonempty array"
    ]


def test_a_fixture_named_other_than_its_file_is_rejected(tmp_path: Path) -> None:
    fixture = conformance.load(FIXTURES / "stf-corpus-forwarder-forward.json")
    path = write(tmp_path / "renamed.json", fixture)
    with pytest.raises(ValueError, match="not its file's stem"):
        conformance.load(path)


def test_a_broken_fixture_is_reported_and_the_rest_still_checked(tmp_path: Path) -> None:
    """An invalid program raises the validator's own error class, which is
    no ValueError, and a file may not be JSON at all; each is that
    fixture's problem, and the next fixture is still checked."""
    fixture = conformance.load(FIXTURES / "stf-corpus-forwarder-forward.json")
    invalid = replace(fixture, name="a-invalid", program={**fixture.program, "blocks": []})
    write(tmp_path / "a-invalid.json", invalid)
    (tmp_path / "b-garbage.json").write_text("not json")
    _, number = corrupted(tmp_path, "stf-corpus-forwarder-forward", flip_output_byte)
    problems = conformance.check_python(tmp_path)
    assert len(problems) == 3
    assert problems[0].startswith("a-invalid: the program does not load: ValidationError: ")
    assert problems[1].startswith("b-garbage: b-garbage.json: ")
    assert problems[2].startswith(f"stf-corpus-forwarder-forward: request {number}: ")
    assert conformance.main(["check-python", "--dir", str(tmp_path)]) == 1


def test_a_reply_with_a_stray_field_is_rejected() -> None:
    fixture = conformance.load(FIXTURES / "stf-corpus-forwarder-forward.json")
    first = fixture.steps[0]
    stray = replace(fixture, steps=(Step(first.request, {**first.reply, "extra": 1}),))
    with pytest.raises(ValueError, match="step 0: a reply has the fields"):
        conformance.loads(conformance.dumps(stray))


# ---------------------------------------------------------------------------
# Sparse cells
# ---------------------------------------------------------------------------


def test_sparse_cells_lose_nothing() -> None:
    for path in PATHS:
        for step in conformance.load(path).steps:
            assert conformance.sparse_reply(conformance.dense_reply(step.reply)) == step.reply


@pytest.mark.parametrize(
    ("cells", "reason"),
    [
        ({"size": 2, "nonzero": [[0, "0x0"]]}, "a zero cell is not listed"),
        ({"size": 2, "nonzero": [[1, "0x1"], [0, "0x1"]]}, "must increase within size"),
        ({"size": 2, "nonzero": [[2, "0x1"]]}, "must increase within size"),
        ({"values": ["0x0"]}, "size and nonzero"),
    ],
)
def test_malformed_sparse_cells_are_rejected(cells: dict[str, object], reason: str) -> None:
    reply = {"outputs": [], "state": {"c": {"kind": "counter", **cells}}, "coverage": []}
    with pytest.raises(ValueError, match=reason):
        conformance.dense_reply(reply)


# ---------------------------------------------------------------------------
# Writing fixtures
# ---------------------------------------------------------------------------


def test_export_replaces_the_fixtures_and_nothing_else(tmp_path: Path) -> None:
    """A stale fixture goes; any other file stays, JSON or not. Python
    stands in for Lean through the DRT's fake endpoint."""
    shutil.copy(PATHS[0], tmp_path / "gone.json")
    foreign = tmp_path / "spectec-rules.json"
    foreign.write_text('{"rules": []}\n')
    chosen = [i for i in inputs.stf_inputs() if i.name == "stf-corpus-stateful-persist"]
    written = conformance.export(chosen, FAKE_LEAN, tmp_path)
    assert written == [tmp_path / "stf-corpus-stateful-persist.json"]
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "spectec-rules.json",
        "stf-corpus-stateful-persist.json",
    ]
    assert foreign.read_text() == '{"rules": []}\n'
    assert conformance.check_python_fixture(written[0]) == []


def test_refresh_rewrites_answers_and_never_inputs(tmp_path: Path) -> None:
    """A changed answer is restored, the other fixture is left byte for
    byte, and no program or request is touched."""
    chosen = [
        i
        for i in inputs.stf_inputs()
        if i.name in ("stf-corpus-forwarder-forward", "stf-corpus-stateful-persist")
    ]
    written = conformance.export(chosen, FAKE_LEAN, tmp_path)
    original = {p: p.read_bytes() for p in written}
    forward = tmp_path / "stf-corpus-forwarder-forward.json"
    fixture = conformance.load(forward)
    first = fixture.steps[0]
    wrong = Step(first.request, flip_output_byte(dict(first.reply)))
    write(forward, replace(fixture, steps=(wrong, *fixture.steps[1:])))
    assert conformance.refresh(FAKE_LEAN, tmp_path) == [forward]
    assert {p: p.read_bytes() for p in written} == original
    assert conformance.refresh(FAKE_LEAN, tmp_path) == []


def test_lean_agrees_refresh_restores_a_changed_answer(tmp_path: Path, lean_binary: Path) -> None:
    path, _ = corrupted(tmp_path, "stf-corpus-forwarder-forward", flip_output_byte)
    assert conformance.refresh([lean_binary], tmp_path) == [path]
    tracked = conformance.load(FIXTURES / path.name)
    refreshed = conformance.load(path)
    assert refreshed.steps == tracked.steps
    assert refreshed.program == tracked.program
    assert refreshed.lean == conformance.lean_provenance(lean=[lean_binary])


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_one_committed_lean_source_answered_every_fixture() -> None:
    """An export from uncommitted Lean sources would name no commit anyone
    can check out; the header records the digests and the commit."""
    recorded = {(f.lean["commit"], f.lean["sources"]) for f in map(conformance.load, PATHS)}
    assert len(recorded) == 1
    lean = conformance.load(PATHS[0]).lean
    assert set(lean) == {"binary", "commit", "sources"}
    assert re.fullmatch(r"[0-9a-f]{40}", str(lean["commit"]))
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", str(lean["sources"]))
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", str(lean["binary"]))


def test_changed_lean_sources_are_reported_not_failed() -> None:
    """The header is informative and the byte comparison is the check:
    other recorded sources give a note naming both digests."""
    fixture = conformance.load(PATHS[0])
    current = conformance.lean_provenance()
    old = replace(fixture, lean={**fixture.lean, "sources": "sha256:" + "1" * 64})
    note = conformance.lean_drift([old])
    assert note is not None
    assert "sha256:" + "1" * 64 in note and str(current["sources"]) in note
    assert "check-lean decides" in note
    assert conformance.lean_drift([replace(fixture, lean=current)]) is None


def test_another_binary_is_reported_not_failed(tmp_path: Path) -> None:
    fixture = conformance.load(PATHS[0])
    binary = tmp_path / "p4blo-lean"
    binary.write_bytes(b"another build")
    note = conformance.binary_drift([fixture], [binary])
    assert note is not None
    current = conformance.lean_provenance(lean=[binary])["binary"]
    assert str(fixture.lean["binary"]) in note and str(current) in note
    assert conformance.binary_drift([replace(fixture, lean={"binary": current})], [binary]) is None
    assert conformance.binary_drift([fixture], FAKE_LEAN) is None


def spec_copy(tmp_path: Path) -> Path:
    """The two specification packages without their build trees."""
    root = tmp_path / "root"
    for package in conformance.LEAN_PACKAGES:
        shutil.copytree(
            conformance.ROOT / package, root / package, ignore=shutil.ignore_patterns(".lake")
        )
    return root


def test_only_semantics_sources_are_digested(tmp_path: Path) -> None:
    """A proof or a test changes no answer, and neither does adding a
    proof module to an umbrella; a definition the endpoint runs does."""
    root = spec_copy(tmp_path)
    before = conformance.lean_provenance(root)["sources"]
    assert before == conformance.lean_provenance()["sources"]
    files = {p.relative_to(root).as_posix() for p in conformance.semantics_files(root)}
    assert "spec/arch/Main.lean" in files and "spec/ir/P4bloIR/Exec.lean" in files
    assert not [f for f in files if re.search(r"(Laws|Audit|Probe|Theorems)\.lean$", f)]
    assert not [f for f in files if "/P4bloIRTest/" in f or "/ArchTests/" in f]
    for proof in (
        "spec/ir/P4bloIR/DeviationLaws.lean",
        "spec/ir/P4bloIRTest/ProofAudit.lean",
        "spec/ir/P4bloIR/Theorems.lean",
        "spec/ir/P4bloIRTest/Main.lean",
        "spec/arch/ArchTests/Main.lean",
    ):
        with (root / proof).open("a") as f:
            f.write("\n-- a proof-only edit\n")
    with (root / "spec/ir/P4bloIR.lean").open("a") as f:
        f.write("import P4bloIR.NewLaws\n")
    assert conformance.lean_provenance(root)["sources"] == before
    with (root / "spec/ir/P4bloIR/Exec.lean").open("a") as f:
        f.write("\n-- a semantics edit\n")
    assert conformance.lean_provenance(root)["sources"] != before


def test_a_binary_older_than_its_sources_answers_nothing(tmp_path: Path) -> None:
    root = spec_copy(tmp_path)
    binary = tmp_path / "p4blo-lean"
    binary.write_bytes(b"")
    newest = max(p.stat().st_mtime for p in conformance.semantics_files(root))
    os.utime(binary, (newest + 10, newest + 10))
    assert conformance.stale_lean([binary], root) is None
    exec_lean = root / "spec/ir/P4bloIR/Exec.lean"
    os.utime(exec_lean, (newest + 20, newest + 20))
    reason = conformance.stale_lean([binary], root)
    assert reason is not None
    assert "is older than spec/ir/P4bloIR/Exec.lean" in reason and "rebuild" in reason
    with pytest.raises(conformance.StaleLean):
        conformance.check_lean(FIXTURES, [binary], root)
    with pytest.raises(conformance.StaleLean):
        conformance.refresh([binary], tmp_path, root)
    # A proof edit after the build does not make the binary stale.
    os.utime(exec_lean, (newest, newest))
    os.utime(root / "spec/ir/P4bloIR/DeviationLaws.lean", (newest + 20, newest + 20))
    assert conformance.stale_lean([binary], root) is None
