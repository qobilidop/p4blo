"""The STF vector reader: parsing, name resolution, replay."""

from __future__ import annotations

from pathlib import Path

import pytest

from p4blo import ir, stf
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.v0 import p4blo_pb2 as pb


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


def test_add_with_an_indexed_key_name() -> None:
    # p4c's ternary2-bmv2.stf writes `extra$0.h`; its runner rewrites that to
    # `extra[0].h`, the name a stack-element key carries in p4blo's corpus.
    statement = only("add ex1 100 extra[0].h:0x25** act1(val:0x25)")
    assert isinstance(statement, stf.Add)
    assert statement.keys == (stf.Key("extra[0].h", 0x2500, 0xFF00, None, 16),)
    assert statement.action == "act1"


def test_setdefault_parses() -> None:
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
    assert expect.matches(bytes.fromhex("0011abcdef"))  # a prefix, unless exact
    assert not stf.Expect(1, 0, expect.data, expect.mask, exact=True).matches(
        b"\x00\x11\xab\xcd\xef"
    )


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
        "packet 512 00",  # a port is a bit<9>
        "expect 600 00",
        "add t 1 hdr.f:12*3 a()",  # `*` needs 0x or 0b
        "add t hdr.f:0x12/x a()",
        "no_packet 1",
        "setdefault t a",
    ],
)
def test_bad_lines_are_rejected(line: str) -> None:
    with pytest.raises(stf.StfError):
        stf.parse(line)


# ---------------------------------------------------------------------------
# Name resolution
# ---------------------------------------------------------------------------

FORWARDER = Path(__file__).resolve().parents[2] / "tests" / "corpus" / "forwarder"

TERNARY = """
    name: "ternary"
    errors: "NoError"
    struct_types { name: "H" fields { name: "f1" type { bits: 32 } } }
    struct_types { name: "M" }
    headers: "H"
    metadata: "M"
    blocks {
      name: "ingress" kind: BLOCK_KIND_CONTROL
      params { name: "data" type { struct: "H" } direction: DIRECTION_INOUT }
      params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
      actions {
        name: "setb1"
        params { name: "val" type { bits: 9 } direction: DIRECTION_NONE }
        params { name: "port" type { bits: 9 } direction: DIRECTION_NONE }
      }
      tables {
        name: "test1"
        keys {
          expr { member { base { var: "data" } field: "f1" } }
          match_kind: MATCH_KIND_TERNARY
        }
        actions: "setb1"
      }
      body { apply { table: "test1" } }
    }
    exports { role: "ingress" block: "ingress" }
"""


# A table keyed on a field of a stack element, as p4c's ternary2-bmv2.p4
# keys `ex1` on `hdrs.extra[0].h`. The key carries the name p4c's STF uses.
STACK_KEY = """
    name: "stack_key"
    errors: "NoError"
    header_types { name: "extra_h" fields { name: "h" type { bits: 16 } } }
    struct_types {
      name: "H" fields { name: "extra" type { stack { header: "extra_h" size: 4 } } }
    }
    struct_types { name: "M" }
    headers: "H"
    metadata: "M"
    blocks {
      name: "ingress" kind: BLOCK_KIND_CONTROL
      params { name: "hdrs" type { struct: "H" } direction: DIRECTION_INOUT }
      params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
      actions { name: "act1" params { name: "val" type { bits: 8 } direction: DIRECTION_NONE } }
      tables {
        name: "ex1"
        keys {
          expr {
            member {
              base {
                index {
                  base { member { base { var: "hdrs" } field: "extra" } }
                  index { literal { bits { width: 32 value: "0" } } }
                }
              }
              field: "h"
            }
          }
          match_kind: MATCH_KIND_TERNARY
          name: "extra[0].h"
        }
        actions: "act1"
      }
      body { apply { table: "ex1" } }
    }
    exports { role: "ingress" block: "ingress" }
"""


@pytest.fixture(scope="module")
def forwarder() -> ir.Index:
    return BoundIndex.build(arch_wire.load_text(FORWARDER / "forwarder.txtpb"))


@pytest.fixture(scope="module")
def ternary() -> ir.Index:
    return BoundIndex.build(arch_wire.load_text(TERNARY))


def resolve(index: ir.Index, text: str) -> pb.Entries:
    return stf.to_entries(index, stf.parse(text))


