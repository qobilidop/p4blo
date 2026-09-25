from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Direction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DIRECTION_UNSPECIFIED: _ClassVar[Direction]
    DIRECTION_NONE: _ClassVar[Direction]
    DIRECTION_IN: _ClassVar[Direction]
    DIRECTION_OUT: _ClassVar[Direction]
    DIRECTION_INOUT: _ClassVar[Direction]

class BlockKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BLOCK_KIND_UNSPECIFIED: _ClassVar[BlockKind]
    BLOCK_KIND_PARSER: _ClassVar[BlockKind]
    BLOCK_KIND_CONTROL: _ClassVar[BlockKind]
    BLOCK_KIND_DEPARSER: _ClassVar[BlockKind]

class MatchKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MATCH_KIND_UNSPECIFIED: _ClassVar[MatchKind]
    MATCH_KIND_EXACT: _ClassVar[MatchKind]
    MATCH_KIND_LPM: _ClassVar[MatchKind]
    MATCH_KIND_TERNARY: _ClassVar[MatchKind]

class UnaryOp(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNARY_OP_UNSPECIFIED: _ClassVar[UnaryOp]
    UNARY_OP_NOT: _ClassVar[UnaryOp]
    UNARY_OP_COMPLEMENT: _ClassVar[UnaryOp]
    UNARY_OP_NEGATE: _ClassVar[UnaryOp]

class BinaryOp(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BINARY_OP_UNSPECIFIED: _ClassVar[BinaryOp]
    BINARY_OP_ADD: _ClassVar[BinaryOp]
    BINARY_OP_SUB: _ClassVar[BinaryOp]
    BINARY_OP_MUL: _ClassVar[BinaryOp]
    BINARY_OP_ADD_SAT: _ClassVar[BinaryOp]
    BINARY_OP_SUB_SAT: _ClassVar[BinaryOp]
    BINARY_OP_BIT_AND: _ClassVar[BinaryOp]
    BINARY_OP_BIT_OR: _ClassVar[BinaryOp]
    BINARY_OP_BIT_XOR: _ClassVar[BinaryOp]
    BINARY_OP_SHL: _ClassVar[BinaryOp]
    BINARY_OP_SHR: _ClassVar[BinaryOp]
    BINARY_OP_CONCAT: _ClassVar[BinaryOp]
    BINARY_OP_EQ: _ClassVar[BinaryOp]
    BINARY_OP_NE: _ClassVar[BinaryOp]
    BINARY_OP_LT: _ClassVar[BinaryOp]
    BINARY_OP_LE: _ClassVar[BinaryOp]
    BINARY_OP_GT: _ClassVar[BinaryOp]
    BINARY_OP_GE: _ClassVar[BinaryOp]
    BINARY_OP_AND: _ClassVar[BinaryOp]
    BINARY_OP_OR: _ClassVar[BinaryOp]
DIRECTION_UNSPECIFIED: Direction
DIRECTION_NONE: Direction
DIRECTION_IN: Direction
DIRECTION_OUT: Direction
DIRECTION_INOUT: Direction
BLOCK_KIND_UNSPECIFIED: BlockKind
BLOCK_KIND_PARSER: BlockKind
BLOCK_KIND_CONTROL: BlockKind
BLOCK_KIND_DEPARSER: BlockKind
MATCH_KIND_UNSPECIFIED: MatchKind
MATCH_KIND_EXACT: MatchKind
MATCH_KIND_LPM: MatchKind
MATCH_KIND_TERNARY: MatchKind
UNARY_OP_UNSPECIFIED: UnaryOp
UNARY_OP_NOT: UnaryOp
UNARY_OP_COMPLEMENT: UnaryOp
UNARY_OP_NEGATE: UnaryOp
BINARY_OP_UNSPECIFIED: BinaryOp
BINARY_OP_ADD: BinaryOp
BINARY_OP_SUB: BinaryOp
BINARY_OP_MUL: BinaryOp
BINARY_OP_ADD_SAT: BinaryOp
BINARY_OP_SUB_SAT: BinaryOp
BINARY_OP_BIT_AND: BinaryOp
BINARY_OP_BIT_OR: BinaryOp
BINARY_OP_BIT_XOR: BinaryOp
BINARY_OP_SHL: BinaryOp
BINARY_OP_SHR: BinaryOp
BINARY_OP_CONCAT: BinaryOp
BINARY_OP_EQ: BinaryOp
BINARY_OP_NE: BinaryOp
BINARY_OP_LT: BinaryOp
BINARY_OP_LE: BinaryOp
BINARY_OP_GT: BinaryOp
BINARY_OP_GE: BinaryOp
BINARY_OP_AND: BinaryOp
BINARY_OP_OR: BinaryOp

class BlockLibrary(_message.Message):
    __slots__ = ("name", "errors", "header_types", "struct_types", "enum_types", "extern_types", "extern_instances", "blocks")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    HEADER_TYPES_FIELD_NUMBER: _ClassVar[int]
    STRUCT_TYPES_FIELD_NUMBER: _ClassVar[int]
    ENUM_TYPES_FIELD_NUMBER: _ClassVar[int]
    EXTERN_TYPES_FIELD_NUMBER: _ClassVar[int]
    EXTERN_INSTANCES_FIELD_NUMBER: _ClassVar[int]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    name: str
    errors: _containers.RepeatedScalarFieldContainer[str]
    header_types: _containers.RepeatedCompositeFieldContainer[HeaderType]
    struct_types: _containers.RepeatedCompositeFieldContainer[StructType]
    enum_types: _containers.RepeatedCompositeFieldContainer[EnumType]
    extern_types: _containers.RepeatedCompositeFieldContainer[ExternType]
    extern_instances: _containers.RepeatedCompositeFieldContainer[ExternInstance]
    blocks: _containers.RepeatedCompositeFieldContainer[Block]
    def __init__(self, name: _Optional[str] = ..., errors: _Optional[_Iterable[str]] = ..., header_types: _Optional[_Iterable[_Union[HeaderType, _Mapping]]] = ..., struct_types: _Optional[_Iterable[_Union[StructType, _Mapping]]] = ..., enum_types: _Optional[_Iterable[_Union[EnumType, _Mapping]]] = ..., extern_types: _Optional[_Iterable[_Union[ExternType, _Mapping]]] = ..., extern_instances: _Optional[_Iterable[_Union[ExternInstance, _Mapping]]] = ..., blocks: _Optional[_Iterable[_Union[Block, _Mapping]]] = ...) -> None: ...

class Type(_message.Message):
    __slots__ = ("bits", "boolean", "header", "struct", "enum_type", "error", "stack")
    BITS_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    STRUCT_FIELD_NUMBER: _ClassVar[int]
    ENUM_TYPE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    STACK_FIELD_NUMBER: _ClassVar[int]
    bits: int
    boolean: BoolType
    header: str
    struct: str
    enum_type: str
    error: ErrorType
    stack: StackType
    def __init__(self, bits: _Optional[int] = ..., boolean: _Optional[_Union[BoolType, _Mapping]] = ..., header: _Optional[str] = ..., struct: _Optional[str] = ..., enum_type: _Optional[str] = ..., error: _Optional[_Union[ErrorType, _Mapping]] = ..., stack: _Optional[_Union[StackType, _Mapping]] = ...) -> None: ...

class BoolType(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ErrorType(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class StackType(_message.Message):
    __slots__ = ("header", "size")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    header: str
    size: int
    def __init__(self, header: _Optional[str] = ..., size: _Optional[int] = ...) -> None: ...

class Field(_message.Message):
    __slots__ = ("name", "type")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: Type
    def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[Type, _Mapping]] = ...) -> None: ...

class HeaderType(_message.Message):
    __slots__ = ("name", "fields")
    NAME_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    name: str
    fields: _containers.RepeatedCompositeFieldContainer[Field]
    def __init__(self, name: _Optional[str] = ..., fields: _Optional[_Iterable[_Union[Field, _Mapping]]] = ...) -> None: ...

class StructType(_message.Message):
    __slots__ = ("name", "fields")
    NAME_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    name: str
    fields: _containers.RepeatedCompositeFieldContainer[Field]
    def __init__(self, name: _Optional[str] = ..., fields: _Optional[_Iterable[_Union[Field, _Mapping]]] = ...) -> None: ...

class EnumType(_message.Message):
    __slots__ = ("name", "members")
    NAME_FIELD_NUMBER: _ClassVar[int]
    MEMBERS_FIELD_NUMBER: _ClassVar[int]
    name: str
    members: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, name: _Optional[str] = ..., members: _Optional[_Iterable[str]] = ...) -> None: ...

class Literal(_message.Message):
    __slots__ = ("bits", "boolean", "enum_member", "error")
    BITS_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_FIELD_NUMBER: _ClassVar[int]
    ENUM_MEMBER_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    bits: BitsLiteral
    boolean: bool
    enum_member: EnumLiteral
    error: str
    def __init__(self, bits: _Optional[_Union[BitsLiteral, _Mapping]] = ..., boolean: _Optional[bool] = ..., enum_member: _Optional[_Union[EnumLiteral, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class BitsLiteral(_message.Message):
    __slots__ = ("width", "value")
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    width: int
    value: str
    def __init__(self, width: _Optional[int] = ..., value: _Optional[str] = ...) -> None: ...

class EnumLiteral(_message.Message):
    __slots__ = ("enum_type", "member")
    ENUM_TYPE_FIELD_NUMBER: _ClassVar[int]
    MEMBER_FIELD_NUMBER: _ClassVar[int]
    enum_type: str
    member: str
    def __init__(self, enum_type: _Optional[str] = ..., member: _Optional[str] = ...) -> None: ...

class Var(_message.Message):
    __slots__ = ("name", "type")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: Type
    def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[Type, _Mapping]] = ...) -> None: ...

class Param(_message.Message):
    __slots__ = ("name", "type", "direction")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: Type
    direction: Direction
    def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[Type, _Mapping]] = ..., direction: _Optional[_Union[Direction, str]] = ...) -> None: ...

