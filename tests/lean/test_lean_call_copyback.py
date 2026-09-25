"""Copy-back writes through the lvalue resolved at copy-in, on both interpreters.

docs/ir-semantics.md, "Copy-back target": an index inside an `out` or
`inout` argument is evaluated once, when the argument is copied in, as
SpecTec's `Copy_in_arg` keeps the storage reference that
`Copy_out_argument` writes through. Each program here makes the callee
change the index variable, so writing through the syntactic lvalue again
would land on another element. The expected bytes are written out by hand
from that rule, not computed by either interpreter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from p4blo import arch, ir, validator
from p4blo.arch.externs.crc import crc16
from p4blo.drt.case import Case
from p4blo.drt.run import compare_program, run_python
from p4blo.v0 import p4blo_pb2 as pb

CallKind = Literal["action", "block"]

_ERRORS = "".join(
    f'errors: "{e}"\n'
    for e in (
        "NoError",
        "PacketTooShort",
        "NoMatch",
        "StackOutOfBounds",
        "HeaderTooShort",
        "ParserTimeout",
        "ParserInvalidArgument",
    )
)


def _lit(width: int, value: int) -> str:
    return f'literal {{ bits {{ width: {width} value: "{value}" }} }}'


def _field(name: str) -> str:
    """`hdr.<name>`, spelled the same as an lvalue and as an expression."""
    return f'member {{ base {{ var: "hdr" }} field: "{name}" }}'


def _extract(stack: str) -> str:
    """A parser statement extracting into `hdr.<stack>.next`."""
    return f"body {{ extract {{ target {{ next {{ stack {{ {_field(stack)} }} }} }} }} }}"


def _element(field: str | None = None) -> str:
    """`hdr.hs[t]`, or its `field`, spelled the same as an lvalue and as an
    expression."""
    element = 'index { base { member { base { var: "hdr" } field: "hs" } } index { var: "t" } }'
    if field is None:
        return element
    return f'member {{ base {{ {element} }} field: "{field}" }}'


def copyback_program(kind: CallKind, first: int, second: int, overlap: bool) -> pb.Program:
    """A control that sets `t = first` and calls with `hdr.hs[t]` as an
    `inout` argument; the callee sets `t` to `second` and writes `x.f`.

    An action writes `t` directly, since it sees its block's variables. A
    sub-control cannot, so it writes an `out` parameter bound to `t`, which
    is copied back before `x` in parameter order. With `overlap`, an `in`
    argument `hdr.hs[t].f` overlaps the `inout` one and `x.f` becomes
    `y + 16`; otherwise `x.f` becomes `170`.
    """

    def set_index(target: str) -> str:
        return f'body {{ assign {{ target {{ var: "{target}" }} value {{ {_lit(8, second)} }} }} }}'

    if overlap:
        in_param = 'params { name: "y" type { bits: 8 } direction: DIRECTION_IN }'
        in_arg = f"args {{ expr {{ {_element('f')} }} }}"
        value = 'binary { op: BINARY_OP_ADD left { var: "y" } right { ' + _lit(8, 16) + " } }"
    else:
        in_param = in_arg = ""
        value = _lit(8, 170)
    write_x = (
        'body { assign { target { member { base { var: "x" } field: "f" } }'
        f" value {{ {value} }} }} }}"
    )
    inout_param = 'params { name: "x" type { header: "h8" } direction: DIRECTION_INOUT }'
    inout_arg = f"args {{ lvalue {{ {_element()} }} }}"
    if kind == "action":
        callee = f"""
  actions {{
    name: "a"
    {in_param}
    {inout_param}
    {set_index("t")}
    {write_x}
  }}"""
        call = f'body {{ call_action {{ action: "a" {in_arg} {inout_arg} }} }}'
        sub = ""
    else:
        callee = ""
        call = (
            'body { call_block { block: "B" args { lvalue { var: "t" } } '
            f"{in_arg} {inout_arg} }} }}"
        )
        sub = f"""
blocks {{
  name: "B" kind: BLOCK_KIND_CONTROL
  params {{ name: "s" type {{ bits: 8 }} direction: DIRECTION_OUT }}
  {in_param}
  {inout_param}
  {set_index("s")}
  {write_x}
}}"""
    text = f"""
