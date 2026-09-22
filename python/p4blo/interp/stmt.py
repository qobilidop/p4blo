"""Statements, calls, and the parser's state machine.

`execute` has one function per `Stmt` kind. Statements are shared by the
three block kinds where the schema allows (proto, "Where each statement may
appear"), so they live together; the parser's states are here too because a
sub-parser call is a statement that walks states.

Calls follow docs/semantics.md, "Controls": `in` arguments are copied in,
`out` parameters start at zero, `out` and `inout` arguments are copied back
in parameter order. Every entry of a block or action binds by name in a
fresh activation (see `env.py`).
"""

from __future__ import annotations

from collections.abc import Iterable

from p4blo.interp.api import InterpError
from p4blo.interp.env import Env
from p4blo.interp.errors import NO_MATCH, PARSER_TIMEOUT, STACK_OUT_OF_BOUNDS, ParseError
from p4blo.interp.expr import (
    evaluate,
    expect_bits,
    expect_bool,
    expect_header,
    expect_stack,
    header_from_bits,
    header_to_bits,
    literal_value,
    read_lvalue,
    write_lvalue,
    zero_header,
)
from p4blo.interp.packet import Emitter
from p4blo.interp.values import (
    NO_ERROR,
    ErrorValue,
    Header,
    Stack,
    Struct,
    Value,
    copy,
    equal,
    zero,
)
from p4blo.interp.widths import width_of
from p4blo.ir import Index
from p4blo.v0 import p4blo_pb2 as pb


def execute(stmts: Iterable[pb.Stmt], env: Env) -> None:
    for stmt in stmts:
        execute_one(stmt, env)


def execute_one(stmt: pb.Stmt, env: Env) -> None:
    match stmt.WhichOneof("kind"):
        case "assign":
            assign(stmt.assign, env)
        case "conditional":
            conditional(stmt.conditional, env)
        case "apply":
            apply(stmt.apply, env)
        case "call_action":
            call_action(stmt.call_action, env)
        case "call_block":
            call_block(stmt.call_block, env)
        case "call_extern":
            call_extern(stmt.call_extern, env)
        case "set_valid":
            set_validity(stmt.set_valid.header, True, env)
        case "set_invalid":
            set_validity(stmt.set_invalid.header, False, env)
        case "push":
            push_front(expect_stack(read_lvalue(stmt.push.stack, env)), stmt.push.count, env.index)
        case "pop":
            pop_front(expect_stack(read_lvalue(stmt.pop.stack, env)), stmt.pop.count, env.index)
        case "extract":
            extract(stmt.extract, env)
        case "advance":
            advance(stmt.advance, env)
        case "verify":
            verify(stmt.verify, env)
        case "emit":
            emit_value(evaluate(stmt.emit.value, env), env.require_emitter())
        case _:
            raise InterpError("statement has no kind")


# ---------------------------------------------------------------------------
# Statements of every block kind
# ---------------------------------------------------------------------------


def assign(a: pb.Assign, env: Env) -> None:
    """The right-hand side is evaluated before the target is resolved."""
    write_lvalue(a.target, evaluate(a.value, env), env)


def conditional(i: pb.If, env: Env) -> None:
    if expect_bool(evaluate(i.condition, env)):
        execute(i.then, env)
    else:
        execute(i.otherwise, env)


def set_validity(lv: pb.LValue, valid: bool, env: Env) -> None:
    """`setValid` and `setInvalid` touch only the validity bit
    (docs/semantics.md, "Headers")."""
    expect_header(read_lvalue(lv, env)).valid = valid


def push_front(stack: Stack, n: int, index: Index) -> None:
    """Shift elements up by `n`, discarding the last `n`; the first `n`
    become invalid zero headers; `nextIndex` grows by `n` up to the size
    (docs/semantics.md, "Header stacks")."""
    size = len(stack.elements)
    n = min(n, size)
    fresh = [zero_header(stack.header_type, index) for _ in range(n)]
    stack.elements = fresh + stack.elements[: size - n]
    stack.next_index = min(stack.next_index + n, size)


def pop_front(stack: Stack, n: int, index: Index) -> None:
    """Shift elements down by `n`; the last `n` become invalid zero headers;
    `nextIndex` shrinks by `n` down to zero."""
    size = len(stack.elements)
    n = min(n, size)
    fresh = [zero_header(stack.header_type, index) for _ in range(n)]
    stack.elements = stack.elements[n:] + fresh
    stack.next_index = max(stack.next_index - n, 0)


# ---------------------------------------------------------------------------
# Calls: blocks, actions, externs
# ---------------------------------------------------------------------------


