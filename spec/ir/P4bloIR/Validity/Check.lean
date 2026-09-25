import P4bloIR.Validity.Rules

/-!
# The validity checker

An executable checker for `Validity.Valid`, organized as the Python
validator is (`impl/python/p4blo/validator.py`): one function per
declaration, statement and expression kind, in the order of the schema,
with the same diagnostic codes. It stops at the first problem, where
Python collects them all; `tests/test_lean_agrees_validity.py` compares
the two on accept or reject and on the first code.

Wire problems the Python validator reports (a oneof with no kind, an
unspecified enum, a bits value that is not decimal) do not reach this
checker: `Program.fromJsonString` rejects them first.

`check_sound` (in `Validity.Sound`) proves that a program the checker
accepts satisfies `Valid`.
-/

namespace P4bloIR.Validity

open Std (HashMap)

/-- The validator's diagnostic codes that can arise after decoding. -/
inductive Code
  | nameEmpty | nameDuplicate | errorList | refUnresolved | refKind | scopeVar | scopeDecl
  | exportDuplicate | exportSignature | typeInvalid | literalRange | blockKindShape
  | parserStartState | blockKindStmt | parserOnly | nextOnlyExtract | paramDirection
  | typeMismatch | castInvalid | sliceRange | lvalueReadonly | stackCount | argCount
  | argDirection | argType | callKind | callAlias | callCycle | externResult
  | selectArity | selectType | keyName | keyType | tableLpmCount | tableKeyMix
  | tableActions | noActionReserved | actionArgs | entryShape | entryRange | entryPriority
  | entryDuplicate | externArgs
  deriving DecidableEq, Repr

/-- The code as the Python validator spells it. -/
def Code.name : Code → String
  | .nameEmpty => "NAME_EMPTY" | .nameDuplicate => "NAME_DUPLICATE"
  | .errorList => "ERROR_LIST" | .refUnresolved => "REF_UNRESOLVED" | .refKind => "REF_KIND"
  | .scopeVar => "SCOPE_VAR" | .scopeDecl => "SCOPE_DECL"
  | .exportDuplicate => "EXPORT_DUPLICATE" | .exportSignature => "EXPORT_SIGNATURE"
  | .typeInvalid => "TYPE_INVALID" | .literalRange => "LITERAL_RANGE"
  | .blockKindShape => "BLOCK_KIND_SHAPE" | .parserStartState => "PARSER_START_STATE"
  | .blockKindStmt => "BLOCK_KIND_STMT" | .parserOnly => "PARSER_ONLY"
  | .nextOnlyExtract => "NEXT_ONLY_EXTRACT" | .paramDirection => "PARAM_DIRECTION"
  | .typeMismatch => "TYPE_MISMATCH" | .castInvalid => "CAST_INVALID"
  | .sliceRange => "SLICE_RANGE" | .lvalueReadonly => "LVALUE_READONLY"
  | .stackCount => "STACK_COUNT" | .argCount => "ARG_COUNT" | .argDirection => "ARG_DIRECTION"
  | .argType => "ARG_TYPE" | .callKind => "CALL_KIND" | .callAlias => "CALL_ALIAS"
  | .callCycle => "CALL_CYCLE" | .externResult => "EXTERN_RESULT"
  | .selectArity => "SELECT_ARITY" | .selectType => "SELECT_TYPE" | .keyName => "KEY_NAME"
  | .keyType => "KEY_TYPE" | .tableLpmCount => "TABLE_LPM_COUNT"
  | .tableKeyMix => "TABLE_KEY_MIX" | .tableActions => "TABLE_ACTIONS"
  | .noActionReserved => "NOACTION_RESERVED" | .actionArgs => "ACTION_ARGS"
  | .entryShape => "ENTRY_SHAPE" | .entryRange => "ENTRY_RANGE"
  | .entryPriority => "ENTRY_PRIORITY" | .entryDuplicate => "ENTRY_DUPLICATE"
  | .externArgs => "EXTERN_ARGS"

/-- A problem: its code, where it is, and what is wrong. -/
structure Diagnostic where
  code : Code
  path : String
  message : String

instance : ToString Diagnostic := ⟨fun d => s!"{d.path}: {d.code.name}: {d.message}"⟩

/-- A check that stops at the first problem. -/
abbrev Chk := Except Diagnostic

/-- Stop with a diagnostic. -/
def fail (code : Code) (path message : String) : Chk α := .error ⟨code, path, message⟩

/-- Go on when `b` holds. -/
def ensure (b : Bool) (code : Code) (path message : String) : Chk Unit :=
  if b then pure () else fail code path message

/-- The value `o` holds, or stop. -/
def need (o : Option α) (code : Code) (path message : String) : Chk α :=
  match o with
  | some a => pure a
  | none => fail code path message

/-- Check every element, in order, with its position. -/
def each (l : List α) (f : Nat → α → Chk Unit) : Chk Unit :=
  go 0 l
where
  go : Nat → List α → Chk Unit
    | _, [] => pure ()
    | i, x :: xs => do f i x; go (i + 1) xs

