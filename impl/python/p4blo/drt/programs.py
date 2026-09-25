"""Small typed IR contexts that make component results packet-observable,
and the typed scalar expressions placed in them.

These are generated programs, not new language semantics or an alternate
evaluator. The ordinary validator, architectures and interpreters execute
each context. Hypothesis strategies live in tests, not the runtime package:
`scalar_expression` makes its decisions through a `Chooser`
(`p4blo.drt.choice`), so the Hypothesis strategy of
tests/drt/test_drt_programs.py and the seeded sampler of
tests/oracle/generated.py are one generator with two sources of choices.
"""

from __future__ import annotations

from dataclasses import dataclass

from p4blo import ir
from p4blo.drt.choice import Chooser
from p4blo.v0 import p4blo_pb2 as pb

WIDTHS = (1, 7, 8, 9, 16, 31, 32, 64, 65, 127)
ARITHMETIC = (
    pb.BINARY_OP_ADD,
    pb.BINARY_OP_SUB,
    pb.BINARY_OP_MUL,
    pb.BINARY_OP_ADD_SAT,
    pb.BINARY_OP_SUB_SAT,
    pb.BINARY_OP_BIT_AND,
    pb.BINARY_OP_BIT_OR,
    pb.BINARY_OP_BIT_XOR,
)
COMPARISONS = (
    pb.BINARY_OP_EQ,
    pb.BINARY_OP_NE,
    pb.BINARY_OP_LT,
    pb.BINARY_OP_LE,
    pb.BINARY_OP_GT,
    pb.BINARY_OP_GE,
)
LOGICAL = (pb.BINARY_OP_AND, pb.BINARY_OP_OR)

_SCALAR_CONTEXT = """
name: "scalar"
errors: "NoError"
errors: "PacketTooShort"
errors: "NoMatch"
errors: "StackOutOfBounds"
errors: "HeaderTooShort"
errors: "ParserTimeout"
errors: "ParserInvalidArgument"
header_types { name: "Result" fields { name: "value" type { bits: 1 } } }
struct_types { name: "H" fields { name: "result" type { header: "Result" } } }
struct_types { name: "M" }
headers: "H"
metadata: "M"
blocks {
  name: "P" kind: BLOCK_KIND_PARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_OUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  states { name: "start" transition { direct { accept {} } } }
  start_state: "start"
}
blocks {
  name: "C" kind: BLOCK_KIND_CONTROL
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_INOUT }
  params { name: "meta" type { struct: "M" } direction: DIRECTION_INOUT }
  body { set_valid { header { member { base { var: "hdr" } field: "result" } } } }
  body { assign {
    target { member {
      base { member { base { var: "hdr" } field: "result" } }
      field: "value"
    } }
  } }
}
blocks {
  name: "D" kind: BLOCK_KIND_DEPARSER
  params { name: "hdr" type { struct: "H" } direction: DIRECTION_IN }
  body { emit { value { member { base { var: "hdr" } field: "result" } } } }
}
exports { role: "parser" block: "P" }
exports { role: "control" block: "C" }
exports { role: "deparser" block: "D" }
"""


def bits(width: int, value: int) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=width, value=str(value))))


def boolean(value: bool) -> pb.Expr:
    return pb.Expr(literal=pb.Literal(boolean=value))


def binary(op: pb.BinaryOp, left: pb.Expr, right: pb.Expr) -> pb.Expr:
    return pb.Expr(binary=pb.Binary(op=op, left=left, right=right))


def scalar_program(expression: pb.Expr, width: int | None) -> pb.Program:
    """Emit a bits result of `width`, or a bool (`None`) cast to bit<1>.

    The parser consumes nothing, so byte-padding of the output does not
    trigger the architecture's byte-aligned-input requirement. An empty
    input packet exposes precisely the expression result, MSB first.
    """
    program = ir.load_text(_SCALAR_CONTEXT)
    program.header_types[0].fields[0].type.bits = width if width is not None else 1
    value = (
        expression
        if width is not None
        else pb.Expr(cast=pb.Cast(to=pb.Type(bits=1), operand=expression))
    )
    program.blocks[1].body[1].assign.value.CopyFrom(value)
    return program


def parser_condition_program(condition: pb.Expr, expected_error: str) -> pb.Program:
    """Expose a parser condition's error outcome as a single emitted bit.

    This makes skipped packet reads observable: unlike closed pure scalar
    expressions, a lookahead on empty input can fault if evaluated eagerly.
    """
    parser_error = pb.Expr(member=pb.Member(base=pb.Expr(var="meta"), field="parser_error"))
    expected = pb.Expr(literal=pb.Literal(error=expected_error))
    program = scalar_program(binary(pb.BINARY_OP_EQ, parser_error, expected), None)
    program.name = "parser-condition"
    program.struct_types[1].fields.add(name="parser_error", type=pb.Type(error=pb.ErrorType()))
    program.blocks[0].states[0].body.add(verify=pb.Verify(condition=condition, error="NoMatch"))
    return program


