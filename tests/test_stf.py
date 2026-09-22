"""The STF vector reader: parsing, name resolution, replay."""

from __future__ import annotations

import pytest

from p4blo import stf


def only(text: str) -> stf.Statement:
    statements = stf.parse(text)
    assert len(statements) == 1
    return statements[0]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_add_with_an_lpm_key() -> None:
    statement = only(
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000101/24 ipv4_forward(dstAddr:0x000102030405, port:1)"
    )
    assert statement == stf.Add(
        line=1,
        table="ipv4_lpm",
        action="ipv4_forward",
        keys=(stf.Key("hdr.ipv4.dstAddr", 0x0A000101, None, 24, 32),),
        args=(
            stf.ActionArg("dstAddr", 0x000102030405, 48),
            stf.ActionArg("port", 1, None),
        ),
        priority=None,
    )


def test_add_with_a_priority_and_a_ternary_key() -> None:
    # p4c's testdata/stf/ternary2.stf writes entries in this shape.
    statement = only("add test1 503 data.f1:0x****0202 ingress.setb1(val:7, port:3)")
    assert isinstance(statement, stf.Add)
    assert statement.table == "test1"
    assert statement.priority == 503
    assert statement.action == "ingress.setb1"
    assert statement.keys == (stf.Key("data.f1", 0x00000202, 0x0000FFFF, None, 32),)
    assert statement.args == (stf.ActionArg("val", 7, None), stf.ActionArg("port", 3, None))


def test_add_with_no_keys_and_no_args() -> None:
    assert only("add t a()") == stf.Add(1, "t", "a")


def test_add_with_a_binary_key() -> None:
    statement = only("add t data.f:0b1*01 a()")
    assert isinstance(statement, stf.Add)
    assert statement.keys == (stf.Key("data.f", 0b1001, 0b1011, None, 4),)


def test_setdefault() -> None:
    assert only("setdefault ipv4_lpm drop()") == stf.SetDefault(1, "ipv4_lpm", "drop")


def test_packet_and_expect() -> None:
    statements = stf.parse(
        """
        # a comment
        packet 0 00 11 22 33
        expect 1 00 11 **** 33   # trailing comment
        """
    )
    assert statements == [
        stf.Packet(3, 0, bytes.fromhex("00112233")),
        stf.Expect(4, 1, bytes.fromhex("0011000033"), bytes.fromhex("ffff0000ff")),
    ]


def test_expect_matches_under_its_mask() -> None:
    expect = stf.Expect(1, 0, bytes.fromhex("00110000"), bytes.fromhex("ffff0000"))
    assert expect.matches(bytes.fromhex("0011abcd"))
    assert not expect.matches(bytes.fromhex("0012abcd"))
    assert not expect.matches(bytes.fromhex("0011abcdef"))


def test_no_packet_and_wait_and_case_insensitivity() -> None:
    assert stf.parse("NO_PACKET\nWait\n") == [stf.NoPacket(1), stf.Wait(2)]


def test_blank_lines_and_comments_are_skipped() -> None:
    assert stf.parse("\n  # nothing here\n\n") == []


@pytest.mark.parametrize(
    "line",
    [
        "frobnicate 1",
        "add t hdr.f:0x12",  # no action
        "packet 0 012",  # odd number of hex digits
        "packet 0 00**",  # wildcards are not allowed in an input packet
        "expect zero 0011",
        "add t 1 hdr.f:12*3 a()",  # `*` needs 0x or 0b
        "add t hdr.f:0x12/x a()",
        "no_packet 1",
        "setdefault t a",
    ],
)
def test_bad_lines_are_rejected(line: str) -> None:
    with pytest.raises(stf.StfError):
        stf.parse(line)
