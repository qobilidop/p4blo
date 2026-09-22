"""Controls: statements, calls of every kind, and the header and stack
rules of docs/semantics.md, "Headers", "Header stacks" and "Controls"."""

from __future__ import annotations

from dataclasses import dataclass, field

from google.protobuf import text_format

from p4blo import interp, ir
from p4blo.interp import ExternResult, values
from p4blo.interp.tables import InstalledEntries
from p4blo.interp.values import Bits, Header, Stack, Struct, Value
from p4blo.v0 import p4blo_pb2 as pb

TEMPLATE = """
errors: "NoError"
header_types { name: "h8" fields { name: "f" type { bits: 8 } } }
struct_types {
  name: "H"
  fields { name: "e" type { header: "h8" } }
  fields { name: "hs" type { stack { header: "h8" size: 2 } } }
}
struct_types {
  name: "M"
  fields { name: "n" type { bits: 8 } }
  fields { name: "flag" type { boolean {} } }
}
extern_types {
  name: "Reg"
  methods {
    name: "read"
    params { name: "i" type { bits: 8 } direction: DIRECTION_IN }
    params { name: "v" type { bits: 8 } direction: DIRECTION_OUT }
  }
  methods {
    name: "bump"
    params { name: "d" type { bits: 8 } direction: DIRECTION_IN }
    returns { bits: 8 }
  }
}
extern_instances { name: "reg" extern_type: "Reg" }
headers: "H"
metadata: "M"
blocks {
  name: "C" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  locals { name: "hit" type { boolean {} } }
  locals { name: "t" type { bits: 8 } }
  @DECLS@
  @BODY@
}
@EXTRA@
"""

HDR_E = 'member { base { var: "hdr" } field: "e" }'
HDR_HS = 'member { base { var: "hdr" } field: "hs" }'
E_F = f'member {{ base {{ {HDR_E} }} field: "f" }}'
META_N = 'member { base { var: "meta" } field: "n" }'
META_FLAG = 'member { base { var: "meta" } field: "flag" }'


def hs_at(i: int) -> str:
    """The lvalue or expression text of `hdr.hs[i]`."""
    return f"index {{ base {{ {HDR_HS} }} index {{ {bits(32, i)} }} }}"


def bits(width: int, value: int) -> str:
    return f'literal {{ bits {{ width: {width} value: "{value}" }} }}'


def assign(target: str, value: str) -> str:
    return f"body {{ assign {{ target {{ {target} }} value {{ {value} }} }} }}"


def stmt(text: str) -> str:
    return f"body {{ {text} }}"


@dataclass
class Run:
    headers: Struct
    metadata: Struct

    @property
    def e(self) -> Header:
        assert isinstance(self.headers.fields[0], Header)
        return self.headers.fields[0]

    @property
    def hs(self) -> Stack:
        assert isinstance(self.headers.fields[1], Stack)
        return self.headers.fields[1]

    @property
    def n(self) -> Value:
        return self.metadata.fields[0]

    @property
    def flag(self) -> Value:
        return self.metadata.fields[1]


@dataclass
class FakeReg:
    """`read(i, v)` writes `i + 1` to `v`; `bump(d)` returns `2 * d`."""

    calls: list[tuple[str, list[Value]]] = field(default_factory=list)

    def call(self, method: str, args: list[Value]) -> ExternResult:
        self.calls.append((method, args))
        first = args[0]
        assert isinstance(first, Bits)
        if method == "read":
            return ExternResult(outs=(Bits(8, first.value + 1),))
        return ExternResult(returns=Bits(8, 2 * first.value))


def run(
    body: str,
    decls: str = "",
    extra: str = "",
    headers: Struct | None = None,
    metadata: Struct | None = None,
    entries: str = "",
    externs: dict[str, FakeReg] | None = None,
) -> Run:
    text = TEMPLATE.replace("@DECLS@", decls).replace("@BODY@", body).replace("@EXTRA@", extra)
    index = ir.Index.build(ir.load_text(text))
    if headers is None:
        headers = values.zero(pb.Type(struct="H"), index)  # type: ignore[assignment]
    if metadata is None:
        metadata = values.zero(pb.Type(struct="M"), index)  # type: ignore[assignment]
    assert isinstance(headers, Struct) and isinstance(metadata, Struct)
    installed = InstalledEntries.build(index, text_format.Parse(entries, pb.Entries()))
    h, m = interp.run_control(index, "C", headers, metadata, installed, externs or {})
    return Run(h, m)