def argument_value(param: pb.Param, arg: pb.Arg, env: Env) -> Value:
    """What the callee's parameter starts as: the argument for `in`, `inout`
    and action data, the zero value for `out`."""
    if param.direction == pb.DIRECTION_OUT:
        return zero(param.type, env.index)
    if arg.WhichOneof("kind") == "expr":
        return copy(evaluate(arg.expr, env))
    return copy(read_lvalue(arg.lvalue, env))


def copy_back(params: Iterable[pb.Param], args: Iterable[pb.Arg], values: Env, env: Env) -> None:
    """Write `out` and `inout` parameters back to their arguments, in
    parameter order."""
    for param, arg in zip(params, args, strict=True):
        if param.direction in (pb.DIRECTION_OUT, pb.DIRECTION_INOUT):
            write_lvalue(arg.lvalue, values.read(param.name), env)


def call_block(cb: pb.CallBlock, env: Env) -> None:
    """Run a sub-parser or sub-control. If a sub-parser raises, its
    arguments are copied back first, so the outcome shows what it had
    already written (docs/semantics.md, "Parsers")."""
    block = env.index.blocks[cb.block]
    if len(cb.args) != len(block.params):
        raise InterpError(f"block {block.name!r} takes {len(block.params)} arguments")
    callee = env.enter_block(block)
    for param, arg in zip(block.params, cb.args, strict=True):
        callee.vars[param.name] = argument_value(param, arg, env)
    try:
        run_block(block, callee)
    finally:
        copy_back(block.params, cb.args, callee, env)


def run_block(block: pb.Block, env: Env) -> None:
    """A parser walks its states; a control or deparser runs its body."""
    if block.kind == pb.BLOCK_KIND_PARSER:
        run_states(block, env)
    else:
        execute(block.body, env)


def call_action(ca: pb.CallAction, env: Env) -> None:
    """A direct action call from a control body, with directional
    arguments passed like a block call's."""
    action = env.scope.actions[ca.action]
    if len(ca.args) != len(action.params):
        raise InterpError(f"action {action.name!r} takes {len(action.params)} arguments")
    params = {
        param.name: argument_value(param, arg, env)
        for param, arg in zip(action.params, ca.args, strict=True)
    }
    inner = env.enter_action(action.name, params)
    execute(action.body, inner)
    copy_back(action.params, ca.args, inner, env)


def run_action_call(call: pb.ActionCall, env: Env) -> None:
    """Run an action chosen by a table, with its action data bound to the
    directionless parameters by value."""
    action = env.scope.actions[call.action]
    if len(call.args) != len(action.params):
        raise InterpError(f"action {action.name!r} takes {len(action.params)} arguments")
    params = {
        param.name: literal_value(arg) for param, arg in zip(action.params, call.args, strict=True)
    }
    execute(action.body, env.enter_action(action.name, params))


def call_extern(ce: pb.CallExtern, env: Env) -> None:
    """Call a method on an extern instance through its binding, then copy
    the `out` and `inout` results and the return value back."""
    instance = env.index.extern_instances[ce.instance]
    extern_type = env.index.extern_types[instance.extern_type]
    method = next((m for m in extern_type.methods if m.name == ce.method), None)
    if method is None:
        raise InterpError(f"extern {extern_type.name!r} has no method {ce.method!r}")
    if len(ce.args) != len(method.params):
        raise InterpError(f"method {ce.method!r} takes {len(method.params)} arguments")
    if instance.name not in env.externs:
        raise InterpError(f"extern instance {instance.name!r} is not bound")
    args = [
        argument_value(param, arg, env) for param, arg in zip(method.params, ce.args, strict=True)
    ]
    result = env.externs[instance.name].call(ce.method, args)
    written = [
        arg
        for param, arg in zip(method.params, ce.args, strict=True)
        if param.direction in (pb.DIRECTION_OUT, pb.DIRECTION_INOUT)
    ]
    if len(result.outs) != len(written):
        raise InterpError(f"method {ce.method!r} produced {len(result.outs)} out values")
    for arg, value in zip(written, result.outs, strict=True):
        write_lvalue(arg.lvalue, value, env)
    if ce.HasField("result"):
        if result.returns is None:
            raise InterpError(f"method {ce.method!r} returned nothing")
        write_lvalue(ce.result, result.returns, env)


# ---------------------------------------------------------------------------
# Control statements
# ---------------------------------------------------------------------------


def apply(ap: pb.Apply, env: Env) -> None:
    """Evaluate the keys once, look them up, run the chosen action, then
    record `hit` (docs/semantics.md, "Tables")."""
    table = env.scope.tables[ap.table]
    keys = [expect_bits(evaluate(k.expr, env)) for k in table.keys]
    match = env.require_entries().lookup((env.block.name, table.name), keys)
    if match.action is not None:
        run_action_call(match.action, env)
    if ap.HasField("hit"):
        write_lvalue(ap.hit, match.hit, env)


