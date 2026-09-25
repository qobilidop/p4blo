"""The exported conformance corpus: the Lean semantics' answers as data.

    python -m p4blo.conformance export      [--lean PATH] [--dir DIR]
    python -m p4blo.conformance check-python [--dir DIR]
    python -m p4blo.conformance check-lean   [--lean PATH] [--dir DIR]

A fixture is one JSON file: a program in the protobuf JSON wire profile,
an ordered sequence of `p4blo-lean run` requests sent from fresh extern
state, and for each request the reply the Lean endpoint gave, recorded as
the pipe protocol of `p4blo.drt.run` defines it (outputs and diagnostic, or
an error, with the complete extern state and the rule coverage tags). The
fixtures are the semantics' test suite as data: an implementation is
checked against them by running each fixture's requests in order under
the switch architecture with the fixture's port count, with no Lean
process, and comparing what it did with the recorded replies.

Agreement is the DRT's (`Outcome.agrees_with`): equal extern states, equal
outputs as (port, bytes) sequences and a diagnostic on both sides or on
neither, or an error on both for the same stated reason. The coverage tags
are the Lean machine's own measure and take no part in it; a third
implementation ignores them just as Python does.

Lean is checked against the fixtures by regeneration: every fixture's
recorded requests go to the endpoint again and the rewritten file must
equal the tracked one byte for byte. The inputs are concrete data, as in a
replay bundle (`p4blo.drt.replay`), so the check does not depend on any
generator; the header names the recipe that produced them only as
provenance, and `export` is the one place the recipe runs.

The header also names the Lean sources that answered: the last commit that
touched `spec/ir` or `spec/arch` and a digest of the files the endpoint is
built from. That record is informative. A later commit that changes the
sources without changing an answer leaves every fixture byte identical,
and `lean_drift` says so rather than failing; a change that alters an
answer fails `check-lean` until the fixtures are deliberately re-exported.

The input set itself is repository data, not part of this package: the
`export` command takes it from `tests/conformance/inputs.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from google.protobuf import json_format

from p4blo import arch, ir
from p4blo.drt._json import loads as strict_json_loads
from p4blo.drt.case import Case
from p4blo.drt.run import (
    Divergence,
    Outcome,
    ProtocolError,
    default_lean_binary,
    parse_reply,
    python_outcome,
    request_json,
)
from p4blo.v0 import p4blo_pb2 as pb

__all__ = [
    "FORMAT",
    "VERSION",
    "Fixture",
    "Input",
    "Step",
    "answer",
    "check_lean",
    "check_lean_fixture",
    "check_python",
    "check_python_fixture",
    "dumps",
    "export",
    "fixture_paths",
    "lean_drift",
    "lean_provenance",
    "load",
    "loads",
    "main",
]

FORMAT = "p4blo.conformance"
VERSION = 1

# This file is impl/python/p4blo/conformance.py, three levels below the root.
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIR = ROOT / "tests" / "conformance" / "fixtures"
INPUTS_MODULE = "tests.conformance.inputs"

# What the `p4blo-lean` endpoint is built from: the two specification
# packages without their test trees, which change no answer.
LEAN_SOURCES = ("spec/ir", "spec/arch")
_LEAN_TEST_TREES = ("Tests", "ArchTests", ".lake")
_LEAN_SUFFIXES = (".lean", ".toml", ".proto")
_LEAN_NAMES = ("lean-toolchain", "lake-manifest.json")

# A request is answered in milliseconds; the bound only keeps a hung
# endpoint from hanging the gate.
_TIMEOUT_PER_REQUEST = 10.0


@dataclass(frozen=True)
class Input:
    """One fixture's inputs before Lean has answered them.

    `source` is the header's account of where the program and requests
    came from; it must be JSON and is recorded as given.
    """

    name: str
    source: Mapping[str, object]
    program: pb.Program
    cases: tuple[Case, ...]
    ports: int


@dataclass(frozen=True)
class Step:
    """One request as sent and the reply as recorded, both parsed JSON."""

    request: Mapping[str, object]
    reply: Mapping[str, object]


@dataclass(frozen=True)
class Fixture:
    name: str
    source: Mapping[str, object]
    lean: Mapping[str, object]
    ports: int
    # The program in the protobuf JSON mapping, as it went to Lean.
    program: Mapping[str, object]
    steps: tuple[Step, ...]

    def program_ir(self) -> pb.Program:
        try:
            return json_format.ParseDict(dict(self.program), pb.Program())
        except json_format.ParseError as e:
            raise ValueError(f"invalid program protobuf JSON: {e}") from e

    def cases(self) -> list[Case]:
        return [_case(step.request) for step in self.steps]

    def outcomes(self) -> list[Outcome]:
        """The recorded replies, parsed as the DRT parses a live reply."""
        return [parse_reply(_compact(step.reply)) for step in self.steps]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _compact(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def dumps(fixture: Fixture) -> str:
    """The canonical text of a fixture.

    Keys are sorted and values compact, so the bytes are a function of the
    content; the header is spread over lines and each step is one line, so
    a changed answer is a one-line diff that names its request.
    """
    lines = [
        "{",
        f' "format": {_compact(FORMAT)},',
        f' "version": {VERSION},',
        f' "name": {_compact(fixture.name)},',
        f' "source": {_compact(fixture.source)},',
        f' "lean": {_compact(fixture.lean)},',
        f' "ports": {fixture.ports},',
        f' "program": {_compact(fixture.program)},',
        ' "steps": [',
    ]
    for i, step in enumerate(fixture.steps):
        comma = "," if i + 1 < len(fixture.steps) else ""
        lines.append(
            f'  {{"request": {_compact(step.request)}, "reply": {_compact(step.reply)}}}{comma}'
        )
    lines += [" ]", "}"]
    return "\n".join(lines) + "\n"


def loads(text: str) -> Fixture:
    """A fixture from its text; raises `ValueError` on anything malformed."""
    data = strict_json_loads(text)
    if not isinstance(data, dict):
        raise ValueError("a fixture must be a JSON object")
    fields = {"format", "version", "name", "source", "lean", "ports", "program", "steps"}
    if set(data) != fields:
        raise ValueError(f"a fixture has exactly the fields {sorted(fields)}")
    if data["format"] != FORMAT or type(data["version"]) is not int or data["version"] != VERSION:
        raise ValueError(f"not a version {VERSION} {FORMAT} fixture")
    name, source, lean, ports = data["name"], data["source"], data["lean"], data["ports"]
    program, steps = data["program"], data["steps"]
    if not isinstance(name, str) or not name:
        raise ValueError("fixture name must be a nonempty string")
    if not isinstance(source, dict) or not isinstance(lean, dict):
        raise ValueError("fixture source and lean must be objects")
    if type(ports) is not int or ports <= 0:
        raise ValueError("fixture ports must be a positive integer")
    if not isinstance(program, dict):
        raise ValueError("fixture program must be an object")
    if not isinstance(steps, list):
        raise ValueError("fixture steps must be an array")
    parsed: list[Step] = []
    for number, step in enumerate(steps):
        if not isinstance(step, dict) or set(step) != {"request", "reply"}:
            raise ValueError(f"step {number} must be an object with a request and a reply")
        request, reply = step["request"], step["reply"]
        if not isinstance(request, dict) or not isinstance(reply, dict):
            raise ValueError(f"step {number}: request and reply must be objects")
        parsed.append(Step(request, reply))
    return Fixture(name, source, lean, ports, program, tuple(parsed))


def load(path: Path) -> Fixture:
    try:
        return loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"{path.name}: {e}") from e


def fixture_paths(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.json"))


def _case(request: Mapping[str, object]) -> Case:
    """The case a request line carries; the inverse of `request_json`."""
    if set(request) != {"entries", "ingress_port", "packet"}:
        raise ValueError("a request has exactly entries, ingress_port and packet")
    entries, ingress, packet = request["entries"], request["ingress_port"], request["packet"]
    if not isinstance(entries, dict):
        raise ValueError("request entries must be an object")
    if type(ingress) is not int or ingress < 0:
        raise ValueError("request ingress_port must be a nonnegative integer")
    if not isinstance(packet, str):
        raise ValueError("request packet must be a hex string")
    try:
        parsed = json_format.ParseDict(entries, pb.Entries())
    except json_format.ParseError as e:
        raise ValueError(f"invalid request entries protobuf JSON: {e}") from e
    return Case(parsed, ingress, bytes.fromhex(packet))


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def _lean_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for top in LEAN_SOURCES:
        for path in (root / top).rglob("*"):
            relative = path.relative_to(root / top)
            if not path.is_file() or any(p in _LEAN_TEST_TREES for p in relative.parts):
                continue
            if path.suffix in _LEAN_SUFFIXES or path.name in _LEAN_NAMES:
                found.append(path)
    return sorted(found)


def _git(root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout.strip()


def lean_provenance(root: Path = ROOT) -> dict[str, object]:
    """Which Lean sources answer now: a digest of the endpoint's source files
    and the last commit that touched them, marked `+modified` when the
    working tree differs from it (None outside a git checkout)."""
    digest = hashlib.sha256()
    for path in _lean_files(root):
        name = path.relative_to(root).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big") + name)
        digest.update(len(content).to_bytes(8, "big") + content)
    commit = _git(root, "log", "-1", "--format=%H", "--", *LEAN_SOURCES) or None
    if commit is not None and _git(root, "status", "--porcelain", "--", *LEAN_SOURCES):
        commit += "+modified"
    return {"commit": commit, "sources": f"sha256:{digest.hexdigest()}"}


def lean_drift(fixtures: Iterable[Fixture], root: Path = ROOT) -> str | None:
    """None when every fixture was answered by the current Lean sources;
    otherwise a sentence saying which sources answered and which are here.

    Only the digest decides: a shallow clone cannot see the recorded
    commit, and a commit that changed no endpoint source is no drift.
    Drift is not a failure either. Whether an answer changed is decided by
    `check_lean`'s byte comparison; this only explains a header that
    names older sources.
    """
    current = lean_provenance(root)
    fixtures = list(fixtures)
    if {f.lean.get("sources") for f in fixtures} == {current["sources"]}:
        return None
    recorded = {_compact(f.lean) for f in fixtures}
    named = "; ".join(sorted(recorded))
    return (
        f"the fixtures were answered by Lean sources {named}, and the current sources are "
        f"{_compact(current)}. check-lean decides by comparing bytes whether any answer "
        "changed; re-export to record the current sources."
    )


# ---------------------------------------------------------------------------
# Lean
# ---------------------------------------------------------------------------


def answer(
    lean: Sequence[str | Path],
    program: Mapping[str, object],
    requests: Sequence[Mapping[str, object]],
    ports: int,
) -> list[dict[str, object]]:
    """Every request's reply from one fresh `p4blo-lean run` process.

    The requests go in one batch: the endpoint answers line by line and
    keeps extern state across lines, so the replies are those of the
    round-trip harness. Each reply must parse as the DRT parses a live one,
    and the process must exit cleanly with exactly one reply per request.
    """
    with tempfile.TemporaryDirectory() as tmp:
        program_json = Path(tmp) / "program.json"
        program_json.write_text(_compact(program))
        command = [str(c) for c in lean] + ["run", "--ports", str(ports), str(program_json)]
        stdin = "".join(_compact(r) + "\n" for r in requests)
        try:
            done = subprocess.run(
                command,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_PER_REQUEST * (len(requests) + 1),
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ProtocolError(f"cannot run {command[0]}: {e}") from e
    if done.returncode != 0:
        raise ProtocolError(f"exit {done.returncode}: {done.stderr.strip()}")
    # Only a newline ends a reply; `splitlines` would also split on the
    # Unicode separators a JSON string may carry unescaped.
    lines = done.stdout.split("\n")
    if lines[-1] == "":
        lines.pop()
    if len(lines) != len(requests):
        raise ProtocolError(f"{len(requests)} requests got {len(lines)} replies")
    replies: list[dict[str, object]] = []
    for line in lines:
        parse_reply(line)
        reply = strict_json_loads(line)
        assert isinstance(reply, dict)
        replies.append(reply)
    return replies


def _answered(item: Input, lean: Sequence[str | Path], provenance: Mapping[str, object]) -> Fixture:
    program = json.loads(ir.dump_json(item.program))
    requests = [json.loads(request_json(case)) for case in item.cases]
    replies = answer(lean, program, requests, item.ports)
    steps = tuple(Step(q, r) for q, r in zip(requests, replies, strict=True))
    return Fixture(item.name, dict(item.source), provenance, item.ports, program, steps)


def export(
    inputs: Iterable[Input],
    lean: Sequence[str | Path],
    directory: Path = DEFAULT_DIR,
    root: Path = ROOT,
) -> list[Path]:
    """Answer every input on Lean and write the fixtures, replacing the
    directory's previous set: a fixture whose input is gone is removed."""
    provenance = lean_provenance(root)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    names: set[str] = set()
    for item in inputs:
        if item.name in names:
            raise ValueError(f"two inputs are named {item.name!r}")
        names.add(item.name)
        path = directory / f"{item.name}.json"
        path.write_text(dumps(_answered(item, lean, provenance)), encoding="utf-8")
        written.append(path)
    for stale in fixture_paths(directory):
        if stale.stem not in names:
            stale.unlink()
    return written


