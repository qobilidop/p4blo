"""Replay corpus vectors on P4-SpecTec's simulator, the oracle for claim 2.

    uv run python tests/oracle/run.py <program.txtpb> <vectors.stf>

For each vector file: the program is printed with `p4blo.arch.v1model.print_program`
into a temporary directory, the vector is translated into the STF dialect the
simulator reads (see `translate`; the `add` lines are re-rendered at the
program's key widths), and

    p4spectec sim spec -arch v1model -i p4c/p4include -p prog.p4 -stf vec.stf

runs from the P4-SpecTec checkout. The verdict per vector is one of

    pass    the simulator matched every expectation and nothing was left over;
    fail    a divergence: an output differs from an expectation, an expected
            packet never came, or an unexpected one did;
    error   the oracle could not judge: a construct the simulator does not
            support, a syntax error in the printed program or the vector, a
            crash, a timeout.

The process exits non-zero on any verdict but pass. The binary is found via
`$P4BLO_ORACLE_BIN`, else `$P4BLO_ORACLE_DIR/p4spectec`, else the default
directory of tests/oracle/build.sh; the spec and the include directory are taken
from the checkout the binary sits in.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex

# Runnable as a script from the repository root without installing anything:
# the package lives under impl/python/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "impl" / "python"))

from p4blo import ir, stf  # noqa: E402
from p4blo.arch import v1model  # noqa: E402
from p4blo.v0 import p4blo_pb2 as pb  # noqa: E402

__all__ = [
    "DEFAULT_ORACLE_DIR",
    "Oracle",
    "Verdict",
    "find_oracle",
    "main",
    "render_masked",
    "run",
    "run_vector",
    "translate",
]

DEFAULT_ORACLE_DIR = Path.home() / ".cache" / "p4blo" / "p4-spectec"
ARCH = "v1model"
# The simulator elaborates the whole spec on every run, which takes a while
# before any packet moves; the limit is generous so that a slow CI runner is
# not mistaken for a hang.
TIMEOUT_SECONDS = 600


# ---------------------------------------------------------------------------
# Locating the oracle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Oracle:
    """A built P4-SpecTec checkout: the binary, its spec and its p4include."""

    binary: Path
    root: Path

    @property
    def spec(self) -> Path:
        return self.root / "spec"

    @property
    def include(self) -> Path:
        return self.root / "p4c" / "p4include"

    def missing(self) -> str | None:
        """Why this checkout cannot run, or None when it can."""
        if not os.access(self.binary, os.X_OK):
            return f"{self.binary} is not an executable"
        if not self.spec.is_dir():
            return f"{self.spec} is not a directory; is {self.root} a P4-SpecTec checkout?"
        if not (self.include / "v1model.p4").is_file():
            return f"{self.include} has no v1model.p4; tests/oracle/build.sh fetches it"
        return None


def find_oracle(environ: dict[str, str] | None = None) -> Oracle | None:
    """The oracle the environment points at, or None when nothing is built.

    `$P4BLO_ORACLE_BIN` names the binary directly; its checkout is the
    directory it sits in, which is where `make build` links it. Otherwise
    the binary is `p4spectec` under `$P4BLO_ORACLE_DIR`, defaulting to where
    tests/oracle/build.sh puts it.
    """
    env = os.environ if environ is None else environ
    bin_var = env.get("P4BLO_ORACLE_BIN")
    if bin_var:
        binary = Path(bin_var).expanduser().resolve()
        oracle = Oracle(binary, binary.parent)
    else:
        root = Path(env.get("P4BLO_ORACLE_DIR") or DEFAULT_ORACLE_DIR).expanduser().resolve()
        oracle = Oracle(root / "p4spectec", root)
    return oracle if oracle.binary.is_file() else None


# ---------------------------------------------------------------------------
# STF translation
# ---------------------------------------------------------------------------


def translate(text: str, index: ir.Index) -> tuple[str, list[str]]:
    """Rewrite a p4blo vector file into what `p4spectec sim` reads.

    p4blo's dialect (impl/python/p4blo/stf.py) is a subset of p4c's, and the
    simulator's grammar (p4spec/lib/stf/parser.mly) parses all of it, but
    its runner gives two things a different meaning:

    - `no_packet` is rejected as "not yet supported". The simulator checks at
      the end of the file that no output was left unclaimed and no
      expectation unmet, which is what `no_packet` asserts here, so the line
      is dropped and that check carries the assertion.
    - An lpm key written `value/len` is not p4c's full-width value with a
      prefix length: the spec (9.1-table-interface.watsup, the `_SLASH`
      rule) reverses the value's bytes and shifts it up by the remaining
      width, which fits only p4c's `lpm_ebpf.stf`. The wildcard forms,
      `0x0a0002**` and `0b0000101000...********`, are read as p4c reads
      them, provided they are written at the key's full width, because the
      simulator casts value and mask to the key type and would zero-extend
      a shorter mask.

    - Longest prefix does not win by itself: the spec matches an lpm entry
      as a ternary one and, when several entries match, picks the largest
      priority, failing if any match has none. An `add` on a table with an
      lpm key and no ternary key therefore gets its prefix length as its
      priority, which is p4testgen's convention too.

    So every `add` and `setdefault` is re-rendered from its parsed form at
    the program's key widths, hex where the mask is nibble-aligned and
    binary otherwise, and with decimal action arguments; the line's comment
    goes. Everything else passes through verbatim. The file is resolved
    against the program first (`stf.to_entries`), so a vector p4blo itself
    would refuse never reaches the oracle.

    Returns the translated text and a note per line that changed.
    """
    rewrites: dict[int, str | None] = {}
    for statement in stf.parse(text):
        match statement:
            case stf.NoPacket():
                rewrites[statement.line] = None
            case stf.Add() | stf.SetDefault():
                # Resolving validates names, widths and match kinds the way
                # the reference replay does.
                stf.to_entries(index, [statement])
                rewrites[statement.line] = _render_table_update(index, statement)
            case _:
                pass
    out: list[str] = []
    notes: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if number not in rewrites:
            out.append(line)
            continue
        rendered = rewrites[number]
        if rendered is None:
            out.append("# no_packet (dropped for P4-SpecTec; its end-of-run check asserts it)")
            notes.append(f"line {number}: dropped no_packet")
            continue
        out.append(rendered)
        if rendered != " ".join(line.split("#", 1)[0].split()):
            notes.append(f"line {number}: rewritten as `{rendered}`")
    return "\n".join(out) + "\n", notes


def _render_table_update(index: ir.Index, statement: stf.Add | stf.SetDefault) -> str:
    # These two helpers are the vector module's own name resolution and key
    # typing; the oracle borrows them so it renders exactly what the
    # reference replay resolved.
    block, table = stf._find_table(index, statement.table, statement.line)
    args = ", ".join(f"{arg.name}:{arg.value}" for arg in statement.args)
    call = f"{statement.action}({args})"
    if isinstance(statement, stf.SetDefault):
        return f"setdefault {statement.table} {call}"
    keys = {stf.key_name(k): k for k in table.keys}
    rendered: list[str] = []
    priority = statement.priority
    for written in statement.keys:
        key = keys[written.name]
        width = stf._key_width(index, block, key)
        text, prefix = _render_key(written, key.match_kind, width)
        rendered.append(f"{written.name}:{text}")
        if priority is None and prefix is not None:
            # The simulator has no longest-prefix rule: an lpm entry is a
            # ternary match, and among several matches only the priority
            # decides, largest first, failing when one is missing
            # (8.09.1-eval-control-table.watsup, $select_action). The prefix
            # length as priority is the lpm rule spelled out for it, as
            # p4testgen's vectors do; p4blo forbids a written priority on a
            # table without a ternary key, so nothing is overridden.
            priority = prefix
    parts = ["add", statement.table]
    if priority is not None:
        parts.append(str(priority))
    return " ".join([*parts, *rendered, call])


def _render_key(written: stf.Key, match_kind: int, width: int) -> tuple[str, int | None]:
    """One key value as value-and-mask digits at the key's full width, and
    the prefix length when the key is lpm."""
    full = (1 << width) - 1
    prefix: int | None = None
    if match_kind == pb.MATCH_KIND_LPM:
        prefix = width if written.prefix_len is None else written.prefix_len
        mask = (full >> (width - prefix)) << (width - prefix)
    elif match_kind == pb.MATCH_KIND_TERNARY:
        mask = full if written.mask is None else written.mask
    else:
        mask = full
    return render_masked(written.value & mask, mask, width), prefix


def render_masked(value: int, mask: int, width: int) -> str:
    """`0x` digits with `*` for masked-out nibbles when every nibble of the
    mask is all or nothing, else `0b` digits with `*` per masked-out bit."""
    if width % 4 == 0:
        nibbles = [(value >> shift) & 0xF for shift in range(width - 4, -1, -4)]
        cares = [(mask >> shift) & 0xF for shift in range(width - 4, -1, -4)]
        if all(care in (0, 0xF) for care in cares):
            return "0x" + "".join(
                f"{nibble:x}" if care else "*" for nibble, care in zip(nibbles, cares, strict=True)
            )
    return "0b" + "".join(
        str((value >> bit) & 1) if (mask >> bit) & 1 else "*" for bit in range(width - 1, -1, -1)
    )


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Verdict:
    vector: Path
    status: str  # "pass" | "fail" | "error"
    detail: str
    command: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __str__(self) -> str:
        head = f"{self.status.upper():5} {self.vector}"
        return head if self.status == "pass" else f"{head}\n{_indent(self.detail)}"


def _indent(text: str) -> str:
    return "\n".join(f"    {line}" for line in text.strip().splitlines())


def _judge(result: subprocess.CompletedProcess[str]) -> tuple[str, str]:
    """Classify the simulator's output into a status and a detail."""
    out = result.stdout.strip()
    err = result.stderr.strip()
    both = "\n".join(part for part in (out, err) if part)
    if result.returncode == 0 and out.splitlines()[-1:] == ["passed"]:
        return "pass", out
    # A mismatch is reported by the STF runner as "expected (port) hex but
    # got (port) hex"; leftovers at the end of the file as "[FAIL] ...".
    if "[FAIL]" in both or ("expected " in both and " but got " in both):
        return "fail", both
    return "error", both or f"exit code {result.returncode} with no output"