class ExternType(_message.Message):
    __slots__ = ("name", "constructor_params", "methods")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTOR_PARAMS_FIELD_NUMBER: _ClassVar[int]
    METHODS_FIELD_NUMBER: _ClassVar[int]
    name: str
    constructor_params: _containers.RepeatedCompositeFieldContainer[Param]
    methods: _containers.RepeatedCompositeFieldContainer[Method]
    def __init__(self, name: _Optional[str] = ..., constructor_params: _Optional[_Iterable[_Union[Param, _Mapping]]] = ..., methods: _Optional[_Iterable[_Union[Method, _Mapping]]] = ...) -> None: ...

class Method(_message.Message):
    __slots__ = ("name", "params", "returns")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    RETURNS_FIELD_NUMBER: _ClassVar[int]
    name: str
    params: _containers.RepeatedCompositeFieldContainer[Param]
    returns: Type
    def __init__(self, name: _Optional[str] = ..., params: _Optional[_Iterable[_Union[Param, _Mapping]]] = ..., returns: _Optional[_Union[Type, _Mapping]] = ...) -> None: ...

class ExternInstance(_message.Message):
    __slots__ = ("name", "extern_type", "args")
    NAME_FIELD_NUMBER: _ClassVar[int]
    EXTERN_TYPE_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    extern_type: str
    args: _containers.RepeatedCompositeFieldContainer[Literal]
    def __init__(self, name: _Optional[str] = ..., extern_type: _Optional[str] = ..., args: _Optional[_Iterable[_Union[Literal, _Mapping]]] = ...) -> None: ...