# ---------------------------------------------------------------------------
# Parser statements
# ---------------------------------------------------------------------------


def extract(ex: pb.Extract, env: Env) -> None:
    """Fill the target header from the packet and make it valid.

    The target is resolved first, so a full stack raises `StackOutOfBounds`
    before the packet is looked at; a short packet raises `PacketTooShort`
    and consumes nothing (docs/semantics.md, "Parsers"). `hs.next`, the
    one place the validator allows it, fills `hs[nextIndex]` and then
    increments `nextIndex` ("Header stacks").
    """
    packet = env.require_packet()
    if ex.target.WhichOneof("kind") == "next":
        stack = expect_stack(read_lvalue(ex.target.next.stack, env))
        if stack.next_index >= len(stack.elements):
            raise ParseError(STACK_OUT_OF_BOUNDS)
        raw = packet.read(width_of(pb.Type(header=stack.header_type), env.index))
        stack.elements[stack.next_index] = header_from_bits(stack.header_type, raw, env.index)
        stack.next_index += 1
        return
    type_name = expect_header(read_lvalue(ex.target, env)).type_name
    raw = packet.read(width_of(pb.Type(header=type_name), env.index))
    write_lvalue(ex.target, header_from_bits(type_name, raw, env.index), env)


def advance(ad: pb.Advance, env: Env) -> None:
    env.require_packet().advance(expect_bits(evaluate(ad.bits, env)).value)


def verify(v: pb.Verify, env: Env) -> None:
    if not expect_bool(evaluate(v.condition, env)):
        raise ParseError(ErrorValue(v.error))


# ---------------------------------------------------------------------------
# Deparser statements
# ---------------------------------------------------------------------------


def emit_value(value: Value, emitter: Emitter) -> None:
    """Emit a header if valid, a struct's fields in order, or a stack's
    elements from 0 to S - 1 (docs/semantics.md, "Deparsers")."""
    match value:
        case Header():
            if value.valid:
                emitter.write(*header_to_bits(value))
        case Struct():
            for f in value.fields:
                emit_value(f, emitter)
        case Stack():
            for e in value.elements:
                emit_value(e, emitter)
        case _:
            raise InterpError(f"cannot emit a {type(value).__name__}")


# ---------------------------------------------------------------------------
# Parser states
# ---------------------------------------------------------------------------


def run_states(block: pb.Block, env: Env) -> None:
    """Walk the states from `start_state` until `accept` returns or
    `reject` raises."""
    state = env.scope.states[block.start_state]
    while True:
        enter_state(state, env)
        execute(state.body, env)
        target = transition(state.transition, env)
        match target.WhichOneof("kind"):
            case "state":
                state = env.scope.states[target.state]
            case "accept":
                return
            case "reject":
                raise ParseError(NO_ERROR)
            case _:
                raise InterpError(f"state {state.name!r} has no transition target")


def enter_state(state: pb.State, env: Env) -> None:
    """The no-consumption revisit rule: entering a state again with the
    cursor where it was at the last entry raises `ParserTimeout`
    (docs/semantics.md, "Parser loop bound")."""
    key = (env.block.name, state.name)
    cursor = env.require_packet().cursor
    if env.visits.get(key) == cursor:
        raise ParseError(PARSER_TIMEOUT)
    env.visits[key] = cursor


def transition(t: pb.Transition, env: Env) -> pb.Target:
    match t.WhichOneof("kind"):
        case "direct":
            return t.direct
        case "select":
            return select(t.select, env)
        case _:
            raise InterpError("transition has no kind")


def select(s: pb.Select, env: Env) -> pb.Target:
    """Evaluate the keys once; the first case whose every set matches wins;
    none raises `NoMatch` (docs/semantics.md, "select")."""
    keys = [evaluate(k, env) for k in s.keys]
    for case in s.cases:
        if all(key_set_matches(ks, k) for ks, k in zip(case.sets, keys, strict=True)):
            return case.target
    raise ParseError(NO_MATCH)


def key_set_matches(ks: pb.KeySet, key: Value) -> bool:
    match ks.WhichOneof("kind"):
        case "exact":
            return equal(key, literal_value(ks.exact))
        case "masked":
            k = expect_bits(key)
            value = expect_bits(literal_value(ks.masked.value))
            mask = expect_bits(literal_value(ks.masked.mask))
            return (k.value & mask.value) == (value.value & mask.value)
        case "range":
            k = expect_bits(key)
            lo = expect_bits(literal_value(ks.range.lo))
            hi = expect_bits(literal_value(ks.range.hi))
            return lo.value <= k.value <= hi.value
        case "dont_care":
            return True
        case _:
            raise InterpError("key set has no kind")
