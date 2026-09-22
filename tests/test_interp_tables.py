"""Installed entries: matching, precedence, and installation errors, per
docs/semantics.md, "Tables"."""

from __future__ import annotations

import pytest
from google.protobuf import text_format

from p4blo import ir
from p4blo.interp.tables import InstalledEntries, InstallError, Match
from p4blo.interp.values import Bits
from p4blo.v0 import p4blo_pb2 as pb

PROGRAM = """
errors: "NoError"
struct_types { name: "H" }
struct_types {
  name: "M"
  fields { name: "a" type { bits: 8 } }
  fields { name: "b" type { bits: 8 } }
}
headers: "H"
metadata: "M"
blocks {
  name: "C" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  actions { name: "set" params { name: "v" type { bits: 8 } direction: DIRECTION_NONE } }
  actions { name: "NoAction" }
  actions { name: "other" }
  tables {
    name: "exact_t"
    keys { expr { member { base { var: "meta" } field: "a" } } match_kind: MATCH_KIND_EXACT }
    actions: "set" actions: "NoAction"
  }
  tables {
    name: "lpm_t"
    keys { expr { member { base { var: "meta" } field: "a" } } match_kind: MATCH_KIND_LPM }
    actions: "set"
    default_action { action: "set" args { bits { width: 8 value: "9" } } }
  }
  tables {
    name: "tern_t"
    keys { expr { member { base { var: "meta" } field: "a" } } match_kind: MATCH_KIND_TERNARY }
    keys { expr { member { base { var: "meta" } field: "b" } } match_kind: MATCH_KIND_EXACT }
    actions: "set"
  }
  tables {
    name: "const_t"
    keys { expr { member { base { var: "meta" } field: "a" } } match_kind: MATCH_KIND_EXACT }
    actions: "set"
    default_action { action: "set" args { bits { width: 8 value: "7" } } }
    const_default_action: true
    const_entries {
      keys { exact: "1" } action { action: "set" args { bits { width: 8 value: "1" } } }
    }
  }
}
"""

EXACT = ("C", "exact_t")
LPM = ("C", "lpm_t")
TERN = ("C", "tern_t")
CONST = ("C", "const_t")


def index() -> ir.Index:
    return ir.Index.build(ir.load_text(PROGRAM))


def call(action: str, *args: int) -> pb.ActionCall:
    return pb.ActionCall(
        action=action, args=[pb.Literal(bits=pb.BitsLiteral(width=8, value=str(a))) for a in args]
    )


def entry(keys: str, action: pb.ActionCall, priority: int = 0) -> pb.Entry:
    """`keys` is the text of the KeyValue messages, e.g. `exact: "5"`."""
    e = text_format.Parse(keys, pb.Entry())
    e.action.CopyFrom(action)
    e.priority = priority
    return e


def installed(host: str = "") -> InstalledEntries:
    return InstalledEntries.build(index(), text_format.Parse(host, pb.Entries()))


def key(*values: int) -> list[Bits]:
    return [Bits(8, v) for v in values]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def test_exact_hit_and_miss_without_a_default() -> None:
    t = installed()
    t.install(EXACT, entry('keys { exact: "5" }', call("set", 1)))
    assert t.lookup(EXACT, key(5)) == Match(call("set", 1), True)
    assert t.lookup(EXACT, key(6)) == Match(None, False)


def test_lpm_longest_prefix_wins_and_the_default_runs_on_a_miss() -> None:
    t = installed()
    t.install(LPM, entry('keys { lpm { value: "0" prefix_len: 0 } }', call("set", 1)))
    t.install(LPM, entry('keys { lpm { value: "128" prefix_len: 1 } }', call("set", 2)))
    t.install(LPM, entry('keys { lpm { value: "160" prefix_len: 3 } }', call("set", 3)))
    assert t.lookup(LPM, key(0b10100001)) == Match(call("set", 3), True)
    assert t.lookup(LPM, key(0b10010000)) == Match(call("set", 2), True)
    assert t.lookup(LPM, key(0b01000000)) == Match(call("set", 1), True)
    assert installed().lookup(LPM, key(0)) == Match(call("set", 9), False)


