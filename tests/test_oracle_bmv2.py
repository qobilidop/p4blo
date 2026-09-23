"""Claim 2's second oracle: every corpus vector replays on BMv2's simple_switch.

The oracle is p4c's BMv2 backend and `simple_switch` in the `p4blo-bmv2`
Docker image (oracle/bmv2/Dockerfile), driven by oracle/bmv2/run.py. Without
Docker or without the image every replay test skips and says how to build it;
with them, each `corpus/<program>/*.stf` must pass, where a divergence and an
oracle-side error (a construct the switch cannot load, a crash, a timeout)
are both failures, labeled apart as in tests/test_oracle.py: the second is not
a disagreement, but it leaves the claim unchecked.

One vector is a known, analysed divergence and is marked `xfail`: see
`KNOWN_DIVERGENCES` below and oracle/bmv2/README.md.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from oracle.bmv2 import run as bmv2_run  # noqa: E402

CORPUS = ROOT / "corpus"
VECTORS = sorted(CORPUS.glob("*/*.stf"))

# A vector p4blo and BMv2 genuinely disagree about, with the reason. Strict,
# so that a vector that starts passing fails here and the entry is removed
# rather than left to rot.
KNOWN_DIVERGENCES = {
    "register_bounds/bounds.stf": (
        "an out-of-range register read yields zero in p4blo (docs/semantics.md, "
        '"Externs") and leaves the destination field untouched in BMv2 '
        "(targets/simple_switch/primitives.cpp, `register_read`); see "
        "oracle/bmv2/README.md"
    ),
}


def program_of(vector: Path) -> Path:
    """The one IR text file beside a vector."""
    programs = sorted(vector.parent.glob("*.txtpb"))
    assert len(programs) == 1, f"{vector.parent} should hold exactly one .txtpb"
    return programs[0]


def vector_id(vector: Path) -> str:
    return f"{vector.parent.name}/{vector.name}"


def marks(vector: Path) -> list[pytest.MarkDecorator]:
    """`xfail`, strictly, when the vector is a known divergence; nothing else."""
    known = KNOWN_DIVERGENCES.get(vector_id(vector))
    return [] if known is None else [pytest.mark.xfail(reason=known, strict=True)]


PARAMETERS = [pytest.param(v, marks=marks(v), id=vector_id(v)) for v in VECTORS]


@pytest.fixture(scope="module")
def image() -> str:
    """The Docker image, or a skip saying why the oracle cannot run here."""
    name = bmv2_run.default_image()
    reason = bmv2_run.unavailable(name)
    if reason is not None:
        pytest.skip(f"the BMv2 oracle is not available: {reason} (see oracle/bmv2/README.md)")
    return name


# ---------------------------------------------------------------------------
# The translation, which needs no oracle
# ---------------------------------------------------------------------------


def test_use_last_rewrites_the_printed_last_index_form() -> None:
    # p4c compiles `stack.last.f` in a select into BMv2's `stack_field` key
    # and `stack[stack.lastIndex].f` into a dynamic index simple_switch
    # refuses to load, so the printed program is rewritten (oracle/bmv2/run.py).
    p4 = (
        "        verify(hdr.h2[hdr.h2.lastIndex].hdr_type == 8w2, error.BadHeaderType);\n"
        "        transition select(hdr.h2[hdr.h2.lastIndex].next_hdr_type) {\n"
        "        packet.extract(hdr.h2.next);\n"
        "        x = hdr.h2[3].f;\n"
    )
    rewritten, notes = bmv2_run.use_last(p4)
    assert rewritten.splitlines() == [
        "        verify(hdr.h2.last.hdr_type == 8w2, error.BadHeaderType);",
        "        transition select(hdr.h2.last.next_hdr_type) {",
        "        packet.extract(hdr.h2.next);",
        "        x = hdr.h2[3].f;",
    ]
    assert len(notes) == 2 and notes[0].startswith("printed line 1: ")


def test_use_last_leaves_an_index_by_another_stack_alone() -> None:
    # The rewrite is sound only when the indexed stack is the one the
    # `lastIndex` belongs to; anything else is a different expression.
    p4 = "x = hdr.h2[hdr.h3.lastIndex].f;\n"
    rewritten, notes = bmv2_run.use_last(p4)
    assert rewritten == p4 and notes == []


def test_every_corpus_vector_parses_and_has_one_program() -> None:
    assert VECTORS, "no corpus vectors found"
    for vector in VECTORS:
        assert program_of(vector).is_file()


# ---------------------------------------------------------------------------
# The replay
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vector", PARAMETERS)
def test_vector_passes_on_bmv2(image: str, vector: Path) -> None:
    (verdict,) = bmv2_run.run(image, program_of(vector), [vector])
    where = f"{vector.relative_to(ROOT)}\ncommand: {shlex.join(verdict.command)}"
    if verdict.status == "fail":
        pytest.fail(f"DIVERGENCE: BMv2 disagrees on {where}\n{verdict.detail}")
    if verdict.status == "error":
        pytest.fail(f"ORACLE ERROR (not a divergence): could not judge {where}\n{verdict.detail}")
    if verdict.status == "skip":
        pytest.skip(verdict.detail)
    assert verdict.status == "pass", verdict
