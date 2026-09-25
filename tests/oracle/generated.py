"""Generated programs and cases on P4-SpecTec's simulator.

    uv run python tests/oracle/generated.py --seeds 0:500 [--out DIR]

The corpus is a dozen hand-written programs; the differential tests against
Lean change the program itself. This module takes the same program families
to the oracle. A seed names one program and its cases exactly: the family is
`FAMILIES[seed % len(FAMILIES)]`, and everything else comes from
`random.Random(seed)`, through the constructors of `p4blo.drt.programs` and
`p4blo.drt.stateful_programs` (and the copy profiles of the DRT tests) and
through `p4blo.drt.generate` for packets. Hypothesis is not used, because its
draws are not a stable function of a seed across versions.

For each seed the program is validated and loaded, the Python interpreter
runs the cases in order, and its outputs become the `expect` lines of an STF
vector. The vector is replayed on Python first, to check that it says what
Python did, then translated and run on the simulator by `tests/oracle/run.py`,
the same path the corpus takes. A `fail` is a disagreement between the
interpreter and the oracle; an `error` means the oracle could not judge. Both
are reported with the seed and the directory that holds the inputs.

Every family observes its result through an emitted header whose total width
is a whole number of bytes. p4blo pads a deparser's bits to a byte boundary
before the payload, and the simulator does not (docs/ir-semantics.md,
"Deparsers"); since the simulator cannot take an empty packet, an unaligned
header would compare that choice on every case instead of the expression under
test. The padding field is assigned explicitly, so its bits are defined.
"""

from __future__ import annotations

import argparse
import random
import shlex
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

# Runnable as a script from the repository root without installing anything.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "impl" / "python"))
sys.path.insert(0, str(ROOT))

from p4blo import arch, ir, stf  # noqa: E402
from p4blo.arch import v1model  # noqa: E402
from p4blo.drt.case import Case, case_to_stf  # noqa: E402
from p4blo.drt.generate import generate  # noqa: E402
from p4blo.drt.programs import (  # noqa: E402
    binary,
    bits,
    boolean,
    parser_condition_program,
    scalar_program,
)
from p4blo.drt.run import Outcome, python_outcome  # noqa: E402
from p4blo.drt.stateful_programs import (  # noqa: E402
    UPDATE_OPS,
    StatefulSpec,
    stateful_program,
)
from p4blo.drt.stateful_programs import WIDTHS as STATEFUL_WIDTHS  # noqa: E402
from p4blo.drt.stateful_programs import packet as stateful_packet  # noqa: E402
from p4blo.interp.tables import InstalledEntries  # noqa: E402
from p4blo.v0 import p4blo_pb2 as pb  # noqa: E402
from tests.oracle import run as oracle_run  # noqa: E402

__all__ = [
    "DEFAULT_OUT",
    "FAMILIES",
    "Generated",
    "Result",
    "materialize",
    "prepare",
    "main",
    "run_generated",
    "run_seed",
]

DEFAULT_OUT = ROOT / ".artifacts" / "oracle" / "generated"
# Packets arrive on the few ports the DRT uses. They leave through a switch
# with ports 0 to 510, because v1model's ports are bit<9> and 511 is its drop
# port: any egress port a program computes is then the same port, or the
# same drop, on both sides.
PORTS = 4
SWITCH_PORTS = 511
CASES = 4
CORPUS = sorted(
    [
        *(ROOT / "tests" / "corpus").glob("*/*.txtpb"),
        *(ROOT / "tests" / "examples").glob("*/*.txtpb"),
    ]
)

# The same widths, operators and shapes as the Hypothesis strategy in
# tests/test_drt_programs.py.
WIDTHS = (1, 7, 8, 9, 16, 31, 32, 64, 65, 127)
ARITHMETIC = (
    pb.BINARY_OP_ADD,
    pb.BINARY_OP_SUB,
    pb.BINARY_OP_MUL,
    pb.BINARY_OP_ADD_SAT,
    pb.BINARY_OP_SUB_SAT,
    pb.BINARY_OP_BIT_AND,
    pb.BINARY_OP_BIT_OR,
    pb.BINARY_OP_BIT_XOR,
)
COMPARISONS = (
    pb.BINARY_OP_EQ,
    pb.BINARY_OP_NE,
    pb.BINARY_OP_LT,
    pb.BINARY_OP_LE,
    pb.BINARY_OP_GT,
    pb.BINARY_OP_GE,
)


