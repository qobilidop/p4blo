"""Run cases on Python and on Lean, and compare.

## The pipe protocol

`p4blo-lean run [--ports N] <program.json>` reads one JSON object per
line from stdin and writes one per line to stdout:

    request:  {"entries": <pb.Entries as protobuf JSON, proto field names>,
               "ingress_port": n, "packet": "<hex>"}
    reply:    {"outputs": [[port, "<hex>"], ...], "diagnostic": "..."}
              or   {"error": "..."}

`diagnostic` is present when the architecture dropped the packet for a
reason the program did not decide (a misaligned parse, an egress port the
switch does not have); on the Python side it is `Switch.diagnostics`.
Extern state persists across the requests of one process, as it does in
one `Loaded` on the Python side, so both sides see the same case sequence
from the same fresh state. Anything else on stdout, or a reply that does
not parse, is a `ProtocolError`: the harness never guesses.

## Agreement

Two sides agree on a case when their outputs are equal as sequences of
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
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import IO

from google.protobuf import json_format

from p4blo import arch, ir
from p4blo.drt.case import Case
from p4blo.drt.generate import generate

__all__ = [
    "Divergence",
    "LeanRunner",
    "Outcome",
    "ProtocolError",
    "Report",
    "compare",
    "compare_cases",
    "normalize_error",
    "run_python",
]


class ProtocolError(Exception):
    """The Lean side did not speak the protocol: it could not be started,
    it exited, or it replied with something that is neither outputs nor an
    error."""


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

    def agrees_with(self, other: Outcome) -> bool:
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
        return Outcome(error=f"{type(e).__name__}: {e}")
    diagnostic = "; ".join(switch.diagnostics) if switch.diagnostics else None
    return Outcome(outputs=tuple(outputs), diagnostic=diagnostic)


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
        reply = json.loads(line)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"reply is not JSON: {line!r}") from e
    if not isinstance(reply, dict):
        raise ProtocolError(f"reply is not an object: {line!r}")
    if "error" in reply:
        return Outcome(error=str(reply["error"]))
    if "outputs" not in reply or not isinstance(reply["outputs"], list):
        raise ProtocolError(f"reply has neither outputs nor error: {line!r}")
    outputs: list[tuple[int, bytes]] = []
    for item in reply["outputs"]:
        try:
            port, data = item
            outputs.append((int(port), bytes.fromhex(data)))
        except (TypeError, ValueError) as e:
            raise ProtocolError(f"bad output {item!r} in {line!r}") from e
    diagnostic = reply.get("diagnostic")
    if diagnostic is not None and not isinstance(diagnostic, str):
        raise ProtocolError(f"bad diagnostic {diagnostic!r} in {line!r}")
    return Outcome(outputs=tuple(outputs), diagnostic=diagnostic)


class LeanRunner:
    """A `p4blo-lean run` process, one case per round trip.

    `command` is the executable and any leading arguments; `run --ports N
    <program>` is appended. Use as a context manager so the process is
    always reaped.
    """

    def __init__(self, command: Sequence[str | Path], program_json: Path, ports: int) -> None:
        self.command = [str(c) for c in command] + ["run", "--ports", str(ports), str(program_json)]
        self.process: subprocess.Popen[str] | None = None
        self.stderr: IO[bytes] | None = None

    def __enter__(self) -> LeanRunner:
        self.stderr = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.stderr,
                text=True,
            )
        except OSError as e:
            self.close()
            raise ProtocolError(f"cannot start {self.command[0]}: {e}") from e
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self.process is not None:
            if self.process.stdin is not None:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
        if self.stderr is not None:
            self.stderr.close()
            self.stderr = None

    def run(self, case: Case) -> Outcome:
        process = self.process
        if process is None or process.stdin is None or process.stdout is None:
            raise ProtocolError("the Lean process is not running")
        try:
            process.stdin.write(request_json(case) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise ProtocolError(f"the Lean process went away: {self._death()}") from e
        line = process.stdout.readline()
        if not line:
            raise ProtocolError(f"no reply: {self._death()}")
        return parse_reply(line.rstrip("\n"))

    def _death(self) -> str:
        """Why the process stopped, from its exit status and stderr."""
        assert self.process is not None and self.stderr is not None
        code = self.process.wait(timeout=10)
        self.stderr.seek(0)
        err = self.stderr.read().decode(errors="replace").strip()
        return f"exit {code}" + (f": {err}" if err else "")

    @staticmethod
    def probe(command: Sequence[str | Path], program_json: Path, ports: int = 4) -> str | None:
        """None when `command` accepts `run` on the program and exits cleanly
        at end of input; otherwise why not, for a skip message."""
        argv = [str(c) for c in command] + ["run", "--ports", str(ports), str(program_json)]
        try:
            done = subprocess.run(
                argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return f"{argv[0]}: {e}"
        if done.returncode != 0:
            err = (done.stderr or done.stdout).strip().splitlines()
            return f"{argv[0]} run exited {done.returncode}" + (f": {err[0]}" if err else "")
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
    report = Report(program, seed, ports)
    for number, case in enumerate(cases):
        python = python_outcome(loaded, case, ports)
        lean = run_lean(case)
        report.cases += 1
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
    program = ir.load_text(program_dir / f"{program_dir.name}.txtpb")
    loaded = arch.load(program)
    cases = generate(loaded.index, seed, count, ports)
    with tempfile.TemporaryDirectory() as tmp:
        program_json = Path(tmp) / f"{program_dir.name}.json"
        program_json.write_text(ir.dump_json(program))
        with LeanRunner(lean, program_json, ports) as runner:
            return compare_cases(program_dir.name, loaded, cases, ports, runner.run, seed)


def default_lean_binary() -> Path:
    """Where `lake build` leaves the executable, relative to this checkout."""
    root = Path(__file__).resolve().parents[3]
    return (
        root
        / "lean"
        / ".lake"
        / "build"
        / "bin"
        / ("p4blo-lean" + (".exe" if os.name == "nt" else ""))
    )
