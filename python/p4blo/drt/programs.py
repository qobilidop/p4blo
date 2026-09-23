"""Small typed IR contexts that make component results packet-observable.

These are generated programs, not new language semantics or an alternate
evaluator. The ordinary validator, architectures and interpreters execute
each context. Hypothesis strategies live in tests, not the runtime package.
"""

from __future__ import annotations

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb

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
