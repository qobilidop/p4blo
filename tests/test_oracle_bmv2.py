"""Claim 2's second oracle: every corpus vector replays on BMv2's simple_switch.

The oracle is p4c's BMv2 backend and `simple_switch` in the `p4blo-bmv2`
Docker image (tests/oracle/bmv2/Dockerfile), driven by tests/oracle/bmv2/run.py. Without
Docker or without the image every replay test skips and says how to build it;
with them, each `tests/corpus/<program>/*.stf` must pass, where a divergence and an
oracle-side error (a construct the switch cannot load, a crash, a timeout)
are both failures, labeled apart as in tests/test_oracle.py: the second is not
a disagreement, but it leaves the claim unchecked.

One vector is a known, analysed divergence and is marked `xfail`: see
`KNOWN_DIVERGENCES` below and tests/oracle/bmv2/README.md.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.oracle import firewall  # noqa: E402
from tests.oracle.bmv2 import run as bmv2_run  # noqa: E402

CORPUS = ROOT / "tests" / "corpus"
VECTORS = sorted([*CORPUS.glob("*/*.stf"), *(ROOT / "tests/examples").glob("*/*.stf")])

# A vector p4blo and BMv2 genuinely disagree about, with the reason. Strict,
# so that a vector that starts passing fails here and the entry is removed
# rather than left to rot.
KNOWN_DIVERGENCES = {
    "register_bounds/bounds.stf": (
        "an out-of-range register read yields zero in p4blo (docs/arch-supports.md, "
        '"Externs") and leaves the destination field untouched in BMv2 '
        "(targets/simple_switch/primitives.cpp, `register_read`); see "
        "tests/oracle/bmv2/README.md"
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
    return (
        []
        if known is None
        else [
            pytest.mark.xfail(reason=known, strict=True, raises=KnownBMv2RegisterBoundsDisagreement)
        ]
    )


PARAMETERS = [pytest.param(v, marks=marks(v), id=vector_id(v)) for v in VECTORS]


@pytest.fixture(scope="module")
def image() -> str:
    """The Docker image, or a skip saying why the oracle cannot run here."""
    name = bmv2_run.default_image()
    reason = bmv2_run.unavailable(name)
    if reason is not None:
        pytest.skip(f"the BMv2 oracle is not available: {reason} (see tests/oracle/bmv2/README.md)")
    return name


# ---------------------------------------------------------------------------
# The translation, which needs no oracle
# ---------------------------------------------------------------------------


def test_use_last_rewrites_the_printed_last_index_form() -> None:
    # p4c compiles `stack.last.f` in a select into BMv2's `stack_field` key
    # and `stack[stack.lastIndex].f` into a dynamic index simple_switch
    # refuses to load, so the printed program is rewritten (tests/oracle/bmv2/run.py).
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


def test_original_firewall_on_bmv2(image: str) -> None:
    compiled = bmv2_run.compile_program(image, firewall.source())
    plan = firewall.plan()
    reply = bmv2_run._driver(image, "replay", json.dumps(plan.request(compiled)))
    assert len(reply["phases"]) == 1, reply
    assert not reply["phases"][0]["error"], reply
    assert "error" not in reply["phases"][0]["cli"].lower(), reply
    assert bmv2_run.judge(plan, reply) == ("pass", "")


def test_original_firewall_observer_rejects_premature_ack() -> None:
    plan = firewall.plan()
    expected = {str(e.port): [e.data.hex()] for e in plan.phases[0].expects}
    assert bmv2_run.judge(plan, {"phases": [{"outputs": expected}]}) == ("pass", "")
    # An ACK admitted before SYN must not stand in for the later allowed ACK.
    premature = bytearray.fromhex(expected["1"][0])
    premature[38:42] = (1).to_bytes(4, "big")
    expected["1"] = [premature.hex()]
    verdict, _ = bmv2_run.judge(plan, {"phases": [{"outputs": expected}]})
    assert verdict == "fail"


# ---------------------------------------------------------------------------
# The replay
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vector", PARAMETERS)
def test_vector_passes_on_bmv2(image: str, vector: Path) -> None:
    (verdict,) = bmv2_run.run(image, program_of(vector), [vector])
    where = f"{vector.relative_to(ROOT)}\ncommand: {shlex.join(verdict.command)}"
    if known_register_bounds_disagreement(verdict):
        raise KnownBMv2RegisterBoundsDisagreement(f"{where}\n{verdict.detail}")
    if verdict.status == "fail":
        pytest.fail(f"DIVERGENCE: BMv2 disagrees on {where}\n{verdict.detail}")
    if verdict.status == "error":
        pytest.fail(f"ORACLE ERROR (not a divergence): could not judge {where}\n{verdict.detail}")
    if verdict.status == "skip":
        pytest.skip(verdict.detail)
    assert verdict.status == "pass", verdict


@pytest.mark.parametrize("status", ["error", "pass", "known", "changed"])
def test_known_bmv2_marker_does_not_hide_errors_or_corrections(tmp_path: Path, status: str) -> None:
    """Exercise pytest's actual marker, not just metadata or the predicate."""
    source = tmp_path / "test_marker.py"
    source.write_text(
        "from tests.test_oracle_bmv2 import CORPUS, marks, bmv2_run, REGISTER_BOUNDS_DETAIL\n"
        "from tests.test_oracle_bmv2 import test_vector_passes_on_bmv2 as check_vector\n"
        "vector = CORPUS / 'register_bounds/bounds.stf'\n"
        "def test_probe(monkeypatch):\n"
        f"    status = {status!r}\n"
        "    detail = REGISTER_BOUNDS_DETAIL + "
        "('\\nextra mismatch' if status == 'changed' else '')\n"
        "    verdict = bmv2_run.Verdict(vector, 'fail' if status in ('known', 'changed') "
        "else status, detail, ())\n"
        "    monkeypatch.setattr(bmv2_run, 'run', lambda *args: [verdict])\n"
        "    check_vector('unused-test-image', vector)\n"
        "test_probe = marks(vector)[0](test_probe)\n"
    )
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--confcutdir", str(tmp_path), str(source)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == (0 if status == "known" else 1), result.stdout + result.stderr
    assert result.stderr == "", result.stderr
    if status == "known":
        assert "1 xfailed" in result.stdout, result.stdout
        return
    assert "1 failed" in result.stdout and "1 xfailed" not in result.stdout, result.stdout
    if status == "error":
        assert "ORACLE ERROR (not a divergence)" in result.stdout, result.stdout
    elif status == "pass":
        assert "XPASS(strict)" in result.stdout, result.stdout
    else:
        assert "DIVERGENCE: BMv2 disagrees" in result.stdout, result.stdout