def check_lean_fixture(path: Path, lean: Sequence[str | Path]) -> list[str]:
    """Answer a fixture's recorded requests again and compare the rewritten
    file with the tracked one byte for byte; the header's Lean provenance
    is kept as recorded, since it is informative (`lean_drift`)."""
    text = path.read_text(encoding="utf-8")
    fixture = load(path)
    try:
        replies = answer(lean, fixture.program, [s.request for s in fixture.steps], fixture.ports)
    except ProtocolError as e:
        return [f"{fixture.name}: Lean did not answer: {e}"]
    steps = tuple(Step(s.request, r) for s, r in zip(fixture.steps, replies, strict=True))
    regenerated = dumps(replace(fixture, steps=steps))
    if regenerated == text:
        return []
    if dumps(fixture) != text:
        return [f"{fixture.name}: the tracked file is not in canonical form"]
    problems: list[str] = []
    for number, (old, new) in enumerate(zip(fixture.steps, steps, strict=True)):
        if old.reply != new.reply:
            changed = sorted(
                k
                for k in old.reply.keys() | new.reply.keys()
                if old.reply.get(k) != new.reply.get(k)
            )
            problems.append(
                f"{fixture.name}: request {number}: Lean's reply changed in {', '.join(changed)}"
            )
    return problems


