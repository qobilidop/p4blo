"""The test infrastructure must detect faults and preserve stateful reproducers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from p4blo import arch, ir
from p4blo.drt import __main__ as cli
from p4blo.drt.case import Case
from p4blo.drt.replay import load, replay, save
from p4blo.drt.replay import main as replay_main
from p4blo.drt.run import (
    Divergence,
    Outcome,
    ProtocolError,
    Report,
    compare,
    compare_cases,
    compare_program,
    python_outcome,
)
from p4blo.drt.state import Observation, snapshot
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[1]
FAKE = [sys.executable, "-m", "p4blo.drt.fake_lean"]


def test_both_clis_describe_state_only_divergences(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    case = Case(pb.Entries(), 0, b"\x00\x01\x00")
    left = Outcome(outputs=(), state=(Observation("counter", "counter", values=(3,)),))
    right = Outcome(outputs=(), state=(Observation("counter", "counter", values=(2,)),))
    report = Report("register_bounds", 0, 4, cases=1)
    report.divergences.append(Divergence(0, case, left, right))
    monkeypatch.setitem(replay_main.__globals__, "replay", lambda *_: report)
    assert replay_main(["unused.json", "--fake"]) == 1
    replay_output = capsys.readouterr().out
    cli.show(report, ROOT / "corpus/register_bounds", 1, None)
    excerpt_output = capsys.readouterr().out
    for output in (replay_output, excerpt_output):
        assert "state counter: Python" in output
        assert '"0x3"' in output and '"0x2"' in output


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


def test_protocol_failure_preserves_the_experiment_and_prior_divergences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    peer = (
        "import sys; "
        "[(print('{\"outputs\":[],\"state\":{}}' if i == 0 else 'not json', flush=True)) "
        "for i, _ in enumerate(sys.stdin)]"
    )

    def faulty_compare(program_dir, seed, count, ports, lean):
        return compare(program_dir, seed, count, ports, [sys.executable, "-c", peer])

    monkeypatch.setattr(cli, "compare", faulty_compare)
    assert cli.main([str(ROOT / "corpus/register_bounds"), "2", "--save", str(tmp_path)]) == 2
    [bundle] = list(tmp_path.glob("*.json"))
    data = json.loads(bundle.read_text())
    assert data["completed_requests"] == 1
    assert data["divergences"] == [0]
    assert "not JSON" in data["protocol_error"]
    assert len(load(bundle)[1]) == 2
    assert replay(bundle, FAKE).passed


def test_report_inputs_do_not_alias_mutable_protobuf_entries() -> None:
    program = register_program()
    entries = pb.Entries()
    case = Case(entries, 0, b"\x00")

    def fail(_: Case) -> Outcome:
        raise ProtocolError("injected fault")

    with pytest.raises(ProtocolError) as error:
        compare_cases("register_bounds", arch.load(program), [case], 4, fail)
    report = error.value.report
    assert report is not None and not report.passed
    entries.tables.add(block="changed")
    assert report.inputs[0].entries == pb.Entries()


def test_startup_failure_still_saves_concrete_inputs(tmp_path: Path) -> None:
    missing = tmp_path / "missing-lean"
    assert (
        cli.main(
            [
                str(ROOT / "corpus/register_bounds"),
                "2",
                "--lean",
                str(missing),
                "--save",
                str(tmp_path),
            ]
        )
        == 2
    )
    [bundle] = list(tmp_path.glob("*.json"))
    assert len(load(bundle)[1]) == 2
    assert replay(bundle, FAKE).passed


def test_shutdown_failure_retains_completed_report(tmp_path: Path) -> None:
    peer = (
        "import sys; sys.stdin.readline(); "
        'print(\'{"outputs":[],"state":{}}\', flush=True); '
        "sys.stdin.read(); sys.exit(3)"
    )
    with pytest.raises(ProtocolError, match="exit 3") as error:
        compare_program(
            register_program(), [Case(pb.Entries(), 0, b"x")], 4, [sys.executable, "-c", peer]
        )
    report = error.value.report
    assert report is not None and report.cases == 1 and not report.passed
    assert len(report.divergences) == 1
    save(report, tmp_path / "shutdown.json")
    assert replay(tmp_path / "shutdown.json", FAKE).passed
