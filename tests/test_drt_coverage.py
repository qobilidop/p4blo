"""The adequacy criterion: every rule tag of the Lean semantics is hit.

Coverage of the specification's own rules, as ESMeta and JEST measure it
for JavaScript, replaces test counts as the measure of the differential
campaigns (docs/assurance.md, "Differential and generated testing"). The
Lean side reports the tags of `P4bloIR.Coverage` for every request; this
module reruns the retained campaigns at their fixed seeds and examples,
accumulates the tags, and compares the unhit tags of the inventory, which
`p4blo-lean coverage-inventory` prints, with `tests/drt-unhit-tags.json`.
That file lists every tag the retained campaigns cannot reach yet, with
the generator gap that keeps it unhit; it is the work list of
coverage-guided generation, and it must shrink, never grow: a tag that
stops being hit is a regression, and a listed tag that becomes hit is a
stale entry to remove. An empty file is the goal.

The campaigns are those the other differential tests retain: the corpus
sample of `tests/test_drt.py` (seed 42, 200 cases per program), the typed
scalar programs of `tests/test_drt_programs.py` (its fixed boundary
families and its derandomized Hypothesis examples), and the stateful
sequences of `tests/test_drt_stateful_programs.py` (its fixed families and
its derandomized campaigns). Every case must also agree; a divergence is
reported by those modules and fails here too, since coverage of a run that
disagrees measures nothing.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo import ir, validator
from p4blo.drt.case import Case
from p4blo.drt.coverage import RuleCoverage, rule_inventory
from p4blo.drt.programs import binary, bits, boolean, parser_condition_program, scalar_program
from p4blo.drt.run import compare, compare_program, parse_reply
from p4blo.drt.stateful_programs import UPDATE_OPS, WIDTHS, StatefulSpec, stateful_program
from p4blo.v0 import p4blo_pb2 as pb
from tests.test_drt_programs import ARITHMETIC, COMPARISONS, scalar
from tests.test_drt_programs import WIDTHS as SCALAR_WIDTHS
from tests.test_drt_stateful_programs import (
    CONDITIONS,
    WRITE_ORDERS,
    boundary_fields,
    campaigns,
    cases_for,
)

CORPUS = Path(__file__).resolve().parent / "corpus"
UNHIT = Path(__file__).resolve().parent / "drt-unhit-tags.json"
LEDGER = Path(__file__).resolve().parents[1] / "docs" / "ir-semantics.md"
WITNESSES = Path(__file__).resolve().parents[1] / "spec/arch/ArchTests/fixtures/witnesses.py"
PROGRAMS = sorted(p for p in CORPUS.iterdir() if (p / f"{p.name}.txtpb").exists())
FAKE: list[str | Path] = [sys.executable, "-m", "p4blo.drt.fake_lean"]
PORTS = 4


class Campaign:
    """Runs programs against Lean and accumulates the rule tags."""

    def __init__(self, lean: Sequence[str | Path]) -> None:
        self.lean = list(lean)
        self.coverage = RuleCoverage()
        self.failures: list[str] = []

    def program(self, program: pb.Program, cases: Sequence[Case]) -> None:
        report = compare_program(program, cases, PORTS, self.lean)
        self.coverage.update(report.rule_coverage)
        if not report.passed:
            self.failures.append(report.summary())

    def scalar(self, expression: pb.Expr, width: int | None) -> None:
        self.program(scalar_program(expression, width), [Case(pb.Entries(), 0, b"")])

    def corpus(self) -> None:
        """The corpus sample of `tests/test_drt.py`."""
        for program_dir in PROGRAMS:
            report = compare(program_dir, 42, 200, PORTS, self.lean)
            self.coverage.update(report.rule_coverage)
            if not report.passed:
                self.failures.append(report.summary())

    def scalar_families(self) -> None:
        """The fixed families of `tests/test_drt_programs.py`."""
        for value in (False, True):
            self.scalar(pb.Expr(unary=pb.Unary(op=pb.UNARY_OP_NOT, operand=boolean(value))), None)
            self.scalar(pb.Expr(cast=pb.Cast(to=pb.Type(bits=1), operand=boolean(value))), 1)
            self.scalar(
                pb.Expr(
                    cast=pb.Cast(to=pb.Type(boolean=pb.BoolType()), operand=bits(1, int(value)))
                ),
                None,
            )
            mux = pb.Mux(
                **{"condition": boolean(value), "then": bits(7, 21), "otherwise": bits(7, 106)}
            )
            self.scalar(pb.Expr(mux=mux), 7)
        for source in (1, 8, 65):
            for target in (1, 7, 8, 9, 65):
                operand = bits(source, (1 << source) - 1)
                self.scalar(pb.Expr(cast=pb.Cast(to=pb.Type(bits=target), operand=operand)), target)
        for hi, lo in ((0, 0), (7, 7), (7, 0), (6, 2)):
            self.scalar(pb.Expr(slice=pb.Slice(operand=bits(8, 0xDA), hi=hi, lo=lo)), hi - lo + 1)
        trap = pb.Expr(
            cast=pb.Cast(
                to=pb.Type(boolean=pb.BoolType()),
                operand=pb.Expr(lookahead=pb.Lookahead(type=pb.Type(bits=1))),
            )
        )
        for condition, error in [
            (binary(pb.BINARY_OP_AND, boolean(False), trap), "NoMatch"),
            (binary(pb.BINARY_OP_OR, boolean(True), trap), "NoError"),
            (binary(pb.BINARY_OP_AND, boolean(True), trap), "PacketTooShort"),
            (binary(pb.BINARY_OP_OR, boolean(False), trap), "PacketTooShort"),
            (
                pb.Expr(
                    mux=pb.Mux(
                        **{"condition": boolean(True), "then": boolean(True), "otherwise": trap}
                    )
                ),
                "NoError",
            ),
            (
                pb.Expr(
                    mux=pb.Mux(
                        **{"condition": boolean(False), "then": trap, "otherwise": boolean(True)}
                    )
                ),
                "NoError",
            ),
        ]:
            self.program(parser_condition_program(condition, error), [Case(pb.Entries(), 0, b"")])
        for width in (1, 7, 8, 9, 31, 32, 65):
            maximum = (1 << width) - 1
            for op in ARITHMETIC + COMPARISONS:
                for x, y in [(maximum, 1), (0, maximum), (maximum, maximum)]:
                    self.scalar(
                        binary(op, bits(width, x), bits(width, y)),
                        None if op in COMPARISONS else width,
                    )
            for op in (pb.BINARY_OP_SHL, pb.BINARY_OP_SHR):
                for amount in (0, width - 1, width, width + 1, 65535):
                    self.scalar(binary(op, bits(width, maximum), bits(16, amount)), width)
            self.scalar(binary(pb.BINARY_OP_CONCAT, bits(width, maximum), bits(3, 5)), width + 3)
            for op in (pb.UNARY_OP_COMPLEMENT, pb.UNARY_OP_NEGATE):
                self.scalar(pb.Expr(unary=pb.Unary(op=op, operand=bits(width, maximum))), width)
        for op in (pb.BINARY_OP_AND, pb.BINARY_OP_OR, pb.BINARY_OP_EQ, pb.BINARY_OP_NE):
            for left in (False, True):
                for right in (False, True):
                    self.scalar(binary(op, boolean(left), boolean(right)), None)

    def scalar_examples(self) -> None:
        """The derandomized Hypothesis examples of `tests/test_drt_programs.py`."""

        @settings(max_examples=200, deadline=None, derandomize=True, database=None)
        @given(data=st.data(), width=st.one_of(st.none(), SCALAR_WIDTHS))
        def run(data: st.DataObject, width: int | None) -> None:
            self.scalar(data.draw(scalar(width)), width)

        run()

    def stateful_families(self) -> None:
        """The fixed families of `tests/test_drt_stateful_programs.py`."""
        for width in WIDTHS:
            for op in UPDATE_OPS:
                for write_order in WRITE_ORDERS:
                    for read_after_write in (False, True):
                        for register_size, counter_size in ((1, 4), (4, 1)):
                            spec = StatefulSpec(
                                width,
                                register_size,
                                counter_size,
                                op,
                                write_order=write_order,
                                read_after_write=read_after_write,
                                count_updates=True,
                            )
                            self.program(
                                stateful_program(spec), cases_for(spec, boundary_fields(spec))
                            )
        for condition in CONDITIONS:
            for count_updates in (False, True):
                spec = StatefulSpec(
                    8, 2, 2, pb.BINARY_OP_ADD, condition=condition, count_updates=count_updates
                )
                fields = [(0, 2), (0, 0), (0, 1), (0, 255), (0, 0), (1, 3)]
                self.program(stateful_program(spec), cases_for(spec, fields))
        spec = StatefulSpec(8, 1, 1, pb.BINARY_OP_ADD)
        self.program(stateful_program(spec), cases_for(spec, [(0, 255), (0, 1), (1, 7), (0, 2)]))

    def stateful_examples(self) -> None:
        """The derandomized campaigns of `tests/test_drt_stateful_programs.py`."""

        @settings(max_examples=100, deadline=None, derandomize=True, database=None)
        @given(campaign=campaigns())
        def run(campaign: tuple[StatefulSpec, list[tuple[int, int]]]) -> None:
            spec, fields = campaign
            self.program(stateful_program(spec), cases_for(spec, fields))

        run()


def test_lean_agrees_and_hits_every_rule_tag(lean_binary: Path) -> None:
    inventory = rule_inventory([lean_binary])
    campaign = Campaign([lean_binary])
    campaign.corpus()
    campaign.scalar_families()
    campaign.scalar_examples()
    campaign.stateful_families()
    campaign.stateful_examples()
    assert campaign.failures == []
    assert campaign.coverage.unreported == 0, "every Lean reply must carry its coverage"
    assert campaign.coverage.unknown(inventory) == []
    unhit = set(campaign.coverage.unhit(inventory))
    known: dict[str, str] = json.loads(UNHIT.read_text(encoding="utf-8"))["unhit"]
    assert set(known) <= set(inventory), (
        f"unknown tags listed as unhit: {set(known) - set(inventory)}"
    )
    regressions = sorted(unhit - set(known))
    stale = sorted(set(known) - unhit)
    assert regressions == [], (
        f"{len(regressions)} rule tags stopped being hit by the retained campaigns:\n"
        + "\n".join(f"  {tag}: {inventory[tag]}" for tag in regressions)
    )
    assert stale == [], (
        "tags listed in tests/drt-unhit-tags.json are now hit; remove them:\n"
        + "\n".join(f"  {tag}" for tag in stale)
    )
    assert len(known) <= 33, "the unhit list grew; it may only shrink"


def test_the_unhit_list_names_reasons() -> None:
    document = json.loads(UNHIT.read_text(encoding="utf-8"))
    for tag, reason in document["unhit"].items():
        assert "." in tag and reason.strip(), tag


def test_lean_agrees_that_the_inventory_is_well_formed(lean_binary: Path) -> None:
    inventory = rule_inventory([lean_binary])
    assert len(inventory) > 100
    for tag, doc in inventory.items():
        assert tag == tag.strip() and "." in tag and " " not in tag, tag
        assert doc and "\n" not in doc, tag
    assert "parser.extract.tooShort" in inventory


def ledger_entry_names() -> set[str]:
    """The names of the ledger's entries: each bold phrase in the paragraph
    that opens an entry, without its final period. An entry that names two
    cases, such as `push_front(n)` and `pop_front(n)`, has two names."""
    names: set[str] = set()
    for entry in re.split(r"^- (?=\*\*)", LEDGER.read_text(encoding="utf-8"), flags=re.M)[1:]:
        lead = " ".join(entry.split("\n  - ")[0].split())
        names.update(m.rstrip(".") for m in re.findall(r"\*\*(.+?)\*\*", lead))
    return names


def test_lean_agrees_that_tag_citations_name_ledger_entries(lean_binary: Path) -> None:
    """A tag docstring that cites the ledger names one of its entries."""
    names = ledger_entry_names()
    assert "Header equality" in names and "`pop_front(n)`" in names
    cited = {tag: doc for tag, doc in rule_inventory([lean_binary]).items() if "ledger:" in doc}
    assert len(cited) > 80
    for tag, doc in cited.items():
        match = re.match(r"ledger: (.+?)\.(?: |$)", doc)
        assert match is not None, f"{tag}: the citation must open the docstring: {doc}"
        assert match[1] in names, f"{tag} cites no ledger entry: {match[1]!r}"


def test_lean_agrees_that_every_reply_carries_coverage(lean_binary: Path) -> None:
    """A truncated packet reports the too-short extract; an install error and
    a malformed request still carry a list."""
    program = ir.load_text(CORPUS / "forwarder" / "forwarder.txtpb")
    bad = pb.Entries()
    entry = bad.tables.add(block="MyIngress", table="ipv4_lpm").entries.add()
    entry.keys.add(lpm=pb.LpmValue(value="1", prefix_len=40))
    entry.action.action = "drop"
    cases = [Case(pb.Entries(), 0, b"\x00\x00"), Case(bad, 0, bytes(34))]
    report = compare_program(program, cases, PORTS, [lean_binary])
    assert report.divergences == [], report.summary()
    assert report.rule_coverage.unreported == 0
    assert report.rule_coverage.reported == 2
    assert report.rule_coverage.hits["parser.extract.tooShort"] == 1


def test_the_fake_reports_no_rule_tags() -> None:
    """The Python stand-in has no rule tags and does not pretend to."""
    assert rule_inventory(FAKE) == {}
    report = compare(CORPUS / "forwarder", 7, 5, PORTS, FAKE)
    assert report.rule_coverage.reported == 5
    assert report.rule_coverage.hits == {}


def test_an_older_peer_without_coverage_is_counted_not_refused() -> None:
    outcome = parse_reply('{"outputs": [], "state": {}}')
    assert outcome.coverage is None
    coverage = RuleCoverage()
    coverage.add(outcome.coverage)
    coverage.add(parse_reply('{"outputs": [], "state": {}, "coverage": ["a.b"]}').coverage)
    assert (coverage.reported, coverage.unreported) == (1, 1)
    assert coverage.unhit(["a.b", "c.d"]) == ["c.d"]
    assert coverage.unknown(["c.d"]) == ["a.b"]
    assert "1 replies carried no coverage" in coverage.describe({"a.b": "x", "c.d": "y"})


def witness_generator() -> ModuleType:
    """The generator of the Lean witness table, loaded from its path."""
    spec = importlib.util.spec_from_file_location("coverage_witnesses", WITNESSES)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Its dataclasses resolve their annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_coverage_witness_programs_are_valid_and_current() -> None:
    """Every program of the Lean witness table passes the validator, and the
    committed table is what its generator produces, replies included: the
    replies are the Python reference interpreter's, and the Lean test
    requires Lean to give the same ones."""
    generator = witness_generator()
    table = json.loads(WITNESSES.with_suffix(".json").read_text(encoding="utf-8"))
    assert len(table["programs"]) > 50 and len(table["cases"]) > 100
    for program_json in table["programs"]:
        program = ir.load_json(json.dumps(program_json))
        assert validator.validate(program) == [], program.name
    assert WITNESSES.with_suffix(".json").read_text(encoding="utf-8") == generator.render(), (
        "witnesses.json is stale; regenerate it with its generator"
    )
