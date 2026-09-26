"""Shared test inputs and checks; no test-module dependencies."""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest
from tests.support.catalog import CORPUS, program_of

from tests.oracles.bmv2 import run as bmv2_run

ROOT = Path(__file__).resolve().parents[2]


KNOWN_DIVERGENCES = {
    "register_bounds/bounds.stf": (
        "an out-of-range register read yields zero in p4blo (docs/arch-supports.md, "
        '"Externs") and leaves the destination field untouched in BMv2 '
        "(targets/simple_switch/primitives.cpp, `register_read`); see "
        "tests/oracles/bmv2/README.md"
    ),
}

REGISTER_BOUNDS_DETAIL = (
    "line 46: expected 040700 $ on port 0, got 0407ff\n"
    "line 52: expected ff0100 $ on port 0, got ff01ff"
)


class KnownBMv2RegisterBoundsDisagreement(Exception):
    """Only the two documented unchanged-destination outputs, not oracle errors."""


def known_register_bounds_disagreement(verdict: bmv2_run.Verdict) -> bool:
    return (
        verdict.vector == CORPUS / "register_bounds/bounds.stf"
        and verdict.status == "fail"
        and verdict.detail == REGISTER_BOUNDS_DETAIL
    )


PRIORITY_SOURCE = ROOT / "tests/oracles/frontend/p4c/table-entries-priority-bmv2.p4"

PRIORITY_VECTOR = CORPUS / "priority" / "table_entries_priority.stf"

PRIORITY_PORTS = [0, 1, 2, 3]

PRIORITY_DETAIL = (
    "line 30: no output packet on port 1\n"
    "line 34: unexpected output on port 3: 0210010000b0\n"
    "line 34: unexpected output on port 3: 0311810000b0\n"
    "line 35: no output packet on port 1"
)


class KnownBMv2PriorityDisagreement(Exception):
    """Only p4c's inverted const-entry order on the two documented packets."""


def known_priority_disagreement(verdict: bmv2_run.Verdict) -> bool:
    return (
        verdict.vector == PRIORITY_VECTOR
        and verdict.status == "fail"
        and verdict.detail == PRIORITY_DETAIL
    )


def vector_id(vector: Path) -> str:
    return f"{vector.parent.name}/{vector.name}"


def marks(vector: Path) -> list[pytest.MarkDecorator]:
    """`xfail`, strictly, when the vector is a known divergence; nothing else."""
    known = KNOWN_DIVERGENCES.get(vector_id(vector))
    return (
        []
        if known is None
        else [
            pytest.mark.xfail(reason=known, strict=True, raises=KnownBMv2RegisterBoundsDisagreement)
        ]
    )


def check_vector(image: str, vector: Path) -> None:
    (verdict,) = bmv2_run.run(image, program_of(vector), [vector])
    where = f"{vector.relative_to(ROOT)}\ncommand: {shlex.join(verdict.command)}"
    if known_register_bounds_disagreement(verdict):
        raise KnownBMv2RegisterBoundsDisagreement(f"{where}\n{verdict.detail}")
    if verdict.status == "fail":
        pytest.fail(f"DIVERGENCE: BMv2 disagrees on {where}\n{verdict.detail}")
    if verdict.status == "error":
        pytest.fail(f"ORACLE ERROR (not a divergence): could not judge {where}\n{verdict.detail}")
    assert verdict.status == "pass", verdict
