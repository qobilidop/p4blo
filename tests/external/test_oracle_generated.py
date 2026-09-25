"""Generated programs and cases on P4-SpecTec's simulator, at CI size.

tests/oracle/generated.py turns a seed into a program from one of the DRT's
generated families (scalar expressions, parser conditions, stateful register
and counter sequences, aggregate copies, calls, corpus programs with random
entries and packets, and the control and parser shape families), and into
vectors whose `expect` lines are what the Python interpreter did. Here a
fixed seed range runs through it, one test per seed. Without a built
simulator the oracle tests skip, as in tests/external/test_oracle.py; the
preparation, which needs no oracle, always runs.

A divergence and an oracle error both fail. A seed whose every non-pass is a
diagnosed simulator defect is a strict expected failure listed in `KNOWN`,
tied to the defect's exact classifier; a corrected simulator turns it into
an XPASS to review. The larger campaign and what its findings mean are in
tests/oracle/README.md, "Generated programs".
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

import pytest

from p4blo import arch, stf
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.programs import binary, bits, scalar_program
from p4blo.interp import tables
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.oracle import generated  # noqa: E402
from tests.oracle import run as oracle_run  # noqa: E402

# Ten programs per family, about four minutes on an M-series Mac.
SEEDS = range(80)
# Seeds in SEEDS the pinned simulator cannot judge, by diagnosed defect.
KNOWN = {5: "table-mask"}
FAMILY_NAMES = list(generated.FAMILIES)


class KnownSpecTecDefect(Exception):
    """Every vector that did not pass is explained by a classified defect."""


class KnownDeviation(Exception):
    """The exact mismatch a documented p4blo choice predicts."""


def seed_id(seed: int) -> str:
    return f"{seed}-{FAMILY_NAMES[seed % len(FAMILY_NAMES)]}"


def seed_param(seed: int) -> object:
    if seed not in KNOWN:
        return pytest.param(seed, id=seed_id(seed))
    return pytest.param(
        seed,
        id=seed_id(seed),
        marks=pytest.mark.xfail(
            strict=True,
            raises=KnownSpecTecDefect,
            reason=f"pinned SpecTec {KNOWN[seed]}; tests/oracle/generated.py, known_defect",
        ),
    )


@pytest.fixture(scope="module")
def oracle() -> oracle_run.Oracle:
    found = oracle_run.find_oracle()
    if found is None:
        pytest.skip(
            "P4-SpecTec's p4spectec is not built: run tests/oracle/build.sh, "
            "or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR (see tests/oracle/README.md)"
        )
    reason = found.missing()
    if reason is not None:
        pytest.skip(f"the oracle checkout is incomplete: {reason}")
    return found


# ---------------------------------------------------------------------------
# Generation, which needs no oracle
# ---------------------------------------------------------------------------


def test_the_seed_set_covers_every_family() -> None:
    assert {generated.materialize(seed).family for seed in SEEDS} == set(generated.FAMILIES)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5, 41])
def test_a_seed_names_its_program_and_cases_exactly(seed: int) -> None:
    first, second = generated.materialize(seed), generated.materialize(seed)
    assert first == second
    other = generated.materialize(seed + len(FAMILY_NAMES))
    assert (other.program, other.cases) != (first.program, first.cases)


@pytest.mark.parametrize("seed", SEEDS, ids=seed_id)
def test_generated_inputs_validate_print_and_replay_on_python(seed: int, tmp_path: Path) -> None:
    prepared = generated.prepare(generated.materialize(seed), tmp_path)
    assert prepared.vectors
    for vector in prepared.vectors:
        oracle_run.translate(vector.read_text(), prepared.index)


def test_every_stateful_sequence_is_one_vector_with_an_expectation_per_request() -> None:
    stateful = next(
        g for g in map(generated.materialize, SEEDS) if g.family == "stateful" and len(g.cases) > 2
    )
    ((name, text),) = generated.vectors(stateful, BoundIndex.build(stateful.program))
    assert name == "sequence.stf"
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    packets = [i for i, line in enumerate(lines) if line.startswith("packet ")]
    assert len(packets) == len(stateful.cases)
    # Each request is followed by its own outcome before the next request.
    for start, end in zip(packets, [*packets[1:], len(lines)], strict=True):
        assert end - start >= 2
        assert all(line.startswith(("expect ", "no_packet")) for line in lines[start + 1 : end])


# ---------------------------------------------------------------------------
# The classifier, which needs no oracle
# ---------------------------------------------------------------------------

SHIFT_TRACE = """\
error: relation V1Model_ingress failed

  source: interp

  trace:
          └── spec/3-operations/3-operations.watsup:269.40-269.48
              function bin_shl failed
          └── spec/3-operations/3-operations.watsup:254.35-254.39
              shift amount too large