class Block(_message.Message):
    __slots__ = ("name", "kind", "params", "locals", "actions", "tables", "states", "start_state", "body")
    NAME_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    LOCALS_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    TABLES_FIELD_NUMBER: _ClassVar[int]
    STATES_FIELD_NUMBER: _ClassVar[int]
    START_STATE_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    name: str
    kind: BlockKind
    params: _containers.RepeatedCompositeFieldContainer[Param]
    locals: _containers.RepeatedCompositeFieldContainer[Var]
    actions: _containers.RepeatedCompositeFieldContainer[Action]
    tables: _containers.RepeatedCompositeFieldContainer[Table]
    states: _containers.RepeatedCompositeFieldContainer[State]
    start_state: str
    body: _containers.RepeatedCompositeFieldContainer[Stmt]
    def __init__(self, name: _Optional[str] = ..., kind: _Optional[_Union[BlockKind, str]] = ..., params: _Optional[_Iterable[_Union[Param, _Mapping]]] = ..., locals: _Optional[_Iterable[_Union[Var, _Mapping]]] = ..., actions: _Optional[_Iterable[_Union[Action, _Mapping]]] = ..., tables: _Optional[_Iterable[_Union[Table, _Mapping]]] = ..., states: _Optional[_Iterable[_Union[State, _Mapping]]] = ..., start_state: _Optional[str] = ..., body: _Optional[_Iterable[_Union[Stmt, _Mapping]]] = ...) -> None: ...