/-- `s` with `[i]` appended, for paths. -/
def at_ (path : String) (i : Nat) : String := s!"{path}[{i}]"

/-- `path.key`, for paths. -/
def dot (path key : String) : String := if path.isEmpty then key else s!"{path}.{key}"

-- ---------------------------------------------------------------------------
-- Names and references
-- ---------------------------------------------------------------------------

/-- Names in one of the small namespaces: fields, enum members, methods and
their params (validator, `check_names`). -/
def checkNames (names : List String) (path what : String) : Chk Unit :=
  go [] 0 names
where
  go (seen : List String) : Nat → List String → Chk Unit
    | _, [] => pure ()
    | i, n :: ns => do
      ensure (!n.isEmpty) .nameEmpty (at_ path i) s!"{what} has no name"
      ensure (!seen.contains n) .nameDuplicate (at_ path i) s!"{what} '{n}' declared twice"
      go (seen ++ [n]) (i + 1) ns

/-- A program-level reference (validator, `resolve`). -/
def resolve (idx : Index) (found : Option α) (name what path : String) : Chk α :=
  match found with
  | some a => pure a
  | none =>
    if idx.programNames.contains name then fail .refKind path s!"'{name}' is not a {what}"
    else if name.isEmpty then fail .refUnresolved path s!"{what} reference is unset"
    else fail .refUnresolved path s!"no {what} named '{name}'"

/-- A block-scoped reference: an action, table or state of this block
(validator, `resolve_local`). `elsewhere` says whether another block
declares the name as that kind. -/
def resolveLocal (c : Ctx) (found : Option α) (elsewhere : BlockScope → Bool)
    (name what path : String) : Chk α :=
  match found with
  | some a => pure a
  | none =>
    let sc := c.scope
    if name.isEmpty then fail .refUnresolved path s!"{what} reference is unset"
    else if sc.vars.contains name || sc.actions.contains name || sc.tables.contains name ||
        sc.states.contains name || c.index.programNames.contains name then
      fail .refKind path s!"'{name}' is not a {what}"
    else if c.index.scopes.toList.any (fun (_, s) => elsewhere s) then
      fail .scopeDecl path s!"{what} '{name}' belongs to another block"
    else fail .refUnresolved path s!"no {what} named '{name}'"

/-- A variable reference (validator, `resolve_var`). -/
def resolveVar (c : Ctx) (name path : String) : Chk VarDecl :=
  match c.var? name with
  | some d => pure d
  | none =>
    let sc := c.scope
    if name.isEmpty then fail .refUnresolved path "variable reference is unset"
    else if sc.actions.contains name || sc.tables.contains name || sc.states.contains name ||
        c.index.programNames.contains name then
      fail .refKind path s!"'{name}' is not a variable"
    else if c.index.scopes.toList.any (fun (_, s) => s.vars.contains name ||
        s.actionParams.toList.any fun (_, ps) => ps.contains name) then
      fail .scopeVar path s!"variable '{name}' is not visible here"
    else fail .refUnresolved path s!"no variable named '{name}'"

-- ---------------------------------------------------------------------------
-- Types and literals
-- ---------------------------------------------------------------------------

/-- A type's names resolve and its widths and sizes are positive
(validator, `check_type`). -/
def checkTypeRefs (idx : Index) (path : String) : Ty → Chk Unit
  | .bits n => ensure (0 < n) .typeInvalid path "bit width must be at least 1"
  | .boolean | .error => pure ()
  | .header n => do let _ ← resolve idx idx.headerTypes[n]? n "header type" path
  | .struct n => do let _ ← resolve idx idx.structTypes[n]? n "struct type" path
  | .enumType n => do let _ ← resolve idx idx.enumTypes[n]? n "enum type" path
  | .stack h size => do
    let _ ← resolve idx idx.headerTypes[h]? h "header type" path
    ensure (0 < size) .typeInvalid path "stack size must be at least 1"

/-- A type used by a declaration or expression: its references, then the
nesting bound. The bound fails only for a struct that contains itself,
which the struct declarations report first. -/
def checkType (idx : Index) (path : String) (ty : Ty) : Chk Unit := do
  checkTypeRefs idx path ty
  ensure (tyDeep idx (fuel idx) ty) .typeInvalid path "a struct contains itself"

/-- The type of a literal (validator, `type_of_literal`). -/
def checkLiteral (idx : Index) (path : String) : Literal → Chk Ty
  | .bits w v => do
    ensure (0 < w) .literalRange path "literal width must be at least 1"
    ensure (v < 2 ^ w) .literalRange path s!"{v} does not fit in bit<{w}>"
    pure (.bits w)
  | .boolean _ => pure .boolean
  | .enumMember t m => do
    let e ← resolve idx idx.enumTypes[t]? t "enum type" path
    ensure (e.members.contains m) .refUnresolved path s!"enum {t} has no member '{m}'"
    pure (.enumType t)
  | .error n => do
    ensure (idx.program.errors.contains n) .refUnresolved path s!"no error named '{n}'"
    pure .error

