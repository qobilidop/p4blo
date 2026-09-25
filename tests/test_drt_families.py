"""The shape families.

`p4blo.drt.families` builds programs from named decisions. Here the same
families run from fixed seeds and from Hypothesis, whose shrinking keeps
every decision inside its typed menu, so a failure shrinks to a smaller
well-typed program. Every program goes through the ordinary validator; a
program it refuses fails the test, never a filter.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo import validator
from p4blo.drt.choice import Chooser
from p4blo.drt.families import FAMILIES, TARGETS, Profile, Sample, sample
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program
from p4blo.v0 import p4blo_pb2 as pb

PROFILES: tuple[Profile, ...] = ("lean", "spectec")
# The seeds the Lean campaigns retain, per family.
SEEDS = range(200)


class HypothesisChooser(Chooser):
    """Decisions drawn from Hypothesis data: an option shrinks toward the
    first, a number toward its lower bound."""

    def __init__(self, data: st.DataObject) -> None:
        super().__init__()
        self.data = data

    def pick(self, point: str, options: Sequence[str]) -> str:
        return self.data.draw(st.sampled_from(list(options)), label=point)

    def integer(self, point: str, lo: int, hi: int) -> int:
        return self.data.draw(st.integers(lo, hi), label=point)


def check(generated: Sample, lean: Sequence[str | Path]) -> None:
    """Compare the sample; on disagreement save a replay bundle and fail."""
    try:
        report = compare_program(generated.program, generated.cases, 4, lean)
    except ProtocolError as error:
        if error.report is None:
            raise
        report = error.report
    if not report.passed:
        target = Path(os.environ.get("P4BLO_DRT_FAILURE_DIR", ".artifacts/drt"))
        target.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(generated.program.SerializeToString()).hexdigest()[:16]
        bundle = target / f"{generated.family}-{digest}.json"
        save(report, bundle)
        pytest.fail(
            f"{generated.describe()}\n{report.summary()}; replay {bundle}\n"
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
# Lean
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_lean_agrees_on_family_seeds(family: str, lean_binary: Path) -> None:
    for seed in SEEDS:
        check(sample(family, seed), [lean_binary])


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_lean_agrees_on_spectec_profile_seeds(family: str, lean_binary: Path) -> None:
    for seed in range(50):
        check(sample(family, seed, "spectec"), [lean_binary])


@settings(max_examples=100, deadline=None, derandomize=True, database=None)
@given(data=st.data(), family=st.sampled_from(sorted(FAMILIES)))
def test_lean_agrees_on_shrinking_family_programs(
    lean_binary: Path, data: st.DataObject, family: str
) -> None:
    check(FAMILIES[family](HypothesisChooser(data), "lean"), [lean_binary])
