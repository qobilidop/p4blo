"""The shape families and the coverage-guided driver.

`p4blo.drt.families` builds programs from named decisions. Here the same
families run three ways: from fixed seeds, as tests/test_drt_coverage.py
retains them; from Hypothesis, whose shrinking keeps every decision inside
its typed menu, so a failure shrinks to a smaller well-typed program; and
under `p4blo.drt.guided`, whose determinism and weighting are checked
without Lean. Every program goes through the ordinary validator; a program
it refuses fails the test, never a filter.
"""

from __future__ import annotations

import hashlib
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo import validator
from p4blo.drt import guided
from p4blo.drt.choice import Chooser
from p4blo.drt.families import FAMILIES, TARGETS, Profile, Sample, sample
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program
from p4blo.v0 import p4blo_pb2 as pb

FAKE: list[str | Path] = [sys.executable, "-m", "p4blo.drt.fake_lean"]
PROFILES: tuple[Profile, ...] = ("lean", "spectec")
# The seeds the Lean campaigns retain, per family; tests/test_drt_coverage.py
# reruns the same ones for the unhit list.
SEEDS = range(200)


class HypothesisChooser(Chooser):
    """Decisions drawn by Hypothesis, from `data.draw` or a composite's
    `draw`: an option shrinks toward the first, a number toward its lower
    bound."""

    def __init__(self, draw: st.DrawFn | Callable[[st.SearchStrategy[Any]], Any]) -> None:
        super().__init__()
        self.draw = draw

    def pick(self, point: str, options: Sequence[str]) -> str:
        return self.draw(st.sampled_from(list(options)))

    def integer(self, point: str, lo: int, hi: int) -> int:
        return self.draw(st.integers(lo, hi))


def check(generated: Sample, lean: Sequence[str | Path], seed: int | None = None) -> None:
    """Compare the sample; on disagreement save a replay bundle and fail.
    The family seed, when the sample has one, names the failure and the
    bundle, so `families.sample(family, seed)` rebuilds the program."""
    try:
        report = compare_program(generated.program, generated.cases, 4, lean, seed or 0)
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        target = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        target.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(generated.program.SerializeToString()).hexdigest()[:16]
        named = "" if seed is None else f"-seed{seed}"
        bundle = target / f"{generated.family}{named}-{digest}.json"
        save(report, bundle)
        where = "a Hypothesis example" if seed is None else f"family seed {seed}"
        pytest.fail(
            f"{generated.describe()} ({where})\n{report.summary()}; replay {bundle}\n"
            + "\n".join(d.describe() for d in report.divergences[:3])
            + f"\n{report.protocol_error or ''}"
        )


# ---------------------------------------------------------------------------
# Generation, without Lean
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_every_seed_is_a_valid_program(family: str, profile: Profile) -> None:
    for seed in range(60):
        generated = sample(family, seed, profile)
        assert validator.validate(generated.program) == [], (seed, generated.describe())
        assert generated.cases and generated.features


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_a_seed_names_its_sample_exactly(family: str) -> None:
    first = sample(family, 7)
    assert sample(family, 7) == first
    assert sample(family, 8) != first


def spectec_parsers_are_acyclic(program: pb.Program) -> bool:
    """Every state transition goes to a later state of its block."""
    for block in program.blocks:
        order = {state.name: i for i, state in enumerate(block.states)}
        for i, state in enumerate(block.states):
            t = state.transition
            targets = (
                [t.direct]
                if t.WhichOneof("kind") == "direct"
                else [c.target for c in t.select.cases]
            )
            for target in targets:
                if target.WhichOneof("kind") == "state" and order[target.state] <= i:
                    return False
    return True


