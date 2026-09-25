"""Parsers: extract, select, errors, the revisit rule, sub-parsers, per
docs/ir-semantics.md, "Parsers" and "Header stacks"."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from p4blo import ir
from p4blo.arch import entry
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.entry import ParseOutcome
from p4blo.interp import values
from p4blo.interp.values import NO_ERROR, Bits, ErrorValue, Header, Stack
from p4blo.v0 import p4blo_pb2 as pb

TEMPLATE = """
errors: "NoError"
errors: "PacketTooShort"
errors: "NoMatch"
errors: "StackOutOfBounds"
errors: "HeaderTooShort"
errors: "ParserTimeout"
errors: "ParserInvalidArgument"
errors: "BadVersion"
header_types { name: "h8" fields { name: "f" type { bits: 8 } } }
header_types { name: "h0" }
header_types {
  name: "mixed"
  fields { name: "a" type { bits: 3 } }
  fields { name: "flag" type { boolean {} } }
  fields { name: "b" type { bits: 12 } }
}
struct_types {
  name: "H"
  fields { name: "e" type { header: "h8" } }
  fields { name: "hs" type { stack { header: "h8" size: 2 } } }
  fields { name: "w" type { header: "mixed" } }
  fields { name: "z" type { header: "h0" } }
}
struct_types {
  name: "M"
  fields { name: "n" type { bits: 8 } }
  fields { name: "flag" type { boolean {} } }
}
headers: "H"
metadata: "M"
blocks {
  name: "P" kind: BLOCK_KIND_PARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_OUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  start_state: "start"
  @STATES@
}
blocks {
  name: "D" kind: BLOCK_KIND_DEPARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_IN }
  body { emit { value { member { base { var: "hdr" } field: "w" } } } }
}
@EXTRA@
"""

HDR_E = 'member { base { var: "hdr" } field: "e" }'
HDR_W = 'member { base { var: "hdr" } field: "w" }'
HDR_HS = 'member { base { var: "hdr" } field: "hs" }'
HS_NEXT = f"next {{ stack {{ {HDR_HS} }} }}"
E_F = f'member {{ base {{ {HDR_E} }} field: "f" }}'
META_N = 'member { base { var: "meta" } field: "n" }'
ACCEPT = "transition { direct { accept {} } }"


def program(states: str, extra: str = "") -> ir.Index:
    text = TEMPLATE.replace("@STATES@", states).replace("@EXTRA@", extra)
    return BoundIndex.build(arch_wire.load_text(text))


def run(states: str, packet: bytes, extra: str = "") -> ParseOutcome:
    index = program(states, extra)
    metadata = values.zero(pb.Type(struct="M"), index)
    assert isinstance(metadata, values.Struct)
    return entry.run_parser(index, "P", packet, metadata, {})


def e(outcome: ParseOutcome) -> Header:
    header = outcome.headers.fields[0]
    assert isinstance(header, Header)
    return header


def hs(outcome: ParseOutcome) -> Stack:
    stack = outcome.headers.fields[1]
    assert isinstance(stack, Stack)
    return stack


def w(outcome: ParseOutcome) -> Header:
    header = outcome.headers.fields[2]
    assert isinstance(header, Header)
    return header


def n(outcome: ParseOutcome) -> Bits:
    value = outcome.metadata.fields[0]
    assert isinstance(value, Bits)
    return value


def state(name: str, body: str, transition: str) -> str:
    return f'states {{ name: "{name}" {body} {transition} }}'


def bits(width: int, value: int) -> str:
    return f'bits {{ width: {width} value: "{value}" }}'


# ---------------------------------------------------------------------------
# Extract, lookahead, advance
# ---------------------------------------------------------------------------


def test_extract_fills_the_fields_and_sets_valid() -> None:
    out = run(state("start", f"body {{ extract {{ target {{ {HDR_E} }} }} }}", ACCEPT), b"\xab\xcd")
    assert out.accepted and out.error == NO_ERROR
    assert e(out) == Header("h8", True, [Bits(8, 0xAB)])
    assert out.consumed_bits == 8


def test_extract_takes_fields_most_significant_first() -> None:
    out = run(state("start", f"body {{ extract {{ target {{ {HDR_W} }} }} }}", ACCEPT), b"\xb5\x67")
    # 0xB567 = 101 1 010101100111
    assert w(out) == Header("mixed", True, [Bits(3, 0b101), True, Bits(12, 0x567)])
    assert out.consumed_bits == 16


def test_extract_past_the_end_is_packet_too_short_and_consumes_nothing() -> None:
    out = run(state("start", f"body {{ extract {{ target {{ {HDR_E} }} }} }}", ACCEPT), b"")
    assert not out.accepted
    assert out.error == ErrorValue("PacketTooShort")
    assert out.consumed_bits == 0
    assert not e(out).valid


def test_lookahead_reads_without_consuming_and_a_header_result_is_valid() -> None:
    peek_bits = "lookahead { type { bits: 8 } }"
    peek_header = 'lookahead { type { header: "mixed" } }'
    body = f"""
    body {{ assign {{ target {{ {META_N} }} value {{ {peek_bits} }} }} }}
    body {{ assign {{ target {{ {HDR_W} }} value {{ {peek_header} }} }} }}
    body {{ extract {{ target {{ {HDR_E} }} }} }}
    """
    out = run(state("start", body, ACCEPT), b"\x2a\x01")
    assert n(out) == Bits(8, 0x2A)
    assert w(out) == Header("mixed", True, [Bits(3, 0b001), False, Bits(12, 0xA01)])
    assert e(out).fields[0] == Bits(8, 0x2A)
    assert out.consumed_bits == 8


def test_lookahead_past_the_end_is_packet_too_short() -> None:
    peek = "lookahead { type { bits: 8 } }"
    body = f"body {{ assign {{ target {{ {META_N} }} value {{ {peek} }} }} }}"
    out = run(state("start", body, ACCEPT), b"")
    assert out.error == ErrorValue("PacketTooShort")


def test_extract_of_a_zero_width_header_sets_valid_and_consumes_nothing() -> None:
    hdr_z = 'member { base { var: "hdr" } field: "z" }'
    out = run(state("start", f"body {{ extract {{ target {{ {hdr_z} }} }} }}", ACCEPT), b"")
    assert out.accepted and out.consumed_bits == 0
    assert out.headers.fields[3] == Header("h0", True, [])
    # It consumes nothing, so a loop over it hits the revisit rule.
    loop = state(
        "start",
        f"body {{ extract {{ target {{ {hdr_z} }} }} }}",
        'transition { direct { state: "start" } }',
    )
    assert run(loop, b"\x01").error == ErrorValue("ParserTimeout")


def test_advance_skips_bits() -> None:
    body = f"""
    body {{ advance {{ bits {{ literal {{ {bits(32, 8)} }} }} }} }}
    body {{ extract {{ target {{ {HDR_E} }} }} }}
    """
    out = run(state("start", body, ACCEPT), b"\x01\x02")
    assert e(out).fields[0] == Bits(8, 2)
    assert out.consumed_bits == 16


def test_advance_past_the_end_is_packet_too_short_and_the_cursor_stays() -> None:
    body = f"body {{ advance {{ bits {{ literal {{ {bits(32, 16)} }} }} }} }}"
    out = run(state("start", body, ACCEPT), b"\x01")
    assert out.error == ErrorValue("PacketTooShort")
    assert out.consumed_bits == 0


# ---------------------------------------------------------------------------
# Select, verify, reject
# ---------------------------------------------------------------------------


def set_n(name: str, value: int) -> str:
    body = (
        f"body {{ assign {{ target {{ {META_N} }} value {{ literal {{ {bits(8, value)} }} }} }} }}"
    )
    return state(name, body, ACCEPT)


SELECT_STATES = (
    state(
        "start",
        f"body {{ extract {{ target {{ {HDR_E} }} }} }}",
        f"""
        transition {{ select {{
          keys {{ {E_F} }}
          cases {{ sets {{ exact {{ {bits(8, 1)} }} }} target {{ state: "s_exact" }} }}
          cases {{
            sets {{ masked {{ value {{ {bits(8, 0x80)} }} mask {{ {bits(8, 0x80)} }} }} }}
            target {{ state: "s_masked" }}
          }}
          cases {{
            sets {{ range {{ lo {{ {bits(8, 0x10)} }} hi {{ {bits(8, 0x1F)} }} }} }}
            target {{ state: "s_range" }}
          }}
          cases {{ sets {{ dont_care {{}} }} target {{ state: "s_default" }} }}
        }} }}
        """,
    )
    + set_n("s_exact", 1)
    + set_n("s_masked", 2)
    + set_n("s_range", 3)
    + set_n("s_default", 4)
)


@pytest.mark.parametrize(
    ("byte", "expected"),
    [(0x01, 1), (0x81, 2), (0x15, 3), (0x05, 4), (0x91, 2), (0x10, 3)],
)
def test_select_tries_the_cases_in_order(byte: int, expected: int) -> None:
    out = run(SELECT_STATES, bytes([byte]))
    assert out.accepted
    assert n(out) == Bits(8, expected)


def test_select_with_no_matching_case_rejects_with_no_match() -> None:
    transition = f"""
    transition {{ select {{
      keys {{ {E_F} }}
      cases {{ sets {{ exact {{ {bits(8, 1)} }} }} target {{ accept {{}} }} }}
    }} }}
    """
    out = run(state("start", f"body {{ extract {{ target {{ {HDR_E} }} }} }}", transition), b"\x02")
    assert not out.accepted
    assert out.error == ErrorValue("NoMatch")
    assert out.consumed_bits == 8


def test_select_on_several_keys_needs_every_set_to_match() -> None:
    transition = f"""
    transition {{ select {{
      keys {{ {E_F} }}
      keys {{ member {{ base {{ var: "meta" }} field: "flag" }} }}
      cases {{
        sets {{ exact {{ {bits(8, 1)} }} }}
        sets {{ exact {{ boolean: true }} }}
        target {{ accept {{}} }}
      }}
      cases {{ sets {{ dont_care {{}} }} sets {{ dont_care {{}} }} target {{ reject {{}} }} }}
    }} }}
    """
    out = run(state("start", f"body {{ extract {{ target {{ {HDR_E} }} }} }}", transition), b"\x01")
    assert not out.accepted  # meta.flag is false


def test_verify_raises_its_error_when_the_condition_is_false() -> None:
    body = f"""
    body {{ extract {{ target {{ {HDR_E} }} }} }}
    body {{ verify {{
      condition {{ binary {{
        op: BINARY_OP_EQ left {{ {E_F} }} right {{ literal {{ {bits(8, 1)} }} }}
      }} }}
      error: "BadVersion"
    }} }}
    """
    assert run(state("start", body, ACCEPT), b"\x01").accepted
    out = run(state("start", body, ACCEPT), b"\x02")
    assert not out.accepted
    assert out.error == ErrorValue("BadVersion")
    assert e(out).valid  # the outcome is the state at the moment of the error


def test_explicit_reject_is_not_accepted_and_has_no_error() -> None:
    out = run(state("start", "", "transition { direct { reject {} } }"), b"\x01")
    assert not out.accepted
    assert out.error == NO_ERROR


def test_verify_with_no_error_is_an_explicit_reject() -> None:
    body = 'body { verify { condition { literal { boolean: false } } error: "NoError" } }'
    out = run(state("start", body, ACCEPT), b"\x01")
    assert not out.accepted
    assert out.error == NO_ERROR


def test_an_error_keeps_the_partial_headers_and_metadata() -> None:
    body = f"""
    body {{ assign {{ target {{ {META_N} }} value {{ literal {{ {bits(8, 5)} }} }} }} }}
    body {{ extract {{ target {{ {HDR_E} }} }} }}
    body {{ extract {{ target {{ {HDR_W} }} }} }}
    """
    out = run(state("start", body, ACCEPT), b"\x07")
    assert out.error == ErrorValue("PacketTooShort")
    assert n(out) == Bits(8, 5)
    assert e(out) == Header("h8", True, [Bits(8, 7)])
    assert not w(out).valid
    assert out.consumed_bits == 8


# ---------------------------------------------------------------------------
# Stacks and the revisit rule
# ---------------------------------------------------------------------------

LOOP_UNTIL_LAST = state(
    "start",
    f"body {{ extract {{ target {{ {HS_NEXT} }} }} }}",
    f"""
    transition {{ select {{
      keys {{ last_index {{ stack {{ {HDR_HS} }} }} }}
      cases {{ sets {{ exact {{ {bits(32, 1)} }} }} target {{ accept {{}} }} }}
      cases {{ sets {{ dont_care {{}} }} target {{ state: "start" }} }}
    }} }}
    """,
)


def test_last_index_wraps_at_next_index_zero() -> None:
    """Before any extract `nextIndex` is 0 and `lastIndex` is `2^32 - 1`;
    after one it is 0 (docs/ir-semantics.md, "`hs.lastIndex`"). A parser is
    the only place P4 allows it."""
    last = f"cast {{ to {{ bits: 8 }} operand {{ last_index {{ stack {{ {HDR_HS} }} }} }} }}"
    before = state(
        "start", f"body {{ assign {{ target {{ {META_N} }} value {{ {last} }} }} }}", ACCEPT
    )
    assert n(run(before, b"")) == Bits(8, 255)
    after = state(
        "start",
        f"body {{ extract {{ target {{ {HS_NEXT} }} }} }}"
        f" body {{ assign {{ target {{ {META_N} }} value {{ {last} }} }} }}",
        ACCEPT,
    )
    assert n(run(after, b"\x0a")) == Bits(8, 0)


LOOP_FOREVER = state(
    "start",
    f"body {{ extract {{ target {{ {HS_NEXT} }} }} }}",
    'transition { direct { state: "start" } }',
)


def test_a_loop_over_a_stack_terminates_by_extraction() -> None:
    out = run(LOOP_UNTIL_LAST, b"\x0a\x0b\x0c")
    assert out.accepted
    assert hs(out).elements == [
        Header("h8", True, [Bits(8, 0x0A)]),
        Header("h8", True, [Bits(8, 0x0B)]),
    ]
    assert hs(out).next_index == 2
    assert out.consumed_bits == 16


def test_extract_into_a_full_stack_is_stack_out_of_bounds() -> None:
    out = run(LOOP_FOREVER, b"\x0a\x0b\x0c")
    assert out.error == ErrorValue("StackOutOfBounds")
    assert all(h.valid for h in hs(out).elements)
    assert out.consumed_bits == 16


def test_a_full_stack_is_reported_before_a_short_packet() -> None:
    out = run(LOOP_FOREVER, b"\x0a\x0b")
    assert out.error == ErrorValue("StackOutOfBounds")
    assert out.consumed_bits == 16


def test_revisiting_a_state_without_consuming_is_parser_timeout() -> None:
    out = run(state("start", "", 'transition { direct { state: "start" } }'), b"\x01")
    assert out.error == ErrorValue("ParserTimeout")
    assert out.consumed_bits == 0


def test_the_revisit_rule_sees_a_cycle_through_another_state() -> None:
    states = state("start", "", 'transition { direct { state: "other" } }') + state(
        "other", "", 'transition { direct { state: "start" } }'
    )
    out = run(states, b"\x01")
    assert out.error == ErrorValue("ParserTimeout")


def test_revisiting_after_consuming_is_allowed() -> None:
    # `start` is entered at cursor 0 and again at 8; the second entry is fine
    # and the loop ends on the stack, not on the revisit rule.
    out = run(LOOP_FOREVER, b"\x0a\x0b\x0c")
    assert out.error == ErrorValue("StackOutOfBounds")


# ---------------------------------------------------------------------------
# Sub-parsers
# ---------------------------------------------------------------------------


def sub_parser(params: str, states: str) -> str:
    return (
        f'blocks {{ name: "Sub" kind: BLOCK_KIND_PARSER {params} start_state: "start" {states} }}'
    )


def test_sub_parser_call_copies_out_arguments_back() -> None:
    sub = sub_parser(
        'params { name: "x" type { header: "h8" } direction: DIRECTION_OUT }',
        state("start", 'body { extract { target { var: "x" } } }', ACCEPT),
    )
    body = f'body {{ call_block {{ block: "Sub" args {{ lvalue {{ {HDR_E} }} }} }} }}'
    out = run(state("start", body, ACCEPT), b"\x42", sub)
    assert out.accepted
    assert e(out) == Header("h8", True, [Bits(8, 0x42)])
    assert out.consumed_bits == 8


def test_sub_parser_error_copies_back_before_propagating() -> None:
    sub = sub_parser(
        'params { name: "x" type { header: "h8" } direction: DIRECTION_OUT }'
        'params { name: "y" type { header: "h8" } direction: DIRECTION_OUT }',
        state(
            "start",
            'body { extract { target { var: "x" } } } body { extract { target { var: "y" } } }',
            ACCEPT,
        ),
    )
    hs0 = f"index {{ base {{ {HDR_HS} }} index {{ literal {{ {bits(32, 0)} }} }} }}"
    body = f"""
    body {{ call_block {{
      block: "Sub" args {{ lvalue {{ {HDR_E} }} }} args {{ lvalue {{ {hs0} }} }}
    }} }}
    """
    out = run(state("start", body, ACCEPT), b"\x42", sub)
    assert out.error == ErrorValue("PacketTooShort")
    assert e(out) == Header("h8", True, [Bits(8, 0x42)])
    assert not hs(out).elements[0].valid
    assert out.consumed_bits == 8


def test_sub_parser_states_count_for_the_revisit_rule() -> None:
    sub = sub_parser(
        'params { name: "x" type { header: "h8" } direction: DIRECTION_OUT }',
        state("start", "", ACCEPT),
    )
    call = f'body {{ call_block {{ block: "Sub" args {{ lvalue {{ {HDR_E} }} }} }} }}'
    out = run(state("start", call + call, ACCEPT), b"\x42", sub)
    assert out.error == ErrorValue("ParserTimeout")


# ---------------------------------------------------------------------------
# Property: emit then extract returns the header
# ---------------------------------------------------------------------------


@given(st.integers(0, 7), st.booleans(), st.integers(0, 4095), st.booleans())
def test_emit_then_extract_roundtrips_a_header(a: int, flag: bool, b: int, valid: bool) -> None:
    index = program(state("start", f"body {{ extract {{ target {{ {HDR_W} }} }} }}", ACCEPT))
    headers = values.zero(pb.Type(struct="H"), index)
    assert isinstance(headers, values.Struct)
    headers.fields[2] = Header("mixed", valid, [Bits(3, a), flag, Bits(12, b)])
    emitted = entry.run_deparser(index, "D", headers, {})
    metadata = values.zero(pb.Type(struct="M"), index)
    assert isinstance(metadata, values.Struct)
    out = entry.run_parser(index, "P", emitted, metadata, {})
    if valid:
        assert len(emitted) == 2
        assert out.accepted
        assert values.equal(w(out), headers.fields[2])
    else:
        assert emitted == b""
        assert out.error == ErrorValue("PacketTooShort")