class Action(_message.Message):
    __slots__ = ("name", "params", "body")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    name: str
    params: _containers.RepeatedCompositeFieldContainer[Param]
    body: _containers.RepeatedCompositeFieldContainer[Stmt]
    def __init__(self, name: _Optional[str] = ..., params: _Optional[_Iterable[_Union[Param, _Mapping]]] = ..., body: _Optional[_Iterable[_Union[Stmt, _Mapping]]] = ...) -> None: ...

class Key(_message.Message):
    __slots__ = ("expr", "match_kind", "name")
    EXPR_FIELD_NUMBER: _ClassVar[int]
    MATCH_KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    expr: Expr
    match_kind: MatchKind
    name: str
    def __init__(self, expr: _Optional[_Union[Expr, _Mapping]] = ..., match_kind: _Optional[_Union[MatchKind, str]] = ..., name: _Optional[str] = ...) -> None: ...

class Table(_message.Message):
    __slots__ = ("name", "keys", "actions", "default_action", "const_default_action", "const_entries", "size")
    NAME_FIELD_NUMBER: _ClassVar[int]
    KEYS_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ACTION_FIELD_NUMBER: _ClassVar[int]
    CONST_DEFAULT_ACTION_FIELD_NUMBER: _ClassVar[int]
    CONST_ENTRIES_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    name: str
    keys: _containers.RepeatedCompositeFieldContainer[Key]
    actions: _containers.RepeatedScalarFieldContainer[str]
    default_action: ActionCall
    const_default_action: bool
    const_entries: _containers.RepeatedCompositeFieldContainer[Entry]
    size: int
    def __init__(self, name: _Optional[str] = ..., keys: _Optional[_Iterable[_Union[Key, _Mapping]]] = ..., actions: _Optional[_Iterable[str]] = ..., default_action: _Optional[_Union[ActionCall, _Mapping]] = ..., const_default_action: _Optional[bool] = ..., const_entries: _Optional[_Iterable[_Union[Entry, _Mapping]]] = ..., size: _Optional[int] = ...) -> None: ...

class ActionCall(_message.Message):
    __slots__ = ("action", "args")
    ACTION_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    action: str
    args: _containers.RepeatedCompositeFieldContainer[Literal]
    def __init__(self, action: _Optional[str] = ..., args: _Optional[_Iterable[_Union[Literal, _Mapping]]] = ...) -> None: ...

class Entry(_message.Message):
    __slots__ = ("keys", "action", "priority")
    KEYS_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    keys: _containers.RepeatedCompositeFieldContainer[KeyValue]
    action: ActionCall
    priority: int
    def __init__(self, keys: _Optional[_Iterable[_Union[KeyValue, _Mapping]]] = ..., action: _Optional[_Union[ActionCall, _Mapping]] = ..., priority: _Optional[int] = ...) -> None: ...

class KeyValue(_message.Message):
    __slots__ = ("exact", "lpm", "ternary")
    EXACT_FIELD_NUMBER: _ClassVar[int]
    LPM_FIELD_NUMBER: _ClassVar[int]
    TERNARY_FIELD_NUMBER: _ClassVar[int]
    exact: str
    lpm: LpmValue
    ternary: TernaryValue
    def __init__(self, exact: _Optional[str] = ..., lpm: _Optional[_Union[LpmValue, _Mapping]] = ..., ternary: _Optional[_Union[TernaryValue, _Mapping]] = ...) -> None: ...

class LpmValue(_message.Message):
    __slots__ = ("value", "prefix_len")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PREFIX_LEN_FIELD_NUMBER: _ClassVar[int]
    value: str
    prefix_len: int
    def __init__(self, value: _Optional[str] = ..., prefix_len: _Optional[int] = ...) -> None: ...

class TernaryValue(_message.Message):
    __slots__ = ("value", "mask")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    MASK_FIELD_NUMBER: _ClassVar[int]
    value: str
    mask: str
    def __init__(self, value: _Optional[str] = ..., mask: _Optional[str] = ...) -> None: ...

class State(_message.Message):
    __slots__ = ("name", "body", "transition")
    NAME_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    TRANSITION_FIELD_NUMBER: _ClassVar[int]
    name: str
    body: _containers.RepeatedCompositeFieldContainer[Stmt]
    transition: Transition
    def __init__(self, name: _Optional[str] = ..., body: _Optional[_Iterable[_Union[Stmt, _Mapping]]] = ..., transition: _Optional[_Union[Transition, _Mapping]] = ...) -> None: ...