name: "copyback-{kind}{"-overlap" if overlap else ""}"
{_ERRORS}
header_types {{ name: "h8" fields {{ name: "f" type {{ bits: 8 }} }} }}
struct_types {{ name: "H" fields {{ name: "hs" type {{ stack {{ header: "h8" size: 2 }} }} }} }}
struct_types {{ name: "M" }}
blocks {{
  name: "P" kind: BLOCK_KIND_PARSER
  params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_OUT }}
  params {{ name: "meta" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
  states {{
    name: "start"
    {_extract("hs")}
    {_extract("hs")}
    transition {{ direct {{ accept {{}} }} }}
  }}
  start_state: "start"
}}
blocks {{
  name: "C" kind: BLOCK_KIND_CONTROL
  params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_INOUT }}
  params {{ name: "meta" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
  locals {{ name: "t" type {{ bits: 8 }} }}{callee}
  body {{ assign {{ target {{ var: "t" }} value {{ {_lit(8, first)} }} }} }}
  {call}
}}{sub}
blocks {{
  name: "D" kind: BLOCK_KIND_DEPARSER
  params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_IN }}
  body {{ emit {{ value {{ member {{ base {{ var: "hdr" }} field: "hs" }} }} }} }}
}}
headers: "H"
metadata: "M"
exports {{ role: "parser" block: "P" }}
exports {{ role: "control" block: "C" }}
exports {{ role: "deparser" block: "D" }}
"""
    return ir.load_text(text)


def expected_copyback(first: int, packet: bytes, overlap: bool) -> bytes:
    """The two elements after the call: only `hs[first]` changes, and not
    at all when `first` is past the end (a write there does nothing)."""
    out = bytearray(packet[:2])
    if first < 2:
        out[first] = (packet[first] + 16) % 256 if overlap else 170
    return bytes(out) + packet[2:]


def check(program: pb.Program, case: Case, expected: bytes, lean_binary: Path) -> None:
    assert validator.validate(program) == []
    report = compare_program(program, [case], 4, [lean_binary])
    assert report.passed, report.summary()
    assert run_python(arch.reference.load(program), case, 4) == [(0, expected)]


@pytest.mark.parametrize("kind", ["action", "block"])
@pytest.mark.parametrize(("first", "second"), [(0, 1), (1, 0), (2, 0), (0, 2)])
def test_lean_agrees_copyback_writes_the_element_resolved_at_copy_in(
    lean_binary: Path, kind: CallKind, first: int, second: int
) -> None:
    """The reproducer of the ledger review: `a(hdr.hs[t])` with the callee
    moving `t`. Writing `hs[second]` instead is the old re-resolution."""
    packet = bytes([0x05, 0x07, 0xDE, 0xAD])
    program = copyback_program(kind, first, second, overlap=False)
    check(
        program, Case(pb.Entries(), 0, packet), expected_copyback(first, packet, False), lean_binary
    )


@pytest.mark.parametrize("kind", ["action", "block"])
@pytest.mark.parametrize(("first", "second"), [(0, 1), (1, 0), (2, 1)])
def test_lean_agrees_copyback_with_an_overlapping_in_argument(
    lean_binary: Path, kind: CallKind, first: int, second: int
) -> None:
    """`a(hdr.hs[t].f, hdr.hs[t])`: the `in` copy and the `inout` target
    both resolve before the body moves `t`."""
    packet = bytes([0x05, 0x07])
    program = copyback_program(kind, first, second, overlap=True)
    check(
        program, Case(pb.Entries(), 0, packet), expected_copyback(first, packet, True), lean_binary
    )


def extern_program(first: int) -> pb.Program:
    """`r.read(hdr.hs[t].f, 0)` and `hdr.ws[t].g = crc.compute(hdr.hs[0].f)`
    with `t = first`.

    No extern family has both an `out` parameter and a result, and none has
    two `out` parameters, so no extern call can move its own target; this
    exercises the resolved paths of `callExtern` and `call_extern` (the out
    argument and the result lvalue) with computed indices, not a difference.
    """
    text = f"""
