"""Package checks without native oracle dependencies."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.replay import load, save
from p4blo.drt.run import (
    Divergence,
    Outcome,
    ProtocolError,
    Report,
)
from p4blo.drt.stateful_programs import (
    StatefulSpec,
    stateful_program,
)
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.drt_stateful_programs import (
    boundary_fields,
    cases_for,
    check_sequence,
    failure_path,
)


def test_stateful_replay_retains_program_and_every_request(tmp_path: Path) -> None:
    spec = StatefulSpec(16, 2, 3, pb.BINARY_OP_SUB_SAT, count_updates=True)
    cases = cases_for(spec, boundary_fields(spec))
    program = stateful_program(spec)
    report = Report(
        program.name, 0, 4, inputs=tuple(cases), program_ir=program, protocol_error="peer lost"
    )
    bundle = failure_path(report, tmp_path)
    save(report, bundle)
    restored_program, restored_cases, ports, seed = load(bundle)
    assert restored_program == program
    assert restored_cases == cases
    assert (ports, seed) == (4, 0)
    shorter = Report(program.name, 0, 4, inputs=tuple(cases[:-1]), program_ir=program)
    assert failure_path(shorter, tmp_path) != bundle


@pytest.mark.parametrize("protocol_failure", [False, True])
def test_stateful_failure_path_saves_the_complete_experiment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, protocol_failure: bool
) -> None:
    spec = StatefulSpec(8, 2, 3, pb.BINARY_OP_ADD)
    fields = [(0, 4), (0, 7), (2, 9)]

    def fail_comparison(
        program: apb.BlockAssembly,
        cases: Sequence[Case],
        ports: int,
        _command: Sequence[str | Path],
    ) -> Report:
        report = Report(program.name, 0, ports, inputs=tuple(cases), program_ir=program, cases=2)
        if protocol_failure:
            report.protocol_error = "injected lost peer"
            raise ProtocolError(report.protocol_error, report)
        report.divergences.append(
            Divergence(1, cases[1], Outcome(outputs=((0, b"original"),)), Outcome(outputs=()))
        )
        return report

    monkeypatch.setenv("P4BLO_DRT_FAILURE_DIR", str(tmp_path))
    monkeypatch.setitem(check_sequence.__globals__, "compare_program", fail_comparison)
    with pytest.raises(pytest.fail.Exception, match="replay"):
        check_sequence(spec, fields, tmp_path / "unused-comparator")
    bundles = list(tmp_path.glob("stateful-*.json"))
    assert len(bundles) == 1
    program, cases, ports, seed = load(bundles[0])
    assert program == stateful_program(spec)
    assert cases == cases_for(spec, fields)
    assert (ports, seed) == (4, 0)