@dataclass(frozen=True)
class Generated:
    """One seed's program and the requests sent to it, in order.

    `sequence` means the cases share extern state and go into one vector
    file; otherwise each case gets a file of its own and a fresh program,
    since host entries installed by one STF `add` persist to the end of the
    file on the simulator.
    """

    seed: int
    family: str
    description: str
    program: pb.Program
    cases: tuple[Case, ...]
    sequence: bool = False


# ---------------------------------------------------------------------------
# Scalar expressions
# ---------------------------------------------------------------------------


class Scalars:
    """Deterministic typed expressions, drawn as tests/test_drt_programs.py's
    `scalar` strategy draws them; `lookahead` adds packet reads as leaves,
    which only a parser may evaluate."""

    def __init__(self, rng: random.Random, lookahead: bool = False) -> None:
        self.rng = rng
        self.lookahead = lookahead

    def expr(self, width: int | None, depth: int = 3) -> pb.Expr:
        rng = self.rng
        kinds = ["leaf"] if depth == 0 else ["leaf", "unary", "binary", "cast", "mux"]
        if width is not None and depth:
            kinds += ["slice", "shift"]
            if width > 1:
                kinds.append("concat")
        kind = rng.choice(kinds)
        if kind == "leaf":
            return self.leaf(width)
        if kind == "unary":
            op = (
                pb.UNARY_OP_NOT
                if width is None
                else rng.choice([pb.UNARY_OP_COMPLEMENT, pb.UNARY_OP_NEGATE])
            )
            return pb.Expr(unary=pb.Unary(op=op, operand=self.expr(width, depth - 1)))
        if kind == "binary":
            if width is None:
                op = rng.choice([*COMPARISONS, pb.BINARY_OP_AND, pb.BINARY_OP_OR])
                operand = None if op in (pb.BINARY_OP_AND, pb.BINARY_OP_OR) else rng.choice(WIDTHS)
            else:
                op, operand = rng.choice(ARITHMETIC), width
            return binary(op, self.expr(operand, depth - 1), self.expr(operand, depth - 1))
        if kind == "cast":
            source = 1 if width is None else rng.choice(WIDTHS)
            target = pb.Type(boolean=pb.BoolType()) if width is None else pb.Type(bits=width)
            return pb.Expr(cast=pb.Cast(to=target, operand=self.expr(source, depth - 1)))
        if kind == "mux":
            return pb.Expr(
                mux=pb.Mux(
                    **{
                        "condition": self.expr(None, depth - 1),
                        "then": self.expr(width, depth - 1),
                        "otherwise": self.expr(width, depth - 1),
                    }
                )
            )
        assert width is not None
        if kind == "slice":
            lo = rng.randint(0, 16)
            extra = rng.randint(0, 16)
            operand = self.expr(width + lo + extra, depth - 1)
            return pb.Expr(slice=pb.Slice(operand=operand, hi=lo + width - 1, lo=lo))
        if kind == "shift":
            op = rng.choice([pb.BINARY_OP_SHL, pb.BINARY_OP_SHR])
            return binary(op, self.expr(width, depth - 1), self.expr(rng.choice(WIDTHS), depth - 1))
        left = rng.randint(1, width - 1)
        return binary(
            pb.BINARY_OP_CONCAT, self.expr(left, depth - 1), self.expr(width - left, depth - 1)
        )

    def leaf(self, width: int | None) -> pb.Expr:
        rng = self.rng
        if self.lookahead and rng.random() < 0.3:
            # A bool read is a cast of one bit, as the DRT's trap is.
            read = pb.Expr(lookahead=pb.Lookahead(type=pb.Type(bits=width or 1)))
            if width is None:
                return pb.Expr(cast=pb.Cast(to=pb.Type(boolean=pb.BoolType()), operand=read))
            return read
        if width is None:
            return boolean(rng.random() < 0.5)
        maximum = (1 << width) - 1
        edges = sorted({0, 1, maximum, maximum - 1, min(width, maximum)})
        value = rng.choice(edges) if rng.random() < 0.5 else rng.randint(0, maximum)
        return bits(width, value)