/-- Literal arguments against params: action data or constructor args
(validator, `check_literal_args`). -/
def checkLiteralArgs (idx : Index) (args : List Literal) (params : List Param) (path : String)
    (code : Code) : Chk Unit := do
  ensure (args.length == params.length) code path
    s!"expected {params.length} arguments, got {args.length}"
  each (args.zip params) fun i (a, q) => do
    let t ← checkLiteral idx (at_ path i) a
    ensure (decide (t = q.type)) code (at_ path i) s!"argument {i} has the wrong type"

-- ---------------------------------------------------------------------------
-- Expressions and lvalues
-- ---------------------------------------------------------------------------

/-- Go on when `t` has the kind `ok` accepts. -/
def expect (t : Ty) (ok : Ty → Bool) (what path : String) : Chk Ty := do
  ensure (ok t) .typeMismatch path s!"expected {what}"
  pure t

def isBits : Ty → Bool | .bits _ => true | _ => false
def isBoolean : Ty → Bool | .boolean => true | _ => false
def isHeader : Ty → Bool | .header _ => true | _ => false
def isStack : Ty → Bool | .stack _ _ => true | _ => false

/-- The type of field `f` of a value of type `bt` (validator,
`type_of_field`). -/
def checkField (idx : Index) (bt : Ty) (f path : String) : Chk Ty :=
  match fieldType? idx bt f with
  | some t => pure t
  | none => match bt with
    | .header _ | .struct _ => fail .refUnresolved (dot path "field") s!"no field '{f}'"
    | _ => fail .typeMismatch (dot path "base") "expected a header or struct"

/-- The type of an expression (validator, `type_of`). -/
def checkExpr (c : Ctx) (path : String) : Expr → Chk Ty
  | .literal lit => checkLiteral c.index (dot path "literal") lit
  | .var x => do pure (← resolveVar c x (dot path "var")).type
  | .member base f => do
    let bt ← checkExpr c (dot path "member.base") base
    checkField c.index bt f (dot path "member")
  | .index base i => do
    let bt ← checkExpr c (dot path "index.base") base
    let _ ← expect bt isStack "a stack" (dot path "index.base")
    let it ← checkExpr c (dot path "index.index") i
    let _ ← expect it isBits "bits" (dot path "index.index")
    match bt with
    | .stack h _ => pure (.header h)
    | _ => fail .typeMismatch path "expected a stack"
  | .lastIndex s => do
    ensure (c.kind == .parser) .parserOnly path "stack.lastIndex is allowed only in a parser"
    let st ← checkExpr c (dot path "last_index.stack") s
    let _ ← expect st isStack "a stack" (dot path "last_index.stack")
    pure (.bits 32)
  | .unary op e => do
    let t ← checkExpr c (dot path "unary.operand") e
    match op with
    | .not => expect t isBoolean "boolean" (dot path "unary.operand")
    | .complement | .negate => expect t isBits "bits" (dot path "unary.operand")
  | .binary op l r => do
    let lt ← checkExpr c (dot path "binary.left") l
    let rt ← checkExpr c (dot path "binary.right") r
    need (binaryType op lt rt) .typeMismatch (dot path "binary") "operand types do not fit the operator"
  | .cast to e => do
    checkType c.index (dot path "cast.to") to
    let a ← checkExpr c (dot path "cast.operand") e
    ensure (castOk a to) .castInvalid (dot path "cast") "the IR does not allow this cast"
    pure to
  | .slice e hi lo => do
    let a ← checkExpr c (dot path "slice.operand") e
    let _ ← expect a isBits "bits" (dot path "slice.operand")
    match a with
    | .bits w =>
      ensure (lo ≤ hi && hi < w) .sliceRange (dot path "slice") s!"[{hi}:{lo}] needs lo <= hi < {w}"
      pure (.bits (hi - lo + 1))
    | _ => fail .typeMismatch path "expected bits"
  | .isValid h => do
    let t ← checkExpr c (dot path "is_valid.header") h
    let _ ← expect t isHeader "a header" (dot path "is_valid.header")
    pure .boolean
  | .mux cnd a b => do
    let ct ← checkExpr c (dot path "mux.condition") cnd
    let _ ← expect ct isBoolean "boolean" (dot path "mux.condition")
    let at_ ← checkExpr c (dot path "mux.then") a
    let bt ← checkExpr c (dot path "mux.otherwise") b
    ensure (decide (at_ = bt)) .typeMismatch (dot path "mux") "branches differ"
    pure at_
  | .lookahead ty => do
    ensure (c.kind == .parser) .parserOnly (dot path "lookahead") "lookahead is allowed only in a parser"
    checkType c.index (dot path "lookahead.type") ty
    ensure (isBits ty || isBoolean ty || isHeader ty) .typeMismatch (dot path "lookahead.type")
      "lookahead reads bits, a boolean or a header"
    pure ty

