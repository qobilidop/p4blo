"""The shape families and the coverage-guided driver.

`p4blo.drt.families` builds programs from named decisions. Here the same
families run three ways: from fixed seeds, as tests/conformance/execution/test_drt_coverage.py
retains them; from Hypothesis, whose shrinking keeps every decision inside
its typed menu, so a failure shrinks to a smaller well-typed program; and
under `p4blo.drt.guided`, whose determinism and weighting are checked
without Lean. Every program goes through the ordinary validator; a program
it refuses fails the test, never a filter.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo.arch import validator
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt import guided
from p4blo.drt.choice import Chooser
from p4blo.drt.families import FAMILIES, TARGETS, Profile, Sample, sample
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program
from p4blo.interp import stmt

FAKE: list[str | Path] = [sys.executable, "-m", "p4blo.drt.fake_lean"]
MEASUREMENT = (
    Path(__file__).resolve().parents[3] / "tests/conformance/coverage/guided-measurement.json"
)
PROFILES: tuple[Profile, ...] = ("lean", "spectec")
# The seeds the Lean campaigns retain, per family; tests/conformance/execution/test_drt_coverage.py
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


def spectec_parsers_are_acyclic(program: apb.BlockAssembly) -> bool:
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
        "eq_header.validity=invalid",
        "eq_header.validity=packet",
        "parser.stmt=push",
        "parser.stmt=pop",
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
    guide.observe(frozenset({"control.feature=call"}), {"call.action"})
    # One target is still unhit.
    assert guide.weight("control.feature=call") == unhit
    guide.observe(frozenset({"control.feature=call"}), {"stmt.callAction"})
    # Both targets are hit: the option is weighted like any other.
    assert guide.weight("control.feature=call") == 1.0


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


def test_the_recorded_measurement_is_whole_and_supports_the_claim() -> None:
    """tests/conformance/coverage/guided-measurement.json has a row per family, seed and arm,
    its summary is what its rows give, and it shows what docs/assurance.md
    says: guided campaigns hit the common targets in fewer programs than
    uniform ones, on average and in most seeds, in both families, and
    reach as many tags."""
    document = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    runs = document["runs"]
    assert sorted((r["family"], r["seed"], r["arm"]) for r in runs) == sorted(
        (f, s, a) for f in guided.MEASURED_FAMILIES for s in document["seeds"] for a in guided.ARMS
    )
    assert document["summary"] == guided.summarize(runs)
    assert document["target_bonus"] == guided.TARGET_BONUS
    for family in guided.MEASURED_FAMILIES:
        arms = document["summary"][family]["arms"]
        g, u = arms["guided"], arms["uniform"]
        assert g["to_targets"]["mean"] < u["to_targets"]["mean"], family
        pairs = zip(g["to_targets"]["per_seed"], u["to_targets"]["per_seed"], strict=True)
        fewer = sum(a < b for a, b in pairs)
        assert fewer > len(document["seeds"]) * 3 // 4, family
        assert abs(g["tags"]["mean"] - u["tags"]["mean"]) < 1, family


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


RIGHT_PUSH_FRONT = stmt.push_front
RIGHT_POP_FRONT = stmt.pop_front


def push_unclamped(stack: Any, n: int, index: Any) -> None:
    """`push_front` whose `nextIndex` grows past the size."""
    next_index = stack.next_index
    RIGHT_PUSH_FRONT(stack, n, index)
    stack.next_index = next_index + n


def pop_unclamped(stack: Any, n: int, index: Any) -> None:
    """`pop_front` whose `nextIndex` shrinks below zero."""
    next_index = stack.next_index
    RIGHT_POP_FRONT(stack, n, index)
    stack.next_index = next_index - n


@pytest.mark.parametrize(
    ("name", "mutant", "feature"),
    [
        ("push_front", push_unclamped, "stmt=push"),
        ("pop_front", pop_unclamped, "stmt=pop"),
    ],
    ids=["push", "pop"],
)
def test_lean_agrees_only_with_the_stack_clamps(
    lean_binary: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    mutant: Callable[[Any, int, Any], None],
    feature: str,
) -> None:
    """`stack.push.clamp` and `stack.pop.clamp` are observable: a Python
    without the clamp disagrees with Lean on some retained parser seed that
    pushes or pops, because the family reads `nextIndex` afterwards."""
    monkeypatch.setattr(stmt, name, mutant)
    for seed in SEEDS:
        generated = sample("parser", seed)
        if not any(f.endswith(feature) for f in generated.features):
            continue
        report = compare_program(generated.program, generated.cases, 4, [lean_binary], seed)
        if not report.passed:
            return
    pytest.fail(f"no retained parser seed tells {name} without its clamp from Lean")


def test_lean_agrees_with_the_recorded_guided_measurement(lean_binary: Path) -> None:
    """The first seed's rows of tests/conformance/coverage/guided-measurement.json come out
    the same when run again, so the document is what `python -m p4blo.drt
    guided measure` makes today; a change to the families, the guidance or
    Lean's tags that moves them means regenerating it (and rereading the
    claim it supports)."""
    document = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    seed = document["seeds"][0]
    for family in guided.MEASURED_FAMILIES:
        for arm in guided.ARMS:
            recorded = next(
                r
                for r in document["runs"]
                if (r["family"], r["seed"], r["arm"]) == (family, seed, arm)
            )
            run = guided.measured_run(family, seed, arm, document["budget"], [lean_binary])
            assert run == recorded, (
                f"{family} seed {seed} {arm} moved; regenerate with python -m p4blo.drt "
                "guided measure --jobs 8 --out tests/conformance/coverage/guided-measurement.json"
            )