@pytest.mark.parametrize(
    "status,detail,vector",
    [
        ("error", REGISTER_BOUNDS_DETAIL, "register_bounds/bounds.stf"),
        ("skip", REGISTER_BOUNDS_DETAIL, "register_bounds/bounds.stf"),
        ("pass", REGISTER_BOUNDS_DETAIL, "register_bounds/bounds.stf"),
        ("fail", REGISTER_BOUNDS_DETAIL, "forwarder/forward.stf"),
        ("fail", REGISTER_BOUNDS_DETAIL + "\nextra mismatch", "register_bounds/bounds.stf"),
        ("fail", REGISTER_BOUNDS_DETAIL + "\n", "register_bounds/bounds.stf"),
        ("fail", REGISTER_BOUNDS_DETAIL.splitlines()[0], "register_bounds/bounds.stf"),
        ("fail", REGISTER_BOUNDS_DETAIL.replace("0407ff", "0407fe"), "register_bounds/bounds.stf"),
        (
            "fail",
            "\n".join(reversed(REGISTER_BOUNDS_DETAIL.splitlines())),
            "register_bounds/bounds.stf",
        ),
        ("fail", "", "register_bounds/bounds.stf"),
    ],
)
def test_register_bounds_classifier_rejects_other_results(
    status: str, detail: str, vector: str
) -> None:
    assert not known_register_bounds_disagreement(
        bmv2_run.Verdict(CORPUS / vector, status, detail, ())
    )


def test_register_bounds_classifier_accepts_exact_observed_packets() -> None:
    # These two literal mismatches correspond to the only ff-preserving OOB
    # outputs; the other seven packets, including in-range state/wrap, agreed.
    verdict = bmv2_run.Verdict(
        CORPUS / "register_bounds/bounds.stf",
        "fail",
        "line 46: expected 040700 $ on port 0, got 0407ff\n"
        "line 52: expected ff0100 $ on port 0, got ff01ff",
        (),
    )
    assert known_register_bounds_disagreement(verdict)
    (marker,) = marks(verdict.vector)
    assert marker.kwargs["raises"] is KnownBMv2RegisterBoundsDisagreement
    assert marker.kwargs["strict"] is True
    assert marks(CORPUS / "forwarder/forward.stf") == []