# ---------------------------------------------------------------------------
# Assignment, if, header and stack rules
# ---------------------------------------------------------------------------


def test_assignment_through_nested_member_and_index_lvalues() -> None:
    out = run(
        assign(f'member {{ base {{ {hs_at(1)} }} field: "f" }}', bits(8, 7))
        + assign(
            E_F,
            f'binary {{ op: BINARY_OP_ADD left {{ member {{ base {{ {hs_at(1)} }} field: "f" }} }}'
            f" right {{ {bits(8, 1)} }} }}",
        )
    )
    assert out.hs.elements[1].fields[0] == Bits(8, 7)
    assert out.e.fields[0] == Bits(8, 8)


def test_if_takes_the_branch_of_its_condition() -> None:
    body = f"""
    body {{ conditional {{
      condition {{ binary {{ op: BINARY_OP_EQ left {{ {META_N} }} right {{ {bits(8, 1)} }} }} }}
      then {{ assign {{ target {{ {META_FLAG} }} value {{ literal {{ boolean: true }} }} }} }}
      otherwise {{ assign {{ target {{ {META_N} }} value {{ {bits(8, 9)} }} }} }}
    }} }}
    """
    assert run(body).n == Bits(8, 9)
    m = Struct("M", [Bits(8, 1), False])
    out = run(body, metadata=m)
    assert out.flag is True and out.n == Bits(8, 1)


def test_writing_a_field_of_an_invalid_header_stores_it_and_keeps_it_invalid() -> None:
    out = run(assign(E_F, bits(8, 9)) + assign(META_N, E_F))
    assert out.e == Header("h8", False, [Bits(8, 9)])
    assert out.n == Bits(8, 9)


def test_set_valid_and_set_invalid_touch_only_validity() -> None:
    out = run(assign(E_F, bits(8, 3)) + stmt(f"set_valid {{ header {{ {HDR_E} }} }}"))
    assert out.e == Header("h8", True, [Bits(8, 3)])
    out = run(stmt(f"set_invalid {{ header {{ {HDR_E} }} }}"), headers=out.headers)
    assert out.e == Header("h8", False, [Bits(8, 3)])


def test_assigning_a_header_copies_validity_and_fields() -> None:
    body = (
        assign(E_F, bits(8, 4))
        + stmt(f"set_valid {{ header {{ {HDR_E} }} }}")
        + assign(hs_at(0), HDR_E)
        + stmt(f"set_invalid {{ header {{ {HDR_E} }} }}")
        + assign(hs_at(1), HDR_E)
    )
    out = run(body)
    assert out.hs.elements[0] == Header("h8", True, [Bits(8, 4)])
    assert out.hs.elements[1] == Header("h8", False, [Bits(8, 4)])


def test_out_of_range_stack_read_is_a_zero_invalid_header_and_write_does_nothing() -> None:
    body = (
        assign(E_F, bits(8, 1))
        + assign(META_N, f'member {{ base {{ {hs_at(5)} }} field: "f" }}')
        + assign(f'member {{ base {{ {hs_at(5)} }} field: "f" }}', bits(8, 3))
        + assign(hs_at(5), HDR_E)
        + stmt(f"set_valid {{ header {{ {hs_at(5)} }} }}")
    )
    out = run(body)
    assert out.n == Bits(8, 0)
    assert out.hs == Stack("h8", [Header("h8", False, [Bits(8, 0)])] * 2, 0)


def test_last_index_wraps_at_next_index_zero() -> None:
    cast = f"cast {{ to {{ bits: 8 }} operand {{ last_index {{ stack {{ {HDR_HS} }} }} }} }}"
    assert run(assign(META_N, cast)).n == Bits(8, 255)


