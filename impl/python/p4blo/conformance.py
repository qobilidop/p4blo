"""The exported conformance corpus: the Lean semantics' answers as data.

    python -m p4blo.conformance check-python [--dir DIR]
    python -m p4blo.conformance check-lean   [--lean PATH] [--dir DIR]
    python -m p4blo.conformance refresh      [--lean PATH] [--dir DIR]
    python -m p4blo.conformance export       [--lean PATH] [--dir DIR]

A fixture is one JSON file: a program in the protobuf JSON wire profile,
an ordered sequence of `p4blo-lean run` requests sent from fresh extern
state, and for each request the reply the Lean endpoint gave, recorded as
the pipe protocol of `p4blo.drt.run` defines it (outputs and diagnostic, or
an error, with the complete extern state and the rule coverage tags),
except that register and counter cells are listed sparsely: a cell that is
zero is left out. The fixtures are the semantics' test suite as data: an
implementation is checked against them by running each fixture's requests
in order under the switch architecture with the fixture's port count, with
no Lean process, and comparing what it did with the recorded replies.
`tests/conformance/README.md` is the format's specification.

Agreement is the DRT's (`Outcome.agrees_with`): equal extern states, equal
outputs as (port, bytes) sequences and a diagnostic on both sides or on
neither, or an error on both for the same stated reason. The coverage tags
are the Lean machine's own measure and take no part in it; a third
implementation ignores them just as Python does.

Lean is checked against the fixtures by regeneration: every fixture's
recorded requests go to the endpoint again and the rewritten file must
equal the tracked one byte for byte. The inputs are concrete data, as in a
replay bundle (`p4blo.drt.replay`), so the check does not depend on any
generator. Two commands write fixtures, and they are kept apart so that a
diff says which kind of change it is: `refresh` answers the tracked
requests again and rewrites replies and the header, never a program or a
request, so a semantics change is a diff of answers only; `export` is the
one place the input recipe runs, for adding or changing inputs.

The header also names what answered: the last commit that touched the
endpoint's semantics sources, a digest of those sources (`semantics_files`
says which they are), and a digest of the `p4blo-lean` binary. That record
is informative. A later commit that changes the sources without changing
an answer leaves every fixture byte identical, and `lean_drift` says so
rather than failing; a change that alters an answer fails `check-lean`
until the fixtures are deliberately refreshed.

The input set itself is repository data, not part of this package: the
`export` command takes it from `tests/conformance/inputs.py`.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib
import json
import re
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
    Outcome,
    ProtocolError,
    default_lean_binary,
    parse_reply,
    python_outcome,
    request_json,
)
from p4blo.drt.state import encode
from p4blo.v0 import p4blo_pb2 as pb

__all__ = [
    "FORMAT",
    "VERSION",
    "Fixture",
    "Input",
    "StaleLean",
    "Step",
    "answer",
    "binary_drift",
    "check_inputs",
    "check_lean",
    "check_lean_fixture",
    "check_python",
    "check_python_fixture",
    "dense_reply",
    "dumps",
    "export",
    "fixture_paths",
    "lean_drift",
    "lean_provenance",
    "load",
    "loads",
    "main",
    "refresh",
    "semantics_files",
    "sparse_reply",
    "stale_lean",
]

FORMAT = "p4blo.conformance"
# Version 2 lists register and counter cells sparsely.
VERSION = 2

# This file is impl/python/p4blo/conformance.py, three levels below the root.
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIR = ROOT / "tests" / "conformance" / "fixtures"
INPUTS_MODULE = "tests.conformance.inputs"

# The two Lean packages the endpoint is built from, and the module whose
# `main` is the endpoint.
LEAN_PACKAGES = ("spec/ir", "spec/arch")
LEAN_ENDPOINT = "spec/arch/Main.lean"
# A module whose last name component ends in one of these holds proofs
# about the definitions, not definitions the endpoint runs: no answer can
# change when it does, so it is neither hashed nor followed.
_PROOF_MODULE = re.compile(r"(Laws|Audit|Probe|Theorems)$")
_TEST_TREES = ("P4bloIRTest", "ArchTests")
_IMPORT = re.compile(r"^import\s+(\S+)\s*$")

# A request is answered in milliseconds; the bound only keeps a hung
# endpoint from hanging the gate.
_TIMEOUT_PER_REQUEST = 10.0

# The reply fields a fixture records, as the protocol defines them.
_OUTPUT_REPLY = {"outputs", "state", "coverage"}
_ERROR_REPLY = {"error", "state", "coverage"}
# Extern kinds with cells, which a fixture lists sparsely.
_CELL_KINDS = ("register", "counter")


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
    """One request as sent and the reply as recorded (cells sparse), both
    parsed JSON."""

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
        """The recorded replies, expanded and parsed as the DRT parses a
        live reply."""
        return [parse_reply(_compact(dense_reply(step.reply))) for step in self.steps]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _compact(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sparse_reply(reply: Mapping[str, object]) -> dict[str, object]:
    """A protocol reply with each register's and counter's `values` array
    replaced by its length, `size`, and its nonzero cells, `nonzero`, as
    `[index, value]` pairs in index order. Most cells of a corpus program
    stay zero, so they were most of the corpus's bytes; nothing is lost."""
    state = reply.get("state")
    if not isinstance(state, dict):
        return dict(reply)
    sparse: dict[str, object] = {}
    for name, fields in state.items():
        if isinstance(fields, dict) and fields.get("kind") in _CELL_KINDS:
            values = fields.get("values")
            if isinstance(values, list):
                rest = {k: v for k, v in fields.items() if k != "values"}
                nonzero = [[i, v] for i, v in enumerate(values) if v != "0x0"]
                fields = {**rest, "size": len(values), "nonzero": nonzero}
        sparse[name] = fields
    return {**reply, "state": sparse}


