"""Check independent expected outcomes in both implementations and retain failures."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from p4blo import arch, ir
from p4blo.drt.case import Case
from p4blo.drt.replay import save
from p4blo.drt.run import LeanRunner, Outcome, ProtocolError, compare_cases, python_outcome
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]


def check_python(program: pb.Program, cases: Sequence[Case], expected: Sequence[Outcome]) -> None:
    loaded = arch.reference.load(program)
    assert len(cases) == len(expected)
    for number, (case, answer) in enumerate(zip(cases, expected, strict=True)):
        actual = python_outcome(loaded, case, 4)
        assert actual == answer, (number, actual, answer)


def check_lean(
    program: pb.Program,
    cases: Sequence[Case],
    expected: Sequence[Outcome],
    lean_binary: Path,
    tmp_path: Path,
) -> None:
    source = tmp_path / "program.json"
    source.write_text(ir.dump_json(program))
    artifacts = ROOT / ".artifacts/drt/examples"
    artifacts.mkdir(parents=True, exist_ok=True)
    observed: list[Outcome] = []
    with LeanRunner([lean_binary], source, 4) as runner:

        def observe(case: Case) -> Outcome:
            answer = runner.run(case)
            observed.append(answer)
            return answer

        try:
            report = compare_cases(program.name, arch.reference.load(program), cases, 4, observe)
        except ProtocolError as error:
            if error.report is not None:
                save(error.report, artifacts / f"{program.name}-protocol.json")
            raise
    if not report.passed or observed != list(expected):
        save(report, artifacts / f"{program.name}.json")
    assert report.passed, report.divergences
    assert observed == list(expected)
