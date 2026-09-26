"""Shared drt coverage fixtures and campaign helpers."""

from __future__ import annotations

import importlib.util
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.coverage import RuleCoverage
from p4blo.drt.families import FAMILIES, sample
from p4blo.drt.generate import generate
from p4blo.drt.programs import (
    ARITHMETIC,
    COMPARISONS,
    binary,
    bits,
    boolean,
    parser_condition_program,
    scalar_program,
)
from p4blo.drt.run import compare, compare_program
from p4blo.drt.stateful_programs import UPDATE_OPS, WIDTHS, StatefulSpec, stateful_program
from p4blo.v0 import p4blo_pb2 as pb
from tests.support.drt import mixed
from tests.support.drt_families import SEEDS as FAMILY_SEEDS
from tests.support.drt_programs import WIDTHS as SCALAR_WIDTHS
from tests.support.drt_programs import scalar
from tests.support.drt_stateful_programs import (
    CONDITIONS,
    WRITE_ORDERS,
    boundary_fields,
    campaigns,
    cases_for,
)

CORPUS = Path(__file__).resolve().parents[2] / "tests/programs/corpus"

UNHIT = Path(__file__).resolve().parents[2] / "tests/conformance/coverage/unhit-tags.json"

LEDGER = Path(__file__).resolve().parents[2] / "docs/ir-semantics.md"

WITNESSES = Path(__file__).resolve().parents[2] / "spec/arch/P4bloArchTest/fixtures/witnesses.py"

PROGRAMS = sorted(p for p in CORPUS.iterdir() if (p / f"{p.name}.txtpb").exists())

FAKE: list[str | Path] = [sys.executable, "-m", "p4blo.drt.fake_lean"]

PORTS = 4


class Campaign:
    """Runs programs against Lean and accumulates the rule tags."""

    def __init__(self, lean: Sequence[str | Path]) -> None:
        self.lean = list(lean)
        self.coverage = RuleCoverage()
        self.failures: list[str] = []

    def program(self, program: apb.BlockAssembly, cases: Sequence[Case]) -> None:
        report = compare_program(program, cases, PORTS, self.lean)
        self.coverage.update(report.rule_coverage)
        if not report.passed:
            self.failures.append(report.summary())

    def scalar(self, expression: pb.Expr, width: int | None) -> None:
        self.program(scalar_program(expression, width), [Case(pb.Entries(), 0, b"")])

    def corpus_program(self, program_dir: Path) -> None:
        """One corpus program sampled as `tests/conformance/execution/test_drt.py` samples it."""
        report = compare(program_dir, 42, 200, PORTS, self.lean)
        self.coverage.update(report.rule_coverage)
        if not report.passed:
            self.failures.append(report.summary())

    def corpus(self) -> None:
        """The corpus sample of `tests/conformance/execution/test_drt.py`."""
        for program_dir in PROGRAMS:
            self.corpus_program(program_dir)

    def mixed(self) -> None:
        """The MIXED execution program, sampled as the corpus is."""
        program = mixed()
        self.program(program, generate(BoundIndex.build(program), 42, 200, PORTS))

    def shape_family(self, family: str) -> None:
        """One family at the fixed seeds of `tests/conformance/execution/test_drt_families.py`."""
        for seed in FAMILY_SEEDS:
            generated = sample(family, seed)
            self.program(generated.program, generated.cases)

    def shape_families(self) -> None:
        """The fixed seeds of `tests/conformance/execution/test_drt_families.py`."""
        for family in sorted(FAMILIES):
            self.shape_family(family)

    def scalar_families(self) -> None:
        """The fixed families of `tests/conformance/execution/test_drt_programs.py`."""
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
        """The derandomized Hypothesis examples of the generated program suite."""

        @settings(max_examples=200, deadline=None, derandomize=True, database=None)
        @given(data=st.data(), width=st.one_of(st.none(), SCALAR_WIDTHS))
        def run(data: st.DataObject, width: int | None) -> None:
            self.scalar(data.draw(scalar(width)), width)

        run()

    def stateful_families(self) -> None:
        """The fixed families of `tests/conformance/execution/test_drt_stateful_programs.py`."""
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
        """The derandomized campaigns of the stateful program suite."""

        @settings(max_examples=100, deadline=None, derandomize=True, database=None)
        @given(campaign=campaigns())
        def run(campaign: tuple[StatefulSpec, list[tuple[int, int]]]) -> None:
            spec, fields = campaign
            self.program(stateful_program(spec), cases_for(spec, fields))

        run()


PARTS_DIR = Path(__file__).resolve().parents[2] / "tests/conformance/coverage/parts"

CAMPAIGN_PARTS = (
    [f"corpus:{p.name}" for p in PROGRAMS]
    + ["mixed"]
    + [f"shape:{family}" for family in sorted(FAMILIES)]
    + ["scalar_families", "scalar_examples", "stateful_families", "stateful_examples"]
)


def run_part(campaign: Campaign, part: str) -> None:
    """Run one named part of the retained campaigns."""
    kind, _, argument = part.partition(":")
    if kind == "corpus":
        campaign.corpus_program(CORPUS / argument)
    elif kind == "shape":
        campaign.shape_family(argument)
    else:
        getattr(campaign, kind)()


def ledger_entry_names() -> set[str]:
    """The names of the ledger's entries: each bold phrase in the paragraph
    that opens an entry, without its final period. An entry that names two
    cases, such as `push_front(n)` and `pop_front(n)`, has two names."""
    names: set[str] = set()
    for entry in re.split(r"^- (?=\*\*)", LEDGER.read_text(encoding="utf-8"), flags=re.M)[1:]:
        lead = " ".join(entry.split("\n  - ")[0].split())
        names.update(m.rstrip(".") for m in re.findall(r"\*\*(.+?)\*\*", lead))
    return names


def witness_generator() -> ModuleType:
    """The generator of the Lean witness table, loaded from its path."""
    spec = importlib.util.spec_from_file_location("coverage_witnesses", WITNESSES)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Its dataclasses resolve their annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