def dense_reply(reply: Mapping[str, object]) -> dict[str, object]:
    """The protocol reply a fixture's reply stands for, `sparse_reply`'s
    inverse. Raises `ValueError` on a malformed sparse listing; the
    expanded cells are then checked as any reply's are (`parse_reply`)."""
    state = reply.get("state")
    if not isinstance(state, dict):
        return dict(reply)
    dense: dict[str, object] = {}
    for name, fields in state.items():
        if isinstance(fields, dict) and fields.get("kind") in _CELL_KINDS:
            size, nonzero = fields.get("size"), fields.get("nonzero")
            if "values" in fields or type(size) is not int or size < 0:
                raise ValueError(f"extern {name!r} must list its cells as size and nonzero")
            if not isinstance(nonzero, list):
                raise ValueError(f"extern {name!r}: nonzero must be an array")
            values: list[object] = ["0x0"] * size
            last = -1
            for cell in nonzero:
                if not isinstance(cell, list) or len(cell) != 2:
                    raise ValueError(f"extern {name!r}: a nonzero cell is [index, value]")
                index, value = cell
                if type(index) is not int or not last < index < size:
                    raise ValueError(f"extern {name!r}: cell indices must increase within size")
                # One spelling per state: a zero cell is always left out.
                if value == "0x0":
                    raise ValueError(f"extern {name!r}: a zero cell is not listed")
                values[index] = value
                last = index
            rest = {k: v for k, v in fields.items() if k not in ("size", "nonzero")}
            fields = {**rest, "values": values}
        dense[name] = fields
    return {**reply, "state": dense}


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


def _check_reply(reply: Mapping[str, object]) -> None:
    """A recorded reply is exactly a reply of the current protocol:
    outputs or an error, the state and the coverage tags, nothing else."""
    keys = set(reply)
    if keys - {"diagnostic"} != _OUTPUT_REPLY and keys != _ERROR_REPLY:
        raise ValueError(f"a reply has the fields {sorted(keys)}")
    try:
        parse_reply(_compact(dense_reply(reply)))
    except ProtocolError as e:
        raise ValueError(str(e)) from e


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
    # A fixture without requests checks nothing, and an emptied file would
    # otherwise pass both checks.
    if not isinstance(steps, list) or not steps:
        raise ValueError("fixture steps must be a nonempty array")
    parsed: list[Step] = []
    for number, step in enumerate(steps):
        if not isinstance(step, dict) or set(step) != {"request", "reply"}:
            raise ValueError(f"step {number} must be an object with a request and a reply")
        request, reply = step["request"], step["reply"]
        if not isinstance(request, dict) or not isinstance(reply, dict):
            raise ValueError(f"step {number}: request and reply must be objects")
        try:
            _check_reply(reply)
        except ValueError as e:
            raise ValueError(f"step {number}: {e}") from e
        parsed.append(Step(request, reply))
    return Fixture(name, source, lean, ports, program, tuple(parsed))


