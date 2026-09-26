"""Run cases on Python and on Lean, and compare.

## The pipe protocol

`p4blo-lean run [--ports N] <program.json>` reads one JSON object per
line from stdin and writes one per line to stdout:

    request:  {"entries": <pb.Entries as protobuf JSON, proto field names>,
               "ingress_port": n, "packet": "<hex>"}
    reply:    {"outputs": [[port, "<hex>"], ...], "state": {...}, "diagnostic": "...",
               "coverage": ["tag", ...]}
              or   {"error": "...", "state": {...}, "coverage": ["tag", ...]}

`diagnostic` is present when the architecture dropped the packet for a
reason the program did not decide (a misaligned parse, an egress port the
switch does not have); on the Python side it is `Switch.diagnostics`.
Extern state persists across the requests of one process, as it does in
one `Loaded` on the Python side, so both sides see the same case sequence
from the same fresh state. Anything else on stdout, or a reply that does
not parse, is a `ProtocolError`: the harness never guesses.
`state` is required, including on errors: logical extern observations as
specified in `p4blo.drt.state`, not either runtime's object layout.

`coverage` is the sorted list of rule tags of the Lean semantics the request
exercised (`P4bloIR.Coverage`; `p4blo-lean coverage-inventory` lists them
all). It is the adequacy measure of the campaign, not part of agreement.
A reply without it comes from an older peer: it is tolerated, recorded as
`None`, and counted by `RuleCoverage.unreported` so that a report can say
the measure is missing rather than empty.

## Agreement

Two sides agree only when their abstract extern states are equal. Their
outputs must also be equal as sequences of
(port, bytes) and either both or neither carry a diagnostic (the texts are
not compared), or when both report an error for the same stated reason:
Lean copies the Python sentences, so the messages are compared after the
Python exception class prefix (`InstallError: `) is stripped. Two sides
that stop for different reasons have not agreed on anything. Everything
else is a `Divergence`, which carries the case and both outcomes.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from types import TracebackType
from typing import IO

from google.protobuf import json_format

from p4blo import arch
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import assembly_of
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt._json import loads as strict_json_loads
from p4blo.drt.case import Case
from p4blo.drt.coverage import RuleCoverage
from p4blo.drt.generate import generate
from p4blo.drt.state import Snapshot, decode, encode, snapshot
from p4blo.v0 import p4blo_pb2 as pb

__all__ = [
    "Divergence",
    "LeanRunner",
    "Outcome",
    "ProtocolError",
    "Report",
    "compare",
    "compare_cases",
    "compare_program",
    "normalize_error",
    "run_python",
]


class ProtocolError(Exception):
    """The Lean side did not speak the protocol: it could not be started,
    it exited, or it replied with something that is neither outputs nor an
    error."""

    def __init__(self, message: str, report: Report | None = None) -> None:
        super().__init__(message)
        self.report = report


_CLASS_PREFIX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*: ")


def normalize_error(message: str) -> str:
    """An error message without the Python exception class prefix, so that
    `InstallError: table 't' has 2 keys` compares equal to Lean's sentence."""
    return _CLASS_PREFIX.sub("", message, count=1)


@dataclass(frozen=True)
class Outcome:
    """What one side produced: output packets, with the architecture's
    diagnostic when it dropped the packet, or an error message."""

    outputs: tuple[tuple[int, bytes], ...] | None = None
    error: str | None = None
    diagnostic: str | None = None
    state: Snapshot = ()
    # The rule tags the Lean side reported, or None when the peer sent none.
    # Coverage measures the campaign; it never takes part in agreement.
    coverage: frozenset[str] | None = field(default=None, compare=False)

    def agrees_with(self, other: Outcome) -> bool:
        if self.state != other.state:
            return False
        if self.error is not None or other.error is not None:
            return (
                self.error is not None
                and other.error is not None
                and normalize_error(self.error) == normalize_error(other.error)
            )
        return self.outputs == other.outputs and (self.diagnostic is None) == (
            other.diagnostic is None
        )

    def __str__(self) -> str:
        if self.error is not None:
            return f"error: {self.error}"
        if not self.outputs:
            return "no packet" + (f" ({self.diagnostic})" if self.diagnostic else "")
        return "; ".join(f"port {port}: {data.hex()}" for port, data in self.outputs)