def check_lean(directory: Path, lean: Sequence[str | Path]) -> list[str]:
    problems: list[str] = []
    for path in fixture_paths(directory):
        problems += check_lean_fixture(path, lean)
    return problems


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------


def check_python_fixture(path: Path) -> list[str]:
    """Run a fixture's requests in order on the Python interpreter, from
    fresh extern state under the switch with the fixture's ports, and
    compare each outcome with the recorded reply as the DRT compares them.
    """
    text = path.read_text(encoding="utf-8")
    fixture = load(path)
    problems: list[str] = []
    if dumps(fixture) != text:
        problems.append(f"{fixture.name}: the file is not in canonical form")
    try:
        loaded = arch.load(fixture.program_ir())
        cases = fixture.cases()
        recorded = fixture.outcomes()
    except (ValueError, ProtocolError) as e:
        return [*problems, f"{fixture.name}: {e}"]
    for number, (case, lean) in enumerate(zip(cases, recorded, strict=True)):
        python = python_outcome(loaded, case, fixture.ports)
        if not python.agrees_with(lean):
            described = Divergence(number, case, python, lean).describe()
            problems.append(f"{fixture.name}: {described.replace('Lean', 'fixture')}")
    return problems


def check_python(directory: Path) -> list[str]:
    problems: list[str] = []
    for path in fixture_paths(directory):
        problems += check_python_fixture(path)
    return problems


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def repository_inputs(root: Path = ROOT) -> list[Input]:
    """The fixed input set, from the repository's `tests/conformance/inputs.py`."""
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    module = importlib.import_module(INPUTS_MODULE)
    return list(module.inputs())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m p4blo.conformance", description=__doc__)
    parser.add_argument("command", choices=["export", "check-python", "check-lean"])
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="the fixture directory")
    parser.add_argument("--lean", type=Path, default=None, help="the p4blo-lean executable")
    args = parser.parse_args(argv)
    lean = [args.lean or default_lean_binary()]
    try:
        if args.command == "export":
            written = export(repository_inputs(), lean, args.dir)
            size = sum(p.stat().st_size for p in written)
            print(f"wrote {len(written)} fixtures, {size} bytes, to {args.dir}")
            return 0
        paths = fixture_paths(args.dir)
        if not paths:
            print(f"no fixtures in {args.dir}", file=sys.stderr)
            return 2
        if args.command == "check-python":
            problems = check_python(args.dir)
        else:
            problems = check_lean(args.dir, lean)
            drift = lean_drift(load(p) for p in paths)
            if drift is not None:
                print(f"note: {drift}")
    except (ProtocolError, ValueError, OSError) as e:
        print(f"{args.command} failed: {e}", file=sys.stderr)
        return 2
    for problem in problems:
        print(problem)
    print(f"{args.command}: {len(paths)} fixtures, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