class Transition(_message.Message):
    __slots__ = ("direct", "select")
    DIRECT_FIELD_NUMBER: _ClassVar[int]
    SELECT_FIELD_NUMBER: _ClassVar[int]
    direct: Target
    select: Select
    def __init__(self, direct: _Optional[_Union[Target, _Mapping]] = ..., select: _Optional[_Union[Select, _Mapping]] = ...) -> None: ...

class Target(_message.Message):
    __slots__ = ("state", "accept", "reject")
    STATE_FIELD_NUMBER: _ClassVar[int]
    ACCEPT_FIELD_NUMBER: _ClassVar[int]
    REJECT_FIELD_NUMBER: _ClassVar[int]
    state: str
    accept: Accept
    reject: Reject
    def __init__(self, state: _Optional[str] = ..., accept: _Optional[_Union[Accept, _Mapping]] = ..., reject: _Optional[_Union[Reject, _Mapping]] = ...) -> None: ...

class Accept(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Reject(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Select(_message.Message):
    __slots__ = ("keys", "cases")
    KEYS_FIELD_NUMBER: _ClassVar[int]
    CASES_FIELD_NUMBER: _ClassVar[int]
    keys: _containers.RepeatedCompositeFieldContainer[Expr]
    cases: _containers.RepeatedCompositeFieldContainer[SelectCase]
    def __init__(self, keys: _Optional[_Iterable[_Union[Expr, _Mapping]]] = ..., cases: _Optional[_Iterable[_Union[SelectCase, _Mapping]]] = ...) -> None: ...

class SelectCase(_message.Message):
    __slots__ = ("sets", "target")
    SETS_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    sets: _containers.RepeatedCompositeFieldContainer[KeySet]
    target: Target
    def __init__(self, sets: _Optional[_Iterable[_Union[KeySet, _Mapping]]] = ..., target: _Optional[_Union[Target, _Mapping]] = ...) -> None: ...

class KeySet(_message.Message):
    __slots__ = ("exact", "masked", "range", "dont_care")
    EXACT_FIELD_NUMBER: _ClassVar[int]
    MASKED_FIELD_NUMBER: _ClassVar[int]
    RANGE_FIELD_NUMBER: _ClassVar[int]
    DONT_CARE_FIELD_NUMBER: _ClassVar[int]
    exact: Literal
    masked: MaskedValue
    range: RangeValue
    dont_care: DontCare
    def __init__(self, exact: _Optional[_Union[Literal, _Mapping]] = ..., masked: _Optional[_Union[MaskedValue, _Mapping]] = ..., range: _Optional[_Union[RangeValue, _Mapping]] = ..., dont_care: _Optional[_Union[DontCare, _Mapping]] = ...) -> None: ...

class MaskedValue(_message.Message):
    __slots__ = ("value", "mask")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    MASK_FIELD_NUMBER: _ClassVar[int]
    value: Literal
    mask: Literal
    def __init__(self, value: _Optional[_Union[Literal, _Mapping]] = ..., mask: _Optional[_Union[Literal, _Mapping]] = ...) -> None: ...

class RangeValue(_message.Message):
    __slots__ = ("lo", "hi")
    LO_FIELD_NUMBER: _ClassVar[int]
    HI_FIELD_NUMBER: _ClassVar[int]
    lo: Literal
    hi: Literal
    def __init__(self, lo: _Optional[_Union[Literal, _Mapping]] = ..., hi: _Optional[_Union[Literal, _Mapping]] = ...) -> None: ...

class DontCare(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Stmt(_message.Message):
    __slots__ = ("assign", "conditional", "apply", "call_action", "call_block", "call_extern", "set_valid", "set_invalid", "push", "pop", "extract", "advance", "verify", "emit")
    ASSIGN_FIELD_NUMBER: _ClassVar[int]
    CONDITIONAL_FIELD_NUMBER: _ClassVar[int]
    APPLY_FIELD_NUMBER: _ClassVar[int]
    CALL_ACTION_FIELD_NUMBER: _ClassVar[int]
    CALL_BLOCK_FIELD_NUMBER: _ClassVar[int]
    CALL_EXTERN_FIELD_NUMBER: _ClassVar[int]
    SET_VALID_FIELD_NUMBER: _ClassVar[int]
    SET_INVALID_FIELD_NUMBER: _ClassVar[int]
    PUSH_FIELD_NUMBER: _ClassVar[int]
    POP_FIELD_NUMBER: _ClassVar[int]
    EXTRACT_FIELD_NUMBER: _ClassVar[int]
    ADVANCE_FIELD_NUMBER: _ClassVar[int]
    VERIFY_FIELD_NUMBER: _ClassVar[int]
    EMIT_FIELD_NUMBER: _ClassVar[int]
    assign: Assign
    conditional: If
    apply: Apply
    call_action: CallAction
    call_block: CallBlock
    call_extern: CallExtern
    set_valid: SetValid
    set_invalid: SetInvalid
    push: Push
    pop: Pop
    extract: Extract
    advance: Advance
    verify: Verify
    emit: Emit
    def __init__(self, assign: _Optional[_Union[Assign, _Mapping]] = ..., conditional: _Optional[_Union[If, _Mapping]] = ..., apply: _Optional[_Union[Apply, _Mapping]] = ..., call_action: _Optional[_Union[CallAction, _Mapping]] = ..., call_block: _Optional[_Union[CallBlock, _Mapping]] = ..., call_extern: _Optional[_Union[CallExtern, _Mapping]] = ..., set_valid: _Optional[_Union[SetValid, _Mapping]] = ..., set_invalid: _Optional[_Union[SetInvalid, _Mapping]] = ..., push: _Optional[_Union[Push, _Mapping]] = ..., pop: _Optional[_Union[Pop, _Mapping]] = ..., extract: _Optional[_Union[Extract, _Mapping]] = ..., advance: _Optional[_Union[Advance, _Mapping]] = ..., verify: _Optional[_Union[Verify, _Mapping]] = ..., emit: _Optional[_Union[Emit, _Mapping]] = ...) -> None: ...

class Assign(_message.Message):
    __slots__ = ("target", "value")
    TARGET_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    target: LValue
    value: Expr
    def __init__(self, target: _Optional[_Union[LValue, _Mapping]] = ..., value: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class If(_message.Message):
    __slots__ = ("condition", "then", "otherwise")
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    THEN_FIELD_NUMBER: _ClassVar[int]
    OTHERWISE_FIELD_NUMBER: _ClassVar[int]
    condition: Expr
    then: _containers.RepeatedCompositeFieldContainer[Stmt]
    otherwise: _containers.RepeatedCompositeFieldContainer[Stmt]
    def __init__(self, condition: _Optional[_Union[Expr, _Mapping]] = ..., then: _Optional[_Iterable[_Union[Stmt, _Mapping]]] = ..., otherwise: _Optional[_Iterable[_Union[Stmt, _Mapping]]] = ...) -> None: ...

class Apply(_message.Message):
    __slots__ = ("table", "hit")
    TABLE_FIELD_NUMBER: _ClassVar[int]
    HIT_FIELD_NUMBER: _ClassVar[int]
    table: str
    hit: LValue
    def __init__(self, table: _Optional[str] = ..., hit: _Optional[_Union[LValue, _Mapping]] = ...) -> None: ...

class CallAction(_message.Message):
    __slots__ = ("action", "args")
    ACTION_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    action: str
    args: _containers.RepeatedCompositeFieldContainer[Arg]
    def __init__(self, action: _Optional[str] = ..., args: _Optional[_Iterable[_Union[Arg, _Mapping]]] = ...) -> None: ...

class CallBlock(_message.Message):
    __slots__ = ("block", "args")
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    block: str
    args: _containers.RepeatedCompositeFieldContainer[Arg]
    def __init__(self, block: _Optional[str] = ..., args: _Optional[_Iterable[_Union[Arg, _Mapping]]] = ...) -> None: ...

class CallExtern(_message.Message):
    __slots__ = ("instance", "method", "args", "result")
    INSTANCE_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    instance: str
    method: str
    args: _containers.RepeatedCompositeFieldContainer[Arg]
    result: LValue
    def __init__(self, instance: _Optional[str] = ..., method: _Optional[str] = ..., args: _Optional[_Iterable[_Union[Arg, _Mapping]]] = ..., result: _Optional[_Union[LValue, _Mapping]] = ...) -> None: ...

class Arg(_message.Message):
    __slots__ = ("expr", "lvalue")
    EXPR_FIELD_NUMBER: _ClassVar[int]
    LVALUE_FIELD_NUMBER: _ClassVar[int]
    expr: Expr
    lvalue: LValue
    def __init__(self, expr: _Optional[_Union[Expr, _Mapping]] = ..., lvalue: _Optional[_Union[LValue, _Mapping]] = ...) -> None: ...

class SetValid(_message.Message):
    __slots__ = ("header",)
    HEADER_FIELD_NUMBER: _ClassVar[int]
    header: LValue
    def __init__(self, header: _Optional[_Union[LValue, _Mapping]] = ...) -> None: ...

class SetInvalid(_message.Message):
    __slots__ = ("header",)
    HEADER_FIELD_NUMBER: _ClassVar[int]
    header: LValue
    def __init__(self, header: _Optional[_Union[LValue, _Mapping]] = ...) -> None: ...

class Push(_message.Message):
    __slots__ = ("stack", "count")
    STACK_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    stack: LValue
    count: int
    def __init__(self, stack: _Optional[_Union[LValue, _Mapping]] = ..., count: _Optional[int] = ...) -> None: ...

class Pop(_message.Message):
    __slots__ = ("stack", "count")
    STACK_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    stack: LValue
    count: int
    def __init__(self, stack: _Optional[_Union[LValue, _Mapping]] = ..., count: _Optional[int] = ...) -> None: ...

class Extract(_message.Message):
    __slots__ = ("target",)
    TARGET_FIELD_NUMBER: _ClassVar[int]
    target: LValue
    def __init__(self, target: _Optional[_Union[LValue, _Mapping]] = ...) -> None: ...

class Advance(_message.Message):
    __slots__ = ("bits",)
    BITS_FIELD_NUMBER: _ClassVar[int]
    bits: Expr
    def __init__(self, bits: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Verify(_message.Message):
    __slots__ = ("condition", "error")
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    condition: Expr
    error: str
    def __init__(self, condition: _Optional[_Union[Expr, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class Emit(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: Expr
    def __init__(self, value: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Expr(_message.Message):
    __slots__ = ("literal", "var", "member", "index", "last_index", "unary", "binary", "cast", "slice", "is_valid", "mux", "lookahead")
    LITERAL_FIELD_NUMBER: _ClassVar[int]
    VAR_FIELD_NUMBER: _ClassVar[int]
    MEMBER_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    LAST_INDEX_FIELD_NUMBER: _ClassVar[int]
    UNARY_FIELD_NUMBER: _ClassVar[int]
    BINARY_FIELD_NUMBER: _ClassVar[int]
    CAST_FIELD_NUMBER: _ClassVar[int]
    SLICE_FIELD_NUMBER: _ClassVar[int]
    IS_VALID_FIELD_NUMBER: _ClassVar[int]
    MUX_FIELD_NUMBER: _ClassVar[int]
    LOOKAHEAD_FIELD_NUMBER: _ClassVar[int]
    literal: Literal
    var: str
    member: Member
    index: Index
    last_index: LastIndex
    unary: Unary
    binary: Binary
    cast: Cast
    slice: Slice
    is_valid: IsValid
    mux: Mux
    lookahead: Lookahead
    def __init__(self, literal: _Optional[_Union[Literal, _Mapping]] = ..., var: _Optional[str] = ..., member: _Optional[_Union[Member, _Mapping]] = ..., index: _Optional[_Union[Index, _Mapping]] = ..., last_index: _Optional[_Union[LastIndex, _Mapping]] = ..., unary: _Optional[_Union[Unary, _Mapping]] = ..., binary: _Optional[_Union[Binary, _Mapping]] = ..., cast: _Optional[_Union[Cast, _Mapping]] = ..., slice: _Optional[_Union[Slice, _Mapping]] = ..., is_valid: _Optional[_Union[IsValid, _Mapping]] = ..., mux: _Optional[_Union[Mux, _Mapping]] = ..., lookahead: _Optional[_Union[Lookahead, _Mapping]] = ...) -> None: ...

class Member(_message.Message):
    __slots__ = ("base", "field")
    BASE_FIELD_NUMBER: _ClassVar[int]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    base: Expr
    field: str
    def __init__(self, base: _Optional[_Union[Expr, _Mapping]] = ..., field: _Optional[str] = ...) -> None: ...

class Index(_message.Message):
    __slots__ = ("base", "index")
    BASE_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    base: Expr
    index: Expr
    def __init__(self, base: _Optional[_Union[Expr, _Mapping]] = ..., index: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class LastIndex(_message.Message):
    __slots__ = ("stack",)
    STACK_FIELD_NUMBER: _ClassVar[int]
    stack: Expr
    def __init__(self, stack: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Unary(_message.Message):
    __slots__ = ("op", "operand")
    OP_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    op: UnaryOp
    operand: Expr
    def __init__(self, op: _Optional[_Union[UnaryOp, str]] = ..., operand: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Binary(_message.Message):
    __slots__ = ("op", "left", "right")
    OP_FIELD_NUMBER: _ClassVar[int]
    LEFT_FIELD_NUMBER: _ClassVar[int]
    RIGHT_FIELD_NUMBER: _ClassVar[int]
    op: BinaryOp
    left: Expr
    right: Expr
    def __init__(self, op: _Optional[_Union[BinaryOp, str]] = ..., left: _Optional[_Union[Expr, _Mapping]] = ..., right: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Cast(_message.Message):
    __slots__ = ("to", "operand")
    TO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    to: Type
    operand: Expr
    def __init__(self, to: _Optional[_Union[Type, _Mapping]] = ..., operand: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Slice(_message.Message):
    __slots__ = ("operand", "hi", "lo")
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    HI_FIELD_NUMBER: _ClassVar[int]
    LO_FIELD_NUMBER: _ClassVar[int]
    operand: Expr
    hi: int
    lo: int
    def __init__(self, operand: _Optional[_Union[Expr, _Mapping]] = ..., hi: _Optional[int] = ..., lo: _Optional[int] = ...) -> None: ...

class IsValid(_message.Message):
    __slots__ = ("header",)
    HEADER_FIELD_NUMBER: _ClassVar[int]
    header: Expr
    def __init__(self, header: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Mux(_message.Message):
    __slots__ = ("condition", "then", "otherwise")
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    THEN_FIELD_NUMBER: _ClassVar[int]
    OTHERWISE_FIELD_NUMBER: _ClassVar[int]
    condition: Expr
    then: Expr
    otherwise: Expr
    def __init__(self, condition: _Optional[_Union[Expr, _Mapping]] = ..., then: _Optional[_Union[Expr, _Mapping]] = ..., otherwise: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Lookahead(_message.Message):
    __slots__ = ("type",)
    TYPE_FIELD_NUMBER: _ClassVar[int]
    type: Type
    def __init__(self, type: _Optional[_Union[Type, _Mapping]] = ...) -> None: ...

class LValue(_message.Message):
    __slots__ = ("var", "member", "index", "next")
    VAR_FIELD_NUMBER: _ClassVar[int]
    MEMBER_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    NEXT_FIELD_NUMBER: _ClassVar[int]
    var: str
    member: LMember
    index: LIndex
    next: Next
    def __init__(self, var: _Optional[str] = ..., member: _Optional[_Union[LMember, _Mapping]] = ..., index: _Optional[_Union[LIndex, _Mapping]] = ..., next: _Optional[_Union[Next, _Mapping]] = ...) -> None: ...

class LMember(_message.Message):
    __slots__ = ("base", "field")
    BASE_FIELD_NUMBER: _ClassVar[int]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    base: LValue
    field: str
    def __init__(self, base: _Optional[_Union[LValue, _Mapping]] = ..., field: _Optional[str] = ...) -> None: ...

class LIndex(_message.Message):
    __slots__ = ("base", "index")
    BASE_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    base: LValue
    index: Expr
    def __init__(self, base: _Optional[_Union[LValue, _Mapping]] = ..., index: _Optional[_Union[Expr, _Mapping]] = ...) -> None: ...

class Next(_message.Message):
    __slots__ = ("stack",)
    STACK_FIELD_NUMBER: _ClassVar[int]
    stack: LValue
    def __init__(self, stack: _Optional[_Union[LValue, _Mapping]] = ...) -> None: ...

class Entries(_message.Message):
    __slots__ = ("tables",)
    TABLES_FIELD_NUMBER: _ClassVar[int]
    tables: _containers.RepeatedCompositeFieldContainer[TableEntries]
    def __init__(self, tables: _Optional[_Iterable[_Union[TableEntries, _Mapping]]] = ...) -> None: ...

class TableEntries(_message.Message):
    __slots__ = ("block", "table", "entries", "default_action")
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    TABLE_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ACTION_FIELD_NUMBER: _ClassVar[int]
    block: str
    table: str
    entries: _containers.RepeatedCompositeFieldContainer[Entry]
    default_action: ActionCall
    def __init__(self, block: _Optional[str] = ..., table: _Optional[str] = ..., entries: _Optional[_Iterable[_Union[Entry, _Mapping]]] = ..., default_action: _Optional[_Union[ActionCall, _Mapping]] = ...) -> None: ...