@dataclass(frozen=True)
class Divergence:
    # The case's index in the report's sequence, from 0.
    number: int
    case: Case
    python: Outcome
    lean: Outcome

    def describe(self) -> str:
        """Include state-only differences, using the lossless hex wire values."""
        lines = [f"case {self.number}: Python {self.python}; Lean {self.lean}"]
        if self.python.state != self.lean.state:
            left, right = encode(self.python.state), encode(self.lean.state)
            for name in sorted(left.keys() | right.keys()):
                if left.get(name) != right.get(name):
                    lines.append(
                        f"state {name}: Python {json.dumps(left.get(name))}; "
                        f"Lean {json.dumps(right.get(name))}"
                    )
        return "\n".join(lines)


@dataclass
class Report:
    program: str
    seed: int
    ports: int
    cases: int = 0
    # Cases where both sides raised an error. They agree only when the
    # reasons are the same; either way the generator promises installable
    # entries and in-range ports, so on a sweep the count should be zero.
    both_errored: int = 0
    divergences: list[Divergence] = field(default_factory=list)
    inputs: tuple[Case, ...] = ()
    program_ir: apb.BlockAssembly | None = field(default=None, repr=False)
    protocol_error: str | None = None
    # The Lean rule tags accumulated over the cases run so far.
    rule_coverage: RuleCoverage = field(default_factory=RuleCoverage, repr=False)

    @property
    def passed(self) -> bool:
        """Generated valid inputs must execute, not merely fail alike."""
        return not self.divergences and self.both_errored == 0 and self.protocol_error is None

    @property
    def agreed(self) -> int:
        return self.cases - len(self.divergences)

    def summary(self) -> str:
        return (
            f"{self.program}: seed {self.seed}, {self.cases} cases, {self.agreed} agreed, "
            f"{len(self.divergences)} diverged, {self.both_errored} errored on both sides"
        )


def run_python(loaded: arch.Loaded, case: Case, ports: int) -> list[tuple[int, bytes]]:
    """One case through the switch on the reference interpreter."""
    switch = arch.Switch(ports)
    return switch.run(loaded, loaded.entries(case.entries), case.ingress_port, case.packet)


def python_outcome(loaded: arch.Loaded, case: Case, ports: int) -> Outcome:
    switch = arch.Switch(ports)
    try:
        outputs = switch.run(loaded, loaded.entries(case.entries), case.ingress_port, case.packet)
    except Exception as e:  # noqa: BLE001 - any failure is this side's outcome
        return Outcome(error=f"{type(e).__name__}: {e}", state=snapshot(loaded))
    diagnostic = "; ".join(switch.diagnostics) if switch.diagnostics else None
    return Outcome(outputs=tuple(outputs), diagnostic=diagnostic, state=snapshot(loaded))


def request_json(case: Case) -> str:
    """The request line for a case, without its newline."""
    return json.dumps(
        {
            "entries": json_format.MessageToDict(case.entries, preserving_proto_field_name=True),
            "ingress_port": case.ingress_port,
            "packet": case.packet.hex(),
        }
    )


def parse_reply(line: str) -> Outcome:
    """A reply line as an outcome; raises `ProtocolError` on anything else."""
    try:
        reply = strict_json_loads(line)
    except ValueError as e:
        raise ProtocolError(f"reply is not JSON: {e}: {line!r}") from e
    if not isinstance(reply, dict):
        raise ProtocolError(f"reply is not an object: {line!r}")
    try:
        state = decode(reply.get("state"))
    except ValueError as e:
        raise ProtocolError(f"bad extern state: {e}") from e
    diagnostic = reply.get("diagnostic")
    if diagnostic is not None and not isinstance(diagnostic, str):
        raise ProtocolError(f"bad diagnostic {diagnostic!r} in {line!r}")
    coverage = parse_coverage(reply, line)
    if "error" in reply:
        if not isinstance(reply["error"], str) or "outputs" in reply:
            raise ProtocolError(f"bad error reply: {line!r}")
        return Outcome(error=reply["error"], state=state, coverage=coverage)
    if "outputs" not in reply or not isinstance(reply["outputs"], list):
        raise ProtocolError(f"reply has neither outputs nor error: {line!r}")
    outputs: list[tuple[int, bytes]] = []
    for item in reply["outputs"]:
        try:
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError("expected [port, hex]")
            port, data = item
            if type(port) is not int or port < 0 or not isinstance(data, str):
                raise ValueError("expected a nonnegative integer port and hex string")
            outputs.append((port, bytes.fromhex(data)))
        except (TypeError, ValueError) as e:
            raise ProtocolError(f"bad output {item!r} in {line!r}") from e
    return Outcome(outputs=tuple(outputs), diagnostic=diagnostic, state=state, coverage=coverage)