/-- The type of an lvalue; its root is writable (validator,
`type_of_lvalue`). -/
def checkLValue (c : Ctx) (path : String) : LValue → Chk Ty
  | .var x => do
    let d ← resolveVar c x (dot path "var")
    ensure (writable d) .lvalueReadonly (dot path "var") s!"'{x}' cannot be written"
    pure d.type
  | .member base f => do
    let bt ← checkLValue c (dot path "member.base") base
    checkField c.index bt f (dot path "member")
  | .index base i => do
    let bt ← checkLValue c (dot path "index.base") base
    let _ ← expect bt isStack "a stack" (dot path "index.base")
    let it ← checkExpr c (dot path "index.index") i
    let _ ← expect it isBits "bits" (dot path "index.index")
    match bt with
    | .stack h _ => pure (.header h)
    | _ => fail .typeMismatch path "expected a stack"
  | .next _ => fail .nextOnlyExtract path "stack.next is only the target of an extract"

/-- Arguments against params, then the aliasing rule (validator,
`check_args`). -/
def checkArgs (c : Ctx) (args : List Arg) (params : List Param) (path : String) : Chk Unit := do
  ensure (args.length == params.length) .argCount path
    s!"expected {params.length} arguments, got {args.length}"
  each (args.zip params) fun i (a, q) => do
    let apath := dot path s!"args[{i}]"
    match isOut q.direction, a with
    | true, .lvalue lv => do
      let t ← checkLValue c (dot apath "lvalue") lv
      ensure (decide (t = q.type)) .argType apath s!"argument does not have the type of '{q.name}'"
    | false, .expr e => do
      let t ← checkExpr c (dot apath "expr") e
      ensure (decide (t = q.type)) .argType apath s!"argument does not have the type of '{q.name}'"
    | true, .expr _ => fail .argDirection apath s!"'{q.name}' is written back; pass an lvalue"
    | false, .lvalue _ => fail .argDirection apath s!"'{q.name}' is an input; pass an expression"
  ensure (noAlias args) .callAlias path "an argument may alias an earlier out argument"

/-- The optional `hit` target of an apply: a boolean lvalue. -/
def checkHit (c : Ctx) (path : String) : Option LValue → Chk Unit
  | some lv => do
    let ht ← checkLValue c path lv
    let _ ← expect ht isBoolean "boolean" path
  | none => pure ()

/-- An extern call's result against the method's return type. -/
def checkResult (c : Ctx) (path : String) : Option Ty → Option LValue → Chk Unit
  | none, none => pure ()
  | some rt, some lv => do
    let t ← checkLValue c (dot path "result") lv
    ensure (decide (t = rt)) .externResult (dot path "result") "result does not have the method's return type"
  | some _, none => fail .externResult path "the method returns a value; result is unset"
  | none, some _ => fail .externResult (dot path "result") "the method returns nothing"

/-- An extract target: a header lvalue, or `stack.next`, which is allowed
nowhere else (validator, `check_extract`). -/
def checkExtractTarget (c : Ctx) (path : String) : LValue → Chk Unit
  | .next st => do
    let t ← checkLValue c (dot path "next.stack") st
    let _ ← expect t isStack "a stack" (dot path "next.stack")
  | lv => do
    let t ← checkLValue c path lv
    let _ ← expect t isHeader "a header" path

-- ---------------------------------------------------------------------------
-- Statements
-- ---------------------------------------------------------------------------

