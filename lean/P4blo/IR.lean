/-!
# The p4blo IR as Lean data

Every type here mirrors one message or enum of `proto/p4blo/v0/p4blo.proto`,
which is the normative syntax; the doc comment on each says which. Field
names are the proto's, lower-camel-cased (`header_types` is `headerTypes`),
and where the proto's name is a Lean keyword the doc comment gives the
substitute (`then` is `thenBranch`, `instance` is `inst`, `in` is `«in»`).

A `oneof` becomes an inductive with one constructor per case, and a message
that exists only to carry one case's fields (`StackType`, `Member`, `If`,
...) is inlined into that constructor rather than declared on its own, so
the Lean shape stays one level flatter than the proto without losing a
field. Every such inlining is named in the constructor's doc comment.

Enums drop their `_UNSPECIFIED` value: decoding it is an error.

Decimal strings in the proto (`BitsLiteral.value`, the `KeyValue` values)
are `Nat` here; the validator, not the decoder, checks them against widths.
-/

namespace P4blo

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------

/-- Mirrors `Direction`. `DIRECTION_NONE` is directionless: action data. -/
inductive Direction
  | none
  | «in»
  | out
  | inout
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `BlockKind`. -/
inductive BlockKind
  | parser
  | control
  | deparser
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `MatchKind`. -/
inductive MatchKind
  | exact
  | lpm
  | ternary
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `UnaryOp`. -/
inductive UnaryOp
  /-- Logical not, on boolean. -/
  | not
  /-- Bitwise complement, on bits. -/
  | complement
  /-- Two's complement negation modulo 2^N, on bits. -/
  | negate
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `BinaryOp`. -/
inductive BinaryOp
  /-- bits x bits -> bits, equal widths, wrapping. -/
  | add
  | sub
  | mul
  /-- Saturating. -/
  | addSat
  | subSat
  | bitAnd
  | bitOr
  | bitXor
  /-- bits x bits -> bits, left width; any right width. -/
  | shl
  | shr
  /-- bits x bits -> bits, width is the sum. -/
  | concat
  /-- any x any -> boolean, same type. -/
  | eq
  | ne
  /-- bits x bits -> boolean, equal widths, unsigned. -/
  | lt
  | le
  | gt
  | ge
  /-- boolean x boolean -> boolean, short-circuit. -/
  | and
  | or
  deriving Repr, BEq, DecidableEq, Inhabited

-- ---------------------------------------------------------------------------
-- Types
-- ---------------------------------------------------------------------------