def parse_coverage(reply: dict[str, object], line: str) -> frozenset[str] | None:
    """The reply's rule tags; None when an older peer sent no `coverage`."""
    if "coverage" not in reply:
        return None
    tags = reply["coverage"]
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise ProtocolError(f"bad coverage in {line!r}")
    return frozenset(tags)


class LeanRunner:
    """A `p4blo-lean run` process, one case per round trip.

    `command` is the executable and any leading arguments; `run --ports N
    <program>` is appended. Use as a context manager so the process is
    always reaped.
    """

    def __init__(
        self, command: Sequence[str | Path], program_json: Path, ports: int, *, timeout: float = 10
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.command = [str(c) for c in command] + ["run", "--ports", str(ports), str(program_json)]
        self.timeout = timeout
        self.process: subprocess.Popen[str] | None = None
        self.stderr: IO[bytes] | None = None
        self.requests: Queue[str | None] = Queue()
        self.replies: Queue[str | Exception] = Queue()
        self.worker: Thread | None = None

    def __enter__(self) -> LeanRunner:
        self.stderr = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.stderr,
                text=True,
                start_new_session=os.name == "posix",
            )
        except OSError as e:
            self.close()
            raise ProtocolError(f"cannot start {self.command[0]}: {e}") from e
        self.worker = Thread(target=self._exchange, daemon=True)
        self.worker.start()
        return self

    def _exchange(self) -> None:
        """Bound both writes and reads from the caller; even a peer that
        never reads a large request or never finishes its line times out."""
        process = self.process
        assert process is not None and process.stdin is not None and process.stdout is not None
        while True:
            request = self.requests.get()
            try:
                if request is None:
                    process.stdin.close()
                    trailing = process.stdout.read()
                    process.wait()
                    self.replies.put(trailing)
                    return
                process.stdin.write(request + "\n")
                process.stdin.flush()
                self.replies.put(process.stdout.readline())
            except (OSError, ValueError, UnicodeError) as e:
                self.replies.put(e)
                return

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                self.finish()
        finally:
            self.close()

    def finish(self) -> None:
        """Require clean EOF, no extra replies, and a successful exit.

        A valid last response must not hide a subsequent crash. The same
        worker bounds draining and waiting, including inherited pipes.
        """
        if self.process is None:
            return
        self.requests.put(None)
        try:
            trailing = self.replies.get(timeout=self.timeout)
        except Empty:
            raise ProtocolError(f"Lean shutdown timed out after {self.timeout:g}s") from None
        if isinstance(trailing, Exception):
            raise ProtocolError(f"Lean shutdown failed: {trailing}") from trailing
        if self.process.returncode != 0:
            raise ProtocolError(f"Lean shutdown failed: {self._death()}")
        if trailing:
            raise ProtocolError(f"unsolicited output after the final reply: {trailing!r}")

    def close(self) -> None:
        if self.process is not None:
            # Kill before closing stdin: another thread may be blocked writing
            # it. Closing the text stream first would wait on its lock forever.
            if os.name == "posix":
                # A wrapper may have spawned children that retain the pipes.
                # The session belongs to this runner, not the user's shell.
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif self.process.poll() is None:
                self.process.kill()
            self.process.wait()
            self.requests.put(None)
            if self.worker is not None:
                self.worker.join(timeout=self.timeout)
            # Never take a text-stream lock from a still-blocked worker, even
            # if a hostile descendant escaped the owned process group.
            if self.worker is None or not self.worker.is_alive():
                if self.process.stdin is not None:
                    try:
                        self.process.stdin.close()
                    except BrokenPipeError:
                        # A failed flush leaves buffered input for close() to
                        # retry. The dead peer must not mask the protocol error
                        # or prevent closing the remaining streams.
                        pass
                if self.process.stdout is not None:
                    self.process.stdout.close()
            self.process = None
        if self.stderr is not None:
            self.stderr.close()
            self.stderr = None

    def run(self, case: Case) -> Outcome:
        process = self.process
        if process is None or process.stdin is None or process.stdout is None:
            raise ProtocolError("the Lean process is not running")
        self.requests.put(request_json(case))
        try:
            line = self.replies.get(timeout=self.timeout)
        except Empty:
            self.close()
            raise ProtocolError(f"Lean request timed out after {self.timeout:g}s") from None
        if isinstance(line, Exception):
            reason = self._death()
            self.close()
            raise ProtocolError(f"the Lean process went away: {reason}") from line
        if not line:
            reason = self._death()
            self.close()
            raise ProtocolError(f"no reply: {reason}")
        try:
            return parse_reply(line.rstrip("\n"))
        except ProtocolError:
            self.close()
            raise

    def _death(self) -> str:
        """Why the process stopped, from its exit status and stderr."""
        assert self.process is not None and self.stderr is not None
        try:
            code = self.process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            return "closed its protocol stream without exiting"
        self.stderr.seek(0)
        err = self.stderr.read().decode(errors="replace").strip()
        return f"exit {code}" + (f": {err}" if err else "")

    @staticmethod
    def probe(
        command: Sequence[str | Path], program_json: Path, ports: int = 4, *, timeout: float = 10
    ) -> str | None:
        """None when `command` accepts `run` on the program and exits cleanly
        at end of input; otherwise why not, for the executable gate."""
        try:
            with LeanRunner(command, program_json, ports, timeout=timeout):
                pass
        except ProtocolError as e:
            return str(e)
        return None