"""


def verdict(status: str, detail: str) -> oracle_run.Verdict:
    return oracle_run.Verdict(Path("case-0.stf"), status, detail, ())


def test_shift_limit_classifier_accepts_only_the_diagnosed_shape() -> None:
    assert generated.known_defect(verdict("error", SHIFT_TRACE)) == "shift-limit"
    parser = SHIFT_TRACE.replace("V1Model_ingress", "V1Model_parser")
    assert generated.known_defect(verdict("error", parser)) == "shift-limit"
    right = SHIFT_TRACE.replace("bin_shl", "bin_shr")
    assert generated.known_defect(verdict("error", right)) == "shift-limit"
    for status in ("pass", "fail"):
        assert generated.known_defect(verdict(status, SHIFT_TRACE)) is None
    for changed in (
        SHIFT_TRACE.replace("function bin_shl failed", "function bin_add failed"),
        SHIFT_TRACE.replace("shift amount too large", "bitstr width too large"),
        SHIFT_TRACE.replace("V1Model_ingress", "V1Model_egress"),
        "error: expected (0) 00 but got (0) 01\n" + SHIFT_TRACE,
        SHIFT_TRACE + "  unrelated trailing line\n",
    ):
        assert generated.known_defect(verdict("error", changed)) is None


def test_table_mask_model_uses_the_base_as_mask_and_ranks_ties() -> None:
    program = arch_wire.load_text(ROOT / "tests/corpus/priority/priority.txtpb")
    (block, table) = next(
        (b.name, t) for b in program.blocks for t in b.tables if t.name == "t_ternary"
    )
    written = pb.Entries()
    te = written.tables.add(block=block, table=table.name)
    for value, mask, priority in ((0x1234, 0xFF00, 1), (0x00F0, 0x00F0, 1)):
        entry = te.entries.add(priority=priority)
        entry.keys.add(ternary=pb.TernaryValue(value=str(value & mask), mask=str(mask)))
        entry.action.action = "a"
    for reverse in (False, True):
        model, entries = generated.table_mask_model(program, written, reverse=reverse)
        keys = [e.keys[0].ternary for e in entries.tables[0].entries]
        assert [(int(k.value), int(k.mask)) for k in keys] == [(0x1200, 0x1200), (0xF0, 0xF0)]
        const = next(t for b in model.blocks for t in b.tables if t.name == "t_ternary")
        priorities = [e.priority for e in [*const.const_entries, *entries.tables[0].entries]]
        assert len(set(priorities)) == len(priorities)
        # The written priority still decides first; only ties are ranked.
        assert [p // generated.RANKS for p in priorities] == [
            *(e.priority for e in table.const_entries),
            1,
            1,
        ]
        assert (priorities[-2] < priorities[-1]) != reverse


def test_table_mask_model_turns_lpm_into_ternary_with_prefix_priority() -> None:
    program = arch_wire.load_text(ROOT / "tests/corpus/forwarder/forwarder.txtpb")
    written = stf.to_entries(
        BoundIndex.build(program),
        stf.parse("add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 drop()\n"),
    )
    model, entries = generated.table_mask_model(program, written)
    table = next(t for b in model.blocks for t in b.tables if t.name == "ipv4_lpm")
    assert [k.match_kind for k in table.keys] == [pb.MATCH_KIND_TERNARY]
    (entry,) = entries.tables[0].entries
    assert (int(entry.keys[0].ternary.value), int(entry.keys[0].ternary.mask)) == (
        0x0A000200,
        0x0A000200,
    )
    assert entry.priority == 24 * generated.RANKS


def lpm_precedence() -> tuple[apb.BlockAssembly, Case]:
    """The forwarder, the two overlapping entries of lpm_precedence.stf and
    the packet both cover, where the /24 must beat the /16."""
    program = arch_wire.load_text(ROOT / "tests/corpus/forwarder/forwarder.txtpb")
    vector = stf.parse((ROOT / "tests/corpus/forwarder/lpm_precedence.stf").read_text())
    entries = stf.to_entries(BoundIndex.build(program), vector)
    packet = next(s for s in vector if isinstance(s, stf.Packet))
    return program, Case(entries, packet.port, packet.data)


def shortest_prefix_wins(entry: pb.Entry, best: pb.Entry, ternary: bool) -> bool:
    """A wrong precedence rule, as a mutant of `tables.beats`."""
    if ternary:
        return entry.priority > best.priority
    return tables.prefix_length(entry) < tables.prefix_length(best)


def test_the_table_mask_control_model_reproduces_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The rewrite with the real masks gives Python's real outputs, so the
    model changes nothing but the masks; with a wrong longest-prefix rule
    in Python it does not, and the classifier refuses before it would ask
    the oracle anything."""
    program, case = lpm_precedence()
    assert generated.table_mask_control_agrees(program, case)
    right = generated.python_outcome(arch.reference.load(program), case, generated.SWITCH_PORTS)
    monkeypatch.setattr(tables, "beats", shortest_prefix_wins)
    wrong = generated.python_outcome(arch.reference.load(program), case, generated.SWITCH_PORTS)
    assert wrong.outputs != right.outputs
    assert not generated.table_mask_control_agrees(program, case)
    unused = cast(Any, None)
    assert not generated.explained_by_table_mask(unused, program, unused, case, unused)


