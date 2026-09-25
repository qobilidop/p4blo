"""The validator: everything the schema cannot express.

`validate` returns every problem it finds as a `Diagnostic`; `check` raises
`ValidationError` on a non-empty list and otherwise hands back the `ir.Index`
the interpreter and the printer build on. The rules are the contract stated
in the header of spec/ir/proto/p4blo/v0/p4blo.proto, made executable, so this package
is meant to be read as that contract's fine print: one method per
declaration, statement and expression kind.

The modules follow the groups of the code list below. Each holds a class
that builds on the ones it needs, and `_Validator` here joins them; its
`run` checks a program in the order of the schema.


  diagnostics   the codes, `Diagnostic` and `ValidationError`
  base          `Checker`: the state of a run, and `report`
  names         names and references; scopes and where each statement may stand
  types         types, literals and parameters
  typer         expressions and lvalues: the one expression typer, which the
                interpreter, the printer and the STF reader call as `expr_type`
  externs       extern types and instances
  calls         calls, their arguments and aliasing, and the call graph
  statements    statements
  parsers       parser states, transitions and select
  tables        tables, keys and const entries
  blocks        blocks and actions

Every diagnostic carries a protobuf-style path to the offending element, for
example `blocks[1].states[2].transition.select.cases[0].sets[1]`.

Codes
-----
Structure and names
  NAME_EMPTY          a declaration, field, member, method or key has no name
  NAME_DUPLICATE      two names collide in one namespace (Index.build stops here)
  ERROR_LIST          BlockLibrary.errors does not begin with core.p4's errors in order
  REF_UNRESOLVED      a reference names no declaration, field, member, method or error
  REF_KIND            a reference names a declaration of the wrong kind
  SCOPE_VAR           a variable that exists is not visible from here
  SCOPE_DECL          an action, table or state of another block is used here
  EXPORT_DUPLICATE    two exports share a role
  EXPORT_SIGNATURE    an exported block lacks the signature of its kind
Types and literals
  TYPE_INVALID        a malformed Type: no kind, bit<0>, an empty stack or enum,
                      a non-scalar header field, a struct that contains itself
  LITERAL_FORMAT      a literal with no value, or a bits value that is not decimal
  LITERAL_RANGE       a bits literal of width 0 or with a value >= 2^width
Blocks
  BLOCK_KIND_SHAPE    a block without a kind, or with the states, body,
                      start_state, actions or tables of another kind
  PARSER_START_STATE  a parser's start_state is not one of its states
  BLOCK_KIND_STMT     a statement in a block kind that does not allow it
  PARSER_ONLY         lookahead or stack.lastIndex outside a parser
  NEXT_ONLY_EXTRACT   stack.next anywhere but as the target of an extract
  PARAM_DIRECTION     a parameter direction its owner does not allow
Expressions, lvalues and statements
  EXPR_INVALID        an expression or lvalue with no kind, or an unspecified operator
  STMT_INVALID        a statement with no kind
  TYPE_MISMATCH       an operand, condition, target or value of the wrong type
  CAST_INVALID        a cast the IR does not allow
  SLICE_RANGE         a slice with lo > hi or hi >= width
  LVALUE_READONLY     a write to an `in` or directionless parameter
  STACK_COUNT         push or pop with count 0
  ARG_COUNT           a call with the wrong number of arguments
  ARG_DIRECTION       an argument's form (in expr / out lvalue) against its param
  ARG_TYPE            an argument's type against its param
  CALL_KIND           a block calling a block of another kind
  CALL_ALIAS          two arguments of one call that may alias (see check_args)
  CALL_CYCLE          a cycle in the block call graph, or among one block's actions
  EXTERN_RESULT       a result lvalue missing, unexpected or of the wrong type
Parsers
  PARSER_TRANSITION   a state without a transition, or a target without a kind
  SELECT_ARITY        a select without keys, or a case with the wrong set count
  SELECT_TYPE         a select key or key set of the wrong type
Tables and entries
  KEY_NAME            two keys of one table share a name
  KEY_TYPE            a match kind on a type it does not apply to
  TABLE_LPM_COUNT     more than one lpm key
  TABLE_KEY_MIX       lpm and ternary keys in one table
  TABLE_ACTIONS       an empty or repeated action list, or a call to an action not in it
  NOACTION_RESERVED   an action named NoAction with a body or parameters
  ACTION_ARGS         action data against the action's params
  ENTRY_SHAPE         key values that do not line up with the keys
  ENTRY_RANGE         a value, prefix length or mask that does not fit its key
  ENTRY_PRIORITY      a priority on a non-ternary table, or two overlapping
                      const entries of a ternary table with one priority
  ENTRY_DUPLICATE     two const entries of a non-ternary table with the same keys
Externs
  EXTERN_ARGS         constructor arguments against the extern type
"""