def test_ternary_largest_priority_wins() -> None:
    t = installed()
    t.install(
        TERN,
        entry('keys { ternary { value: "0" mask: "0" } } keys { exact: "1" }', call("set", 1), 1),
    )
    t.install(
        TERN,
        entry(
            'keys { ternary { value: "128" mask: "128" } } keys { exact: "1" }', call("set", 5), 5
        ),
    )
    assert t.lookup(TERN, key(0x81, 1)) == Match(call("set", 5), True)
    assert t.lookup(TERN, key(0x01, 1)) == Match(call("set", 1), True)
    assert t.lookup(TERN, key(0x81, 2)) == Match(None, False)


def test_const_entries_are_installed_first() -> None:
    assert installed().lookup(CONST, key(1)) == Match(call("set", 1), True)
    assert installed().lookup(CONST, key(2)) == Match(call("set", 7), False)


def test_host_entries_come_from_the_block_scoped_table_name() -> None:
    host = """
    tables {
      block: "C" table: "exact_t"
      entries { keys { exact: "5" } action { action: "set" args { bits { width: 8 value: "1" } } } }
    }
    """
    assert installed(host).lookup(EXACT, key(5)) == Match(call("set", 1), True)
    with pytest.raises(InstallError):
        installed(host.replace('block: "C"', 'block: "X"'))


# ---------------------------------------------------------------------------
# Installation errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("table", "keys", "action", "priority"),
    [
        (EXACT, 'keys { exact: "1" } keys { exact: "2" }', call("set", 1), 0),  # arity
        (EXACT, 'keys { exact: "256" }', call("set", 1), 0),  # wider than the key
        (EXACT, 'keys { exact: "abc" }', call("set", 1), 0),  # not decimal
        (EXACT, 'keys { lpm { value: "0" prefix_len: 0 } }', call("set", 1), 0),  # wrong kind
        (EXACT, 'keys { exact: "1" }', call("set", 1), 1),  # priority without a ternary key
        (EXACT, 'keys { exact: "1" }', call("other"), 0),  # action not in the table
        (EXACT, 'keys { exact: "1" }', call("set"), 0),  # missing action data
        (EXACT, 'keys { exact: "1" }', call("set", 1, 2), 0),  # too much action data
        (EXACT, 'keys { exact: "1" }', call("missing", 1), 0),  # no such action
        (LPM, 'keys { lpm { value: "1" prefix_len: 7 } }', call("set", 1), 0),  # bit outside prefix
        (LPM, 'keys { lpm { value: "0" prefix_len: 9 } }', call("set", 1), 0),  # prefix too long
        (
            TERN,
            'keys { ternary { value: "1" mask: "0" } } keys { exact: "1" }',
            call("set", 1),
            0,
        ),  # bit outside mask
    ],
)
def test_install_rejects_an_entry_that_does_not_fit(
    table: tuple[str, str], keys: str, action: pb.ActionCall, priority: int
) -> None:
    with pytest.raises(InstallError):
        installed().install(table, entry(keys, action, priority))


def test_install_rejects_action_data_of_the_wrong_width() -> None:
    wide = pb.ActionCall(action="set", args=[pb.Literal(bits=pb.BitsLiteral(width=16, value="1"))])
    with pytest.raises(InstallError):
        installed().install(EXACT, entry('keys { exact: "1" }', wide))