def byte_aligned(program: pb.Program) -> pb.Program:
    """Pad the one-field Result header of a scalar context to whole bytes.

    The pad is a separate field after the value, assigned zero right after
    the header is made valid, so the value's bits and position are
    unchanged and every emitted bit is defined.
    """
    header = program.header_types[0]
    width = sum(f.type.bits for f in header.fields)
    pad = -width % 8
    if pad:
        header.fields.add(name="pad", type=pb.Type(bits=pad))
        target = pb.LValue(
            member=pb.LMember(
                base=pb.LValue(member=pb.LMember(base=pb.LValue(var="hdr"), field="result")),
                field="pad",
            )
        )
        control = program.blocks[1]
        control.body.insert(1, pb.Stmt(assign=pb.Assign(target=target, value=bits(pad, 0))))
    return program


def _random_cases(program: pb.Program, rng: random.Random) -> tuple[Case, ...]:
    index = ir.Index.build(program)
    return tuple(generate(index, rng.getrandbits(32), CASES, PORTS))


def scalar_family(seed: int, rng: random.Random) -> Generated:
    width = rng.choice([None, *WIDTHS])
    expression = Scalars(rng).expr(width)
    program = byte_aligned(scalar_program(expression, width))
    kind = "bool" if width is None else f"bit<{width}>"
    return Generated(seed, "scalar", kind, program, _random_cases(program, rng))


def parser_condition_family(seed: int, rng: random.Random) -> Generated:
    condition = Scalars(rng, lookahead=True).expr(None)
    expected = rng.choice(["NoError", "NoMatch", "PacketTooShort"])
    program = byte_aligned(parser_condition_program(condition, expected))
    return Generated(
        seed, "parser_condition", f"== {expected}", program, _random_cases(program, rng)
    )


# ---------------------------------------------------------------------------
# Stateful programs
# ---------------------------------------------------------------------------


def stateful_family(seed: int, rng: random.Random) -> Generated:
    """A spec and a request sequence, drawn as tests/test_drt_stateful_programs.py's
    `campaigns` strategy draws them."""
    spec = StatefulSpec(
        width=rng.choice(STATEFUL_WIDTHS),
        register_size=rng.randint(1, 4),
        counter_size=rng.randint(1, 4),
        op=rng.choice(UPDATE_OPS),
        condition=rng.choice(("always", "nonzero", "old_lt_data")),
        write_order=rng.choice(("computed", "computed_then_data", "data_then_computed")),
        read_after_write=rng.random() < 0.5,
        count_updates=rng.random() < 0.5,
    )
    maximum = (1 << spec.width) - 1
    indices = [0, spec.register_size - 1, spec.register_size, spec.counter_size, 255]
    cases: list[Case] = []
    for i in range(rng.randint(2, 16)):
        index = rng.choice(indices) if rng.random() < 0.5 else rng.randint(0, 255)
        data = (
            rng.choice([0, 1, maximum - 1, maximum])
            if rng.random() < 0.5
            else rng.getrandbits(spec.width)
        )
        cases.append(Case(pb.Entries(), i % PORTS, stateful_packet(spec, index, data)))
    description = (
        f"bit<{spec.width}> reg[{spec.register_size}] ctr[{spec.counter_size}] "
        f"{pb.BinaryOp.Name(spec.op)} {spec.condition} {spec.write_order} "
        f"read_after_write={spec.read_after_write} count_updates={spec.count_updates}"
    )
    return Generated(
        seed, "stateful", description, stateful_program(spec), tuple(cases), sequence=True
    )


# ---------------------------------------------------------------------------
# Aggregate copies and calls
# ---------------------------------------------------------------------------


def aggregate_copy_family(seed: int, rng: random.Random) -> Generated:
    # The profile lives with its Hypothesis tests; it is a plain function.
    from tests.test_drt_aggregate_copy import WIDTHS as COPY_WIDTHS
    from tests.test_drt_aggregate_copy import CopyKind, copy_program

    kinds: tuple[CopyKind, ...] = ("header", "struct")
    kind = rng.choice(kinds)
    width = rng.choice(COPY_WIDTHS)
    valid = rng.random() < 0.5
    values = [rng.getrandbits(width) for _ in range(4)]
    program, _ = copy_program(kind, width, valid, *values)
    description = f"{kind} bit<{width}> valid={valid} values={values}"
    return Generated(seed, "aggregate_copy", description, program, _random_cases(program, rng))