from __future__ import annotations

from p4blo import ir
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.blocks import BlockChecks
from p4blo.validator.diagnostics import (
    ACTION_ARGS,
    ARG_COUNT,
    ARG_DIRECTION,
    ARG_TYPE,
    BLOCK_KIND_SHAPE,
    BLOCK_KIND_STMT,
    CALL_ALIAS,
    CALL_CYCLE,
    CALL_KIND,
    CAST_INVALID,
    ENTRY_DUPLICATE,
    ENTRY_PRIORITY,
    ENTRY_RANGE,
    ENTRY_SHAPE,
    ERROR_LIST,
    EXPORT_DUPLICATE,
    EXPORT_SIGNATURE,
    EXPR_INVALID,
    EXTERN_ARGS,
    EXTERN_RESULT,
    KEY_NAME,
    KEY_TYPE,
    LITERAL_FORMAT,
    LITERAL_RANGE,
    LVALUE_READONLY,
    NAME_DUPLICATE,
    NAME_EMPTY,
    NEXT_ONLY_EXTRACT,
    NOACTION_RESERVED,
    PARAM_DIRECTION,
    PARSER_ONLY,
    PARSER_START_STATE,
    PARSER_TRANSITION,
    REF_KIND,
    REF_UNRESOLVED,
    SCOPE_DECL,
    SCOPE_VAR,
    SELECT_ARITY,
    SELECT_TYPE,
    SLICE_RANGE,
    STACK_COUNT,
    STMT_INVALID,
    TABLE_ACTIONS,
    TABLE_KEY_MIX,
    TABLE_LPM_COUNT,
    TYPE_INVALID,
    TYPE_MISMATCH,
    Diagnostic,
    ValidationError,
)
from p4blo.validator.externs import ExternChecks

__all__ = [
    "ACTION_ARGS",
    "ARG_COUNT",
    "ARG_DIRECTION",
    "ARG_TYPE",
    "BLOCK_KIND_SHAPE",
    "BLOCK_KIND_STMT",
    "CALL_ALIAS",
    "CALL_CYCLE",
    "CALL_KIND",
    "CAST_INVALID",
    "ENTRY_DUPLICATE",
    "ENTRY_PRIORITY",
    "ENTRY_RANGE",
    "ENTRY_SHAPE",
    "ERROR_LIST",
    "EXPORT_DUPLICATE",
    "EXPORT_SIGNATURE",
    "EXPR_INVALID",
    "EXTERN_ARGS",
    "EXTERN_RESULT",
    "KEY_NAME",
    "KEY_TYPE",
    "LITERAL_FORMAT",
    "LITERAL_RANGE",
    "LVALUE_READONLY",
    "NAME_DUPLICATE",
    "NAME_EMPTY",
    "NEXT_ONLY_EXTRACT",
    "NOACTION_RESERVED",
    "PARAM_DIRECTION",
    "PARSER_ONLY",
    "PARSER_START_STATE",
    "PARSER_TRANSITION",
    "REF_KIND",
    "REF_UNRESOLVED",
    "SCOPE_DECL",
    "SCOPE_VAR",
    "SELECT_ARITY",
    "SELECT_TYPE",
    "SLICE_RANGE",
    "STACK_COUNT",
    "STMT_INVALID",
    "TABLE_ACTIONS",
    "TABLE_KEY_MIX",
    "TABLE_LPM_COUNT",
    "TYPE_INVALID",
    "TYPE_MISMATCH",
    "Diagnostic",
    "ValidationError",
    "check",
    "validate",
]


def validate(program: pb.BlockLibrary) -> list[Diagnostic]:
    """Every problem found in `program`, in the order of the schema."""
    return _Validator(program).run()


def check(program: pb.BlockLibrary) -> ir.Index:
    """The program's `ir.Index`, or `ValidationError` listing every problem."""
    validator = _Validator(program)
    diagnostics = validator.run()
    if diagnostics or validator.index is None:
        raise ValidationError(diagnostics)
    return validator.index


class _Validator(BlockChecks, ExternChecks):
    """One run over one program: every rule class, in the order `run` calls
    them."""

    def run(self) -> list[Diagnostic]:
        try:
            self.index = ir.Index.build(self.program)
        except ir.DuplicateName as e:
            message = str(e)
            code = NAME_EMPTY if "empty" in message or "''" in message else NAME_DUPLICATE
            self.report(code, message, "")
            return self.diagnostics
        self.check_errors()
        self.check_type_declarations()
        self.check_extern_types()
        self.check_extern_instances()
        for i, block in enumerate(self.program.blocks):
            self.block_paths[block.name] = f"blocks[{i}]"
        for i, block in enumerate(self.program.blocks):
            self.check_block(block, f"blocks[{i}]")
        self.check_call_graph()
        return self.diagnostics
