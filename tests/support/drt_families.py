"""Shared drt families fixtures and campaign helpers."""

from __future__ import annotations

import hashlib
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
from hypothesis import strategies as st

from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.choice import Chooser
from p4blo.drt.families import Profile, Sample
from p4blo.drt.replay import save
from p4blo.drt.run import ProtocolError, compare_program
from p4blo.interp import stmt

FAKE: list[str | Path] = [sys.executable, "-m", "p4blo.drt.fake_lean"]

MEASUREMENT = (
    Path(__file__).resolve().parents[2] / "tests/conformance/coverage/guided-measurement.json"
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
