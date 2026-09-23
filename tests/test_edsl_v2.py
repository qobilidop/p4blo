"""The typed eDSL builds the IR it says it does, one focused test per construct.

Every test compares what a v2 program builds with hand-written text-format
IR. The forwarder rebuilding its golden (tests/test_corpus.py) is the
acceptance test; tests/test_pyright.py covers what pyright rejects.
"""

from __future__ import annotations

from enum import IntEnum

import pytest
from google.protobuf import text_format

from p4blo.edsl import (
    Bits,
    Bool,
    Control,
    CoreErrors,
    Deparser,
    EdslError,
    Enum,
    Error,
    Errors,
    Header,
    In,
    L,
    Out,
    Parser,
    Program,
    Stack,
    Struct,
    Table,
    Transition,
    action,
    bit,
    bit8,
    bit9,
    bit16,
    bit32,
    concat,
    entry,
    exact,
    lpm,
    masked,
    mux,
    state,
    ternary,
)
from p4blo.edsl.core import Program as CoreProgram
from p4blo.edsl.core import bit as core_bit
from p4blo.edsl.core.externs import checksum16, counter, register
from p4blo.edsl.externs import Checksum16, Counter, Register
from p4blo.v0 import p4blo_pb2 as pb

# -- a small program every test builds on ---------------------------------------


class h_t(Header):
    f: bit8
    g: bit16
    type: bit8  # a field named like an Expr attribute of the core: still a field


class headers(Struct):
    h: h_t
    stack: Stack[h_t, L[2]]


class metadata(Struct):
    x: bit8
    idx: bit32
    ok: Bool


class Kind(IntEnum):
    A = 1
    B = 2


def block(text: str) -> pb.Block:
    return text_format.Parse(text, pb.Block())


def member(base: str, field: str) -> str:
    return f'member {{ base {{ {base} }} field: "{field}" }}'


HDR_H = member('var: "hdr"', "h")
HDR_H_F = member(HDR_H, "f")
HDR_H_G = member(HDR_H, "g")
META_X = member('var: "meta"', "x")
META_IDX = member('var: "meta"', "idx")


class NoParser(Parser[headers, metadata]):
    @state
    def start(self) -> Transition:
        return self.accept


class NoControl(Control[headers, metadata]):
    pass


class NoDeparser(Deparser[headers]):
    pass


def build(
    parser: type[Parser[headers, metadata]] = NoParser,
    control: type[Control[headers, metadata]] = NoControl,
    deparser: type[Deparser[headers]] = NoDeparser,
    **kwargs: object,
) -> pb.Program:
    return Program(
        "t",
        headers=headers,
        metadata=metadata,
        parser=parser,
        control=control,
        deparser=deparser,
        **kwargs,  # pyright: ignore[reportArgumentType]
    ).build()


def control_of(cls: type[Control[headers, metadata]]) -> pb.Block:
    return build(control=cls).blocks[1]


# -- values and widths ------------------------------------------------------------