def call_copy_family(seed: int, rng: random.Random) -> Generated:
    from tests.test_drt_call_copy import CallKind, call_program

    kinds: tuple[CallKind, ...] = ("action", "block")
    kind = rng.choice(kinds)
    width = rng.choice([8, 9, 65])
    valid = rng.random() < 0.5
    values = [rng.getrandbits(width) for _ in range(3)]
    program, _ = call_program(kind, width, valid, *values)
    description = f"{kind} bit<{width}> valid={valid} values={values}"
    return Generated(seed, "call_copy", description, program, _random_cases(program, rng))


def corpus_family(seed: int, rng: random.Random) -> Generated:
    """A corpus or example program with random entries and packets, as
    `python -m p4blo.drt` sends them to Lean."""
    path = rng.choice(CORPUS)
    program = ir.load_text(path)
    name = str(path.parent.relative_to(ROOT))
    return Generated(seed, "corpus", name, program, _random_cases(program, rng))


type Family = Callable[[int, random.Random], Generated]

FAMILIES: dict[str, Family] = {
    "scalar": scalar_family,
    "parser_condition": parser_condition_family,
    "stateful": stateful_family,
    "aggregate_copy": aggregate_copy_family,
    "call_copy": call_copy_family,
    "corpus": corpus_family,
}


def materialize(seed: int) -> Generated:
    """The program and cases a seed names."""
    names = list(FAMILIES)
    family = FAMILIES[names[seed % len(names)]]
    return family(seed, random.Random(seed))


# ---------------------------------------------------------------------------
# Vectors
# ---------------------------------------------------------------------------


def expectation(outcome: Outcome) -> list[str]:
    """What Python did with one packet, as STF lines."""
    if not outcome.outputs:
        return ["no_packet"]
    return [f"expect {port} {data.hex()} $" for port, data in outcome.outputs]


def vectors(generated: Generated, index: ir.Index) -> list[tuple[str, str]]:
    """Name and text of every vector file, with Python's outputs expected.

    Raises `ValueError` when Python cannot run a case to an output: an
    exception is not something STF can expect.
    """
    groups = [generated.cases] if generated.sequence else [(c,) for c in generated.cases]
    files: list[tuple[str, str]] = []
    for number, group in enumerate(groups):
        loaded = arch.load(generated.program)
        lines: list[str] = []
        for case in group:
            outcome = python_outcome(loaded, case, SWITCH_PORTS)
            if outcome.error is not None:
                raise ValueError(f"Python raised on {case}: {outcome.error}")
            lines.append(case_to_stf(index, case).rstrip("\n"))
            if outcome.diagnostic is not None:
                lines.append(f"# python diagnostic: {outcome.diagnostic}")
            lines.extend(expectation(outcome))
        name = "sequence.stf" if generated.sequence else f"case-{number}.stf"
        files.append((name, "\n".join(lines) + "\n"))
    return files


def self_check(program: pb.Program, index: ir.Index, text: str) -> None:
    """The vector must replay on Python from fresh state: it says what
    Python did, and nothing else."""
    loaded = arch.load(program)
    stf.assert_replay(index, stf.parse(text), arch.stf_driver(arch.Switch(SWITCH_PORTS), loaded))


# ---------------------------------------------------------------------------
# Known defects of the pinned simulator
# ---------------------------------------------------------------------------


# The blocks a generated shift runs in: the control's expressions and the
# parser's conditions.
SHIFT_LIMIT_RELATIONS = (
    "error: relation V1Model_ingress failed",
    "error: relation V1Model_parser failed",
)