# ---------------------------------------------------------------------------
# Typed scalar expressions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Leaves:
    """What an expression's leaves may be besides literals.

    `packet`: the parsed input of `packet_scalar_program`: its fields,
    control locals copied from them, a stack element at a packet-derived
    index, and validity. `lookahead`: packet reads, which only a parser may
    evaluate. `shift_widths`: the widths a shift amount is drawn at; P4-SpecTec
    refuses amounts above 2048, so its sampler keeps them at most 9 bits
    wide.
    """

    packet: bool = False
    lookahead: bool = False
    shift_widths: tuple[int, ...] = WIDTHS


def _width(ch: Chooser, point: str, widths: tuple[int, ...]) -> int:
    return int(ch.choice(point, [str(w) for w in widths]))


def _op(ch: Chooser, point: str, ops: tuple[pb.BinaryOp, ...]) -> pb.BinaryOp:
    """An operator, labelled by its name so that a feature reads as one."""
    by_name = {pb.BinaryOp.Name(op): op for op in ops}
    return by_name[ch.choice(point, list(by_name))]


CLOSED = Leaves()


def scalar_expression(
    ch: Chooser, width: int | None, depth: int = 3, leaves: Leaves = CLOSED
) -> pb.Expr:
    """A `bit<width>` expression, or a `bool` one when `width` is None.

    Every decision keeps the requested type, including nested operands, so
    shrinking a decision never makes an ill-typed program.
    """
    kinds = ["leaf"] if depth == 0 else ["leaf", "unary", "binary", "cast", "mux"]
    if width is not None and depth:
        kinds += ["slice", "shift"]
        if width > 1:
            kinds.append("concat")
    kind = ch.choice("scalar.kind", kinds)
    if kind == "leaf":
        return scalar_leaf(ch, width, leaves)
    if kind == "unary":
        if width is None:
            op = pb.UNARY_OP_NOT
        elif ch.choice("scalar.unary", ("complement", "negate")) == "complement":
            op = pb.UNARY_OP_COMPLEMENT
        else:
            op = pb.UNARY_OP_NEGATE
        operand = scalar_expression(ch, width, depth - 1, leaves)
        return pb.Expr(unary=pb.Unary(op=op, operand=operand))
    if kind == "binary":
        if width is None:
            op = _op(ch, "scalar.binary.bool", (*COMPARISONS, *LOGICAL))
            operand = None if op in LOGICAL else _width(ch, "scalar.operand", WIDTHS)
        else:
            op, operand = _op(ch, "scalar.binary.bits", ARITHMETIC), width
        return binary(
            op,
            scalar_expression(ch, operand, depth - 1, leaves),
            scalar_expression(ch, operand, depth - 1, leaves),
        )
    if kind == "cast":
        source = 1 if width is None else _width(ch, "scalar.cast", WIDTHS)
        target = pb.Type(boolean=pb.BoolType()) if width is None else pb.Type(bits=width)
        operand = scalar_expression(ch, source, depth - 1, leaves)
        return pb.Expr(cast=pb.Cast(to=target, operand=operand))
    if kind == "mux":
        return pb.Expr(
            mux=pb.Mux(
                **{
                    "condition": scalar_expression(ch, None, depth - 1, leaves),
                    "then": scalar_expression(ch, width, depth - 1, leaves),
                    "otherwise": scalar_expression(ch, width, depth - 1, leaves),
                }
            )
        )
    assert width is not None
    if kind == "slice":
        lo = ch.integer("scalar.slice", 0, 16)
        extra = ch.integer("scalar.slice", 0, 16)
        operand = scalar_expression(ch, width + lo + extra, depth - 1, leaves)
        return pb.Expr(slice=pb.Slice(operand=operand, hi=lo + width - 1, lo=lo))
    if kind == "shift":
        op = _op(ch, "scalar.shift", (pb.BINARY_OP_SHL, pb.BINARY_OP_SHR))
        amount = _width(ch, "scalar.shift.width", leaves.shift_widths)
        return binary(
            op,
            scalar_expression(ch, width, depth - 1, leaves),
            scalar_expression(ch, amount, depth - 1, leaves),
        )
    left = ch.integer("scalar.concat", 1, width - 1)
    return binary(
        pb.BINARY_OP_CONCAT,
        scalar_expression(ch, left, depth - 1, leaves),
        scalar_expression(ch, width - left, depth - 1, leaves),
    )