def stack_of(a: int, b: int, next_index: int) -> Struct:
    return Struct(
        "H",
        [
            Header("h8", False, [Bits(8, 0)]),
            Stack(
                "h8",
                [Header("h8", True, [Bits(8, a)]), Header("h8", True, [Bits(8, b)])],
                next_index,
            ),
        ],
    )


def test_push_front_shifts_up_and_pops_the_last() -> None:
    out = run(stmt(f"push {{ stack {{ {HDR_HS} }} count: 1 }}"), headers=stack_of(1, 2, 2))
    assert out.hs == Stack(
        "h8", [Header("h8", False, [Bits(8, 0)]), Header("h8", True, [Bits(8, 1)])], 2
    )
    out = run(stmt(f"push {{ stack {{ {HDR_HS} }} count: 1 }}"), headers=stack_of(1, 2, 1))
    assert out.hs.next_index == 2


def test_pop_front_shifts_down_and_clears_the_last() -> None:
    out = run(stmt(f"pop {{ stack {{ {HDR_HS} }} count: 1 }}"), headers=stack_of(1, 2, 2))
    assert out.hs == Stack(
        "h8", [Header("h8", True, [Bits(8, 2)]), Header("h8", False, [Bits(8, 0)])], 1
    )
    out = run(stmt(f"pop {{ stack {{ {HDR_HS} }} count: 3 }}"), headers=stack_of(1, 2, 1))
    assert out.hs == Stack("h8", [Header("h8", False, [Bits(8, 0)])] * 2, 0)


# ---------------------------------------------------------------------------
# Tables and actions
# ---------------------------------------------------------------------------

SET_N = f"""
actions {{
  name: "set_n"
  params {{ name: "v" type {{ bits: 8 }} direction: DIRECTION_NONE }}
  body {{ assign {{ target {{ {META_N} }} value {{ var: "v" }} }} }}
}}
actions {{ name: "NoAction" }}
"""

TABLE = f"""
tables {{
  name: "tbl"
  keys {{ expr {{ {E_F} }} match_kind: MATCH_KIND_EXACT name: "hdr.e.f" }}
  actions: "set_n"
  actions: "NoAction"
}}
"""

ENTRIES = """
tables {
  block: "C" table: "tbl"
  entries { keys { exact: "5" } action { action: "set_n" args { bits { width: 8 value: "3" } } } }
}
"""


def test_apply_runs_the_matching_action_and_records_hit() -> None:
    body = (
        assign(E_F, bits(8, 5))
        + stmt('apply { table: "tbl" hit { var: "hit" } }')
        + assign(META_FLAG, 'var: "hit"')
    )
    out = run(body, SET_N + TABLE, entries=ENTRIES)
    assert out.n == Bits(8, 3) and out.flag is True


def test_apply_on_a_miss_runs_the_default_and_hit_is_false() -> None:
    body = (
        assign(E_F, bits(8, 6))
        + assign(META_FLAG, "literal { boolean: true }")
        + stmt('apply { table: "tbl" hit { var: "hit" } }')
        + assign(META_FLAG, 'var: "hit"')
    )
    out = run(body, SET_N + TABLE, entries=ENTRIES)
    assert out.n == Bits(8, 0) and out.flag is False


def test_direct_action_call_passes_directional_arguments() -> None:
    decls = """
    actions {
      name: "inc"
      params { name: "v" type { bits: 8 } direction: DIRECTION_INOUT }
      params { name: "d" type { bits: 8 } direction: DIRECTION_IN }
      params { name: "done" type { boolean {} } direction: DIRECTION_OUT }
      body { assign { target { var: "v" } value {
        binary { op: BINARY_OP_ADD left { var: "v" } right { var: "d" } } } } }
      body { assign { target { var: "done" } value { literal { boolean: true } } } }
    }
    """
    call = f"""
    body {{ call_action {{
      action: "inc"
      args {{ lvalue {{ {META_N} }} }}
      args {{ expr {{ {bits(8, 2)} }} }}
      args {{ lvalue {{ {META_FLAG} }} }}
    }} }}
    """
    out = run(assign(META_N, bits(8, 40)) + call, decls)
    assert out.n == Bits(8, 42) and out.flag is True