def test_to_entries_finds_the_block_that_declares_the_table(forwarder: ir.Index) -> None:
    entries = resolve(
        forwarder,
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 ipv4_forward(dstAddr:0x000000000202, port:2)",
    )
    assert len(entries.tables) == 1
    installed = entries.tables[0]
    assert (installed.block, installed.table) == ("MyIngress", "ipv4_lpm")
    entry = installed.entries[0]
    assert entry.keys[0].lpm == pb.LpmValue(value=str(0x0A000200), prefix_len=24)
    assert entry.priority == 0
    assert entry.action.action == "ipv4_forward"
    assert [(a.bits.width, a.bits.value) for a in entry.action.args] == [(48, "514"), (9, "2")]


def test_an_lpm_key_without_a_prefix_is_a_full_length_one(forwarder: ir.Index) -> None:
    entries = resolve(
        forwarder,
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000202 ipv4_forward(dstAddr:1, port:2)",
    )
    assert entries.tables[0].entries[0].keys[0].lpm.prefix_len == 32


def test_entries_of_one_table_keep_their_order(forwarder: ir.Index) -> None:
    entries = resolve(
        forwarder,
        """
        add ipv4_lpm hdr.ipv4.dstAddr:0x0a000000/16 ipv4_forward(dstAddr:1, port:1)
        add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 ipv4_forward(dstAddr:2, port:2)
        """,
    )
    assert len(entries.tables) == 1
    assert [e.keys[0].lpm.prefix_len for e in entries.tables[0].entries] == [16, 24]


def test_setdefault_installs_a_default_action(forwarder: ir.Index) -> None:
    entries = resolve(forwarder, "setdefault ipv4_lpm NoAction()")
    assert entries.tables[0].default_action.action == "NoAction"
    assert not entries.tables[0].entries


def test_a_ternary_key_and_a_qualified_action(ternary: ir.Index) -> None:
    entries = resolve(ternary, "add test1 503 data.f1:0x****0202 ingress.setb1(val:7, port:3)")
    entry = entries.tables[0].entries[0]
    assert entry.priority == 503
    assert entry.keys[0].ternary == pb.TernaryValue(value="514", mask="65535")
    assert entry.action.action == "setb1"


def test_a_plain_number_on_a_ternary_key_is_an_exact_match(ternary: ir.Index) -> None:
    entries = resolve(ternary, "add test1 1 data.f1:0x0202 ingress.setb1(val:7, port:3)")
    assert entries.tables[0].entries[0].keys[0].ternary.mask == str(0xFFFFFFFF)


def test_a_key_on_a_stack_element_resolves_by_its_name() -> None:
    index = BoundIndex.build(arch_wire.load_text(STACK_KEY))
    entries = resolve(index, "add ex1 100 extra[0].h:0x25** act1(val:0x25)")
    entry = entries.tables[0].entries[0]
    assert entry.priority == 100
    assert entry.keys[0].ternary == pb.TernaryValue(value="9472", mask="65280")
    with pytest.raises(stf.StfError):
        # 0x25*** is 24 bits wide, wider than the 16-bit key.
        resolve(index, "add ex1 100 extra[0].h:0x25**** act1(val:0x25)")


@pytest.mark.parametrize(
    "line",
    [
        "add nosuchtable hdr.ipv4.dstAddr:1 drop()",
        "add ipv4_lpm hdr.ipv4.dstAddr:1 nosuchaction()",
        "add ipv4_lpm drop()",  # the key is missing
        "add ipv4_lpm hdr.ipv4.srcAddr:1 drop()",  # not a key of this table
        "add ipv4_lpm hdr.ipv4.dstAddr:1 ipv4_forward(port:1)",  # dstAddr is missing
        "add ipv4_lpm hdr.ipv4.dstAddr:1 ipv4_forward(dstAddr:1, port:1, x:1)",
        "add ipv4_lpm 7 hdr.ipv4.dstAddr:1 drop()",  # no ternary key, so no priority
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a0001010a/24 drop()",  # too wide for bit<32>
        "add ipv4_lpm hdr.ipv4.dstAddr:1/33 drop()",
        "add ipv4_lpm hdr.ipv4.dstAddr:0x**01 drop()",  # a mask on an lpm key
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000201/24 drop()",  # bits below the prefix
        "add ipv4_lpm hdr.ipv4.dstAddr:1 ipv4_forward(dstAddr:1, port:512)",
    ],
)
def test_entries_that_do_not_fit_the_forwarder(forwarder: ir.Index, line: str) -> None:
    with pytest.raises(stf.StfError):
        resolve(forwarder, line)


def test_a_non_canonical_lpm_value_is_reported_with_its_line(forwarder: ir.Index) -> None:
    with pytest.raises(stf.StfError, match=r"line 2: .*below its /24 prefix"):
        resolve(forwarder, "\nadd ipv4_lpm hdr.ipv4.dstAddr:0x0a000201/24 drop()\n")


