"""Fail-closed orchestration checks; the expensive catalogue is explicitly opt-in."""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

from p4blo.drt.case import Case
from p4blo.drt.run import Divergence, Outcome, Report
from p4blo.drt.state import Observation
from p4blo.v0 import p4blo_pb2 as pb
from tests.assurance import runner


def test_tracked_inventory() -> None:
    selected = runner.inputs()
    runner.check_inputs(selected)
    runner.baseline_known_answers(selected)
    with pytest.raises(RuntimeError, match="three nonempty"):
        runner.check_inputs(selected[:2])
    changed = runner.Input(selected[0].name, selected[0].program, (Case(pb.Entries(), 1, b""),))
    with pytest.raises(RuntimeError, match="pinned hashes"):
        runner.check_inputs((changed, *selected[1:]))


def junit(path: Path) -> ET.Element:
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for node in runner.NODES:
        file, name = node.split("::")
        suffixes = (
            ("[header]", "[struct]")
            if name.endswith("kills_aliasing")
            else (
                ("[outputs]", "[state]", "[diagnostic]")
                if name.endswith("false_agreement")
                else ("",)
            )
        )
        for suffix in suffixes:
            ET.SubElement(
                suite, "testcase", classname=file[:-3].replace("/", "."), name=name + suffix
            )
    ET.ElementTree(root).write(path)
    return root


@pytest.mark.parametrize("problem", ["skipped", "error", "failure", "empty", "renamed"])
def test_junit_rejects_false_success(tmp_path: Path, problem: str) -> None:
    path = tmp_path / "report.xml"
    tree = junit(path)
    runner.check_junit(path)
    case = tree.findall(".//testcase")[0]
    if problem == "empty":
        tree.clear()
    elif problem == "renamed":
        case.set("name", "unrelated_pass")
    else:
        ET.SubElement(case, problem)
    ET.ElementTree(tree).write(path)
    with pytest.raises(RuntimeError):
        runner.check_junit(path)


def test_mutation_restores_after_failure(tmp_path: Path) -> None:
    source = tmp_path / "source.lean"
    source.write_text("original\n")
    with pytest.raises(ValueError):
        with runner.mutate(source, "original", "wrong"):
            assert source.read_text() == "wrong\n"
            raise ValueError("build failed, not a kill")
    assert source.read_bytes() == b"original\n"
    for anchor in ("missing", "i"):
        with pytest.raises(RuntimeError, match="not unique"):
            with runner.mutate(source, anchor, "wrong"):
                pytest.fail("bad anchor entered mutation")
    assert source.read_bytes() == b"original\n"


def crc_report() -> Report:
    report = Report("tutorial_firewall", 0, 4, cases=4)
    case = Case(pb.Entries(), 0, b"")
    for number in [1, 2, 3]:
        report.divergences.append(
            Divergence(
                number,
                case,
                Outcome(outputs=(), state=(Observation("r", "register", values=(0,)),)),
                Outcome(outputs=(), state=(Observation("r", "register", values=(1,)),)),
            )
        )
    return report


@pytest.mark.parametrize("fault", ["error", "diagnostic", "packet", "state", "protocol", "count"])
def test_crc_detector_only_counts_semantic_state_faults(fault: str) -> None:
    report = crc_report()
    runner.checked_crc(report)
    if fault == "protocol":
        report.protocol_error = "truncated"
    elif fault == "count":
        report.cases = 3
    else:
        d = report.divergences[0]
        wrong = {
            "error": Outcome(error="bad build"),
            "diagnostic": Outcome(outputs=(), diagnostic="parser failed"),
            "packet": Outcome(outputs=((0, b"wrong"),)),
            "state": d.python,
        }[fault]
        report.divergences[0] = Divergence(d.number, d.case, d.python, wrong)
    with pytest.raises(RuntimeError):
        runner.checked_crc(report)


def test_native_detector_requires_exact_independent_failures() -> None:
    names = [
        "block codec literal kind constructor",
        "block codec direct kind observer",
        "block codec all fields regardless of kind",
    ] * 2
    output = "ok   control\n" * 100 + "\n".join("FAIL " + n for n in names) + "\n"
    diagnostic = "uncaught exception: block codec tests failed: [" + ", ".join(names) + "]\n"
    runner.checked_native_failure(1, output, diagnostic)
    for code, stdout, stderr in [
        (-9, output, diagnostic),
        (1, output, "segfault"),
        (1, output + "FAIL unrelated\n", diagnostic),
        (1, "", diagnostic),
        (0, output, diagnostic),
    ]:
        with pytest.raises(RuntimeError):
            runner.checked_native_failure(code, stdout, stderr)


def test_command_failure_is_not_a_kill_and_logs_do_not_overwrite(tmp_path: Path) -> None:
    run = runner.Run(tmp_path)
    with pytest.raises(RuntimeError, match="expected 0"):
        run.command("compile", [sys.executable, "-c", "raise SystemExit(1)"], cwd=tmp_path)
    with pytest.raises(FileExistsError):
        run.command("compile", [sys.executable, "-c", "pass"], cwd=tmp_path)
    assert run.phases[0]["exit"] == 1


def test_timeout_stops_owned_process_group(tmp_path: Path) -> None:
    run = runner.Run(tmp_path)
    with pytest.raises(RuntimeError, match="process group stopped"):
        run.command(
            "timeout", [sys.executable, "-c", "import time; time.sleep(5)"], cwd=tmp_path, timeout=1
        )


@pytest.mark.parametrize("error", [ProcessLookupError(), PermissionError("denied")])
def test_timeout_signal_race_still_reaps(monkeypatch: pytest.MonkeyPatch, error: OSError) -> None:
    process = Mock(spec=subprocess.Popen)
    process.pid = 123
    kill = Mock(side_effect=error)
    monkeypatch.setattr(runner.os, "killpg", kill)
    if isinstance(error, PermissionError):
        with pytest.raises(RuntimeError, match="signal denied"):
            runner.stop_owned(process)
    else:
        runner.stop_owned(process)
    process.wait.assert_called_once_with(timeout=10)
    kill.assert_called_once_with(123, runner.signal.SIGKILL)


def test_cleanup_uncertainty_never_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    process = Mock(spec=subprocess.Popen)
    process.pid = 123
    process.wait.side_effect = subprocess.TimeoutExpired("child", 10)
    monkeypatch.setattr(runner.os, "killpg", Mock(side_effect=PermissionError("denied")))
    with pytest.raises(RuntimeError, match="leader did not exit"):
        runner.stop_owned(process)
    process.wait.assert_called_once_with(timeout=10)


def test_provenance_covers_both_engines_fixtures_and_tools() -> None:
    source = runner.provenance(runner.ROOT)
    hashes = source["sha256"]
    assert isinstance(hashes, dict)
    for file in [
        "impl/python/p4blo/interp/stmt.py",
        "spec/ir/P4bloIR/Json.lean",
        "uv.lock",
        "flake.lock",
        "spec/ir/lean-toolchain",
        "tests/lean/test_lean_firewall_bloom.py",
        "tests/assurance/runner.py",
        "scripts/check-assurance.py",
    ]:
        assert hashes[file] == runner.digest((runner.ROOT / file).read_bytes())
    assert isinstance(source["head"], str) and len(source["head"]) == 40


def test_explicit_output_directory_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["assurance", "--output", str(tmp_path)])
    with pytest.raises(FileExistsError):
        runner.main()