def test_an_out_parameter_starts_at_zero() -> None:
    decls = """
    actions {
      name: "one"
      params { name: "v" type { bits: 8 } direction: DIRECTION_OUT }
      body { assign { target { var: "v" } value { binary {
        op: BINARY_OP_ADD left { var: "v" } right { literal { bits { width: 8 value: "1" } } }
      } } } }
    }
    """
    call = f'body {{ call_action {{ action: "one" args {{ lvalue {{ {META_N} }} }} }} }}'
    assert run(assign(META_N, bits(8, 40)) + call, decls).n == Bits(8, 1)


def test_an_action_sees_the_blocks_variables() -> None:
    decls = f"""
    actions {{
      name: "bump_t"
      body {{ assign {{ target {{ var: "t" }} value {{ {bits(8, 7)} }} }} }}
    }}
    """
    body = stmt('call_action { action: "bump_t" }') + assign(META_N, 'var: "t"')
    assert run(body, decls).n == Bits(8, 7)


# ---------------------------------------------------------------------------
# Sub-controls and externs
# ---------------------------------------------------------------------------

SUB = """
blocks {
  name: "Sub" kind: BLOCK_KIND_CONTROL
  params { name: "a" type { bits: 8 } direction: DIRECTION_IN }
  params { name: "b" type { bits: 8 } direction: DIRECTION_OUT }
  params { name: "c" type { bits: 8 } direction: DIRECTION_INOUT }
  locals { name: "scratch" type { bits: 8 } }
  body { assign { target { var: "b" } value {
    binary { op: BINARY_OP_ADD left { var: "b" } right { var: "a" } } } } }
  body { assign { target { var: "c" } value {
    binary { op: BINARY_OP_ADD left { var: "c" } right { var: "a" } } } } }
  body { assign { target { var: "scratch" } value { var: "c" } } }
}
"""


def test_sub_control_call_copies_in_and_out() -> None:
    call = f"""
    body {{ call_block {{
      block: "Sub"
      args {{ expr {{ {E_F} }} }}
      args {{ lvalue {{ var: "t" }} }}
      args {{ lvalue {{ {META_N} }} }}
    }} }}
    """
    body = (
        assign(E_F, bits(8, 3))
        + assign(META_N, bits(8, 10))
        + assign('var: "t"', bits(8, 100))
        + call
        + assign(
            META_FLAG, f'binary {{ op: BINARY_OP_EQ left {{ var: "t" }} right {{ {bits(8, 3)} }} }}'
        )
    )
    out = run(body, extra=SUB)
    assert out.n == Bits(8, 13)  # inout: copied in, added to, copied out
    assert out.flag is True  # out: started at zero in the callee, copied out


def test_extern_call_with_an_out_argument_and_a_return_value() -> None:
    reg = FakeReg()
    body = (
        assign(META_N, bits(8, 4))
        + stmt(
            f'call_extern {{ instance: "reg" method: "read" '
            f'args {{ expr {{ {META_N} }} }} args {{ lvalue {{ var: "t" }} }} }}'
        )
        + stmt(
            f'call_extern {{ instance: "reg" method: "bump" '
            f'args {{ expr {{ var: "t" }} }} result {{ {META_N} }} }}'
        )
    )
    out = run(body, externs={"reg": reg})
    assert out.n == Bits(8, 10)
    assert reg.calls == [("read", [Bits(8, 4), Bits(8, 0)]), ("bump", [Bits(8, 5)])]


def test_run_control_does_not_mutate_its_arguments() -> None:
    headers = stack_of(1, 2, 2)
    metadata = Struct("M", [Bits(8, 1), False])
    run(assign(E_F, bits(8, 9)) + assign(META_N, bits(8, 9)), headers=headers, metadata=metadata)
    assert headers == stack_of(1, 2, 2)
    assert metadata == Struct("M", [Bits(8, 1), False])