def known_defect(verdict: oracle_run.Verdict) -> str | None:
    """The name of a diagnosed simulator defect that explains a verdict.

    `shift-limit`: the simulator's `$shl` and `$shr` builtins
    (p4spec/lib/interface/builtin/numerics.ml at the pin) refuse any shift
    amount above 2048 with "shift amount too large", although P4 defines
    `x << n` and `x >> n` for every `n` (zero once `n` reaches the width;
    docs/ir-semantics.md). Only an `error` whose sole failure is that
    refusal, reached through the binary shift operator, qualifies; the
    vector is then not judged at all, so this is never a pass.
    """
    if verdict.status != "error":
        return None
    lines = [line.strip() for line in verdict.detail.splitlines() if line.strip()]
    errors = [line for line in lines if line.startswith("error:")]
    if (
        lines[-1:] == ["shift amount too large"]
        and len(errors) == 1
        and errors[0] in SHIFT_LIMIT_RELATIONS
        and any(line in lines for line in ("function bin_shl failed", "function bin_shr failed"))
    ):
        return "shift-limit"
    return None


# Room between two written priorities for the model's tie-breaking ranks.
RANKS = 1024


def table_mask_model(
    program: pb.Program, entries: pb.Entries, *, reverse: bool = False
) -> tuple[pb.Program, pb.Entries]:
    """The program and host entries under which p4blo computes what the
    pinned simulator computes for the `add` lines `run.py` writes.

    The simulator builds a ternary or lpm entry's key set as `base &&& base`
    where it should be `base &&& mask` (spec/9-arch/9.1-table-interface.watsup,
    `$tableObject_create_entry_key`: the mask expression is cast from the
    base), so an entry matches every key that has at least the base's bits
    set. As p4blo entries that is a ternary value and mask both equal to the
    base, which for an lpm key also means a ternary key, with the prefix
    length as priority as `run.py` writes it. Exact keys and `const
    entries`, which the printer writes with their real masks, keep their
    key sets.

    Such key sets overlap far more than the real ones, and p4blo refuses
    two overlapping entries of equal priority, where the simulator breaks
    the tie by an order of its own. So every entry of a ternary table gets
    a distinct priority, its written one times `RANKS` plus its position,
    const entries first, in `reverse` order when asked; a result that does
    not depend on the tie-break is the same both ways.
    """
    index = ir.Index.build(program)
    installed = InstalledEntries(index)
    model = pb.Program()
    model.CopyFrom(program)
    lpm_only: set[tuple[str, str]] = set()
    ternary: dict[tuple[str, str], pb.Table] = {}
    for block in model.blocks:
        for table in block.tables:
            kinds = {key.match_kind for key in table.keys}
            if pb.MATCH_KIND_LPM in kinds:
                if table.const_entries:
                    raise ValueError(f"const entries on lpm table {table.name!r} are not modelled")
                if pb.MATCH_KIND_TERNARY not in kinds:
                    lpm_only.add((block.name, table.name))
                for key in table.keys:
                    if key.match_kind == pb.MATCH_KIND_LPM:
                        key.match_kind = pb.MATCH_KIND_TERNARY
            if kinds & {pb.MATCH_KIND_LPM, pb.MATCH_KIND_TERNARY}:
                ternary[block.name, table.name] = table
    host = pb.Entries()
    host.CopyFrom(entries)
    for te in host.tables:
        widths = installed.key_widths((te.block, te.table))
        for entry in te.entries:
            prefix: int | None = None
            for i, (kv, width) in enumerate(zip(entry.keys, widths, strict=True)):
                match kv.WhichOneof("kind"):
                    case "lpm":
                        length = kv.lpm.prefix_len
                        mask = ((1 << width) - 1) ^ ((1 << (width - length)) - 1)
                        base = int(kv.lpm.value) & mask
                        prefix = length if prefix is None else prefix
                    case "ternary":
                        base = int(kv.ternary.value) & int(kv.ternary.mask)
                    case _:
                        continue
                entry.keys[i].CopyFrom(
                    pb.KeyValue(ternary=pb.TernaryValue(value=str(base), mask=str(base)))
                )
            if (te.block, te.table) in lpm_only and prefix is not None:
                entry.priority = prefix
    for ref, table in ternary.items():
        ranked = [*table.const_entries]
        for te in host.tables:
            if (te.block, te.table) == ref:
                ranked.extend(te.entries)
        if len(ranked) >= RANKS:
            raise ValueError(f"table {table.name!r} has too many entries to rank")
        for rank, entry in enumerate(reversed(ranked) if reverse else ranked):
            entry.priority = entry.priority * RANKS + rank
    return model, host