/-- Whether a statement may appear in a block of `kind` (proto, "Where
each statement may appear"). -/
def allowed (kind : BlockKind) : Stmt → Bool
  | .assign .. | .conditional .. | .callBlock .. | .callExtern .. | .setValid _
  | .setInvalid _ | .push .. | .pop .. => true
  | .apply .. | .callAction .. => kind == .control
  | .extract _ | .advance _ | .verify .. => kind == .parser
  | .emit _ => kind == .deparser

mutual
/-- Every statement's check (validator, `check_stmt`). -/
def checkStmt (c : Ctx) (path : String) : Stmt → Chk Unit
  | s@(.assign target value) => do
    ensure (allowed c.kind s) .blockKindStmt path "assign is not allowed here"
    let tt ← checkLValue c (dot path "assign.target") target
    let vt ← checkExpr c (dot path "assign.value") value
    ensure (decide (tt = vt)) .typeMismatch (dot path "assign") "cannot assign a value of another type"
  | s@(.conditional cnd yes no) => do
    ensure (allowed c.kind s) .blockKindStmt path "conditional is not allowed here"
    let ct ← checkExpr c (dot path "conditional.condition") cnd
    let _ ← expect ct isBoolean "boolean" (dot path "conditional.condition")
    checkStmts c (dot path "conditional.then") 0 yes
    checkStmts c (dot path "conditional.otherwise") 0 no
  | s@(.apply t hit) => do
    ensure (allowed c.kind s) .blockKindStmt path "apply is not allowed here"
    ensure c.action.isNone .blockKindStmt (dot path "apply") "apply is not allowed inside an action"
    let _ ← resolveLocal c c.scope.tables[t]? (·.tables.contains t) t "table" (dot path "apply.table")
    checkHit c (dot path "apply.hit") hit
  | s@(.callAction a args) => do
    ensure (allowed c.kind s) .blockKindStmt path "call_action is not allowed here"
    let act ← resolveLocal c c.scope.actions[a]? (·.actions.contains a) a "action"
      (dot path "call_action.action")
    checkArgs c args act.params (dot path "call_action")
  | s@(.callBlock b args) => do
    ensure (allowed c.kind s) .blockKindStmt path "call_block is not allowed here"
    ensure c.action.isNone .blockKindStmt (dot path "call_block")
      "call_block is not allowed inside an action"
    let blk ← resolve c.index c.index.blocks[b]? b "block" (dot path "call_block.block")
    ensure (blk.kind == c.kind) .callKind (dot path "call_block.block")
      "a block may only call a block of its own kind"
    checkArgs c args blk.params (dot path "call_block")
  | s@(.callExtern inst m args result) => do
    ensure (allowed c.kind s) .blockKindStmt path "call_extern is not allowed here"
    let i ← resolve c.index c.index.externInstances[inst]? inst "extern instance"
      (dot path "call_extern.instance")
    let et ← resolve c.index c.index.externTypes[i.externType]? i.externType "extern type"
      (dot path "call_extern.instance")
    let meth ← need (et.methods.find? (·.name == m)) .refUnresolved (dot path "call_extern.method")
      s!"extern {et.name} has no method '{m}'"
    checkArgs c args meth.params (dot path "call_extern")
    checkResult c (dot path "call_extern") meth.returns result
  | s@(.setValid lv) => do
    ensure (allowed c.kind s) .blockKindStmt path "set_valid is not allowed here"
    let t ← checkLValue c (dot path "set_valid.header") lv
    let _ ← expect t isHeader "a header" (dot path "set_valid.header")
  | s@(.setInvalid lv) => do
    ensure (allowed c.kind s) .blockKindStmt path "set_invalid is not allowed here"
    let t ← checkLValue c (dot path "set_invalid.header") lv
    let _ ← expect t isHeader "a header" (dot path "set_invalid.header")
  | s@(.push lv count) => do
    ensure (allowed c.kind s) .blockKindStmt path "push is not allowed here"
    let t ← checkLValue c (dot path "push.stack") lv
    let _ ← expect t isStack "a stack" (dot path "push.stack")
    ensure (0 < count) .stackCount (dot path "push.count") "count must be at least 1"
  | s@(.pop lv count) => do
    ensure (allowed c.kind s) .blockKindStmt path "pop is not allowed here"
    let t ← checkLValue c (dot path "pop.stack") lv
    let _ ← expect t isStack "a stack" (dot path "pop.stack")
    ensure (0 < count) .stackCount (dot path "pop.count") "count must be at least 1"
  | s@(.extract target) => do
    ensure (allowed c.kind s) .blockKindStmt path "extract is not allowed here"
    checkExtractTarget c (dot path "extract.target") target
  | s@(.advance e) => do
    ensure (allowed c.kind s) .blockKindStmt path "advance is not allowed here"
    let t ← checkExpr c (dot path "advance.bits") e
    let _ ← expect t (fun t => decide (t = .bits 32)) "bit<32>" (dot path "advance.bits")
  | s@(.verify cnd err) => do
    ensure (allowed c.kind s) .blockKindStmt path "verify is not allowed here"
    let t ← checkExpr c (dot path "verify.condition") cnd
    let _ ← expect t isBoolean "boolean" (dot path "verify.condition")
    ensure (c.index.program.errors.contains err) .refUnresolved (dot path "verify.error")
      s!"no error named '{err}'"
  | s@(.emit e) => do
    ensure (allowed c.kind s) .blockKindStmt path "emit is not allowed here"
    let t ← checkExpr c (dot path "emit.value") e
    ensure (emittable c.index (fuel c.index) t) .typeMismatch (dot path "emit.value")
      "emit takes a header, a stack, or a struct of those"

/-- A statement list, each at its position. -/
def checkStmts (c : Ctx) (path : String) : Nat → List Stmt → Chk Unit
  | _, [] => pure ()
  | i, s :: ss => do checkStmt c (at_ path i) s; checkStmts c path (i + 1) ss

end

-- ---------------------------------------------------------------------------
-- Parser states
-- ---------------------------------------------------------------------------

/-- A transition target (validator, `check_target`). -/
def checkTarget (c : Ctx) (path : String) : Target → Chk Unit
  | .state n => do
    let _ ← resolveLocal c c.scope.states[n]? (·.states.contains n) n "state" (dot path "state")
  | .accept | .reject => pure ()

/-- A key set against its key's type (validator, `check_key_set`). -/
def checkKeySet (idx : Index) (key : Ty) (path : String) : KeySet → Chk Unit
  | .exact lit => do
    let t ← checkLiteral idx (dot path "exact") lit
    ensure (decide (t = key)) .selectType (dot path "exact") "the literal does not have the key's type"
  | .masked v m => do
    ensure (isBits key) .selectType path "masked needs a bits key"
    let t ← checkLiteral idx (dot path "masked.value") v
    ensure (decide (t = key)) .selectType (dot path "masked.value") "the literal does not have the key's type"
    let t ← checkLiteral idx (dot path "masked.mask") m
    ensure (decide (t = key)) .selectType (dot path "masked.mask") "the literal does not have the key's type"
  | .range lo hi => do
    ensure (isBits key) .selectType path "range needs a bits key"
    let t ← checkLiteral idx (dot path "range.lo") lo
    ensure (decide (t = key)) .selectType (dot path "range.lo") "the literal does not have the key's type"
    let t ← checkLiteral idx (dot path "range.hi") hi
    ensure (decide (t = key)) .selectType (dot path "range.hi") "the literal does not have the key's type"
  | .dontCare => pure ()

/-- The select keys' types, each selectable. -/
def checkSelectKeys (c : Ctx) (path : String) : Nat → List Expr → Chk (List Ty)
  | _, [] => pure []
  | i, e :: es => do
    let t ← checkExpr c (at_ (dot path "keys") i) e
    ensure (selectable t) .selectType (at_ (dot path "keys") i) "select key must be a scalar"
    pure (t :: (← checkSelectKeys c path (i + 1) es))

/-- A parser state: its body, then its transition (validator,
`check_state`, `check_select`). -/
def checkState (c : Ctx) (path : String) (s : State) : Chk Unit := do
  checkStmts c (dot path "body") 0 s.body
  let tpath := dot path "transition"
  match s.transition with
  | .direct t => checkTarget c (dot tpath "direct") t
  | .select keys cases => do
    let spath := dot tpath "select"
    ensure (!keys.isEmpty) .selectArity spath "select has no keys"
    let tys ← checkSelectKeys c spath 0 keys
    each cases fun i cs => do
      let cpath := at_ (dot spath "cases") i
      ensure (cs.sets.length == keys.length) .selectArity (dot cpath "sets")
        s!"case has {cs.sets.length} sets for {keys.length} keys"
      each (tys.zip cs.sets) fun j (t, ks) => checkKeySet c.index t (at_ (dot cpath "sets") j) ks
      checkTarget c (dot cpath "target") cs.target

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

/-- An action call a table makes: default action or entry (validator,
`check_action_call`). -/
def checkCall (c : Ctx) (t : Table) (path : String) (call : ActionCall) : Chk Unit := do
  let act ← resolveLocal c c.scope.actions[call.action]? (·.actions.contains call.action)
    call.action "action" (dot path "action")
  ensure (t.actions.contains call.action) .tableActions (dot path "action")
    s!"action '{call.action}' is not in the table's action list"
  checkLiteralArgs c.index call.args act.params (dot path "args") .actionArgs

/-- A key's name, when it has one, is not taken yet. -/
def checkKeyName (seen : List String) (path : String) (k : Key) : Chk Unit :=
  match keyName k with
  | some n => ensure (!seen.contains n) .keyName path s!"key name '{n}' used twice"
  | none => pure ()

/-- A key's type and name, keys in order; the widths (validator,
`check_keys`). -/
def checkKeys (c : Ctx) (path : String) (seen : List String) : Nat → List Key → Chk (List Nat)
  | _, [] => pure []
  | i, k :: ks => do
    let kpath := at_ (dot path "keys") i
    checkKeyName seen (dot kpath "name") k
    let t ← checkExpr c (dot kpath "expr") k.expr
    match t with
    | .bits w => pure (w :: (← checkKeys c path ((keyName k).toList ++ seen) (i + 1) ks))
    | _ => fail .keyType kpath "a table key must be bits"

