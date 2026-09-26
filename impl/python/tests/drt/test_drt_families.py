"""Package checks without native oracle dependencies."""

from __future__ import annotations

import json

import pytest

from p4blo.arch import validator
from p4blo.drt import guided
from p4blo.drt.families import FAMILIES, TARGETS, Profile, sample
from tests.support.drt_families import FAKE, MEASUREMENT, PROFILES, spectec_parsers_are_acyclic

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
