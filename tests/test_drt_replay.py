"""The test infrastructure must detect faults and preserve stateful reproducers."""

from __future__ import annotations

import sys
from pathlib import Path

from p4blo import arch, ir
from p4blo.drt.case import Case
from p4blo.drt.replay import load, replay, save
from p4blo.drt.run import Outcome, compare_cases, python_outcome
from p4blo.drt.state import snapshot
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[1]
FAKE = [sys.executable, "-m", "p4blo.drt.fake_lean"]


def register_program() -> pb.Program:
    return ir.load_text(ROOT / "corpus/register_bounds/register_bounds.txtpb")


def test_replay_keeps_the_prefix_that_establishes_register_state(tmp_path: Path) -> None:
    program = register_program()
    cases = [Case(pb.Entries(), 0, bytes.fromhex(p)) for p in ("0005ff", "000300")]

    # A broken implementation resets state before each packet. The second
    # request alone cannot expose the fault; replaying the prefix must.
    def reset_each_packet(case: Case) -> Outcome:
        return python_outcome(arch.load(program), case, 4)

    report = compare_cases("register_bounds", arch.load(program), cases, 4, reset_each_packet)
    assert [d.number for d in report.divergences] == [1]
    assert report.divergences[0].python.outputs == ((0, bytes.fromhex("000308")),)
    bundle = tmp_path / "failure.json"
    save(report, bundle)
    recovered_program, recovered_cases, ports, seed = load(bundle)
    assert recovered_program == program
    assert recovered_cases == cases
    recovered = compare_cases(
        "register_bounds",
        arch.load(recovered_program),
        recovered_cases,
        ports,
        reset_each_packet,
        seed,
    )
    assert recovered.divergences == report.divergences
    assert replay(bundle, FAKE).passed


def test_replay_preserves_values_stf_cannot_express(tmp_path: Path) -> None:
    program = register_program()
    # This is deliberately an invalid installation. The replay format must
    # preserve it too, including boolean action data and an empty packet.
    entries = pb.Entries(tables=[pb.TableEntries(block="C", table="unknown")])
    entries.tables[0].default_action.args.add(boolean=True)
    cases = [Case(entries, -1, b"")]
    report = compare_cases("register_bounds", arch.load(program), cases, 4, lambda _: Outcome())
    bundle = tmp_path / "invalid.json"
    save(report, bundle)
    assert load(bundle)[1] == cases


def test_matching_errors_are_not_a_successful_valid_input_campaign() -> None:
    program = register_program()
    case = Case(pb.Entries(), 99, b"\x00")
    report = compare_cases(
        "register_bounds",
        arch.load(program),
        [case],
        4,
        lambda _: Outcome(
            error="ingress_port 99 is not a port of this switch", state=snapshot(arch.load(program))
        ),
    )
    assert not report.divergences
    assert not report.passed