def exact_where_masked(kv: pb.KeyValue, key: Any) -> bool:
    """A ternary matching bug that fires only where the mask differs from
    the value, as a mutant of `tables.key_value_matches`: the key must then
    equal the value. The table-mask model writes every mask equal to its
    value, so the bug never runs there."""
    if kv.WhichOneof("kind") == "ternary" and int(kv.ternary.mask) != int(kv.ternary.value):
        return key.value == int(kv.ternary.value)
    return RIGHT_KEY_VALUE_MATCHES(kv, key)


RIGHT_KEY_VALUE_MATCHES = tables.key_value_matches
# Corpus-family seeds (tests/corpus/acl) whose outputs `exact_where_masked`
# changes on cases the control model reproduces; found by an offline search
# of seeds below 4000.
MASK_BUG_SEEDS = (605, 845, 1205)


def test_the_table_mask_defect_must_change_a_winner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Seed 5's diagnosed case is one where the defect's key sets change
    which entry wins; the other cases of the same seeds are not. A Python
    matcher that disagrees with the standalone winner is refused even where
    the control model, which runs through that matcher, agrees."""
    known = generated.materialize(5)
    assert [generated.table_mask_changes_a_winner(known.program, c) for c in known.cases] == [
        False,
        False,
        True,
        False,
    ]
    monkeypatch.setattr(tables, "key_value_matches", exact_where_masked)
    unused = cast(Any, None)
    for seed in MASK_BUG_SEEDS:
        seeded = generated.materialize(seed)
        for case in seeded.cases:
            assert generated.table_mask_control_agrees(seeded.program, case)
            assert not generated.table_mask_changes_a_winner(seeded.program, case)
            assert not generated.explained_by_table_mask(
                unused, seeded.program, unused, case, unused
            )


# ---------------------------------------------------------------------------
# The oracle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [seed_param(seed) for seed in SEEDS])
def test_generated_program_on_the_oracle(
    oracle: oracle_run.Oracle, seed: int, tmp_path: Path
) -> None:
    result = generated.run_seed(oracle, seed, tmp_path)
    report = result.report()
    if seed in KNOWN and result.status == "known":
        defects = {result.known(v) for v in result.verdicts if v.status != "pass"}
        if defects == {KNOWN[seed]}:
            raise KnownSpecTecDefect(report)
    if result.status == "fail":
        pytest.fail(f"DIVERGENCE: the oracle disagrees with Python\n{report}")
    if result.status == "error":
        pytest.fail(f"ORACLE ERROR (not a divergence): could not judge\n{report}")
    if result.status == "known":
        pytest.fail(f"classified defect on a seed not listed in KNOWN; review it\n{report}")
    assert result.status == "pass", report


CASE = Case(pb.Entries(), 0, b"\xab\xcd")


def shift_program(op: pb.BinaryOp, amount: int) -> generated.Generated:
    program = generated.byte_aligned(scalar_program(binary(op, bits(8, 1), bits(16, amount)), 8))
    return generated.Generated(amount, "probe", f"shift by {amount}", program, (CASE,))


@pytest.mark.parametrize("op", [pb.BINARY_OP_SHL, pb.BINARY_OP_SHR], ids=["shl", "shr"])
def test_shifts_up_to_the_simulator_limit_pass(
    oracle: oracle_run.Oracle, op: pb.BinaryOp, tmp_path: Path
) -> None:
    result = generated.run_generated(oracle, shift_program(op, 2048), tmp_path)
    assert result.status == "pass", result.report()


@pytest.mark.parametrize("op", [pb.BINARY_OP_SHL, pb.BINARY_OP_SHR], ids=["shl", "shr"])
@pytest.mark.xfail(
    strict=True,
    raises=KnownSpecTecDefect,
    reason="pinned SpecTec refuses shift amounts above 2048; tests/oracle/generated.py",
)
def test_shift_beyond_the_simulator_limit(
    oracle: oracle_run.Oracle, op: pb.BinaryOp, tmp_path: Path
) -> None:
    result = generated.run_generated(oracle, shift_program(op, 2049), tmp_path)
    (v,) = result.verdicts
    if generated.known_defect(v) == "shift-limit":
        raise KnownSpecTecDefect(result.report())
    assert result.status == "pass", result.report()


@pytest.mark.xfail(
    strict=True,
    raises=KnownDeviation,
    reason="p4blo pads emitted bits before the payload; docs/ir-semantics.md, Deparsers",
)
def test_unaligned_emission_before_a_payload(oracle: oracle_run.Oracle, tmp_path: Path) -> None:
    # A 7-bit header 0010110 before the payload abcd: p4blo writes
    # 0010110 0 then the payload, the simulator 0010110 then the payload's
    # bits, one position earlier. This is why the families pad their result.
    program = scalar_program(bits(7, 0x16), 7)
    probe = generated.Generated(7, "probe", "7-bit result", program, (CASE,))
    result = generated.run_generated(oracle, probe, tmp_path)
    (v,) = result.verdicts
    mismatch = "error: expected (0) 2CABCD but got (0) 2D579A; source: sim"
    if v.status == "fail" and generated.brief(v.detail) == mismatch:
        raise KnownDeviation(mismatch)
    assert result.status == "pass", result.report()


def test_a_wrong_longest_prefix_rule_is_a_failure_not_a_known_defect(
    oracle: oracle_run.Oracle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Python that lets the shorter prefix win disagrees with the oracle,
    and the table-mask classifier must not explain that away."""
    program, case = lpm_precedence()
    monkeypatch.setattr(tables, "beats", shortest_prefix_wins)
    probe = generated.Generated(0, "probe", "shortest prefix wins", program, (case,))
    result = generated.run_generated(oracle, probe, tmp_path)
    assert result.modelled == {}
    assert result.status == "fail", result.report()


@pytest.mark.parametrize("seed", MASK_BUG_SEEDS)
def test_a_matching_bug_on_real_masks_is_a_failure_not_a_known_defect(
    oracle: oracle_run.Oracle, seed: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Python that matches wrongly only where a mask differs from its
    value disagrees with the oracle, and the table-mask classifier, whose
    model never has such a mask, must not explain that away."""
    monkeypatch.setattr(tables, "key_value_matches", exact_where_masked)
    result = generated.run_seed(oracle, seed, tmp_path)
    assert result.modelled == {}
    assert result.status == "fail", result.report()