/-- A key value against its key and width (validator, `key_pattern`). -/
def checkKeyValue (k : Key) (w : Nat) (path : String) : KeyValue → Chk Pattern
  | .exact v => do
    ensure (k.matchKind == .exact) .entryShape path "the key value has the wrong kind"
    ensure (v < 2 ^ w) .entryRange (dot path "exact") s!"value {v} does not fit in bit<{w}>"
    pure (.exact v)
  | .lpm v p => do
    ensure (k.matchKind == .lpm) .entryShape path "the key value has the wrong kind"
    ensure (v < 2 ^ w) .entryRange (dot path "lpm.value") s!"value {v} does not fit in bit<{w}>"
    ensure (p ≤ w) .entryRange (dot path "lpm.prefix_len") s!"prefix length {p} exceeds bit<{w}>"
    ensure (v &&& ((2 ^ w - 1) ^^^ Pattern.lpmMask p w) == 0) .entryRange (dot path "lpm.value")
      "lpm value has bits below its prefix"
    pure (.lpm v p w)
  | .ternary v m => do
    ensure (k.matchKind == .ternary) .entryShape path "the key value has the wrong kind"
    ensure (v < 2 ^ w) .entryRange (dot path "ternary.value") s!"value {v} does not fit in bit<{w}>"
    ensure (m < 2 ^ w) .entryRange (dot path "ternary.mask") s!"mask {m} does not fit in bit<{w}>"
    ensure (v &&& ((2 ^ w - 1) ^^^ m) == 0) .entryRange (dot path "ternary.value")
      "ternary value has bits outside its mask"
    pure (.ternary v m)