def explained_by_table_mask(
    oracle: oracle_run.Oracle,
    program: pb.Program,
    prepared: Prepared,
    case: Case,
    vector: Path,
) -> bool:
    """Whether the simulator does exactly what the table-mask model says.

    The model's outputs, computed by Python, replace the expectations of the
    failed vector, and the unchanged program and `add` lines run again. Only
    a pass explains the failure. A model whose outputs depend on how ties
    are broken, or equal the real ones, explains nothing.
    """
    outcomes: list[Outcome] = []
    try:
        for reverse in (False, True):
            model, entries = table_mask_model(program, case.entries, reverse=reverse)
            modelled = Case(entries, case.ingress_port, case.packet)
            outcomes.append(python_outcome(arch.load(model), modelled, SWITCH_PORTS))
    except ValueError:
        return False
    original = python_outcome(arch.load(program), case, SWITCH_PORTS)
    outcome = outcomes[0]
    if (
        any(o.error is not None for o in outcomes)
        or outcomes[1].outputs != outcome.outputs
        or outcome.outputs == original.outputs
    ):
        return False
    lines = [case_to_stf(prepared.index, case).rstrip("\n"), *expectation(outcome)]
    directory = vector.parent / "table-mask"
    directory.mkdir(exist_ok=True)
    path = directory / vector.name
    path.write_text("\n".join(lines) + "\n")
    verdict = oracle_run.run_vector(oracle, prepared.index, prepared.p4, path, directory)
    return verdict.status == "pass"


def brief(detail: str) -> str:
    """The lines of the simulator's output that say what happened."""
    lines = [line.strip() for line in detail.splitlines() if line.strip()]
    said = [
        line
        for line in lines
        if line.startswith(("error:", "[FAIL]", "before the oracle")) or " but got " in line
    ]
    if lines and lines[-1] not in said:
        said.append(lines[-1])
    return "; ".join(said)


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@dataclass
class Result:
    seed: int
    family: str
    description: str
    directory: Path
    verdicts: list[oracle_run.Verdict] = field(default_factory=list)
    # Why the seed could not reach the oracle, when it could not.
    problem: str | None = None
    # Vectors a model of a defect explains, by file name (`table-mask`).
    modelled: dict[str, str] = field(default_factory=dict)

    def known(self, verdict: oracle_run.Verdict) -> str | None:
        """The diagnosed defect behind a verdict that did not pass, if any."""
        return known_defect(verdict) or self.modelled.get(verdict.vector.name)

    @property
    def status(self) -> str:
        if self.problem is not None:
            return "error"
        unexplained = [v for v in self.verdicts if v.status != "pass" and not self.known(v)]
        for status in ("error", "fail"):
            if any(v.status == status for v in unexplained):
                return status
        return "known" if any(v.status != "pass" for v in self.verdicts) else "pass"

    def report(self) -> str:
        lines = [f"seed {self.seed} {self.family} ({self.description}): {self.status}"]
        lines.append(f"    inputs: {self.directory}")
        if self.problem is not None:
            lines.append(f"    {self.problem}")
        for verdict in self.verdicts:
            if verdict.status != "pass":
                known = self.known(verdict)
                label = verdict.status if known is None else f"known {known}"
                lines.append(f"    {label} {verdict.vector.name}: {brief(verdict.detail)}")
        return "\n".join(lines)


def run_seed(oracle: oracle_run.Oracle, seed: int, out: Path) -> Result:
    """Materialize one seed under `out`, run it on the oracle, and write
    `verdict.txt` beside its inputs."""
    return run_generated(oracle, materialize(seed), out)


@dataclass(frozen=True)
class Prepared:
    """What the oracle is given: an index, the printed program and the
    vector files, all written under one directory."""

    index: ir.Index
    p4: Path
    vectors: tuple[Path, ...]