/-- Mirrors `Type` (named `Ty` because `Type` is Lean's). One constructor per
case of its `oneof kind`; `BoolType`, `ErrorType` and `StackType` are inlined. -/
inductive Ty
  /-- `bit<N>`, N >= 1. -/
  | bits (n : Nat)
  /-- `BoolType {}`. -/
  | boolean
  /-- Name of a `HeaderType`. -/
  | header (name : String)
  /-- Name of a `StructType`. -/
  | struct (name : String)
  /-- Name of an `EnumType`. -/
  | enumType (name : String)
  /-- `ErrorType {}`. -/
  | error
  /-- `StackType`: a header stack of `size` headers of type `header`. -/
  | stack (header : String) (size : Nat)
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `Field`. -/
structure Field where
  name : String
  type : Ty
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `HeaderType`. Header fields are bits or boolean; varbit is out of
scope. -/
structure HeaderType where
  name : String
  fields : List Field
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `StructType`. Struct fields may be any type, including headers,
structs and stacks. -/
structure StructType where
  name : String
  fields : List Field
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `EnumType`: a plain enum. Serializable enums are elaborated to
bits and literals. -/
structure EnumType where
  name : String
  members : List String
  deriving Repr, BEq, DecidableEq, Inhabited

-- ---------------------------------------------------------------------------
-- Literals
-- ---------------------------------------------------------------------------

/-- Mirrors `Literal`. One constructor per case of its `oneof value`;
`BitsLiteral` and `EnumLiteral` are inlined. -/
inductive Literal
  /-- `BitsLiteral`: a `bit<width>` value, in `[0, 2^width)`. Decimal in the
  proto, a `Nat` here. -/
  | bits (width : Nat) (value : Nat)
  | boolean (value : Bool)
  /-- `EnumLiteral`: member `member` of enum `enumType`. -/
  | enumMember (enumType : String) (member : String)
  /-- A name from `Program.errors`. -/
  | error (name : String)
  deriving Repr, BEq, DecidableEq, Inhabited

-- ---------------------------------------------------------------------------
-- Variables and parameters
-- ---------------------------------------------------------------------------

/-- Mirrors `Var`. -/
structure Var where
  name : String
  type : Ty
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `Param`. -/
structure Param where
  name : String
  type : Ty
  direction : Direction
  deriving Repr, BEq, DecidableEq, Inhabited

-- ---------------------------------------------------------------------------
-- Externs
-- ---------------------------------------------------------------------------

/-- Mirrors `Method`. -/
structure Method where
  name : String
  params : List Param
  /-- `none` for a method that returns nothing. -/
  returns : Option Ty
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `ExternType`. An extern type is monomorphic: every method has
concrete parameter types. -/
structure ExternType where
  name : String
  constructorParams : List Param
  methods : List Method
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `ExternInstance`: program-level state. -/
structure ExternInstance where
  name : String
  externType : String
  args : List Literal
  deriving Repr, BEq, DecidableEq, Inhabited

-- ---------------------------------------------------------------------------
-- Expressions
-- ---------------------------------------------------------------------------

/-- Mirrors `Expr`. One constructor per case of its `oneof kind`; the
sub-messages `Member`, `Index`, `LastIndex`, `Unary`, `Binary`, `Cast`,
`Slice`, `IsValid`, `Mux` and `Lookahead` are inlined. Expressions carry no
type annotations. -/
inductive Expr
  | literal (value : Literal)
  /-- Name of a param or local visible here. -/
  | var (name : String)
  /-- `Member`: field `field` of a header or struct. -/
  | member (base : Expr) (field : String)
  /-- `Index`: element `index` of a stack. -/
  | index (base : Expr) (index : Expr)
  /-- `LastIndex`: `stack.lastIndex`, a `bit<32>`. -/
  | lastIndex (stack : Expr)
  /-- `Unary`. -/
  | unary (op : UnaryOp) (operand : Expr)
  /-- `Binary`. -/
  | binary (op : BinaryOp) (left : Expr) (right : Expr)
  /-- `Cast`. Allowed: bits to bits of any width; boolean to `bit<1>`;
  `bit<1>` to boolean. -/
  | cast (to : Ty) (operand : Expr)
  /-- `Slice`: `operand[hi:lo]`, width `hi - lo + 1`, with
  `lo <= hi < width(operand)`. -/
  | slice (operand : Expr) (hi : Nat) (lo : Nat)
  /-- `IsValid`. -/
  | isValid (header : Expr)
  /-- `Mux`: `condition ? then : otherwise`, same type on both branches.
  `then` is `thenBranch`. -/
  | mux (condition : Expr) (thenBranch : Expr) (otherwise : Expr)
  /-- `Lookahead`: read a value of `type` from the packet without consuming
  it. Parser only. -/
  | lookahead (type : Ty)
  deriving Repr, BEq, Inhabited

-- ---------------------------------------------------------------------------
-- Lvalues
-- ---------------------------------------------------------------------------

/-- Mirrors `LValue`. One constructor per case of its `oneof kind`; `LMember`,
`LIndex` and `Next` are inlined. -/
inductive LValue
  | var (name : String)
  /-- `LMember`. -/
  | member (base : LValue) (field : String)
  /-- `LIndex`. -/
  | index (base : LValue) (index : Expr)
  /-- `Next`: `stack.next`, parser only, the target of an extract into a
  stack. -/
  | next (stack : LValue)
  deriving Repr, BEq, Inhabited

/-- Mirrors `Arg`. An `in` argument is an expression; an `out` or `inout`
argument is an lvalue, copied back after the call. -/
inductive Arg
  | expr (value : Expr)
  | lvalue (value : LValue)
  deriving Repr, BEq, Inhabited

-- ---------------------------------------------------------------------------
-- Statements
-- ---------------------------------------------------------------------------

/-- Mirrors `Stmt`. One constructor per case of its `oneof kind`; every
sub-message (`Assign`, `If`, `Apply`, `CallAction`, `CallBlock`,
`CallExtern`, `SetValid`, `SetInvalid`, `Push`, `Pop`, `Extract`, `Advance`,
`Verify`, `Emit`) is inlined.

Where each statement may appear:
- any block: `assign`, `conditional`, `callBlock`, `callExtern`, `setValid`,
  `setInvalid`, `push`, `pop`;
- control: `apply`, `callAction`;
- parser: `extract`, `advance`, `verify`;
- deparser: `emit`. -/
inductive Stmt
  /-- `Assign`. -/
  | assign (target : LValue) (value : Expr)
  /-- `If`. `then` is `thenBranch`. -/
  | conditional (condition : Expr) (thenBranch : List Stmt) (otherwise : List Stmt)
  /-- `Apply` a table. `hit`, when present, receives whether an entry
  matched. -/
  | apply (table : String) (hit : Option LValue)
  /-- `CallAction`. -/
  | callAction (action : String) (args : List Arg)
  /-- `CallBlock`: call a sub-parser or sub-control. A parser may only call
  parsers and a control only controls. -/
  | callBlock (block : String) (args : List Arg)
  /-- `CallExtern`. `instance` is `inst`; `result` receives the return value
  when the method has one. -/
  | callExtern (inst : String) (method : String) (args : List Arg) (result : Option LValue)
  /-- `SetValid`. -/
  | setValid (header : LValue)
  /-- `SetInvalid`. -/
  | setInvalid (header : LValue)
  /-- `Push`. -/
  | push (stack : LValue) (count : Nat)
  /-- `Pop`. -/
  | pop (stack : LValue) (count : Nat)
  /-- `Extract` a fixed-size header from the packet into `target`. -/
  | extract (target : LValue)
  /-- `Advance`: skip `bits` bits of the packet. -/
  | advance (bits : Expr)
  /-- `Verify`: raise `error` unless `condition` holds. -/
  | verify (condition : Expr) (error : String)
  /-- `Emit` a header, or every header in a struct or stack, to the packet. -/
  | emit (value : Expr)
  deriving Repr, BEq, Inhabited

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

/-- Mirrors `Key`. -/
structure Key where
  expr : Expr
  matchKind : MatchKind
  /-- The name the host uses for this key in entries; defaults to the
  expression rendered as a dotted path when it is one. -/
  name : String
  deriving Repr, BEq, Inhabited

/-- Mirrors `ActionCall`. -/
structure ActionCall where
  action : String
  args : List Literal
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `KeyValue`. One constructor per case of its `oneof kind`;
`LpmValue` and `TernaryValue` are inlined. Values are decimal in the proto,
of the key's width; `Nat` here. -/
inductive KeyValue
  | exact (value : Nat)
  /-- `LpmValue`. -/
  | lpm (value : Nat) (prefixLen : Nat)
  /-- `TernaryValue`. -/
  | ternary (value : Nat) (mask : Nat)
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `Entry`. -/
structure Entry where
  /-- One per table key, in order. -/
  keys : List KeyValue
  action : ActionCall
  /-- Required when the table has a ternary key; larger wins. -/
  priority : Nat
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `Table`. -/
structure Table where
  name : String
  keys : List Key
  /-- Names of the actions an entry may invoke. -/
  actions : List String
  /-- Runs on a miss. `none` means NoAction: do nothing. -/
  defaultAction : Option ActionCall
  /-- A const default action cannot be changed by the host. -/
  constDefaultAction : Bool
  /-- Installed before any host entry and never removed. -/
  constEntries : List Entry
  /-- Informative: the size hint P4 lets a table declare. No meaning. -/
  size : Nat
  deriving Repr, BEq, Inhabited

-- ---------------------------------------------------------------------------
-- Parser states
-- ---------------------------------------------------------------------------

/-- Mirrors `Target`. One constructor per case of its `oneof kind`; `Accept`
and `Reject` are inlined. -/
inductive Target
  | state (name : String)
  | accept
  | reject
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `KeySet`. One constructor per case of its `oneof kind`;
`MaskedValue`, `RangeValue` and `DontCare` are inlined. -/
inductive KeySet
  | exact (value : Literal)
  /-- `MaskedValue`: matches when `(key & mask) == (value & mask)`. -/
  | masked (value : Literal) (mask : Literal)
  /-- `RangeValue`: matches when `lo <= key <= hi`. -/
  | range (lo : Literal) (hi : Literal)
  /-- `DontCare {}`. -/
  | dontCare
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `SelectCase`. -/
structure SelectCase where
  /-- One per select key, in order. -/
  sets : List KeySet
  target : Target
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `Transition`. One constructor per case of its `oneof kind`;
`Select` is inlined. -/
inductive Transition
  | direct (target : Target)
  /-- `Select`: cases are tried in order; the first whose every key set
  matches wins. No match transitions to reject with error NoMatch. -/
  | select (keys : List Expr) (cases : List SelectCase)
  deriving Repr, BEq, Inhabited

/-- Mirrors `State`. -/
structure State where
  name : String
  body : List Stmt
  transition : Transition
  deriving Repr, BEq, Inhabited

-- ---------------------------------------------------------------------------
-- Blocks
-- ---------------------------------------------------------------------------

/-- Mirrors `Action`. -/
structure Action where
  name : String
  /-- Directionless params are action data, supplied by table entries. -/
  params : List Param
  body : List Stmt
  deriving Repr, BEq, Inhabited

/-- Mirrors `Block`: a function. It performs no effects: it reads and writes
its parameters, the packet when it is a parser or deparser, and the externs
it calls, and nothing else. A parser has states and a start state and no
body; a control or deparser has a body and no states. -/
structure Block where
  name : String
  kind : BlockKind
  params : List Param
  locals : List Var
  actions : List Action
  tables : List Table
  states : List State
  startState : String
  body : List Stmt
  deriving Repr, BEq, Inhabited

-- ---------------------------------------------------------------------------
-- Program
-- ---------------------------------------------------------------------------

/-- Mirrors `Export`. The role name is a label; the block must have the
calling convention of its kind. -/
structure Export where
  role : String
  block : String
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `Program`. -/
structure Program where
  /-- Human-readable name; carries no meaning. -/
  name : String
  /-- Error values by name. The first seven are core.p4's, in the order
  NoError, PacketTooShort, NoMatch, StackOutOfBounds, HeaderTooShort,
  ParserTimeout, ParserInvalidArgument. -/
  errors : List String
  headerTypes : List HeaderType
  structTypes : List StructType
  enumTypes : List EnumType
  externTypes : List ExternType
  externInstances : List ExternInstance
  blocks : List Block
  /-- The struct type of the headers value H. -/
  headers : String
  /-- The struct type of the metadata value M. -/
  metadata : String
  /-- The blocks the program offers to an architecture, by role. -/
  exports : List Export
  deriving Repr, BEq, Inhabited

-- ---------------------------------------------------------------------------
-- Host-installed state
-- ---------------------------------------------------------------------------

/-- Mirrors `TableEntries`. -/
structure TableEntries where
  /-- The block and table names, since table names are block-scoped. -/
  block : String
  table : String
  entries : List Entry
  /-- Overrides the program's default action unless it is const. -/
  defaultAction : Option ActionCall
  deriving Repr, BEq, DecidableEq, Inhabited

/-- Mirrors `Entries`: what a host installs before packets run. Not part of a
program. -/
structure Entries where
  tables : List TableEntries
  deriving Repr, BEq, DecidableEq, Inhabited

end P4blo