/-- One const entry (validator, `check_entry`). -/
def checkEntry (c : Ctx) (t : Table) (ws : List Nat) (path : String) (e : Entry) : Chk Unit := do
  checkCall c t (dot path "action") e.action
  ensure (ternary t || e.priority == 0) .entryPriority (dot path "priority")
    "only a table with a ternary key has priorities"
  ensure (e.keys.length == t.keys.length) .entryShape (dot path "keys")
    s!"entry has {e.keys.length} values for {t.keys.length} keys"
  each ((t.keys.zip ws).zip e.keys) fun i ((k, w), v) => do
    let _ ← checkKeyValue k w (at_ (dot path "keys") i) v

/-- A table's action list: no action twice, each an action of this block
with directionless params (validator, `check_table`). -/
def checkTableActions (c : Ctx) (path : String) (seen : List String) :
    Nat → List String → Chk Unit
  | _, [] => pure ()
  | i, a :: as => do
    ensure (!seen.contains a) .tableActions (at_ path i) s!"action '{a}' listed twice"
    let act ← resolveLocal c c.scope.actions[a]? (·.actions.contains a) a "action" (at_ path i)
    ensure (act.params.all (·.direction == .none)) .paramDirection (at_ path i)
      s!"action '{a}' is invoked by a table, so its params must be directionless"
    checkTableActions c path (seen ++ [a]) (i + 1) as

/-- A table's default action, when it has one. -/
def checkDefault (c : Ctx) (t : Table) (path : String) : Option ActionCall → Chk Unit
  | some call => checkCall c t path call
  | none => pure ()

/-- The code of a tie: overlap in a ternary table, duplicate otherwise. -/
def tieCode (t : Table) : Code := if ternary t then .entryPriority else .entryDuplicate

/-- A table (validator, `check_table`). -/
def checkTable (c : Ctx) (path : String) (t : Table) : Chk Unit := do
  let ws ← checkKeys c path [] 0 t.keys
  let kinds := t.keys.map (·.matchKind)
  ensure ((kinds.filter (· == .lpm)).length ≤ 1) .tableLpmCount (dot path "keys")
    "a table has at most one lpm key"
  ensure (!(kinds.contains .lpm && kinds.contains .ternary)) .tableKeyMix (dot path "keys")
    "a table with an lpm key has no ternary key"
  ensure (!t.actions.isEmpty) .tableActions (dot path "actions") "table lists no actions"
  checkTableActions c (dot path "actions") [] 0 t.actions
  checkDefault c t (dot path "default_action") t.defaultAction
  each t.constEntries fun i e => checkEntry c t ws (at_ (dot path "const_entries") i) e
  ensure (entriesDistinct (ternary t) (entryPatterns t ws)) (tieCode t) (dot path "const_entries")
    "two const entries tie"

-- ---------------------------------------------------------------------------
-- Blocks
-- ---------------------------------------------------------------------------

/-- Params' directions and types (validator, `check_params`). -/
def checkParams (idx : Index) (params : List Param) (ok : Direction → Bool) (path what : String) :
    Chk Unit :=
  each params fun i q => do
    ensure (ok q.direction) .paramDirection (at_ path i) s!"{what} param '{q.name}' has a direction it may not"
    checkType idx (dot (at_ path i) "type") q.type

/-- An action (validator, `check_action`). -/
def checkAction (c : Ctx) (path : String) (a : Action) : Chk Unit := do
  ensure (a.name != "NoAction" || (a.body.isEmpty && a.params.isEmpty)) .noActionReserved path
    "NoAction must have no body and no parameters"
  checkParams c.index a.params (fun _ => true) (dot path "params") "action"
  checkStmts { c with action := some a } (dot path "body") 0 a.body

/-- A block's shape by kind (validator, `check_block`). -/
def checkShape (sc : BlockScope) (b : Block) (path : String) : Chk Unit :=
  match b.kind with
  | .parser => do
    ensure (!b.states.isEmpty) .blockKindShape path "a parser has at least one state"
    ensure (sc.states.contains b.startState) .parserStartState (dot path "start_state")
      s!"start_state '{b.startState}' is not a state of this parser"
    ensure b.body.isEmpty .blockKindShape (dot path "body") "a parser has states, not a body"
    ensure b.actions.isEmpty .blockKindShape (dot path "actions") "a parser has no actions"
    ensure b.tables.isEmpty .blockKindShape (dot path "tables") "a parser has no tables"
  | .control | .deparser => do
    ensure b.states.isEmpty .blockKindShape (dot path "states") "only a parser has states"
    ensure b.startState.isEmpty .blockKindShape (dot path "start_state")
      "only a parser has a start state"