def prepare(generated: Generated, directory: Path) -> Prepared:
    """Validate, print and write the vectors of a program, checking each
    vector against Python first. Needs no oracle; raises on any problem."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "program.txtpb").write_text(ir.dump_text(generated.program))
    index = ir.Index.build(generated.program)
    arch.load(generated.program)  # validates; a generator mistake is an error
    p4 = directory / "program.p4"
    p4.write_text(v1model.print_program(index.program, index=index))
    paths: list[Path] = []
    for name, text in vectors(generated, index):
        path = directory / name
        path.write_text(text)
        self_check(generated.program, index, text)
        paths.append(path)
    return Prepared(index, p4, tuple(paths))


def run_generated(oracle: oracle_run.Oracle, generated: Generated, out: Path) -> Result:
    """Run a program and its cases, however they were made, under `out`."""
    directory = out.resolve() / f"seed-{generated.seed:05d}-{generated.family}"
    result = Result(generated.seed, generated.family, generated.description, directory)
    try:
        prepared = prepare(generated, directory)
    except Exception as e:  # noqa: BLE001 - any failure before the oracle is reported
        result.problem = f"before the oracle: {type(e).__name__}: {e}"
    else:
        spectec = directory / "spectec"
        spectec.mkdir(exist_ok=True)
        for vector in prepared.vectors:
            result.verdicts.append(
                oracle_run.run_vector(oracle, prepared.index, prepared.p4, vector, spectec)
            )
        if not generated.sequence:
            for case, verdict in zip(generated.cases, result.verdicts, strict=True):
                if verdict.status == "fail" and explained_by_table_mask(
                    oracle, generated.program, prepared, case, verdict.vector
                ):
                    result.modelled[verdict.vector.name] = "table-mask"
    (directory / "verdict.txt").write_text(_verdict_text(result))
    return result


def _verdict_text(result: Result) -> str:
    lines = [result.report(), ""]
    for verdict in result.verdicts:
        lines.append(f"{verdict.status} {verdict.vector.name}")
        if verdict.command:
            lines.append(f"command: {shlex.join(verdict.command)}")
        lines.extend(f"note: {note}" for note in verdict.notes)
        lines.append(verdict.detail)
        lines.append("")
    return "\n".join(lines)


def parse_seeds(text: str) -> list[int]:
    """`7`, `0:500` (half-open) or a comma-separated list of either."""
    seeds: list[int] = []
    for part in text.split(","):
        if ":" in part:
            start, stop = part.split(":", 1)
            seeds.extend(range(int(start), int(stop)))
        else:
            seeds.append(int(part))
    return seeds


def summary(results: Sequence[Result]) -> str:
    table: dict[str, Counter[str]] = {}
    for result in results:
        counts = table.setdefault(result.family, Counter())
        counts["programs"] += 1
        counts["vectors"] += len(result.verdicts)
        counts[result.status] += 1
    header = (
        f"{'family':18} {'programs':>8} {'vectors':>8} "
        f"{'pass':>6} {'known':>6} {'fail':>6} {'error':>6}"
    )
    rows = [header, "-" * len(header)]
    total: Counter[str] = Counter()
    for family in sorted(table):
        counts = table[family]
        total.update(counts)
        rows.append(_row(family, counts))
    rows.append(_row("total", total))
    return "\n".join(rows)


def _row(name: str, counts: Counter[str]) -> str:
    return (
        f"{name:18} {counts['programs']:>8} {counts['vectors']:>8} "
        f"{counts['pass']:>6} {counts['known']:>6} {counts['fail']:>6} {counts['error']:>6}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tests/oracle/generated.py",
        description="run generated programs and cases on P4-SpecTec's simulator",
    )
    parser.add_argument("--seeds", default="0:50", help="`N`, `A:B` (half-open) or a list")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where inputs are saved")
    args = parser.parse_args(argv)

    oracle = oracle_run.find_oracle()
    reason = "no p4spectec binary" if oracle is None else oracle.missing()
    if oracle is None or reason is not None:
        print(
            f"{reason}: run tests/oracle/build.sh, or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR",
            file=sys.stderr,
        )
        return 2

    # The simulator runs from its checkout, so every path it is given is
    # absolute.
    out = args.out.resolve()
    start = time.monotonic()
    results: list[Result] = []
    for seed in parse_seeds(args.seeds):
        result = run_seed(oracle, seed, out)
        results.append(result)
        if result.status != "pass":
            print(result.report(), flush=True)
    print(f"\n{summary(results)}\n\n{time.monotonic() - start:.0f}s; inputs under {out}")
    return 0 if all(r.status in ("pass", "known") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