def test_values_and_widths() -> None:
    class C(Control[headers, metadata]):
        def apply(self) -> None:
            h = self.hdr.h
            self.assign(h.f, h.f + 1)  # an int takes the other operand's width
            self.assign(h.g, h.f.cast(bit16))
            self.assign(h.f, concat(h.f[3:0], h.f[7:4]).as_(bit8))
            self.assign(h.f, mux(h.f == Kind.A, bit8(2), 3))
            self.assign(self.meta.idx, bit(32)(7))

    body = control_of(C).body
    assert body[0] == text_format.Parse(
        f"""assign {{ target {{ {HDR_H_F} }}
          value {{ binary {{ op: BINARY_OP_ADD left {{ {HDR_H_F} }}
                    right {{ literal {{ bits {{ width: 8 value: "1" }} }} }} }} }} }}""",
        pb.Stmt(),
    )
    assert body[1].assign.value == text_format.Parse(
        f"cast {{ to {{ bits: 16 }} operand {{ {HDR_H_F} }} }}", pb.Expr()
    )
    assert body[2].assign.value == text_format.Parse(
        f"""binary {{ op: BINARY_OP_CONCAT
          left {{ slice {{ operand {{ {HDR_H_F} }} hi: 3 lo: 0 }} }}
          right {{ slice {{ operand {{ {HDR_H_F} }} hi: 7 lo: 4 }} }} }}""",
        pb.Expr(),
    )
    assert body[3].assign.value == text_format.Parse(
        f"""mux {{ condition {{ binary {{ op: BINARY_OP_EQ left {{ {HDR_H_F} }}
                  right {{ literal {{ bits {{ width: 8 value: "1" }} }} }} }} }}
          then {{ literal {{ bits {{ width: 8 value: "2" }} }} }}
          otherwise {{ literal {{ bits {{ width: 8 value: "3" }} }} }} }}""",
        pb.Expr(),
    )
    assert body[4].assign.value.literal.bits.width == 32


def test_width_mismatches_are_refused_at_run_time_too() -> None:
    class C(Control[headers, metadata]):
        def apply(self) -> None:
            self.assign(self.hdr.h.f, self.hdr.h.g)  # pyright: ignore[reportArgumentType, reportCallIssue]

    with pytest.raises(EdslError, match="expected bit<8>, got bit<16>"):
        control_of(C)
    with pytest.raises(EdslError, match="operands differ"):
        _ = bit8(1) + bit16(1)  # pyright: ignore[reportOperatorIssue]
    with pytest.raises(EdslError, match="is bit<16>, not bit<8>"):
        concat(bit8(1), bit8(2)).as_(bit8)
    with pytest.raises(EdslError, match="no truth value"):
        bool(bit8(1) == 1)


# -- views -----------------------------------------------------------------------


def test_views_declare_types_and_fields_are_attributes() -> None:
    program = build()
    assert [h.name for h in program.header_types] == ["h_t"]
    assert [f.name for f in program.header_types[0].fields] == ["f", "g", "type"]
    assert program.struct_types[0].fields[1].type == pb.Type(
        stack=pb.StackType(header="h_t", size=2)
    )
    assert program.struct_types[1].fields[2].type == pb.Type(boolean=pb.BoolType())
    assert program.headers == "headers" and program.metadata == "metadata"


def test_reserved_and_renamed_fields() -> None:
    with pytest.raises(EdslError, match="did you mean is_valid_"):

        class bad(Header):
            is_valid: bit8  # pyright: ignore[reportIncompatibleMethodOverride]

    class ok(Header, name="renamed_t", rename={"is_valid_": "is_valid"}):
        is_valid_: bit8

    assert ok.__core_type__ is not None
    assert ok.__core_type__.build() == text_format.Parse(
        'name: "renamed_t" fields { name: "is_valid" type { bits: 8 } }', pb.HeaderType()
    )

    class C(Control[headers, metadata]):
        def apply(self) -> None:
            self.assign(self.hdr.h.type, 1)
            self.assign(self.hdr.h.field("f"), 2)  # pyright: ignore[reportArgumentType, reportCallIssue]

    body = control_of(C).body
    assert body[0].assign.target == text_format.Parse(member(HDR_H, "type"), pb.LValue())
    assert body[1].assign.target == text_format.Parse(HDR_H_F, pb.LValue())


