"""Real Lean execution conformance."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from p4blo.drt import guided
from p4blo.drt.families import FAMILIES, sample
from p4blo.drt.run import compare_program
from p4blo.interp import stmt
from tests.support.drt_families import (
    MEASUREMENT,
    SEEDS,
    HypothesisChooser,
    check,
    pop_unclamped,
    push_unclamped,
)

# ---------------------------------------------------------------------------
# Lean
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("family", sorted(FAMILIES))
@pytest.mark.lean
def test_lean_agrees_on_family_seeds(family: str, lean_binary: Path) -> None:
    for seed in SEEDS:
        check(sample(family, seed), [lean_binary], seed)


@pytest.mark.parametrize("family", sorted(FAMILIES))
@pytest.mark.lean
def test_lean_agrees_on_spectec_profile_seeds(family: str, lean_binary: Path) -> None:
    for seed in range(50):
        check(sample(family, seed, "spectec"), [lean_binary], seed)


@settings(max_examples=100, deadline=None, derandomize=True, database=None)
@given(data=st.data(), family=st.sampled_from(sorted(FAMILIES)))
@pytest.mark.lean
def test_lean_agrees_on_shrinking_family_programs(
    lean_binary: Path, data: st.DataObject, family: str
) -> None:
    check(FAMILIES[family](HypothesisChooser(data.draw), "lean"), [lean_binary])


@pytest.mark.parametrize(
    ("name", "mutant", "feature"),
    [
        ("push_front", push_unclamped, "stmt=push"),
        ("pop_front", pop_unclamped, "stmt=pop"),
    ],
    ids=["push", "pop"],
)
@pytest.mark.lean
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


@pytest.mark.lean
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
