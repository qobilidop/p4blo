"""Claim 2's oracle: every corpus vector replays on P4-SpecTec's simulator.

The oracle is P4-SpecTec's `p4spectec sim`, built by tests/oracle/build.sh and
driven by tests/oracle/run.py. Without a built binary every replay test skips and
says so; with one, each `tests/corpus/<program>/*.stf` must pass, where a
divergence and an oracle-side error (a construct the simulator does not
support, a crash) are both failures, labeled apart: the second is not a
disagreement, but it leaves the claim unchecked.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from p4blo import ir, stf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.oracle import firewall  # noqa: E402
from tests.oracle import run as oracle_run  # noqa: E402

CORPUS = ROOT / "tests" / "corpus"
VECTORS = sorted([*CORPUS.glob("*/*.stf"), *(ROOT / "tests/examples").glob("*/*.stf")])


def program_of(vector: Path) -> Path:
    """The one IR text file beside a vector."""
    programs = sorted(vector.parent.glob("*.txtpb"))
    assert len(programs) == 1, f"{vector.parent} should hold exactly one .txtpb"
    return programs[0]


@pytest.fixture(scope="module")
def forwarder() -> ir.Index:
    return ir.Index.build(ir.load_text(CORPUS / "forwarder" / "forwarder.txtpb"))


@pytest.fixture(scope="module")
def oracle() -> oracle_run.Oracle:
    found = oracle_run.find_oracle()
    if found is None:
        pytest.skip(
            "P4-SpecTec's p4spectec is not built: run tests/oracle/build.sh, "
            "or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR (see tests/oracle/README.md)"
        )
    reason = found.missing()
    if reason is not None:
        pytest.skip(f"the oracle checkout is incomplete: {reason}")
    return found


# ---------------------------------------------------------------------------
# The translation, which needs no oracle
# ---------------------------------------------------------------------------


def test_translate_drops_no_packet_and_passes_the_rest_through(forwarder: ir.Index) -> None:
    text = "# a comment\npacket 0 00 11\nno_packet\nwait\npacket 1 22\nexpect 1 2* $\n"
    translated, notes = oracle_run.translate(text, forwarder)
    lines = translated.splitlines()
    assert len(lines) == 6
    assert lines[2].startswith("# no_packet")
    assert lines[:2] + lines[3:] == text.splitlines()[:2] + text.splitlines()[3:]
    assert notes == ["line 3: dropped no_packet"]


def test_translate_renders_lpm_prefixes_as_wildcards_with_priority(forwarder: ir.Index) -> None:
    # P4-SpecTec reads `value/len` its own way and has no longest-prefix
    # rule (tests/oracle/README.md): the wildcard form at the key's full width is
    # what both it and p4c read as a prefix, hex when the prefix is
    # nibble-aligned and binary otherwise, and the prefix length becomes the
    # entry's priority, larger winning.
    text = (
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 ipv4_forward(dstAddr:0x000000000202, port:2)"
        "  # trailing comment\n"
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000000/22 ipv4_forward(dstAddr:1, port:1)\n"
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000202 drop()\n"
    )
    translated, notes = oracle_run.translate(text, forwarder)
    assert translated.splitlines() == [
        "add ipv4_lpm 24 hdr.ipv4.dstAddr:0x0a0002** ipv4_forward(dstAddr:514, port:2)",
        "add ipv4_lpm 22 hdr.ipv4.dstAddr:0b0000101000000000000000**********"
        " ipv4_forward(dstAddr:1, port:1)",
        "add ipv4_lpm 32 hdr.ipv4.dstAddr:0x0a000202 drop()",
    ]
    assert len(notes) == 3 and notes[0].startswith("line 1: rewritten as `add ipv4_lpm 24")


@pytest.mark.parametrize(
    ("value", "mask", "width", "expected"),
    [
        (0x0A000200, 0xFFFFFF00, 32, "0x0a0002**"),
        (0x0A000202, 0xFFFFFFFF, 32, "0x0a000202"),
        (0x0A000000, 0xFFFFFC00, 32, "0b0000101000000000000000**********"),
        (0x25, 0xF0, 8, "0x2*"),
        (0x2525, 0xFF0F, 16, "0x25*5"),
        (0b101, 0b101, 3, "0b1*1"),
    ],
)
def test_render_masked(value: int, mask: int, width: int, expected: str) -> None:
    assert oracle_run.render_masked(value, mask, width) == expected


def test_translate_refuses_what_p4blo_refuses(forwarder: ir.Index) -> None:
    with pytest.raises(stf.StfError):
        oracle_run.translate("packet 0 0*\n", forwarder)
    with pytest.raises(stf.StfError):
        oracle_run.translate("add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 nope()\n", forwarder)


def test_every_corpus_vector_translates() -> None:
    assert VECTORS, "no corpus vectors found"
    for vector in VECTORS:
        index = ir.Index.build(ir.load_text(program_of(vector)))
        oracle_run.translate(vector.read_text(), index)


def test_original_firewall_source_is_pinned() -> None:
    assert "V1Switch(" in firewall.source()


def test_original_firewall_vectors_distinguish_requests() -> None:
    phase = firewall.plan().phases[0]
    assert len(phase.packets) == 4 and len(phase.expects) == 2
    assert all(len(p.data) == 54 for p in phase.packets)
    assert [int.from_bytes(p.data[38:42], "big") for p in phase.packets] == [1, 2, 3, 4]
    # Same inbound five-tuple before and after SYN, distinct observable bytes.
    assert phase.packets[0].data[26:38] == phase.packets[2].data[26:38]
    assert phase.packets[0].data != phase.packets[2].data
    for expected in phase.expects:
        assert expected.exact and len(expected.data) == 54
        header = expected.data[14:34]
        total = sum(int.from_bytes(header[i : i + 2], "big") for i in range(0, 20, 2))
        while total >> 16:
            total = (total & 0xFFFF) + (total >> 16)
        assert total == 0xFFFF


def test_original_firewall_adapter_rejects_configuration_drift() -> None:
    with pytest.raises(ValueError, match="configuration changed"):
        firewall.plan(firewall.VECTOR.replace("dir:0", "dir:1", 1))
    with pytest.raises(ValueError, match="only packets/expectations"):
        firewall.plan(firewall.VECTOR + firewall.CONFIGURATION[0] + "\n")


def test_original_firewall_on_spectec(oracle: oracle_run.Oracle, tmp_path: Path) -> None:
    firewall.source()  # Verify unchanged upstream source; do not print our IR.
    firewall.plan()  # Both oracle encodings must still describe this fixed profile.
    vector = tmp_path / "firewall.stf"
    vector.write_text(firewall.VECTOR)
    result = subprocess.run(
        [
            str(oracle.binary),
            "sim",
            str(oracle.spec),
            "-arch",
            "v1model",
            "-i",
            str(oracle.include),
            "-p",
            str(firewall.SOURCE),
            "-stf",
            str(vector),
        ],
        cwd=oracle.root,
        capture_output=True,
        text=True,
        timeout=oracle_run.TIMEOUT_SECONDS,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1:] == ["passed"], result.stdout + result.stderr


# ---------------------------------------------------------------------------
# The replay
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vector", VECTORS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_vector_passes_on_the_oracle(oracle: oracle_run.Oracle, vector: Path) -> None:
    (verdict,) = oracle_run.run(oracle, program_of(vector), [vector])
    where = f"{vector.relative_to(ROOT)}\ncommand: {shlex.join(verdict.command)}"
    if verdict.status == "fail":
        pytest.fail(f"DIVERGENCE: the oracle disagrees on {where}\n{verdict.detail}")
    if verdict.status == "error":
        pytest.fail(f"ORACLE ERROR (not a divergence): could not judge {where}\n{verdict.detail}")
    assert verdict.status == "pass", verdict