def test_stacks() -> None:
    class P(Parser[headers, metadata]):
        @state
        def start(self) -> Transition:
            self.extract(self.hdr.stack.next)
            self.assign(self.meta.x, self.hdr.stack.last.f)
            self.assign(self.meta.x, self.hdr.stack[1].f)
            return self.accept

    body = build(parser=P).blocks[0].states[0].body
    stack = member('var: "hdr"', "stack")
    assert body[0] == text_format.Parse(
        f"extract {{ target {{ next {{ stack {{ {stack} }} }} }} }}", pb.Stmt()
    )
    assert body[1].assign.value == text_format.Parse(
        f"""member {{ base {{ index {{ base {{ {stack} }}
              index {{ last_index {{ stack {{ {stack} }} }} }} }} }} field: "f" }}""",
        pb.Expr(),
    )
    assert body[2].assign.value == text_format.Parse(
        f"""member {{ base {{ index {{ base {{ {stack} }}
              index {{ literal {{ bits {{ width: 32 value: "1" }} }} }} }} }} field: "f" }}""",
        pb.Expr(),
    )


# -- states and transitions --------------------------------------------------------


def test_states_forward_reference_loop_and_select() -> None:
    class P(Parser[headers, metadata]):
        @state
        def start(self) -> Transition:
            return self.goto(self.again)  # a forward reference

        @state
        def again(self) -> Transition:
            self.extract(self.hdr.h)
            return self.select(
                self.hdr.h.f,
                {Kind.A: self.again, masked(0x80, 0x80): self.reject},  # a loop
                default=self.accept,
            )

    parser = build(parser=P).blocks[0]
    assert parser.start_state == "start"
    assert parser.states[0].transition == text_format.Parse(
        'direct { state: "again" }', pb.Transition()
    )
    assert parser.states[1].transition == text_format.Parse(
        f"""select {{ keys {{ {HDR_H_F} }}
          cases {{ sets {{ exact {{ bits {{ width: 8 value: "1" }} }} }}
                   target {{ state: "again" }} }}
          cases {{ sets {{ masked {{ value {{ bits {{ width: 8 value: "128" }} }}
                                   mask {{ bits {{ width: 8 value: "128" }} }} }} }}
                   target {{ reject {{ }} }} }}
          cases {{ sets {{ dont_care {{ }} }} target {{ accept {{ }} }} }} }}""",
        pb.Transition(),
    )


def test_a_state_must_return_its_transition() -> None:
    class P(Parser[headers, metadata]):
        @state
        def start(self) -> Transition:
            self.goto(self.start)
            return None  # pyright: ignore[reportReturnType]

    with pytest.raises(EdslError, match="must return its transition"):
        build(parser=P)


# -- actions and tables ------------------------------------------------------------


class Acting(Control[headers, metadata]):
    @action
    def nop(self) -> None:
        pass

    @action
    def set_f(self, value: bit8, port: bit9) -> None:
        self.assign(self.hdr.h.f, value)

    t1 = Table(keys=[lpm(headers.h.g)], actions=[set_f, nop], default=set_f(bit8(1), port=bit9(2)))
    t2 = Table(
        keys=(ternary(headers.h.f, name="h.f"), exact(headers.h.g)),
        actions=[set_f, nop],
        default=nop(),
        const_default=True,
        entries=[
            entry((masked(0x10, 0xF0), 5), set_f(bit8(3), bit9(4)), priority=1),
            entry((0x20, bit16(6)), nop(), priority=2),
        ],
        size=4,
    )

    def apply(self) -> None:
        # A recorded call; the checker wants places or literals for action
        # data, the core takes any value of the width.
        self.set_f(self.hdr.h.f + 1, 3)  # pyright: ignore[reportArgumentType]
        self.apply_table(self.t1)
        self.apply_table(self.t2, hit=self.meta.ok)


def test_actions_in_bodies_and_as_literals() -> None:
    c = control_of(Acting)
    assert [a.name for a in c.actions] == ["nop", "set_f"]
    assert (
        c.actions[1]
        == block(
            f"""actions {{ name: "set_f"
            params {{ name: "value" type {{ bits: 8 }} direction: DIRECTION_NONE }}
            params {{ name: "port" type {{ bits: 9 }} direction: DIRECTION_NONE }}
            body {{ assign {{ target {{ {HDR_H_F} }} value {{ var: "value" }} }} }} }}"""
        ).actions[0]
    )
    assert c.body[0] == text_format.Parse(
        f"""call_action {{ action: "set_f"
          args {{ expr {{ binary {{ op: BINARY_OP_ADD left {{ {HDR_H_F} }}
                    right {{ literal {{ bits {{ width: 8 value: "1" }} }} }} }} }} }}
          args {{ expr {{ literal {{ bits {{ width: 9 value: "3" }} }} }} }} }}""",
        pb.Stmt(),
    )
    assert c.tables[0].default_action == text_format.Parse(
        'action: "set_f" args { bits { width: 8 value: "1" } }'
        ' args { bits { width: 9 value: "2" } }',
        pb.ActionCall(),
    )


