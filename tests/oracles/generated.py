"""Generated programs and cases on P4-SpecTec's simulator.

    uv run python tests/oracles/generated.py --seeds 0:500 [--out DIR]

The corpus is a dozen hand-written programs; the differential tests against
Lean change the program itself. This module takes the same program families
to the oracle. A seed names one program and its cases exactly: the family is
`FAMILIES[seed % len(FAMILIES)]`, and everything else comes from
`random.Random(seed)`, through the constructors of `p4blo.drt.programs`,
`p4blo.drt.stateful_programs` and `p4blo.drt.families` (and the copy
profiles of the DRT tests) and through `p4blo.drt.generate` for packets.
Hypothesis is not used, because its draws are not a stable function of a
seed across versions; the scalar expressions come from the generator the
Hypothesis strategy uses too (`programs.scalar_expression`), driven by a
`RandomChooser`, with leaves that read a parsed input so that each case
computes something else, and with shift amounts narrow enough for the
simulator. The control and parser families run in their `spectec`
profile, which leaves out what the ledger records as deviating from the
simulator.

For each seed the program is validated and loaded, the Python interpreter
runs the cases in order, and its outputs become the `expect` lines of an STF
vector. The vector is replayed on Python first, to check that it says what
Python did, then translated and run on the simulator by `tests/oracles/run.py`,
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
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex, assembly_of
from p4blo.arch.v0 import assembly_pb2 as apb

# Runnable as a script from the repository root without installing anything.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "impl" / "python"))
sys.path.insert(0, str(ROOT))

from p4blo import arch, ir, stf  # noqa: E402
from p4blo.arch import v1model  # noqa: E402
from p4blo.drt.case import Case, case_to_stf  # noqa: E402
from p4blo.drt.choice import RandomChooser  # noqa: E402
from p4blo.drt.families import FAMILIES as SHAPES  # noqa: E402
from p4blo.drt.generate import generate  # noqa: E402
from p4blo.drt.programs import WIDTHS as PROGRAM_WIDTHS  # noqa: E402
from p4blo.drt.programs import (  # noqa: E402
    Leaves,
    binary,
    bits,
    has_lookahead,
    packet_scalar_program,
    parser_condition_program,
    scalar_expression,
)
from p4blo.drt.run import Outcome, python_outcome  # noqa: E402
from p4blo.drt.stateful_programs import (  # noqa: E402
    UPDATE_OPS,
    StatefulSpec,
    stateful_program,
)
from p4blo.drt.stateful_programs import WIDTHS as STATEFUL_WIDTHS  # noqa: E402
from p4blo.drt.stateful_programs import packet as stateful_packet  # noqa: E402
from p4blo.interp.tables import InstalledEntries, Match, TableRef  # noqa: E402
from p4blo.interp.values import Bits  # noqa: E402
from p4blo.v0 import p4blo_pb2 as pb  # noqa: E402
from tests.oracles import run as oracle_run  # noqa: E402

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
        *(ROOT / "tests/programs/corpus").glob("*/*.txtpb"),
        *(ROOT / "tests/programs/examples").glob("*/*.txtpb"),
    ]
)

# Shift amounts at most this wide stay under the simulator's limit of 2048
# (`known_defect`, shift-limit), which is then never what a seed tests.
SHIFT_WIDTHS = tuple(w for w in PROGRAM_WIDTHS if w <= 9)
SCALAR_LABELS = tuple(str(w) for w in PROGRAM_WIDTHS)
PACKET_LEAVES = Leaves(packet=True, shift_widths=SHIFT_WIDTHS)
LOOKAHEAD_LEAVES = Leaves(lookahead=True, shift_widths=SHIFT_WIDTHS)


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
    program: apb.BlockAssembly
    cases: tuple[Case, ...]
    sequence: bool = False


# ---------------------------------------------------------------------------
# Scalar expressions
# ---------------------------------------------------------------------------


def byte_aligned(program: apb.BlockAssembly) -> apb.BlockAssembly:
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


def _random_cases(program: apb.BlockAssembly, rng: random.Random) -> tuple[Case, ...]:
    index = BoundIndex.build(program)
    return tuple(generate(index, rng.getrandbits(32), CASES, PORTS))


def scalar_family(seed: int, rng: random.Random) -> Generated:
    """An expression of `tests/conformance/execution/test_drt_programs.py`'s generator whose leaves
    also read a parsed input, so that every case computes something else."""
    ch = RandomChooser(rng)
    width = None if ch.chance("scalar.bool") else int(ch.choice("scalar.width", SCALAR_LABELS))
    expression = scalar_expression(ch, width, 3, PACKET_LEAVES)
    program = byte_aligned(packet_scalar_program(expression, width))
    kind = "bool" if width is None else f"bit<{width}>"
    return Generated(seed, "scalar", kind, program, _random_cases(program, rng))


def parser_condition_family(seed: int, rng: random.Random) -> Generated:
    """A `verify` condition holding at least one lookahead, placed on either
    side of an `&&` or `||` when the drawn expression has none, so that a
    short packet can fault it wherever it sits."""
    ch = RandomChooser(rng)
    condition = scalar_expression(ch, None, 3, LOOKAHEAD_LEAVES)
    if not has_lookahead(condition):
        read = scalar_expression(ch, None, 0, Leaves(lookahead=True))
        while not has_lookahead(read):
            read = scalar_expression(ch, None, 0, Leaves(lookahead=True))
        op = pb.BINARY_OP_AND if ch.chance("condition.and") else pb.BINARY_OP_OR
        pair = (condition, read) if ch.chance("condition.left") else (read, condition)
        condition = binary(op, *pair)
    expected = rng.choice(["NoError", "NoMatch", "PacketTooShort"])
    program = byte_aligned(parser_condition_program(condition, expected))
    return Generated(
        seed, "parser_condition", f"== {expected}", program, _random_cases(program, rng)
    )


# ---------------------------------------------------------------------------
# Stateful programs
# ---------------------------------------------------------------------------


def stateful_family(seed: int, rng: random.Random) -> Generated:
    """A spec and request sequence drawn like the stateful campaigns strategy."""
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
    from tests.conformance.execution.test_drt_aggregate_copy import WIDTHS as COPY_WIDTHS
    from tests.conformance.execution.test_drt_aggregate_copy import CopyKind, copy_program

    kinds: tuple[CopyKind, ...] = ("header", "struct")
    kind = rng.choice(kinds)
    width = rng.choice(COPY_WIDTHS)
    valid = rng.random() < 0.5
    values = [rng.getrandbits(width) for _ in range(4)]
    program, _ = copy_program(kind, width, valid, *values)
    description = f"{kind} bit<{width}> valid={valid} values={values}"
    return Generated(seed, "aggregate_copy", description, program, _random_cases(program, rng))


def call_copy_family(seed: int, rng: random.Random) -> Generated:
    from tests.conformance.execution.test_drt_call_copy import CallKind, call_program

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
    `python -m p4blo.drt` sends them to Lean. The program goes round the
    corpus with the seed, so that consecutive seeds of this family reach
    every program before any repeats."""
    path = CORPUS[(seed // len(FAMILIES)) % len(CORPUS)]
    program = arch_wire.load_text(path)
    name = str(path.parent.relative_to(ROOT))
    return Generated(seed, "corpus", name, program, _random_cases(program, rng))


def shape_family(name: str) -> Callable[[int, random.Random], Generated]:
    """A family of `p4blo.drt.families` in its `spectec` profile, which
    leaves out what the ledger records as deviating from the simulator."""

    def family(seed: int, rng: random.Random) -> Generated:
        drawn = SHAPES[name](RandomChooser(rng), "spectec")
        return Generated(seed, name, drawn.describe(), drawn.program, drawn.cases)

    return family


type Family = Callable[[int, random.Random], Generated]

FAMILIES: dict[str, Family] = {
    "scalar": scalar_family,
    "parser_condition": parser_condition_family,
    "stateful": stateful_family,
    "aggregate_copy": aggregate_copy_family,
    "call_copy": call_copy_family,
    "corpus": corpus_family,
    "control": shape_family("control"),
    "parser": shape_family("parser"),
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
        loaded = v1model.load(generated.program)
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


def self_check(program: apb.BlockAssembly, index: ir.Index, text: str) -> None:
    """The vector must replay on Python from fresh state: it says what
    Python did, and nothing else."""
    loaded = v1model.load(program)
    stf.assert_replay(
        index, stf.parse(text), arch.stf_driver(v1model.V1Model(SWITCH_PORTS), loaded)
    )


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
    """The name of a diagnosed simulator defect that explains a verdict by
    its text alone. The other classified defect, `table-mask`, needs a rerun
    under a model and is decided by `explained_by_table_mask`.

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


@dataclass(frozen=True)
class Prepared:
    """What the oracle is given: an index, the printed program and the
    vector files, all written under one directory."""

    index: ir.Index
    p4: Path
    vectors: tuple[Path, ...]


# Room between two written priorities for the model's tie-breaking ranks.
RANKS = 1024


def table_mask_model(
    program: apb.BlockAssembly,
    entries: pb.Entries,
    *,
    reverse: bool = False,
    real_masks: bool = False,
) -> tuple[apb.BlockAssembly, pb.Entries]:
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

    `real_masks` keeps each key's own mask while doing everything else the
    same: the control model, which must reproduce p4blo's real result, so
    that the rewrite and the ranking are known to change nothing but the
    masks (`explained_by_table_mask`).
    """
    index = BoundIndex.build(program)
    installed = InstalledEntries(index)
    model = apb.BlockAssembly()
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
                        mask = int(kv.ternary.mask)
                        base = int(kv.ternary.value) & mask
                    case _:
                        continue
                written = mask if real_masks else base
                entry.keys[i].CopyFrom(
                    pb.KeyValue(ternary=pb.TernaryValue(value=str(base), mask=str(written)))
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


def table_mask_control_agrees(program: apb.BlockAssembly, case: Case) -> bool:
    """Whether the table-mask rewrite with the real masks gives Python's real
    outputs under both tie orders."""
    original = python_outcome(v1model.load(program), case, SWITCH_PORTS)
    try:
        for reverse in (False, True):
            model, entries = table_mask_model(
                program, case.entries, reverse=reverse, real_masks=True
            )
            control = Case(entries, case.ingress_port, case.packet)
            outcome = python_outcome(v1model.load(model), control, SWITCH_PORTS)
            if outcome.error is not None or outcome.outputs != original.outputs:
                return False
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class Lookup:
    """One table lookup of a Python run: the table, its installed entries
    (const entries first, in installation order), the key values and what
    Python's matcher chose."""

    table: pb.Table
    entries: tuple[pb.Entry, ...]
    keys: tuple[Bits, ...]
    chosen: Match


@contextmanager
def recording_lookups() -> Iterator[list[Lookup]]:
    """Record every table lookup made inside the block. The lookup itself
    still runs through the interpreter, so what it chose is recorded as it
    was, right or wrong."""
    lookups: list[Lookup] = []
    lookup = InstalledEntries.lookup

    def recorded(self: InstalledEntries, table: TableRef, keys: list[Bits]) -> Match:
        chosen = lookup(self, table, keys)
        entries = tuple(self.entries[table])
        lookups.append(Lookup(self.table(table), entries, tuple(keys), chosen))
        return chosen

    InstalledEntries.lookup = recorded  # type: ignore[method-assign]
    try:
        yield lookups
    finally:
        InstalledEntries.lookup = lookup  # type: ignore[method-assign]


# A winner as far as the packet can tell: whether an entry hit, and the
# action call it chose. Two entries with the same call are the same winner.
type Winner = tuple[bool, bytes]


def _winner(entry: pb.Entry | None) -> Winner:
    return (False, b"") if entry is None else (True, entry.action.SerializeToString())


def _prefix_mask(width: int, length: int) -> int:
    return ((1 << width) - 1) ^ ((1 << (width - length)) - 1)


def real_winner(lookup: Lookup) -> Winner:
    """The entry docs/ir-semantics.md, "Tables", says wins, computed here
    from the entries and key values alone: exact equality, prefix equality
    and equality under the mask; the largest priority in a table with a
    ternary key, the longest prefix otherwise, the first installed on a
    tie."""
    ternary = any(k.match_kind == pb.MATCH_KIND_TERNARY for k in lookup.table.keys)
    best: pb.Entry | None = None
    best_rank = 0
    for entry in lookup.entries:
        rank = 0
        for kv, key in zip(entry.keys, lookup.keys, strict=True):
            match kv.WhichOneof("kind"):
                case "exact":
                    mask, base = (1 << key.width) - 1, int(kv.exact)
                case "lpm":
                    mask = _prefix_mask(key.width, kv.lpm.prefix_len)
                    base = int(kv.lpm.value)
                    rank += kv.lpm.prefix_len
                case _:
                    mask, base = int(kv.ternary.mask), int(kv.ternary.value)
            if key.value & mask != base & mask:
                break
        else:
            rank = entry.priority if ternary else rank
            if best is None or rank > best_rank:
                best, best_rank = entry, rank
    return _winner(best)


def defect_winner(lookup: Lookup, *, reverse: bool) -> Winner | None:
    """The entry the simulator's table-mask defect makes win, computed from
    the entries and key values alone, as `table_mask_model` describes it: a
    host entry's ternary or lpm key matches every key with the base's bits
    set, const entries keep their key sets, an lpm-only table orders by
    prefix length and any other by priority, and ties go by position,
    backwards when `reverse`. None where the model does not apply."""
    kinds = {k.match_kind for k in lookup.table.keys}
    if not kinds & {pb.MATCH_KIND_LPM, pb.MATCH_KIND_TERNARY}:
        return real_winner(lookup)
    lpm_only = pb.MATCH_KIND_TERNARY not in kinds
    consts = len(lookup.table.const_entries)
    if lpm_only and consts:
        return None
    best: pb.Entry | None = None
    best_order = (0, 0)
    count = len(lookup.entries)
    for position, entry in enumerate(lookup.entries):
        prefix: int | None = None
        for kv, key in zip(entry.keys, lookup.keys, strict=True):
            match kv.WhichOneof("kind"):
                case "exact":
                    matched = key.value == int(kv.exact)
                case "lpm":
                    base = int(kv.lpm.value) & _prefix_mask(key.width, kv.lpm.prefix_len)
                    prefix = kv.lpm.prefix_len if prefix is None else prefix
                    matched = key.value & base == base
                case _:
                    mask, value = int(kv.ternary.mask), int(kv.ternary.value)
                    if position < consts:
                        matched = key.value & mask == value & mask
                    else:
                        matched = key.value & (value & mask) == value & mask
            if not matched:
                break
        else:
            priority = prefix if lpm_only and prefix is not None else entry.priority
            order = (priority, count - 1 - position if reverse else position)
            if best is None or order > best_order:
                best, best_order = entry, order
    return _winner(best)


def table_mask_changes_a_winner(program: apb.BlockAssembly, case: Case) -> bool:
    """Whether the table-mask defect changes which entry wins some lookup
    of the case, established without the interpreter's matcher.

    Python runs the case once, and every lookup is recorded with its key
    values. Each lookup's winner is then computed twice from the entries and
    keys directly: under the real key sets and under the defect's. Python's
    own choice must be the real winner at every lookup; otherwise Python's
    table code is in question, whatever the model says. And some lookup's
    winner must differ under the defect's key sets in both tie orders;
    otherwise the defect cannot explain a different output. The model, run
    through the same matcher that is under test, cannot establish either:
    a bug that fires only where a mask differs from its value never runs on
    a model whose masks equal their values.
    """
    with recording_lookups() as lookups:
        python_outcome(v1model.load(program), case, SWITCH_PORTS)
    changed = False
    for lookup in lookups:
        real = real_winner(lookup)
        if lookup.chosen.hit != real[0] or (
            real[0] and lookup.chosen.action.SerializeToString() != real[1]  # type: ignore[union-attr]
        ):
            return False
        defects = [defect_winner(lookup, reverse=reverse) for reverse in (False, True)]
        if None in defects:
            return False
        changed = changed or all(d != real for d in defects)
    return changed


def explained_by_table_mask(
    oracle: oracle_run.Oracle,
    program: apb.BlockAssembly,
    prepared: Prepared,
    case: Case,
    vector: Path,
) -> bool:
    """Whether the simulator does exactly what the table-mask model says.

    The model's outputs, computed by Python, replace the expectations of the
    failed vector, and the unchanged program and `add` lines run again. Only
    a pass explains the failure. A model whose outputs depend on how ties
    are broken, or equal the real ones, explains nothing.

    The model does more than swap each mask for its base: it turns lpm keys
    into ternary ones and ranks the entries, so Python's longest-prefix code
    never runs on it, and a wrong longest-prefix rule in Python would look
    like the simulator's defect. So the control model, the same rewrite and
    ranking with the real masks, must first reproduce Python's real outputs
    under both tie orders; if it does not, Python's own table code is in
    question and the failure stays a failure. The control model is itself
    run through Python's matcher, so it cannot tell a matching bug that
    fires only on real masks, which it keeps, from none at all; hence
    `table_mask_changes_a_winner` first, which does not use the matcher.
    """
    if not table_mask_changes_a_winner(program, case):
        return False
    if not table_mask_control_agrees(program, case):
        return False
    outcomes: list[Outcome] = []
    try:
        for reverse in (False, True):
            model, entries = table_mask_model(program, case.entries, reverse=reverse)
            modelled = Case(entries, case.ingress_port, case.packet)
            outcomes.append(python_outcome(v1model.load(model), modelled, SWITCH_PORTS))
    except ValueError:
        return False
    original = python_outcome(v1model.load(program), case, SWITCH_PORTS)
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


def prepare(generated: Generated, directory: Path) -> Prepared:
    """Validate, print and write the vectors of a program, checking each
    vector against Python first. Needs no oracle; raises on any problem."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "program.txtpb").write_text(arch_wire.dump_text(generated.program))
    index = BoundIndex.build(generated.program)
    v1model.load(generated.program)  # validates; a generator mistake is an error
    p4 = directory / "program.p4"
    p4.write_text(v1model.print_program(assembly_of(index.program, index.bindings), index=index))
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
        prog="tests/oracles/generated.py",
        description="run generated programs and cases on P4-SpecTec's simulator",
    )
    parser.add_argument("--seeds", default="0:50", help="`N`, `A:B` (half-open) or a list")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where inputs are saved")
    args = parser.parse_args(argv)

    oracle = oracle_run.find_oracle()
    reason = "no p4spectec binary" if oracle is None else oracle.missing()
    if oracle is None or reason is not None:
        print(
            f"{reason}: run tests/oracles/build.sh, or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR",
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