/-- A block (validator, `check_block`). -/
def checkBlock (idx : Index) (path : String) (b : Block) : Chk Unit := do
  checkParams idx b.params (· != .none) (dot path "params") "block"
  each b.locals fun i v => checkType idx (dot (at_ (dot path "locals") i) "type") v.type
  let sc ← need idx.scopes[b.name]? .refUnresolved path s!"block '{b.name}' has no scope"
  checkShape sc b path
  let c := Ctx.ofBlock idx sc b
  each b.actions fun i a => checkAction c (at_ (dot path "actions") i) a
  ensure (acyclic (b.actions.map (·.name))
      (fun n => ((b.actions.find? (·.name == n)).map actionCallees).getD [])) .callCycle
    (dot path "actions") "action calls form a cycle"
  each b.tables fun i t => checkTable c (at_ (dot path "tables") i) t
  each b.states fun i s => checkState c (at_ (dot path "states") i) s
  checkStmts c (dot path "body") 0 b.body

-- ---------------------------------------------------------------------------
-- The program
-- ---------------------------------------------------------------------------

/-- An `Index.build` error as the validator reports it: `NAME_EMPTY` for an
empty name, else `NAME_DUPLICATE`. -/
def indexDiagnostic (message : String) : Diagnostic :=
  if (message.splitOn "empty").length > 1 || (message.splitOn "''").length > 1 then
    ⟨.nameEmpty, "", message⟩
  else ⟨.nameDuplicate, "", message⟩

/-- An extern type (validator, `check_extern_types`). -/
def checkExternType (idx : Index) (path : String) (et : ExternType) : Chk Unit := do
  checkNames (et.constructorParams.map (·.name)) (dot path "constructor_params") "param"
  checkParams idx et.constructorParams (· == .in) (dot path "constructor_params") "constructor"
  checkNames (et.methods.map (·.name)) (dot path "methods") "method"
  each et.methods fun j m => do
    let mpath := at_ (dot path "methods") j
    checkNames (m.params.map (·.name)) (dot mpath "params") "param"
    checkParams idx m.params (· != .none) (dot mpath "params") "method"
    match m.returns with
    | some t => checkType idx (dot mpath "returns") t
    | none => pure ()

/-- The exports: roles distinct, each block resolved, with the signature
of its kind (validator, `check_exports`). -/
def checkExports (p : Program) (idx : Index) (seen : List String) : Nat → List Export → Chk Unit
  | _, [] => pure ()
  | i, e :: es => do
    let path := at_ "exports" i
    ensure (!seen.contains e.role) .exportDuplicate path s!"role '{e.role}' exported twice"
    let b ← resolve idx idx.blocks[e.block]? e.block "block" (dot path "block")
    ensure (signatureOk p b) .exportSignature path s!"'{b.name}' lacks the signature of its kind"
    checkExports p idx (seen ++ [e.role]) (i + 1) es

/-- Check the program; its index, or the first problem. -/
def check (p : Program) : Except Diagnostic Index := do
  let idx ← (Index.build p).mapError indexDiagnostic
  ensure (coreErrors.isPrefixOf p.errors) .errorList "errors"
    s!"errors must begin with {", ".intercalate coreErrors}"
  each p.headerTypes fun i h => do
    let path := at_ "header_types" i
    checkNames (h.fields.map (·.name)) (dot path "fields") "field"
    each h.fields fun j f => do
      let fpath := dot (at_ (dot path "fields") j) "type"
      checkTypeRefs idx fpath f.type
      ensure (scalarField f.type) .typeInvalid fpath "header fields are bits or boolean"
  each p.structTypes fun i s => do
    let path := at_ "struct_types" i
    checkNames (s.fields.map (·.name)) (dot path "fields") "field"
    each s.fields fun j f => checkTypeRefs idx (dot (at_ (dot path "fields") j) "type") f.type
  each p.enumTypes fun i e => do
    let path := at_ "enum_types" i
    checkNames e.members (dot path "members") "enum member"
    ensure (!e.members.isEmpty) .typeInvalid path "enum has no members"
  each p.structTypes fun i s =>
    ensure (tyDeep idx (fuel idx) (.struct s.name)) .typeInvalid (at_ "struct_types" i)
      "struct contains itself"
  let _ ← resolve idx idx.structTypes[p.headers]? p.headers "struct type" "headers"
  let _ ← resolve idx idx.structTypes[p.metadata]? p.metadata "struct type" "metadata"
  each p.externTypes fun i et => checkExternType idx (at_ "extern_types" i) et
  each p.externInstances fun i inst => do
    let path := at_ "extern_instances" i
    let et ← resolve idx idx.externTypes[inst.externType]? inst.externType "extern type"
      (dot path "extern_type")
    checkLiteralArgs idx inst.args et.constructorParams (dot path "args") .externArgs
  each p.blocks fun i b => checkBlock idx (at_ "blocks" i) b
  checkExports p idx [] 0 p.exports
  ensure (acyclic (p.blocks.map (·.name))
      (fun n => ((p.blocks.find? (·.name == n)).map blockCallees).getD [])) .callCycle "blocks"
    "block calls form a cycle"
  pure idx

end P4bloIR.Validity