def compare_cases(
    program: str,
    loaded: arch.Loaded,
    cases: Sequence[Case],
    ports: int,
    run_lean: Callable[[Case], Outcome],
    seed: int = 0,
) -> Report:
    """Run every case on both sides, in order, and collect the divergences."""
    frozen_program = assembly_of(loaded.index.program, loaded.bindings)
    inputs = tuple(
        Case(pb.Entries.FromString(c.entries.SerializeToString()), c.ingress_port, c.packet)
        for c in cases
    )
    report = Report(program, seed, ports, inputs=inputs, program_ir=frozen_program)
    for number, case in enumerate(inputs):
        python = python_outcome(loaded, case, ports)
        try:
            lean = run_lean(case)
        except ProtocolError as e:
            report.protocol_error = str(e)
            e.report = report
            raise
        report.cases += 1
        report.rule_coverage.add(lean.coverage)
        if python.error is not None and lean.error is not None:
            report.both_errored += 1
        if not python.agrees_with(lean):
            report.divergences.append(Divergence(number, case, python, lean))
    return report


def compare(
    program_dir: Path,
    seed: int,
    count: int,
    ports: int,
    lean: Sequence[str | Path],
) -> Report:
    """`count` random cases of the corpus program in `program_dir`, on the
    Python reference and on `lean` (the executable and leading arguments)."""
    program = arch_wire.load_text(program_dir / f"{program_dir.name}.txtpb")
    loaded = arch.reference.load(program)
    cases = generate(loaded.index, seed, count, ports)
    return compare_program(program, cases, ports, lean, seed)


def compare_program(
    program: apb.BlockAssembly,
    cases: Sequence[Case],
    ports: int,
    lean: Sequence[str | Path],
    seed: int = 0,
) -> Report:
    """Compare concrete inputs from fresh state, retaining every peer failure."""
    loaded = arch.reference.load(program)
    with tempfile.TemporaryDirectory() as tmp:
        program_json = Path(tmp) / "program.json"
        program_json.write_text(arch_wire.dump_json(program))
        report: Report | None = None
        try:
            with LeanRunner(lean, program_json, ports) as runner:
                report = compare_cases(program.name, loaded, cases, ports, runner.run, seed)
        except ProtocolError as e:
            if e.report is None:
                e.report = report or Report(
                    program.name,
                    seed,
                    ports,
                    inputs=tuple(cases),
                    program_ir=program,
                    protocol_error=str(e),
                )
                e.report.protocol_error = str(e)
            raise
        return report


def default_lean_binary() -> Path:
    """Where `lake build` leaves the executable, relative to this checkout.

    This file is impl/python/p4blo/drt/run.py, four levels below the root; the
    endpoint belongs to the reference architecture package.
    """
    root = Path(__file__).resolve().parents[4]
    return (
        root
        / "spec"
        / "arch"
        / ".lake"
        / "build"
        / "bin"
        / ("p4blo-lean" + (".exe" if os.name == "nt" else ""))
    )