@pytest.mark.parametrize(
    "line",
    [
        "add test1 data.f1:0x0202 ingress.setb1(val:7, port:3)",  # ternary needs a priority
        "add test1 1 data.f1:0x0202/8 ingress.setb1(val:7, port:3)",  # prefix, not mask
    ],
)
def test_entries_that_do_not_fit_a_ternary_table(ternary: ir.Index, line: str) -> None:
    with pytest.raises(stf.StfError):
        resolve(ternary, line)


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

ONE = "packet 0 0011\nexpect 1 0011\n"


def echo(port: int, data: bytes) -> stf.RunPacket:
    """A `run_packet` that always emits `data` on `port`."""

    def run(entries: pb.Entries, ingress: int, packet: bytes) -> list[tuple[int, bytes]]:
        return [(port, data)]

    return run


def nothing(entries: pb.Entries, ingress: int, packet: bytes) -> list[tuple[int, bytes]]:
    return []


def test_replay_passes(forwarder: ir.Index) -> None:
    stf.assert_replay(forwarder, stf.parse(ONE), echo(1, bytes.fromhex("0011")))


def test_replay_sees_the_ingress_port_and_the_entries(forwarder: ir.Index) -> None:
    seen: list[tuple[int, bytes, int]] = []

    def run(entries: pb.Entries, ingress: int, packet: bytes) -> list[tuple[int, bytes]]:
        seen.append((ingress, packet, len(entries.tables[0].entries)))
        return [(1, packet)]

    text = (
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 ipv4_forward(dstAddr:1, port:1)\n"
        "packet 3 0011\n"
        "expect 1 0011\n"
    )
    stf.assert_replay(forwarder, stf.parse(text), run)
    assert seen == [(3, bytes.fromhex("0011"), 1)]


def test_replay_reports_the_wrong_port(forwarder: ir.Index) -> None:
    failures = stf.replay(forwarder, stf.parse(ONE), echo(2, bytes.fromhex("0011")))
    assert len(failures) == 1
    assert failures[0].line == 2
    assert "port 2" in failures[0].message


def test_replay_reports_the_wrong_bytes(forwarder: ir.Index) -> None:
    failures = stf.replay(forwarder, stf.parse(ONE), echo(1, bytes.fromhex("0012")))
    assert len(failures) == 1
    assert "0012" in failures[0].message


def test_replay_accepts_a_wildcard_nibble(forwarder: ir.Index) -> None:
    text = "packet 0 0011\nexpect 1 00**\n"
    assert stf.replay(forwarder, stf.parse(text), echo(1, bytes.fromhex("00ab"))) == []


def test_replay_reports_a_missing_output(forwarder: ir.Index) -> None:
    failures = stf.replay(forwarder, stf.parse(ONE), nothing)
    assert [f.line for f in failures] == [2]
    assert failures[0].message == "no output packet"


def test_replay_reports_an_extra_output(forwarder: ir.Index) -> None:
    text = "packet 0 0011\nno_packet\n"
    failures = stf.replay(forwarder, stf.parse(text), echo(1, bytes.fromhex("0011")))
    assert [f.line for f in failures] == [2]
    assert "unexpected output on port 1" in failures[0].message


def test_a_packet_with_no_expect_asserts_nothing_came_out(forwarder: ir.Index) -> None:
    text = "packet 0 0011\n"
    assert stf.replay(forwarder, stf.parse(text), nothing) == []
    assert len(stf.replay(forwarder, stf.parse(text), echo(1, b"\x00"))) == 1


def test_expect_before_any_packet_is_a_failure(forwarder: ir.Index) -> None:
    failures = stf.replay(forwarder, stf.parse("expect 1 0011\n"), nothing)
    assert [f.line for f in failures] == [1]


def test_assert_replay_lists_every_failure(forwarder: ir.Index) -> None:
    text = "packet 0 0011\nexpect 1 0011\npacket 0 0011\nexpect 1 0011\n"
    with pytest.raises(stf.ReplayFailed) as raised:
        stf.assert_replay(forwarder, stf.parse(text), echo(2, bytes.fromhex("0011")))
    assert "line 2" in str(raised.value)
    assert "line 4" in str(raised.value)


def test_expect_is_a_prefix_unless_it_ends_in_dollar() -> None:
    (loose,) = stf.parse("expect 1 0011")
    (strict,) = stf.parse("expect 1 0011 $")
    assert isinstance(loose, stf.Expect) and isinstance(strict, stf.Expect)
    assert loose.matches(bytes.fromhex("001122"))
    assert not loose.matches(bytes.fromhex("00"))
    assert strict.matches(bytes.fromhex("0011"))
    assert not strict.matches(bytes.fromhex("001122"))