def test_tables_with_typed_entries_over_two_keys() -> None:
    c = control_of(Acting)
    assert (
        c.tables[1]
        == block(
            f"""tables {{ name: "t2"
            keys {{ expr {{ {HDR_H_F} }} match_kind: MATCH_KIND_TERNARY name: "h.f" }}
            keys {{ expr {{ {HDR_H_G} }} match_kind: MATCH_KIND_EXACT }}
            actions: "set_f" actions: "nop"
            default_action {{ action: "nop" }} const_default_action: true
            const_entries {{ keys {{ ternary {{ value: "16" mask: "240" }} }} keys {{ exact: "5" }}
              action {{ action: "set_f" args {{ bits {{ width: 8 value: "3" }} }}
                        args {{ bits {{ width: 9 value: "4" }} }} }} priority: 1 }}
            const_entries {{ keys {{ ternary {{ value: "32" mask: "255" }} }} keys {{ exact: "6" }}
              action {{ action: "nop" }} priority: 2 }}
            size: 4 }}"""
        ).tables[0]
    )
    assert c.body[2] == text_format.Parse(
        f'apply {{ table: "t2" hit {{ {member('var: "meta"', "ok")} }} }}', pb.Stmt()
    )


def test_a_key_path_binds_to_the_parameter_of_its_type() -> None:
    class Two(Control):
        a: In[headers]
        b: In[headers]
        t = Table(keys=[exact(headers.h.f)], actions=[])

    with pytest.raises(EdslError, match="has 2 such parameters"):
        build(control=Two)  # pyright: ignore[reportArgumentType]


# -- sub-blocks ------------------------------------------------------------------------


def test_sub_block_call_with_in_and_out_parameters() -> None:
    class Sub(Control):
        hdr: In[headers]
        out: Out[bit8]

        def apply(self) -> None:
            self.assign(self.out, self.hdr.h.f)

    class Main(Control[headers, metadata]):
        def apply(self) -> None:
            tmp = self.local("tmp", bit8)
            self.call(Sub, self.hdr, tmp)
            self.assign(self.meta.x, tmp)

    program = build(control=Main)
    assert [b.name for b in program.blocks] == ["NoParser", "Sub", "Main", "NoDeparser"]
    assert program.blocks[1] == block(
        f"""name: "Sub" kind: BLOCK_KIND_CONTROL
        params {{ name: "hdr" type {{ struct: "headers" }} direction: DIRECTION_IN }}
        params {{ name: "out" type {{ bits: 8 }} direction: DIRECTION_OUT }}
        body {{ assign {{ target {{ var: "out" }} value {{ {HDR_H_F} }} }} }}"""
    )
    main = program.blocks[2]
    assert main.locals[0] == pb.Var(name="tmp", type=pb.Type(bits=8))
    assert main.body[0] == text_format.Parse(
        'call_block { block: "Sub" args { expr { var: "hdr" } } args { lvalue { var: "tmp" } } }',
        pb.Stmt(),
    )


# -- externs ---------------------------------------------------------------------------


r = Register[bit8]("r", size=4)
pkts = Counter("pkts", size=4)
csum = Checksum16[Bits[L[24]]]("csum")