def scalar_leaf(ch: Chooser, width: int | None, leaves: Leaves) -> pb.Expr:
    kinds = ["literal"]
    if leaves.packet:
        if width is None:
            kinds += ["field", "valid"]
        elif width in WIDTHS:
            kinds += ["field", "variable"]
        if width == 8:
            kinds.append("index")
    if leaves.lookahead:
        kinds.append("lookahead")
    match ch.choice("scalar.leaf", kinds):
        case "literal":
            if width is None:
                return boolean(ch.chance("scalar.bool"))
            maximum = (1 << width) - 1
            if ch.choice("scalar.literal", ("edge", "any")) == "edge":
                edges = sorted({0, 1, maximum, maximum - 1, min(width, maximum)})
                return bits(width, edges[ch.integer("scalar.edge", 0, len(edges) - 1)])
            return bits(width, ch.integer("scalar.literal", 0, maximum))
        case "field":
            if width is None:
                return pb.Expr(cast=pb.Cast(to=pb.Type(boolean=pb.BoolType()), operand=_input(1)))
            return _input(width)
        case "variable":
            return pb.Expr(var=f"l{width}")
        case "index":
            # The index is the packet's one-bit field: always in range.
            index = pb.Expr(cast=pb.Cast(to=pb.Type(bits=32), operand=_input(1)))
            element = pb.Expr(index=pb.Index(base=_hdr("st"), index=index))
            return pb.Expr(member=pb.Member(base=element, field="v"))
        case "valid":
            header = _hdr("inp")
            if ch.choice("scalar.valid", ("input", "element")) == "element":
                header = pb.Expr(index=pb.Index(base=_hdr("st"), index=bits(32, 1)))
            return pb.Expr(is_valid=pb.IsValid(header=header))
        case _:
            # A bool read is a cast of one bit, as the DRT's trap is.
            read = pb.Expr(lookahead=pb.Lookahead(type=pb.Type(bits=width or 1)))
            if width is None:
                return pb.Expr(cast=pb.Cast(to=pb.Type(boolean=pb.BoolType()), operand=read))
            return read


def _hdr(name: str) -> pb.Expr:
    return pb.Expr(member=pb.Member(base=pb.Expr(var="hdr"), field=name))


def _input(width: int) -> pb.Expr:
    return pb.Expr(member=pb.Member(base=_hdr("inp"), field=f"w{width}"))


def has_lookahead(expr: pb.Expr) -> bool:
    """Whether a packet read occurs anywhere in `expr`."""
    if expr.WhichOneof("kind") == "lookahead":
        return True
    return any(
        isinstance(value, pb.Expr) and has_lookahead(value)
        for message in [getattr(expr, expr.WhichOneof("kind") or "literal")]
        for _, value in message.ListFields()
    )


def packet_scalar_program(expression: pb.Expr, width: int | None) -> pb.Program:
    """`scalar_program` whose expression may read a parsed input.

    The parser extracts `hdr.inp`, a header with one field `w<W>` per width
    of `WIDTHS` (45 bytes), and the two-element stack `hdr.st` of one-byte
    headers; the control copies every field into a local `l<W>` before it
    computes the result. Only `hdr.result` is emitted, so the output is the
    result followed by what the parser did not consume, and a short packet
    leaves the input invalid, with every field zero.
    """
    program = scalar_program(expression, width)
    program.name = "packet-scalar"
    program.header_types.add(
        name="In", fields=[pb.Field(name=f"w{w}", type=pb.Type(bits=w)) for w in WIDTHS]
    )
    program.header_types.add(name="B8", fields=[pb.Field(name="v", type=pb.Type(bits=8))])
    headers = program.struct_types[0]
    headers.fields.add(name="inp", type=pb.Type(header="In"))
    headers.fields.add(name="st", type=pb.Type(stack=pb.StackType(header="B8", size=2)))
    element = pb.LValue(next=pb.Next(stack=_lvalue("st")))
    for target in (_lvalue("inp"), element, element):
        program.blocks[0].states[0].body.add(extract=pb.Extract(target=target))
    control = program.blocks[1]
    copies = []
    for w in WIDTHS:
        control.locals.add(name=f"l{w}", type=pb.Type(bits=w))
        copies.append(pb.Stmt(assign=pb.Assign(target=pb.LValue(var=f"l{w}"), value=_input(w))))
    result = control.body.pop()
    control.body.extend([*copies, result])
    return program


def _lvalue(name: str) -> pb.LValue:
    return pb.LValue(member=pb.LMember(base=pb.LValue(var="hdr"), field=name))
