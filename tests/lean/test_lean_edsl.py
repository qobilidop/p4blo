"""Lean-authored scalar IR against independent answers and both interpreters.

The exporter emits syntax only. Expected bytes below do not call the Lean
source denotation or mirror its lowering. Thus a bad notation expansion can
fail even when the core lowering theorem remains true.
"""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest
from google.protobuf import json_format

from p4blo import arch
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import replay
from p4blo.drt.case import Case
from p4blo.drt.programs import bits, boolean, scalar_program
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program, run_python
from p4blo.interp.env import Env
from p4blo.interp.values import Value
from p4blo.v0 import p4blo_pb2 as pb

# Width is independently specified, including bool (None) and non-byte bits.
EXPECTED: dict[str, tuple[int | None, bytes]] = {
    "zero": (8, b"\x00"),
    "maximum": (8, b"\xff"),
    "add": (8, b"\x1a"),
    "wrap": (8, b"\x00"),
    "one-bit-wrap": (1, b"\x00"),
    "wide": (65, b"\x00\x00\x00\x00\x00\x00\x00\x00\x80"),
    "equal": (None, b"\x80"),
    "unequal": (None, b"\x00"),
    "yes": (8, b"\x13"),
    "no": (8, b"\x07"),
    "bool-yes": (None, b"\x00"),
    "bool-no": (None, b"\x80"),
    "nested": (8, b"\x2e"),
    "read-x": (8, b"\x13"),
    "read-y": (8, b"\x07"),
    "read-add": (8, b"\x1a"),
    "read-wrap": (8, b"\x01"),
    "read-yes": (8, b"\x13"),
    "read-no": (8, b"\x07"),
    "read-equal": (None, b"\x80"),
    "read-unequal": (None, b"\x00"),
}

# Inputs are independently checked too: a corrupted exporter must not silently
# change the case being tested while retaining its ID and expected answer.
INPUTS = {
    "read-x": (19, 7, True),
    "read-y": (19, 7, True),
    "read-add": (19, 7, True),
    "read-wrap": (255, 2, False),
    "read-yes": (19, 7, True),
    "read-no": (19, 7, False),
    "read-equal": (7, 7, False),
    "read-unequal": (19, 7, True),
}


def test_user_proof_audit_and_exporter_are_default_targets() -> None:
    root = Path(__file__).resolve().parents[2]
    package = tomllib.loads((root / "impl/lean/lakefile.toml").read_text())
    assert {"P4bloTest", "p4blo"} <= set(package["defaultTargets"])


@pytest.fixture(scope="module")
def authored_expressions(lean_binary: Path) -> dict[str, apb.BlockAssembly]:
    # lean_binary enforces the shared absent-vs-broken/required gate policy.
    assert lean_binary.is_file()
    root = Path(__file__).resolve().parents[2]
    exporter = root / "impl/lean/.lake/build/bin/p4blo"
    assert exporter.is_file(), f"missing Lean eDSL exporter: run {root}/scripts/check-lean.sh"
    completed = subprocess.run(
        [str(exporter), "scalarExamples"], capture_output=True, text=True, check=True, timeout=30
    )
    result: dict[str, apb.BlockAssembly] = {}
    for line in completed.stdout.splitlines():
        record = json.loads(line)
        name = record["name"]
        assert name not in result, f"duplicate exported example: {name}"
        assert name in EXPECTED, f"unexpected exported example: {name}"
        assert record["width"] == EXPECTED[name][0]
        expression = json_format.ParseDict(record["expression"], pb.Expr())
        program = scalar_program(expression, EXPECTED[name][0])
        expected_inputs = (
            {
                "x": bits(8, INPUTS[name][0]),
                "y": bits(8, INPUTS[name][1]),
                "choose": boolean(INPUTS[name][2]),
            }
            if name in INPUTS
            else {}
        )
        bindings = record["bindings"]
        assert len(bindings) == len(expected_inputs), name
        actual_inputs = {
            item["name"]: json_format.ParseDict(item["value"], pb.Expr()) for item in bindings
        }
        assert actual_inputs == expected_inputs, f"unexpected initial bindings: {name}"
        control = program.blocks[1]
        initializers: list[pb.Stmt] = []
        for key, value in actual_inputs.items():
            ty = pb.Type(boolean=pb.BoolType()) if key == "choose" else pb.Type(bits=8)
            control.locals.add(name=key, type=ty)
            initializers.append(pb.Stmt(assign=pb.Assign(target=pb.LValue(var=key), value=value)))
        body = [*initializers, *control.body]
        del control.body[:]
        control.body.extend(body)
        result[name] = program
    assert result.keys() == EXPECTED.keys(), "export must include every authored example"
    return result


@pytest.mark.parametrize("name", EXPECTED)
def test_lean_agrees_on_authored_scalar_known_answers(
    name: str, authored_expressions: dict[str, apb.BlockAssembly], lean_binary: Path
) -> None:
    _, expected = EXPECTED[name]
    program = authored_expressions[name]
    case = Case(pb.Entries(), 0, b"")
    # Retain concrete differential failures before a Python-only assertion can
    # exit early. Independent known answers still judge agreement below.
    try:
        report = compare_program(program, [case], 4, [lean_binary])
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        target = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        target.mkdir(parents=True, exist_ok=True)
        bundle = target / f"lean-edsl-{name}.json"
        save(report, bundle)
        pytest.fail(
            f"{report.summary()}; replay {bundle}\n{report.divergences}\n{report.protocol_error}"
        )
    # Catch shared mistakes, including valid but unintended source expressions.
    assert run_python(arch.reference.load(program), case, 4) == [(0, expected)]


def test_lean_agrees_after_retained_authoring_mutant(
    authored_expressions: dict[str, apb.BlockAssembly],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A real Python read fault must save its inputs before any assertion exits."""
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    original_read = Env.read

    def wrong_read(self: Env, name: str) -> Value:
        return original_read(self, "y" if name == "x" else name)

    bundle = tmp_path / "lean-edsl-read-x.json"
    with monkeypatch.context() as fault:
        fault.setattr(Env, "read", wrong_read)
        with pytest.raises(pytest.fail.Exception, match="replay"):
            test_lean_agrees_on_authored_scalar_known_answers(
                "read-x", authored_expressions, lean_binary
            )
        program, cases, ports, seed = replay.load(bundle)
        assert program == authored_expressions["read-x"]
        assert cases == [Case(pb.Entries(), 0, b"")]
        assert (ports, seed) == (4, 0)
        report = replay.replay(bundle, [lean_binary])
        assert report.protocol_error is None and report.both_errored == 0
        assert report.agreed == 0 and len(report.divergences) == 1
        mismatch = report.divergences[0]
        assert mismatch.python.outputs == ((0, b"\x07"),)
        assert mismatch.lean.outputs == ((0, b"\x13"),)
    restored = replay.replay(bundle, [lean_binary])
    assert restored.passed and restored.agreed == 1


def test_lean_agrees_but_wrong_authored_answer_fails(
    authored_expressions: dict[str, apb.BlockAssembly],
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Interpreter agreement must not excuse a valid but unintended source term."""
    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    wrong_source = {**authored_expressions, "read-x": authored_expressions["read-y"]}
    agreement = compare_program(
        wrong_source["read-x"], [Case(pb.Entries(), 0, b"")], 4, [lean_binary]
    )
    assert agreement.passed and agreement.agreed == 1
    with pytest.raises(AssertionError):
        test_lean_agrees_on_authored_scalar_known_answers("read-x", wrong_source, lean_binary)
    assert list(tmp_path.iterdir()) == []  # This fault is not a differential mismatch.