def test_the_spectec_profile_leaves_out_the_ledgers_deviations() -> None:
    """No loops, one sub-parser call at most, headers compared only while
    valid, no out-of-range stack reads and no lastIndex before an extract:
    the choices the profile removes are the ledger's deviations."""
    lean_features: set[str] = set()
    spectec_features: set[str] = set()
    for seed in range(200):
        for family in FAMILIES:
            lean_features |= sample(family, seed, "lean").features
            generated = sample(family, seed, "spectec")
            spectec_features |= generated.features
            assert spectec_parsers_are_acyclic(generated.program), (family, seed)
            calls = [
                s
                for b in generated.program.blocks
                for state in b.states
                for s in state.body
                if s.WhichOneof("kind") == "call_block"
            ]
            assert len(calls) <= 1
            assert all(c.packet for c in generated.cases), "STF cannot send an empty packet"
    removed = lean_features - spectec_features
    for feature in [
        "validity=invalid",
        "validity=packet",
        "parser.transition=loop",
        "subparser.transition=loop",
        "eq_stack.push=packet",
    ]:
        assert feature in removed, feature
    assert "stack.use=read" in spectec_features  # in range, from the masked index


def test_targets_name_decisions_the_families_take() -> None:
    features: set[str] = set()
    for seed in range(200):
        for family in FAMILIES:
            features |= sample(family, seed).features
    assert set(TARGETS) <= features, set(TARGETS) - features


# ---------------------------------------------------------------------------
# The guided driver, without Lean
# ---------------------------------------------------------------------------


def test_the_guide_prefers_options_whose_targets_are_unhit() -> None:
    inventory = {"call.action": "", "stmt.callAction": "", "expr.literal": ""}
    guide = guided.Guide(inventory)
    unhit = guide.weight("control.feature=call")
    assert unhit > guide.weight("control.feature=eq_enum") == 1.0
    guide.observe(frozenset({"control.feature=call"}), {"call.action", "stmt.callAction"})
    # The targets are hit; what is left is the novelty of the first use.
    assert 1.0 < guide.weight("control.feature=call") < unhit
    for _ in range(30):
        guide.observe(frozenset({"control.feature=call"}), {"call.action"})
    assert guide.weight("control.feature=call") == pytest.approx(1.0, abs=0.01)


def test_the_guide_counts_tag_feature_pairs() -> None:
    guide = guided.Guide({"a.b": "", "c.d": ""})
    assert guide.observe(frozenset({"x=1", "y=2"}), {"a.b"}) == (1, 2)
    assert guide.observe(frozenset({"x=1", "z=3"}), {"a.b"}) == (0, 1)
    assert guide.observe(frozenset({"x=1"}), {"a.b", "c.d"}) == (1, 1)
    assert guide.pairs == {("a.b", "x=1"), ("a.b", "y=2"), ("a.b", "z=3"), ("c.d", "x=1")}


def test_a_guided_campaign_is_a_function_of_its_seed() -> None:
    """Through the fake peer, which reports no tags: the campaign still runs
    every sample, and the same seed makes the same programs."""
    runs = [
        guided.guided_campaign("parser", FAKE, seed=3, budget=4, inventory={}) for _ in range(2)
    ]
    assert runs[0].samples == runs[1].samples == 4
    assert runs[0].failures == [] and runs[0].requests == 16
    chooser = [guided.GuidedChooser(guided.sample_rng(3, 0), None) for _ in range(2)]
    assert FAMILIES["control"](chooser[0], "lean") == FAMILIES["control"](chooser[1], "lean")


def test_the_command_line_runs_a_guided_campaign(capsys: pytest.CaptureFixture[str]) -> None:
    from p4blo.drt.__main__ import main

    assert main(["guided", "control", "2", "--fake", "--seed", "5"]) == 0
    out = capsys.readouterr().out
    assert "control: seed 5, 2 programs, 8 requests, 0 disagreed" in out


# ---------------------------------------------------------------------------
# Lean
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_lean_agrees_on_family_seeds(family: str, lean_binary: Path) -> None:
    for seed in SEEDS:
        check(sample(family, seed), [lean_binary], seed)


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_lean_agrees_on_spectec_profile_seeds(family: str, lean_binary: Path) -> None:
    for seed in range(50):
        check(sample(family, seed, "spectec"), [lean_binary], seed)


@settings(max_examples=100, deadline=None, derandomize=True, database=None)
@given(data=st.data(), family=st.sampled_from(sorted(FAMILIES)))
def test_lean_agrees_on_shrinking_family_programs(
    lean_binary: Path, data: st.DataObject, family: str
) -> None:
    check(FAMILIES[family](HypothesisChooser(data.draw), "lean"), [lean_binary])
