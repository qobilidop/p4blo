"""Replay corpus vectors on BMv2's simple_switch, the second oracle for claim 2.

    uv run python oracle/bmv2/run.py corpus/forwarder/forwarder.txtpb corpus/forwarder/*.stf

The program is printed with `p4blo.printer.print_program` under the v1model
shim and compiled once with `p4c-bm2-ss prog.p4 -o prog.json` inside the
`p4blo-bmv2` Docker image (oracle/bmv2/Dockerfile). Each vector is then
translated (see `translate`) into runs of simple_switch: `add` and
`setdefault` lines become `simple_switch_CLI` commands, `packet` lines
become pcap records, and the image's driver (oracle/bmv2/driver.py) plays
them the way p4c's own backends/bmv2/bmv2stf.py does, through `--use-files`.
The outputs come back per port and are compared with the `expect` lines
under p4blo's rules (`stf.Expect.matches`: a prefix unless `$`, `*` nibbles).
The verdict per vector is one of

    pass    every expectation was met, in order, and nothing else came out;
    fail    a divergence: an output differs from an expectation, an expected
            packet never came, or an unexpected one did;
    error   the oracle could not judge: p4c-bm2-ss rejected the program, a
            CLI command was refused, the switch crashed or timed out, Docker
            failed;
    skip    the vector's program uses `flood`, which the shim cannot express.

The process exits non-zero on any fail or error. The image is named by
`$P4BLO_BMV2_IMAGE`, default `p4blo-bmv2`.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# Runnable as a script from the repository root without installing anything:
# the package lives under python/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "python"))

from p4blo import ir, printer, stf  # noqa: E402
from p4blo.v0 import p4blo_pb2 as pb  # noqa: E402

__all__ = [
    "DEFAULT_IMAGE",
    "Compiled",
    "OracleError",
    "Phase",
    "Plan",
    "Verdict",
    "compile_program",
    "default_image",
    "judge",
    "main",
    "render",
    "run",
    "translate",
    "unavailable",
    "uses_flood",
]

DEFAULT_IMAGE = "p4blo-bmv2"
# p4c's bmv2stf.py inverts an STF priority as `10000 - prio`, because STF
# and p4blo have the larger priority winning and BMv2 the smaller.
PRIORITY_BASE = 10000
# One `docker run`; the driver has its own, shorter, bounds per step.
DOCKER_TIMEOUT = 600
_DOCKER_EXIT_CODES = {125, 126, 127}


class OracleError(Exception):
    """The oracle could not judge: not a divergence."""


def default_image() -> str:
    return os.environ.get("P4BLO_BMV2_IMAGE") or DEFAULT_IMAGE


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------


@functools.cache
def unavailable(image: str | None = None) -> str | None:
    """Why the oracle cannot run here, or None when it can."""
    image = image or default_image()
    if shutil.which("docker") is None:
        return "docker is not installed"
    try:
        probe = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"docker did not run: {e}"
    if probe.returncode != 0:
        return f"the {image} image is not built: docker build -t {image} oracle/bmv2"
    try:
        probe = subprocess.run(
            ["docker", "run", "--rm", image, "p4blo-bmv2-driver", "--version"],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"docker did not run: {e}"
    if probe.returncode != 0:
        return f"{image} did not run: {probe.stderr.strip()}"
    return None


def _docker_command(image: str, command: str) -> tuple[str, ...]:
    return ("docker", "run", "--rm", "-i", image, "p4blo-bmv2-driver", command)


def _driver(image: str, command: str, stdin: str) -> dict:
    """Run one driver command in the container, JSON in and out."""
    argv = _docker_command(image, command)
    try:
        result = subprocess.run(
            argv, input=stdin, capture_output=True, text=True, timeout=DOCKER_TIMEOUT
        )
    except subprocess.TimeoutExpired as e:
        raise OracleError(f"docker did not finish in {DOCKER_TIMEOUT}s") from e
    except OSError as e:
        raise OracleError(f"could not run docker: {e}") from e
    if result.returncode != 0:
        what = "docker" if result.returncode in _DOCKER_EXIT_CODES else "the driver"
        raise OracleError(
            f"{what} exited with code {result.returncode}:\n{result.stderr.strip()[-2000:]}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise OracleError(f"the driver's output is not JSON: {result.stdout[-500:]!r}") from e


# ---------------------------------------------------------------------------
# The compiled program
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Compiled:
    """A program as p4c-bm2-ss compiled it: the BMv2 JSON and the compiler's
    warnings. Table and action names in BMv2 are p4c's, the printed name
    prefixed with the control's (`MyIngress.ipv4_lpm`), so they are looked
    up here rather than guessed."""

    json: dict
    output: str

    def tables(self) -> list[dict]:
        return [t for pipeline in self.json.get("pipelines", []) for t in pipeline["tables"]]

    def find_table(self, block: str, name: str) -> dict:
        """The JSON table for an IR table declared in `block`."""
        tables = self.tables()
        exact = [t for t in tables if t["name"] in (f"{block}.{name}", name)]
        if len(exact) == 1:
            return exact[0]
        found = exact or [t for t in tables if t["name"].endswith(f".{name}")]
        if len(found) == 1:
            return found[0]
        names = ", ".join(t["name"] for t in found) or "nothing"
        raise OracleError(f"table {block}.{name} in the BMv2 JSON matches {names}")

    def find_action(self, table: dict, block: str, name: str) -> str:
        """The JSON name of an action a table may run."""
        allowed = list(table["actions"])
        exact = [a for a in allowed if a in (f"{block}.{name}", name)]
        if len(exact) == 1:
            return exact[0]
        found = exact or [a for a in allowed if a.endswith(f".{name}")]
        if len(found) == 1:
            return found[0]
        names = ", ".join(found) or "nothing"
        raise OracleError(f"action {name} of table {table['name']} matches {names} in the JSON")


def compile_program(image: str, p4: str) -> Compiled:
    reply = _driver(image, "compile", p4)
    if not reply.get("ok"):
        raise OracleError(f"p4c-bm2-ss rejected the printed program:\n{reply.get('output', '')}")
    return Compiled(reply["json"], reply.get("output", ""))


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------


@dataclass
class Phase:
    """One run of simple_switch: the CLI commands installed before any of
    its packets, then the packets and what the vector claims about them."""

    commands: list[str] = field(default_factory=list)
    lines: list[int] = field(default_factory=list)  # the vector line per command
    packets: list[stf.Packet] = field(default_factory=list)
    expects: list[stf.Expect] = field(default_factory=list)
    no_packets: list[stf.NoPacket] = field(default_factory=list)


@dataclass
class Plan:
    phases: list[Phase]
    ports: list[int]
    notes: list[str]

    def request(self, compiled: Compiled) -> dict:
        return {
            "json": compiled.json,
            "ports": self.ports,
            "phases": [
                {
                    "commands": phase.commands,
                    "packets": [{"port": p.port, "data": p.data.hex()} for p in phase.packets],
                }
                for phase in self.phases
            ],
        }


_MATCH_KINDS = {
    pb.MATCH_KIND_EXACT: "exact",
    pb.MATCH_KIND_LPM: "lpm",
    pb.MATCH_KIND_TERNARY: "ternary",
}


def render(index: ir.Index, compiled: Compiled, statement: stf.Add | stf.SetDefault) -> str:
    """One `add` or `setdefault` as a simple_switch_CLI command.

    The statement is resolved by p4blo's own STF machinery first
    (`stf.to_entries`), so names, widths, match kinds and the presence of a
    priority are checked exactly as the reference replay checks them, and
    the command is rendered from the resolved entry: keys in the table's
    declared order, which is the JSON's, action arguments in parameter
    order, values in hex (the CLI reads `0x` at any width) and arguments in
    decimal.

    Match kinds need no translation: BMv2 has lpm tables of its own, so a
    prefix is written `value/len` and the longest-prefix rule is the
    switch's, not this file's. A ternary entry's priority is inverted as
    p4c's runner inverts it, `10000 - priority`, because BMv2 has the
    smaller priority winning; the CLI takes the priority only on a table
    whose JSON match type is ternary, which is exactly when p4blo requires
    one.
    """
    block, table = stf._find_table(index, statement.table, statement.line)
    resolved = stf.to_entries(index, [statement]).tables[0]
    json_table = compiled.find_table(block, table.name)
    if isinstance(statement, stf.SetDefault):
        call = resolved.default_action
        action = compiled.find_action(json_table, block, call.action)
        args = " ".join(str(int(arg.bits.value)) for arg in call.args)
        return f"table_set_default {json_table['name']} {action} {args}".rstrip()
    entry = resolved.entries[0]
    json_keys = json_table["key"]
    if len(json_keys) != len(entry.keys):
        raise OracleError(
            f"{json_table['name']} has {len(json_keys)} key fields in the JSON, "
            f"{len(entry.keys)} in the IR"
        )
    keys: list[str] = []
    for position, (key, json_key, value) in enumerate(
        zip(table.keys, json_keys, entry.keys, strict=True)
    ):
        kind = _MATCH_KINDS.get(key.match_kind)
        if json_key["match_type"] != kind:
            raise OracleError(
                f"key {position} of {json_table['name']} is {json_key['match_type']} in the "
                f"JSON, {kind} in the IR"
            )
        match value.WhichOneof("kind"):
            case "exact":
                keys.append(f"0x{int(value.exact):x}")
            case "lpm":
                keys.append(f"0x{int(value.lpm.value):x}/{value.lpm.prefix_len}")
            case "ternary":
                keys.append(f"0x{int(value.ternary.value):x}&&&0x{int(value.ternary.mask):x}")
            case other:
                raise OracleError(f"cannot render a {other} key for BMv2")
    action = compiled.find_action(json_table, block, entry.action.action)
    args = " ".join(str(int(arg.bits.value)) for arg in entry.action.args)
    command = f"table_add {json_table['name']} {action} {' '.join(keys)} => {args}".rstrip()
    ternary = any(k.match_kind == pb.MATCH_KIND_TERNARY for k in table.keys)
    if json_table["match_type"] in ("ternary", "range"):
        if not ternary:
            raise OracleError(
                f"{json_table['name']} is a {json_table['match_type']} table for BMv2, which "
                "needs a priority the IR does not have"
            )
        if entry.priority > PRIORITY_BASE:
            raise OracleError(
                f"line {statement.line}: priority {entry.priority} exceeds {PRIORITY_BASE}, "
                "p4c's inversion base for BMv2"
            )
        command += f" {PRIORITY_BASE - entry.priority}"
    elif ternary:
        raise OracleError(
            f"{json_table['name']} has a ternary key but is a {json_table['match_type']} "
            "table for BMv2"
        )
    return command


def uses_flood(index: ir.Index) -> bool:
    """Whether the program's metadata contract has `flood`, which the v1model
    shim leaves unmapped (printer.standard_metadata_binding), so BMv2 would
    not see the decision."""
    return any(f.name == "flood" for f in index.fields(index.program.metadata))


def translate(index: ir.Index, statements: Sequence[stf.Statement], compiled: Compiled) -> Plan:
    """Cut a vector into simple_switch runs.

    Every `add`/`setdefault` becomes a CLI command in the current phase;
    the first one after a `packet` opens a new phase, because a run's
    entries all go in before its packets (the pcap reader cannot be paused
    between packets), and the new phase repeats the earlier commands so the
    entries accumulate as the vector wrote them. A fresh switch has fresh
    registers and counters, so a program with extern state is refused when
    it would need more than one phase: the oracle would not be replaying
    the vector. `wait` does nothing. `no_packet` and `expect` are kept with
    their phase for the judge.

    Returns the plan and a note per command, with its vector line.
    """
    phases = [Phase()]
    notes: list[str] = []
    ports: set[int] = {0}
    for statement in statements:
        match statement:
            case stf.Add() | stf.SetDefault():
                if phases[-1].packets:
                    phases.append(
                        Phase(commands=list(phases[-1].commands), lines=list(phases[-1].lines))
                    )
                    notes.append(
                        f"line {statement.line}: entries after a packet, so a new "
                        f"simple_switch run (number {len(phases)}) with the entries so far"
                    )
                command = render(index, compiled, statement)
                phases[-1].commands.append(command)
                phases[-1].lines.append(statement.line)
                notes.append(f"line {statement.line}: `{command}`")
            case stf.Packet():
                phases[-1].packets.append(statement)
                ports.add(statement.port)
            case stf.Expect():
                if not phases[-1].packets:
                    raise stf.StfError(f"line {statement.line}: expect before any packet")
                phases[-1].expects.append(statement)
                ports.add(statement.port)
            case stf.NoPacket():
                if not phases[-1].packets:
                    raise stf.StfError(f"line {statement.line}: no_packet before any packet")
                phases[-1].no_packets.append(statement)
            case stf.Wait():
                pass
    if len(phases) > 1 and index.program.extern_instances:
        names = ", ".join(e.name for e in index.program.extern_instances)
        raise OracleError(
            f"the vector adds entries after packets, which takes {len(phases)} simple_switch "
            f"runs, but the program's state ({names}) would not carry from one to the next"
        )
    return Plan(phases, sorted(ports), notes)


# ---------------------------------------------------------------------------
# Judging
# ---------------------------------------------------------------------------


def judge(plan: Plan, reply: dict) -> tuple[str, str]:
    """Compare the driver's outputs with the vector, phase by phase.

    Within a phase the outputs of a port must be, in order, exactly the
    `expect` lines written for that port, each matched under p4blo's rules,
    and no port may carry anything else. That is p4c's per-port matching
    made strict about leftovers; unlike the reference replay it cannot say
    which input packet an output came from, since this BMv2 build logs
    nothing per packet, so a wrong output that happens to equal a later
    expectation on the same port is not caught (oracle/bmv2/README.md).
    """
    failures: list[stf.Failure] = []
    results = reply.get("phases", [])
    for number, phase in enumerate(plan.phases):
        if number >= len(results):
            return "error", f"the driver returned no result for run {number + 1}"
        result = results[number]
        if result.get("error"):
            return "error", f"run {number + 1}: {result['error']}\n{result.get('log', '')}".strip()
        outputs = {
            int(port): [bytes.fromhex(h) for h in hexes]
            for port, hexes in result["outputs"].items()
        }
        for port in sorted(set(outputs) | {e.port for e in phase.expects}):
            got = outputs.get(port, [])
            expected = [e for e in phase.expects if e.port == port]
            for expect, data in zip(expected, got, strict=False):
                if not expect.matches(data):
                    failures.append(
                        stf.Failure(
                            expect.line,
                            f"expected {stf._hex(expect.data, expect.mask)}"
                            f"{' $' if expect.exact else ''} on port {port}, got {data.hex()}",
                        )
                    )
            for expect in expected[len(got) :]:
                failures.append(stf.Failure(expect.line, f"no output packet on port {port}"))
            for data in got[len(expected) :]:
                line = (phase.no_packets or phase.packets)[-1].line
                failures.append(
                    stf.Failure(line, f"unexpected output on port {port}: {data.hex()}")
                )
    if failures:
        failures.sort(key=lambda f: f.line)
        return "fail", "\n".join(str(f) for f in failures)
    return "pass", ""


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    vector: Path
    status: str  # "pass" | "fail" | "error" | "skip"
    detail: str
    command: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __str__(self) -> str:
        head = f"{self.status.upper():5} {self.vector}"
        return head if self.status == "pass" else f"{head}\n{_indent(self.detail)}"


def _indent(text: str) -> str:
    return "\n".join(f"    {line}" for line in text.strip().splitlines())


def run_vector(image: str, index: ir.Index, compiled: Compiled, vector: Path) -> Verdict:
    command = _docker_command(image, "replay")
    try:
        statements = stf.parse(vector.read_text())
        plan = translate(index, statements, compiled)
    except stf.StfError as e:
        return Verdict(vector, "error", f"p4blo cannot resolve the vector: {e}", command)
    except OracleError as e:
        return Verdict(vector, "error", str(e), command)
    notes = tuple(plan.notes)
    try:
        reply = _driver(image, "replay", json.dumps(plan.request(compiled)))
    except OracleError as e:
        return Verdict(vector, "error", str(e), command, notes)
    status, detail = judge(plan, reply)
    if status == "pass":
        detail = "\n".join(r.get("cli", "") for r in reply["phases"]).strip()
    return Verdict(vector, status, detail, command, notes)


def run(image: str, program: Path, vectors: list[Path]) -> list[Verdict]:
    """Print and compile the program once and run every vector against it."""
    index = ir.Index.build(ir.load_text(program))
    if uses_flood(index):
        detail = "the program uses flood, which the v1model shim cannot express for BMv2"
        return [Verdict(vector, "skip", detail, ()) for vector in vectors]
    p4 = printer.print_program(index.program, index=index)
    command = _docker_command(image, "compile")
    try:
        compiled = compile_program(image, p4)
    except OracleError as e:
        return [Verdict(vector, "error", str(e), command) for vector in vectors]
    return [run_vector(image, index, compiled, vector) for vector in vectors]


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="oracle/bmv2/run.py", description="replay STF vectors on BMv2's simple_switch"
    )
    parser.add_argument("program", type=Path, help="the program, in IR text format (.txtpb)")
    parser.add_argument("vectors", type=Path, nargs="+", help="STF vector files")
    parser.add_argument("--image", default=default_image(), help="the Docker image to run")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show the translation and the CLI's output"
    )
    args = parser.parse_args(argv)

    reason = unavailable(args.image)
    if reason is not None:
        print(reason, file=sys.stderr)
        return 2

    verdicts = run(args.image, args.program, list(args.vectors))
    for verdict in verdicts:
        print(verdict)
        if args.verbose:
            for note in verdict.notes:
                print(f"    note: {note}")
            if verdict.status == "pass" and verdict.detail:
                print(_indent(verdict.detail))
    failed = [v for v in verdicts if v.status in ("fail", "error")]
    skipped = [v for v in verdicts if v.status == "skip"]
    if failed:
        print(f"\n{len(failed)} of {len(verdicts)} vector(s) did not pass; the command was")
        print(f"    {shlex.join(failed[0].command)}")
        return 1
    print(f"\nall {len(verdicts) - len(skipped)} vector(s) passed, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
