"""Reconstruct and challenge a fixed assurance inventory in isolated source copies."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from google.protobuf.json_format import MessageToDict

from p4blo import arch, ir
from p4blo.drt import replay
from p4blo.drt._json import loads
from p4blo.drt.case import Case
from p4blo.drt.run import ProtocolError, Report, compare_program, python_outcome, request_json
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]
NODES = (
    "tests/test_lean_forwarder_apply.py::test_lean_agrees_skip_default_packet_replay",
    "tests/test_lean_forwarder_tables.py::test_lean_agrees_shortest_prefix_fault_replay",
    "tests/test_lean_firewall_bloom.py::test_lean_agrees_bloom_read_alias_is_not_expected",
    "tests/test_lean_firewall_bloom.py::test_lean_agrees_bloom_order_survives_final_cells",
    "tests/test_lean_firewall_bloom.py::test_lean_agrees_bloom_observer_rejects_effects[repair]",
    "tests/test_drt_aggregate_copy.py::test_lean_agrees_copy_observer_kills_aliasing",
    "tests/test_drt_replay.py::test_ambiguous_peer_cannot_produce_false_agreement",
)
EXPECTED_TESTS = 10
# Canonical complete inputs, not report metadata or interpreter-generated answers.
INPUT_HASHES = {
    "empty-default": "f3c078924462e5a2f0772f765e043a05acf2c4525a7f4714590121f0cfe7ffe2",
    "overlapping-lpm": "5bba09916c247a4498f17717f1190e306f8c2a36d7f13737738915870ecb1c39",
    "firewall-connection": "0978d83374dfda732b9fc57718d19e4c47e294b9ebcb95a953cf081f01ddfaf7",
}
CRC_OLD = "  fullCRC 32 0x04c11db7 0xffffffff 0xffffffff dataWidth value"
CRC_NEW = "  (fullCRC 32 0x04c11db7 0xffffffff 0xffffffff dataWidth value) ^^^ 1"
KIND_OLD = '[("BLOCK_KIND_PARSER", .parser), ("BLOCK_KIND_CONTROL", .control),'
KIND_NEW = '[("BLOCK_KIND_PARSER", .control), ("BLOCK_KIND_CONTROL", .parser),'
OBSERVER_OLD = '  | .parser => "BLOCK_KIND_PARSER"\n  | .control => "BLOCK_KIND_CONTROL"'
OBSERVER_NEW = '  | .parser => "BLOCK_KIND_CONTROL"\n  | .control => "BLOCK_KIND_PARSER"'
CODEC_REQUEST = {"kind": "block", "wire": {"kind": "BLOCK_KIND_PARSER"}}
CODEC_EXPECTED = {
    "value": {
        "name": "",
        "kind": "BLOCK_KIND_PARSER",
        "params": [],
        "locals": [],
        "actions": [],
        "tables": [],
        "states": [],
        "start_state": "",
        "body": [],
    },
    "encoded": {"kind": "BLOCK_KIND_PARSER"},
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def provenance(root: Path) -> dict[str, object]:
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
    paths = {Path(p.decode()) for p in tracked.split(b"\0") if p}
    # Include this runner even before its first commit during implementation/review.
    paths.update({Path("scripts/check-assurance.py"), Path("tests/test_assurance.py")})
    paths.update(p.relative_to(root) for p in (root / "tests/assurance").glob("*.py"))
    return {
        "head": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"])
        .decode()
        .strip(),
        "status": subprocess.check_output(["git", "-C", str(root), "status", "--short"]).decode(),
        "sha256": {
            str(p): digest((root / p).read_bytes()) for p in sorted(paths) if (root / p).is_file()
        },
        "python": sys.version,
    }


def stop_owned(process: subprocess.Popen[bytes]) -> None:
    """One kill of our own session only, followed by bounded reap even on denial."""
    failure: OSError | None = None
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # The child may exit between the timeout and signal.
    except OSError as error:
        failure = error
    finally:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("cleanup uncertain: task-owned leader did not exit") from error
    if failure is not None:
        raise RuntimeError("cleanup uncertain: task-owned process group signal denied") from failure


@dataclass(frozen=True)
class Input:
    name: str
    program: pb.Program
    cases: tuple[Case, ...]

    def fingerprint(self) -> str:
        return digest(
            canonical(
                {
                    "program": MessageToDict(self.program, preserving_proto_field_name=True),
                    "requests": [loads(request_json(case)) for case in self.cases],
                    "ports": 4,
                    "seed": 0,
                }
            ).encode()
        )


def inputs() -> tuple[Input, ...]:
    from tests.corpus.tutorial_firewall.tutorial_firewall import build
    from tests.test_firewall import connection
    from tests.test_lean_forwarder_apply import application_packet
    from tests.test_lean_forwarder_tables import packet_case

    forwarder = ir.load_text(ROOT / "tests/corpus/forwarder/forwarder.txtpb")
    firewall = build()
    require(
        firewall == ir.load_text(ROOT / "tests/corpus/tutorial_firewall/tutorial_firewall.txtpb"),
        "firewall authoring no longer matches the golden",
    )
    return (
        Input("empty-default", forwarder, (application_packet("empty/drop/false"),)),
        Input("overlapping-lpm", forwarder, (packet_case(),)),
        Input("firewall-connection", firewall, tuple(step.case for step in connection())),
    )


def check_inputs(selected: tuple[Input, ...]) -> None:
    require(
        len(selected) == 3 and sum(len(i.cases) for i in selected) == 6,
        "expected exactly three nonempty inputs and six requests",
    )
    require(
        {i.name: i.fingerprint() for i in selected} == INPUT_HASHES,
        "tracked input inventory changed: review and explicitly update its pinned hashes",
    )


def check_junit(path: Path) -> None:
    cases = ET.parse(path).findall(".//testcase")
    require(len(cases) == EXPECTED_TESTS, "selected pytest inventory changed or is empty")
    require(all(not list(c) for c in cases), "selected tests skipped, failed, or errored")
    actual = Counter((c.attrib["classname"], c.attrib["name"]) for c in cases)
    expected: Counter[tuple[str, str]] = Counter()
    for node in NODES:
        file, name = node.split("::")
        suffixes = (
            ("[header]", "[struct]")
            if name.endswith("kills_aliasing")
            else ("[outputs]", "[state]", "[diagnostic]")
            if name.endswith("false_agreement")
            else ("",)
        )
        for suffix in suffixes:
            expected[(file.removesuffix(".py").replace("/", "."), name + suffix)] += 1
    require(actual == expected, "selected testcase identities differ from the fixed catalogue")


@contextmanager
def mutate(path: Path, old: str, new: str) -> Iterator[None]:
    """Only used on task-owned scratch sources; restore even after a failed build."""
    original = path.read_bytes()
    text = original.decode()
    require(text.count(old) == 1, f"mutation anchor is not unique: {path}")
    path.write_text(text.replace(old, new, 1))
    try:
        yield
    finally:
        path.write_bytes(original)
        require(path.read_bytes() == original, f"source restoration failed: {path}")


def checked_crc(report: Report) -> None:
    require(
        report.cases == 4
        and report.agreed == 1
        and len(report.divergences) == 3
        and report.both_errored == 0
        and report.protocol_error is None,
        "CRC fault did not produce the required three state-only divergences",
    )
    require([d.number for d in report.divergences] == [1, 2, 3], "wrong CRC fault requests")
    for d in report.divergences:
        require(
            d.python.error is None
            and d.lean.error is None
            and d.python.diagnostic is None
            and d.lean.diagnostic is None
            and d.python.outputs == d.lean.outputs
            and d.python.state != d.lean.state,
            "CRC detection was not clean state-only semantic disagreement",
        )


def checked_native_failure(code: int, stdout: str, stderr: str) -> None:
    expected = Counter(
        {
            "FAIL block codec literal kind constructor": 2,
            "FAIL block codec direct kind observer": 2,
            "FAIL block codec all fields regardless of kind": 2,
        }
    )
    failures = Counter(line for line in stdout.splitlines() if line.startswith("FAIL"))
    ordered = [
        line.removeprefix("FAIL ") for line in stdout.splitlines() if line.startswith("FAIL ")
    ]
    diagnostic = "uncaught exception: block codec tests failed: [" + ", ".join(ordered) + "]\n"
    require(
        code == 1 and stderr == diagnostic and failures == expected,
        "paired observer did not fail exactly the independent native anchors",
    )
    require(
        sum(line.startswith("ok   ") for line in stdout.splitlines()) >= 100,
        "native controls did not execute",
    )


class Run:
    def __init__(self, output: Path):
        self.output = output
        self.phases: list[dict[str, object]] = []

    def command(
        self,
        name: str,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: int = 600,
        expected: int = 0,
        stdin: bytes | None = None,
    ) -> tuple[int, bytes, bytes]:
        print(name, flush=True)
        out, err = self.output / f"{name}.stdout", self.output / f"{name}.stderr"
        with out.open("xb") as stdout, err.open("xb") as stderr:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            try:
                process.communicate(stdin, timeout=timeout)
            except subprocess.TimeoutExpired:
                stop_owned(process)
                raise RuntimeError(f"{name}: timed out; task-owned process group stopped") from None
            except BaseException:
                stop_owned(process)
                raise
        self.phases.append(
            {"name": name, "argv": list(argv), "cwd": str(cwd), "exit": process.returncode}
        )
        require(
            process.returncode == expected,
            f"{name}: exit {process.returncode}, expected {expected}; see {err}",
        )
        return process.returncode, out.read_bytes(), err.read_bytes()

    def compare(self, name: str, item: Input, binary: Path, *, fault: bool = False) -> None:
        path = self.output / f"{name}.json"
        try:
            report = compare_program(item.program, item.cases, 4, [binary], 0)
        except ProtocolError as error:
            if error.report is not None:
                replay.save(error.report, path)
            raise
        replay.save(report, path)  # Retain before any expected-outcome assertion.
        program, cases, ports, seed = replay.load(path)
        require(
            Input(item.name, program, tuple(cases)).fingerprint() == item.fingerprint()
            and ports == 4
            and seed == 0,
            "retained replay changed complete inputs",
        )
        if fault:
            checked_crc(report)
        else:
            require(report.passed and report.cases == len(item.cases), report.summary())
        repeated = replay.replay(path, [binary])
        if fault:
            checked_crc(repeated)
        else:
            require(repeated.passed and repeated.cases == len(item.cases), repeated.summary())
        self.phases.append(
            {
                "name": name,
                "input_sha256": item.fingerprint(),
                "replay_sha256": digest(path.read_bytes()),
                "summary": report.summary(),
            }
        )


def baseline_known_answers(selected: tuple[Input, ...]) -> None:
    from tests.test_firewall import connection
    from tests.test_lean_forwarder_apply import application_output
    from tests.test_lean_forwarder_tables import packet_expected

    for item in selected:
        loaded = arch.load(item.program)
        if item.name == "firewall-connection":
            for case, step in zip(item.cases, connection(), strict=True):
                actual = python_outcome(loaded, case, 4)
                require(
                    actual.outputs == step.outputs
                    and actual.state == step.state
                    and actual.error is None
                    and actual.diagnostic is None,
                    "independent firewall known answer failed",
                )
        else:
            expected = (
                application_output("empty/drop/false")
                if item.name == "empty-default"
                else packet_expected()
            )
            actual = python_outcome(loaded, item.cases[0], 4)
            require(
                actual.outputs == tuple(expected)
                and actual.error is None
                and actual.diagnostic is None,
                "independent forwarder known answer failed",
            )


def execute(run: Run) -> None:
    source_inventory = provenance(ROOT)
    (run.output / "provenance.json").write_text(json.dumps(source_inventory, indent=2) + "\n")
    selected = inputs()
    check_inputs(selected)
    baseline_known_answers(selected)
    binary = ROOT / "spec/arch/.lake/build/bin/p4blo-lean"
    for path in (
        binary,
        *(
            ROOT / "impl/lean/.lake/build/bin" / name
            for name in ("forwarderApply", "forwarderTables", "leanTutorialFirewall")
        ),
    ):
        require(path.is_file(), f"missing {path}; run scripts/check-lean.sh first")
    tracked = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z", "spec/ir", "spec/arch"]
    )
    paths = [Path(p.decode()) for p in tracked.split(b"\0") if p]
    require(
        bool(paths) and all(".lake" not in p.parts and not p.is_absolute() for p in paths),
        "invalid tracked spec inventory",
    )
    sources = {str(p): digest((ROOT / p).read_bytes()) for p in paths}
    (run.output / "sources.json").write_text(json.dumps(sources, indent=2) + "\n")
    (run.output / "mutations.json").write_text(
        json.dumps(
            {
                "crc": {
                    "file": "spec/arch/P4bloArch/Externs.lean",
                    "old": CRC_OLD,
                    "new": CRC_NEW,
                },
                "kind": {"file": "spec/ir/P4bloIR/Json.lean", "old": KIND_OLD, "new": KIND_NEW},
                "observer": {
                    "file": "spec/ir/P4bloIRTest/BlockCodec.lean",
                    "old": OBSERVER_OLD,
                    "new": OBSERVER_NEW,
                },
            },
            indent=2,
        )
        + "\n"
    )
    scratch = run.output / "scratch"
    for path in paths:
        destination = scratch / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, destination)
    spec = scratch / "spec/ir"
    arch = scratch / "spec/arch"
    toolchain = (spec / "lean-toolchain").read_text().strip()
    lake = ["lake", "+" + toolchain, "build"]
    run.command(
        "scratch-baseline-build",
        [*lake, "+P4bloIRTest.ProofAudit", "+P4bloIRTest.CodecProofAudit", "codec-leaves"],
        cwd=spec,
    )
    # The endpoint belongs to the architecture package, whose scratch copy
    # depends on the scratch IR copy by relative path.
    run.command("scratch-endpoint-build", [*lake, "p4blo-lean"], cwd=arch)
    native = spec / ".lake/build/bin/codec-leaves"
    scratch_binary = arch / ".lake/build/bin/p4blo-lean"
    run.command("scratch-native-baseline", [str(native), "--self-test"], cwd=spec)
    for item in selected:
        run.compare("baseline-" + item.name, item, scratch_binary)
    os.environ["P4BLO_REQUIRE_LEAN"] = "1"
    run.command(
        "python-fault-catalogue",
        [
            sys.executable,
            "-m",
            "pytest",
            *NODES,
            "-q",
            "--junitxml=" + str(run.output / "pytest.xml"),
            "--basetemp=" + str(run.output / "pytest-temp"),
        ],
        cwd=ROOT,
        timeout=240,
    )
    check_junit(run.output / "pytest.xml")
    externs = arch / "P4bloArch/Externs.lean"
    with mutate(externs, CRC_OLD, CRC_NEW):
        run.phases.append({"name": "crc-source", "sha256": digest(externs.read_bytes())})
        run.command("crc-runtime-build", [*lake, "p4blo-lean"], cwd=arch)
        run.compare("crc-runtime-fault", selected[2], scratch_binary, fault=True)
    run.command("crc-restored-build", [*lake, "p4blo-lean"], cwd=arch)
    run.compare("crc-restored", selected[2], scratch_binary)
    restored_fault = replay.replay(run.output / "crc-runtime-fault.json", [scratch_binary])
    require(restored_fault.passed and restored_fault.cases == 4, restored_fault.summary())
    run.phases.append({"name": "crc-retained-restored", "summary": restored_fault.summary()})
    source, observer = spec / "P4bloIR/Json.lean", spec / "P4bloIRTest/BlockCodec.lean"

    def codec(name: str) -> object:
        _, stdout, stderr = run.command(
            name,
            [str(native)],
            cwd=spec,
            timeout=30,
            stdin=(canonical(CODEC_REQUEST) + "\n").encode(),
        )
        require(not stderr, "codec emitted stderr")
        return loads(stdout.decode())

    require(
        canonical(codec("codec-baseline")) == canonical(CODEC_EXPECTED), "codec baseline differs"
    )
    with mutate(source, KIND_OLD, KIND_NEW):
        run.phases.append({"name": "codec-source", "sha256": digest(source.read_bytes())})
        run.command(
            "codec-paired-build", [*lake, "+P4bloIRTest.CodecProofAudit", "codec-leaves"], cwd=spec
        )
        reply = codec("codec-paired-reply")
        expected_wrong = json.loads(canonical(CODEC_EXPECTED))
        expected_wrong["value"]["kind"] = "BLOCK_KIND_CONTROL"
        require(
            canonical(reply) == canonical(expected_wrong),
            "paired map did not give exact semantic mismatch",
        )
        with mutate(observer, OBSERVER_OLD, OBSERVER_NEW):
            run.phases.append({"name": "observer-source", "sha256": digest(observer.read_bytes())})
            run.command(
                "observer-paired-build",
                [*lake, "+P4bloIRTest.CodecProofAudit", "codec-leaves"],
                cwd=spec,
            )
            require(
                canonical(codec("observer-paired-reply")) == canonical(CODEC_EXPECTED),
                "paired observer did not demonstrate weak equality survival",
            )
            code, stdout, stderr = run.command(
                "observer-native-kill", [str(native), "--self-test"], cwd=spec, expected=1
            )
            checked_native_failure(code, stdout.decode(), stderr.decode())
    run.command(
        "final-restored-build",
        [*lake, "+P4bloIRTest.ProofAudit", "+P4bloIRTest.CodecProofAudit", "codec-leaves"],
        cwd=spec,
    )
    run.command("final-restored-endpoint-build", [*lake, "p4blo-lean"], cwd=arch)
    run.command("final-restored-native", [str(native), "--self-test"], cwd=spec)
    require(
        canonical(codec("codec-restored")) == canonical(CODEC_EXPECTED), "restored codec differs"
    )
    for item in selected:
        run.compare("restored-" + item.name, item, scratch_binary)
    require(
        all(digest((scratch / p).read_bytes()) == sha for p, sha in sources.items()),
        "scratch sources not restored exactly",
    )
    require(
        all(digest((ROOT / p).read_bytes()) == sha for p, sha in sources.items()),
        "source checkout changed during the experiment",
    )
    require(
        provenance(ROOT)["sha256"] == source_inventory["sha256"],
        "source, test, runner, or lockfile changed during the experiment",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new evidence directory (must not exist)")
    args = parser.parse_args()
    if args.output is None:
        parent = ROOT / ".artifacts/assurance"
        parent.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
    else:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)
    print(f"Evidence: {output}", flush=True)
    run = Run(output)
    status, error = "failed", None
    try:
        execute(run)
        status = "passed"
        return 0
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(error, file=sys.stderr)
        return 1
    finally:
        (output / "result.json").write_text(
            json.dumps(
                {
                    "status": status,
                    "error": error,
                    "phases": run.phases,
                    "inputs": INPUT_HASHES,
                    "python_nodes": NODES,
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    sys.exit(main())