def test_extern_families_match_the_core_helpers() -> None:
    class C(Control[headers, metadata]):
        def apply(self) -> None:
            pkts.count(self.meta.idx)
            r.read(self.meta.x, self.meta.idx)
            r.write(self.meta.idx, Kind.B)
            data = concat(self.hdr.h.f, self.hdr.h.g)
            self.assign(self.hdr.h.g, csum.compute(data.as_(Bits[L[24]])))

    program = build(control=C, externs=[r, pkts, csum])
    core = CoreProgram("core")
    register(core, core_bit(8))
    counter(core)
    checksum16(core, core_bit(24))
    assert list(program.extern_types) == list(core.build().extern_types)
    assert [(i.name, i.extern_type) for i in program.extern_instances] == [
        ("r", "register"),
        ("pkts", "counter"),
        ("csum", "checksum16"),
    ]
    body = program.blocks[1].body
    assert body[1] == text_format.Parse(
        f"""call_extern {{ instance: "r" method: "read"
          args {{ lvalue {{ {META_X} }} }} args {{ expr {{ {META_IDX} }} }} }}""",
        pb.Stmt(),
    )
    assert body[2].call_extern.args[1].expr.literal.bits == pb.BitsLiteral(width=8, value="2")
    assert body[3].call_extern.method == "compute"
    assert body[3].call_extern.result == text_format.Parse(HDR_H_G, pb.LValue())


def test_extern_results_must_be_assigned_and_instances_listed() -> None:
    class Dropped(Control[headers, metadata]):
        def apply(self) -> None:
            csum.compute(self.hdr.h.f)

    with pytest.raises(EdslError, match="never assigned"):
        build(control=Dropped, externs=[csum])

    class Unlisted(Control[headers, metadata]):
        def apply(self) -> None:
            pkts.count(0)

    with pytest.raises(EdslError, match="not listed in Program"):
        build(control=Unlisted)


# -- program assembly: errors, enums, exports --------------------------------------


class errors(Errors):
    BadKind: Error


class Color(Enum):
    RED: Color
    GREEN: Color


def test_program_assembly() -> None:
    class P(Parser[headers, metadata]):
        @state
        def start(self) -> Transition:
            self.verify(self.hdr.h.f == 1, errors.BadKind)
            color = self.local("color", Color)
            self.assign(color, Color.GREEN)
            return self.reject

    program = build(parser=P, errors=errors)
    assert list(program.errors)[-2:] == ["ParserInvalidArgument", "BadKind"]
    assert program.enum_types[0] == pb.EnumType(name="Color", members=["RED", "GREEN"])
    assert [(e.role, e.block) for e in program.exports] == [
        ("parser", "P"),
        ("control", "NoControl"),
        ("deparser", "NoDeparser"),
    ]
    start = program.blocks[0].states[0]
    assert start.body[0].verify.error == "BadKind"
    assert start.body[1].assign.value.literal.enum_member == pb.EnumLiteral(
        enum_type="Color", member="GREEN"
    )
    assert program.blocks[0].locals[0].type == pb.Type(enum_type="Color")
    assert start.transition.direct.HasField("reject")
    assert build().blocks[0].states[0].body[:] == []  # a second build starts afresh
    with pytest.raises(EdslError, match="not declared by this program"):
        build(parser=P)
    assert CoreErrors.PacketTooShort.name == "PacketTooShort"


# -- provenance --------------------------------------------------------------------


def test_errors_carry_the_users_location() -> None:
    class C(Control[headers, metadata]):
        def apply(self) -> None:
            self.assign(self.meta.x, 256)  # line noted below

    with pytest.raises(EdslError) as e:
        control_of(C)
    line = test_errors_carry_the_users_location.__code__.co_firstlineno + 3
    assert str(e.value).endswith(f"(defined at {__file__}:{line})")
    assert "256 does not fit in bit<8>" in str(e.value)
    with pytest.raises(EdslError, match=rf"is not a p4blo type.*\(defined at {__file__}:\d+\)"):

        class bad(Struct):
            x: int