def test_install_rejects_duplicate_exact_and_lpm_entries() -> None:
    t = installed()
    t.install(EXACT, entry('keys { exact: "1" }', call("set", 1)))
    with pytest.raises(InstallError):
        t.install(EXACT, entry('keys { exact: "1" }', call("set", 2)))
    t.install(LPM, entry('keys { lpm { value: "128" prefix_len: 1 } }', call("set", 1)))
    with pytest.raises(InstallError):
        t.install(LPM, entry('keys { lpm { value: "128" prefix_len: 1 } }', call("set", 2)))
    # A different length with the same bits is another prefix, not a duplicate.
    t.install(LPM, entry('keys { lpm { value: "128" prefix_len: 2 } }', call("set", 3)))


def test_install_rejects_overlapping_ternary_entries_of_equal_priority() -> None:
    t = installed()
    t.install(
        TERN,
        entry(
            'keys { ternary { value: "128" mask: "128" } } keys { exact: "1" }', call("set", 1), 3
        ),
    )
    with pytest.raises(InstallError):
        t.install(
            TERN,
            entry(
                'keys { ternary { value: "0" mask: "0" } } keys { exact: "1" }', call("set", 2), 3
            ),
        )
    # Disjoint on the exact key, or at another priority: fine.
    t.install(
        TERN,
        entry('keys { ternary { value: "0" mask: "0" } } keys { exact: "2" }', call("set", 2), 3),
    )
    t.install(
        TERN,
        entry('keys { ternary { value: "0" mask: "0" } } keys { exact: "1" }', call("set", 2), 4),
    )


TWINS = """
errors: "NoError"
struct_types { name: "H" }
struct_types { name: "M" }
headers: "H"
metadata: "M"
blocks {
  name: "A" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  actions { name: "set" params { name: "v" type { bits: 8 } direction: DIRECTION_NONE } }
  tables { name: "t" actions: "set" }
  body { apply { table: "t" } }
}
blocks {
  name: "B" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  actions { name: "set" params { name: "v" type { bits: 16 } direction: DIRECTION_NONE } }
  tables { name: "t" actions: "set" }
  body { apply { table: "t" } }
}
"""


def test_action_data_is_checked_against_the_tables_own_block() -> None:
    # A.t and B.t are byte-identical tables; their `set` actions differ.
    twins = ir.Index.build(ir.load_text(TWINS))
    wide = pb.ActionCall(action="set", args=[pb.Literal(bits=pb.BitsLiteral(width=16, value="1"))])
    t = InstalledEntries.build(twins)
    t.install(("B", "t"), entry("", wide))
    assert t.lookup(("B", "t"), []) == Match(wide, True)
    with pytest.raises(InstallError):
        t.install(("A", "t"), entry("", wide))


def test_host_entry_duplicating_a_const_entry_is_rejected() -> None:
    host = """
    tables {
      block: "C" table: "const_t"
      entries { keys { exact: "1" } action { action: "set" args { bits { width: 8 value: "2" } } } }
    }
    """
    with pytest.raises(InstallError):
        installed(host)


# ---------------------------------------------------------------------------
# Default actions
# ---------------------------------------------------------------------------


def test_host_default_replaces_a_non_const_default_and_none_restores_the_programs() -> None:
    host = """
    tables {
      block: "C" table: "lpm_t"
      default_action { action: "set" args { bits { width: 8 value: "2" } } }
    }
    """
    t = installed(host)
    assert t.lookup(LPM, key(0)) == Match(call("set", 2), False)
    t.set_default(LPM, None)
    assert t.lookup(LPM, key(0)) == Match(call("set", 9), False)


def test_host_default_cannot_replace_a_const_default() -> None:
    with pytest.raises(InstallError):
        installed().set_default(CONST, call("set", 2))


def test_host_default_must_be_one_of_the_tables_actions() -> None:
    with pytest.raises(InstallError):
        installed().set_default(LPM, call("NoAction"))
    with pytest.raises(InstallError):
        installed().set_default(LPM, call("set"))


def test_a_table_without_a_default_falls_back_to_no_action() -> None:
    t = installed()
    t.set_default(EXACT, None)
    assert t.lookup(EXACT, key(0)) == Match(None, False)