def load(path: Path) -> Fixture:
    try:
        fixture = loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"{path.name}: {e}") from e
    if fixture.name != path.stem:
        raise ValueError(f"{path.name}: the fixture is named {fixture.name!r}, not its file's stem")
    return fixture


def fixture_paths(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.json"))


def _is_fixture(path: Path) -> bool:
    """Whether a file declares itself a fixture of this format, of any
    version: the only kind of file `export` may remove."""
    try:
        data = strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return False
    return isinstance(data, dict) and data.get("format") == FORMAT


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


def _module_file(root: Path, module: str) -> Path | None:
    """The file of a module of the two packages; None for the toolchain's
    own (`Std`, `Lean`, `Init`), which `lean-toolchain` pins."""
    relative = Path(*module.split(".")).with_suffix(".lean")
    for package in LEAN_PACKAGES:
        path = root / package / relative
        if path.is_file():
            return path
    return None


def _imports(path: Path) -> list[str]:
    modules: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _IMPORT.match(line.strip())
        if match:
            modules.append(match.group(1))
    return modules


def _only_imports(path: Path) -> bool:
    """A file of imports alone (an umbrella such as `P4bloIR.lean`) means
    nothing beyond the modules it imports."""
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return all(not line or line.startswith("--") or _IMPORT.match(line) for line in lines)


def semantics_files(root: Path = ROOT) -> list[Path]:
    """The files whose content decides what `p4blo-lean run` answers.

    The rule: start at the endpoint, `spec/arch/Main.lean`, and follow its
    `import` lines through the two specification packages. A proof module
    (a name ending in `Laws`, `Audit`, `Probe` or `Theorems`) and anything
    under a package's `P4bloIRTest/` or `ArchTests/` is neither followed nor
    included: it states facts about the definitions and changes no answer.
    A file of imports alone is followed but not included, since adding a
    proof module to an umbrella changes no answer either. Each package's
    `lean-toolchain` is included, since the toolchain compiles the rest.
    Proof-support modules that an umbrella imports without a proof name
    (the typing and certificate modules) stay in: a change there costs a
    needless note, never a missed one.
    """
    found: set[Path] = set()
    seen: set[Path] = set()
    pending = [root / LEAN_ENDPOINT]
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        if not _only_imports(path):
            found.add(path)
        for module in _imports(path):
            parts = module.split(".")
            if _PROOF_MODULE.search(parts[-1]) or parts[0] in _TEST_TREES:
                continue
            target = _module_file(root, module)
            if target is not None:
                pending.append(target)
    for package in LEAN_PACKAGES:
        toolchain = root / package / "lean-toolchain"
        if toolchain.is_file():
            found.add(toolchain)
    return sorted(found)


def _git(root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout.strip()


def _binary(lean: Sequence[str | Path]) -> Path | None:
    """The executable when the command is one file; a command with
    arguments (a stand-in endpoint in the tests) has no binary to vouch
    for."""
    if len(lean) != 1:
        return None
    path = Path(lean[0])
    return path if path.is_file() else None


def _binary_digest(lean: Sequence[str | Path]) -> str | None:
    binary = _binary(lean)
    if binary is None:
        return None
    return f"sha256:{hashlib.sha256(binary.read_bytes()).hexdigest()}"


def lean_provenance(
    root: Path = ROOT, lean: Sequence[str | Path] | None = None
) -> dict[str, object]:
    """What answers now: a digest of the endpoint's semantics sources
    (`semantics_files`), the last commit that touched them, marked
    `+modified` when the working tree differs from it (None outside a git
    checkout), and a digest of the binary when `lean` is one file."""
    digest = hashlib.sha256()
    files = semantics_files(root)
    for path in files:
        name = path.relative_to(root).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big") + name)
        digest.update(len(content).to_bytes(8, "big") + content)
    relative = [path.relative_to(root).as_posix() for path in files]
    commit = _git(root, "log", "-1", "--format=%H", "--", *relative) or None
    if commit is not None and _git(root, "status", "--porcelain", "--", *relative):
        commit += "+modified"
    return {
        "binary": _binary_digest(lean) if lean is not None else None,
        "commit": commit,
        "sources": f"sha256:{digest.hexdigest()}",
    }


def lean_drift(fixtures: Iterable[Fixture], root: Path = ROOT) -> str | None:
    """None when every fixture was answered by the current semantics
    sources; otherwise a sentence naming the recorded and current digests.

    Only the digest decides: a shallow clone cannot see the recorded
    commit, and a commit that changed no semantics source is no drift.
    Drift is not a failure either. Whether an answer changed is decided by
    `check_lean`'s byte comparison; this only explains a header that
    names older sources.
    """
    current = lean_provenance(root)
    recorded = {str(f.lean.get("sources")) for f in fixtures}
    if recorded == {current["sources"]}:
        return None
    return (
        f"the fixtures were answered by Lean sources {', '.join(sorted(recorded))}, and the "
        f"current sources are {current['sources']} (commit {current['commit']}). check-lean "
        "decides by comparing bytes whether any answer changed; refresh to record the "
        "current sources."
    )


def binary_drift(fixtures: Iterable[Fixture], lean: Sequence[str | Path]) -> str | None:
    """None when the binary is the one that answered every fixture, or when
    there is no single binary to compare; otherwise a sentence naming both
    digests. A binary built on another platform differs by its bytes
    alone, so this is a note like `lean_drift`, never a failure."""
    current = _binary_digest(lean)
    if current is None:
        return None
    recorded = {str(f.lean.get("binary")) for f in fixtures}
    if recorded == {current}:
        return None
    return (
        f"the fixtures were answered by a p4blo-lean binary {', '.join(sorted(recorded))}, "
        f"and {lean[0]} is {current}. A rebuild or another platform explains this; "
        "check-lean's byte comparison decides whether any answer changed."
    )


class StaleLean(ValueError):
    """The binary is older than a semantics source it is built from."""


def stale_lean(lean: Sequence[str | Path], root: Path = ROOT) -> str | None:
    """Why the binary may not reflect the sources, or None.

    A binary built before a semantics change answers for the old sources,
    so `check_lean` would pass falsely and `refresh` would record stale
    answers under the current source digest. A modification-time
    comparison is what can be known without a build tool; the required
    gate builds Lean first, so this guards local use.
    """
    binary = _binary(lean)
    if binary is None:
        return None
    built = binary.stat().st_mtime
    newest = max(semantics_files(root), key=lambda p: p.stat().st_mtime)
    changed = newest.stat().st_mtime
    if changed <= built:
        return None

    def when(t: float) -> str:
        return datetime.datetime.fromtimestamp(t).isoformat(timespec="seconds")

    return (
        f"{binary} (built {when(built)}) is older than {newest.relative_to(root).as_posix()} "
        f"(modified {when(changed)}); rebuild it with scripts/check-lean.sh before asking it "
        "for answers. If Lake finds nothing to rebuild, the build already matches the "
        f"sources and `touch {binary}` records that."
    )


def _require_current(lean: Sequence[str | Path], root: Path) -> None:
    reason = stale_lean(lean, root)
    if reason is not None:
        raise StaleLean(reason)


# ---------------------------------------------------------------------------
# Lean
# ---------------------------------------------------------------------------


def answer(
    lean: Sequence[str | Path],
    program: Mapping[str, object],
    requests: Sequence[Mapping[str, object]],
    ports: int,
) -> list[dict[str, object]]:
    """Every request's reply from one fresh `p4blo-lean run` process, as
    the protocol spells it (cells dense).

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


def _reanswered(fixture: Fixture, lean: Sequence[str | Path]) -> tuple[Step, ...]:
    """The fixture's steps with Lean's replies to its recorded requests."""
    requests = [s.request for s in fixture.steps]
    replies = answer(lean, fixture.program, requests, fixture.ports)
    return tuple(Step(q, sparse_reply(r)) for q, r in zip(requests, replies, strict=True))


def _answered(item: Input, lean: Sequence[str | Path], provenance: Mapping[str, object]) -> Fixture:
    program = json.loads(ir.dump_json(item.program))
    requests = [json.loads(request_json(case)) for case in item.cases]
    replies = answer(lean, program, requests, item.ports)
    steps = tuple(Step(q, sparse_reply(r)) for q, r in zip(requests, replies, strict=True))
    return Fixture(item.name, dict(item.source), provenance, item.ports, program, steps)


def export(
    inputs: Iterable[Input],
    lean: Sequence[str | Path],
    directory: Path = DEFAULT_DIR,
    root: Path = ROOT,
) -> list[Path]:
    """Answer every input on Lean and write the fixtures, replacing the
    directory's previous set: a fixture whose input is gone is removed.
    Only a file that declares itself a fixture is ever removed, and every
    input is answered before anything is written."""
    _require_current(lean, root)
    provenance = lean_provenance(root, lean)
    items = list(inputs)
    names: set[str] = set()
    for item in items:
        if item.name in names:
            raise ValueError(f"two inputs are named {item.name!r}")
        names.add(item.name)
    fixtures = [_answered(item, lean, provenance) for item in items]
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fixture in fixtures:
        path = directory / f"{fixture.name}.json"
        path.write_text(dumps(fixture), encoding="utf-8")
        written.append(path)
    for stale in fixture_paths(directory):
        if stale.stem not in names and _is_fixture(stale):
            stale.unlink()
    return written


def refresh(
    lean: Sequence[str | Path], directory: Path = DEFAULT_DIR, root: Path = ROOT
) -> list[Path]:
    """Answer every fixture's recorded requests again and rewrite the
    fixtures whose replies changed or whose header names other semantics
    sources; return the rewritten paths.

    No generator runs and no program or request changes, so the diff is
    replies and headers only. Every fixture is answered before any is
    written, so a failure leaves the set as it was. A fixture whose
    replies and sources are unchanged is left byte for byte, even when
    another binary answered, so that a refresh on another machine is no
    diff at all.
    """
    _require_current(lean, root)
    provenance = lean_provenance(root, lean)
    pending: list[tuple[Path, Fixture]] = []
    for path in fixture_paths(directory):
        text = path.read_text(encoding="utf-8")
        fixture = load(path)
        current = replace(fixture, steps=_reanswered(fixture, lean))
        if dumps(current) != text or fixture.lean.get("sources") != provenance["sources"]:
            pending.append((path, replace(current, lean=provenance)))
    for path, fixture in pending:
        path.write_text(dumps(fixture), encoding="utf-8")
    return [path for path, _ in pending]


def check_lean_fixture(path: Path, lean: Sequence[str | Path]) -> list[str]:
    """Answer a fixture's recorded requests again and compare the rewritten
    file with the tracked one byte for byte; the header's provenance is
    kept as recorded, since it is informative (`lean_drift`)."""
    try:
        text = path.read_text(encoding="utf-8")
        fixture = load(path)
    except (OSError, UnicodeError, ValueError) as e:
        return [f"{path.stem}: {e}"]
    try:
        steps = _reanswered(fixture, lean)
    except ProtocolError as e:
        return [f"{fixture.name}: Lean did not answer: {e}"]
    if dumps(replace(fixture, steps=steps)) == text:
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


def check_lean(directory: Path, lean: Sequence[str | Path], root: Path = ROOT) -> list[str]:
    """Every fixture answered again. Raises `StaleLean` before asking when
    the binary is older than its sources, whose answers would prove
    nothing about them."""
    _require_current(lean, root)
    problems: list[str] = []
    for path in fixture_paths(directory):
        problems += check_lean_fixture(path, lean)
    return problems


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------


def _describe(number: int, python: Outcome, recorded: Outcome) -> str:
    """A disagreement with both sides named, and every extern whose state
    differs in the protocol's lossless spelling."""
    lines = [f"request {number}: Python {python}; fixture {recorded}"]
    if python.state != recorded.state:
        left, right = encode(python.state), encode(recorded.state)
        for name in sorted(left.keys() | right.keys()):
            if left.get(name) != right.get(name):
                lines.append(
                    f"state {name}: Python {json.dumps(left.get(name))}; "
                    f"fixture {json.dumps(right.get(name))}"
                )
    return "\n".join(lines)


def check_python_fixture(path: Path) -> list[str]:
    """Run a fixture's requests in order on the Python interpreter, from
    fresh extern state under the switch with the fixture's ports, and
    compare each outcome with the recorded reply as the DRT compares them.
    A fixture that cannot be read or loaded is that fixture's problem,
    reported like any other, so the remaining fixtures are still checked.
    """
    try:
        text = path.read_text(encoding="utf-8")
        fixture = load(path)
    except (OSError, UnicodeError, ValueError) as e:
        return [f"{path.stem}: {e}"]
    problems: list[str] = []
    if dumps(fixture) != text:
        problems.append(f"{fixture.name}: the file is not in canonical form")
    try:
        cases = fixture.cases()
        recorded = fixture.outcomes()
        program = fixture.program_ir()
    except (ValueError, ProtocolError) as e:
        return [*problems, f"{fixture.name}: {e}"]
    try:
        loaded = arch.load(program)
    # Validation, the metadata contract and extern binding each raise their
    # own class; any of them means the recorded program does not load.
    except Exception as e:  # noqa: BLE001
        return [*problems, f"{fixture.name}: the program does not load: {type(e).__name__}: {e}"]
    for number, (case, lean) in enumerate(zip(cases, recorded, strict=True)):
        python = python_outcome(loaded, case, fixture.ports)
        if not python.agrees_with(lean):
            problems.append(f"{fixture.name}: {_describe(number, python, lean)}")
    return problems


def check_python(directory: Path) -> list[str]:
    problems: list[str] = []
    for path in fixture_paths(directory):
        problems += check_python_fixture(path)
    return problems


def check_inputs(directory: Path, inputs: Iterable[Input]) -> list[str]:
    """Whether the directory holds one fixture per input with one step per
    request. Only names and counts are compared, so a generator whose
    output changes fails nothing until the next export; a fixture that
    lost steps fails here, since neither check can see a request that is
    not there."""
    expected = {item.name: len(item.cases) for item in inputs}
    problems: list[str] = []
    found: dict[str, int | None] = {}
    for path in fixture_paths(directory):
        try:
            found[path.stem] = len(load(path).steps)
        except (OSError, UnicodeError, ValueError) as e:
            problems.append(f"{path.stem}: {e}")
            found[path.stem] = None
    for name in sorted(expected.keys() - found.keys()):
        problems.append(f"{name}: an input with no fixture")
    for name in sorted(found.keys() - expected.keys()):
        problems.append(f"{name}: a fixture with no input")
    for name in sorted(expected.keys() & found.keys()):
        count = found[name]
        if count is not None and count != expected[name]:
            problems.append(f"{name}: {count} steps, but its input has {expected[name]} requests")
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
    parser = argparse.ArgumentParser(
        prog="python -m p4blo.conformance",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=["check-python", "check-lean", "refresh", "export"])
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
        if args.command == "refresh":
            rewritten = refresh(lean, args.dir)
            print(f"refresh: {len(paths)} fixtures, {len(rewritten)} rewritten")
            return 0
        if args.command == "check-python":
            problems = check_python(args.dir)
        else:
            problems = check_lean(args.dir, lean)
            fixtures: list[Fixture] = []
            for path in paths:
                try:
                    fixtures.append(load(path))
                except ValueError:
                    continue  # check_lean has reported it
            for note in (lean_drift(fixtures), binary_drift(fixtures, lean)):
                if note is not None:
                    print(f"note: {note}")
    except (ProtocolError, ValueError, OSError) as e:
        print(f"{args.command} failed: {e}", file=sys.stderr)
        return 2
    for problem in problems:
        print(problem)
    print(f"{args.command}: {len(paths)} fixtures, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