def run_vector(
    oracle: Oracle, index: ir.Index, program_p4: Path, vector: Path, workdir: Path
) -> Verdict:
    """Run one vector file against an already printed program."""
    text = vector.read_text()
    try:
        translated, notes = translate(text, index)
    except stf.StfError as e:
        return Verdict(vector, "error", f"p4blo cannot resolve the vector: {e}", (), ())
    stf_path = workdir / vector.name
    stf_path.write_text(translated)
    command = (
        str(oracle.binary),
        "sim",
        str(oracle.spec),
        "-arch",
        ARCH,
        "-i",
        str(oracle.include),
        "-p",
        str(program_p4),
        "-stf",
        str(stf_path),
    )
    try:
        result = subprocess.run(
            command,
            cwd=oracle.root,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return Verdict(
            vector,
            "error",
            f"the oracle did not finish in {TIMEOUT_SECONDS}s",
            command,
            tuple(notes),
        )
    except OSError as e:
        return Verdict(vector, "error", f"could not run the oracle: {e}", command, tuple(notes))
    status, detail = _judge(result)
    return Verdict(vector, status, detail, command, tuple(notes))


def run(oracle: Oracle, program: Path, vectors: list[Path]) -> list[Verdict]:
    """Print the program once and run every vector against it."""
    index = BoundIndex.build(arch_wire.load_text(program))
    p4 = v1model.print_program(index.program, index=index)
    with tempfile.TemporaryDirectory(prefix="p4blo-oracle-") as tmp:
        workdir = Path(tmp)
        program_p4 = workdir / f"{program.stem}.p4"
        program_p4.write_text(p4)
        return [run_vector(oracle, index, program_p4, vector, workdir) for vector in vectors]


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tests/oracle/run.py", description="replay STF vectors on P4-SpecTec's simulator"
    )
    parser.add_argument("program", type=Path, help="the program, in IR text format (.txtpb)")
    parser.add_argument("vectors", type=Path, nargs="+", help="STF vector files")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show the simulator's output for passes too"
    )
    args = parser.parse_args(argv)

    oracle = find_oracle()
    if oracle is None:
        print(
            "no p4spectec binary: run tests/oracle/build.sh, "
            "or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR",
            file=sys.stderr,
        )
        return 2
    reason = oracle.missing()
    if reason is not None:
        print(reason, file=sys.stderr)
        return 2

    verdicts = run(oracle, args.program, list(args.vectors))
    for verdict in verdicts:
        print(verdict)
        if args.verbose and verdict.status == "pass":
            print(_indent(verdict.detail))
        for note in verdict.notes:
            print(f"    note: {note}")
    failed = [v for v in verdicts if v.status != "pass"]
    if failed:
        print(f"\n{len(failed)} of {len(verdicts)} vector(s) did not pass; the command was")
        print(f"    {shlex.join(failed[0].command)}")
        return 1
    print(f"\nall {len(verdicts)} vector(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