name: "copyback-extern"
{_ERRORS}
header_types {{ name: "h8" fields {{ name: "f" type {{ bits: 8 }} }} }}
header_types {{ name: "h16" fields {{ name: "g" type {{ bits: 16 }} }} }}
struct_types {{
  name: "H"
  fields {{ name: "hs" type {{ stack {{ header: "h8" size: 2 }} }} }}
  fields {{ name: "ws" type {{ stack {{ header: "h16" size: 2 }} }} }}
}}
struct_types {{ name: "M" }}
extern_types {{
  name: "register"
  constructor_params {{ name: "size" type {{ bits: 32 }} direction: DIRECTION_IN }}
  methods {{
    name: "read"
    params {{ name: "result" type {{ bits: 8 }} direction: DIRECTION_OUT }}
    params {{ name: "index" type {{ bits: 32 }} direction: DIRECTION_IN }}
  }}
  methods {{
    name: "write"
    params {{ name: "index" type {{ bits: 32 }} direction: DIRECTION_IN }}
    params {{ name: "value" type {{ bits: 8 }} direction: DIRECTION_IN }}
  }}
}}
extern_types {{
  name: "crc16"
  methods {{
    name: "compute"
    params {{ name: "data" type {{ bits: 8 }} direction: DIRECTION_IN }}
    returns {{ bits: 16 }}
  }}
}}
extern_instances {{ name: "r" extern_type: "register" args {{ bits {{ width: 32 value: "4" }} }} }}
extern_instances {{ name: "crc" extern_type: "crc16" }}
blocks {{
  name: "P" kind: BLOCK_KIND_PARSER
  params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_OUT }}
  params {{ name: "meta" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
  states {{
    name: "start"
    {_extract("hs")}
    {_extract("hs")}
    {_extract("ws")}
    {_extract("ws")}
    transition {{ direct {{ accept {{}} }} }}
  }}
  start_state: "start"
}}
blocks {{
  name: "C" kind: BLOCK_KIND_CONTROL
  params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_INOUT }}
  params {{ name: "meta" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
  locals {{ name: "t" type {{ bits: 8 }} }}
  body {{ assign {{ target {{ var: "t" }} value {{ {_lit(8, first)} }} }} }}
  body {{ call_extern {{ instance: "r" method: "write"
    args {{ expr {{ {_lit(32, 0)} }} }} args {{ expr {{ {_lit(8, 0x5A)} }} }} }} }}
  body {{ call_extern {{ instance: "r" method: "read"
    args {{ lvalue {{ {_element("f")} }} }} args {{ expr {{ {_lit(32, 0)} }} }} }} }}
  body {{ call_extern {{ instance: "crc" method: "compute"
    args {{ expr {{ member {{ base {{ index {{ base {{ {_field("hs")} }}
      index {{ {_lit(8, 0)} }} }} }} field: "f" }} }} }}
    result {{ member {{ base {{ index {{ base {{ {_field("ws")} }}
      index {{ var: "t" }} }} }} field: "g" }} }} }} }}
}}
blocks {{
  name: "D" kind: BLOCK_KIND_DEPARSER
  params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_IN }}
  body {{ emit {{ value {{ member {{ base {{ var: "hdr" }} field: "hs" }} }} }} }}
  body {{ emit {{ value {{ member {{ base {{ var: "hdr" }} field: "ws" }} }} }} }}
}}
headers: "H"
metadata: "M"
exports {{ role: "parser" block: "P" }}
exports {{ role: "control" block: "C" }}
exports {{ role: "deparser" block: "D" }}
"""
    return ir.load_text(text)


@pytest.mark.parametrize("first", [0, 1, 2])
def test_lean_agrees_extern_out_and_result_through_computed_indices(
    lean_binary: Path, first: int
) -> None:
    packet = bytes([0x05, 0x07, 0x11, 0x22, 0x33, 0x44])
    hs = bytearray(packet[:2])
    ws = bytearray(packet[2:6])
    if first < 2:
        hs[first] = 0x5A
        # The crc reads hs[0] after the register read wrote it.
        ws[2 * first : 2 * first + 2] = crc16(bytes([hs[0]])).to_bytes(2, "big")
    check(extern_program(first), Case(pb.Entries(), 0, packet), bytes(hs + ws), lean_binary)
