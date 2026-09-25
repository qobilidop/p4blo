import P4bloIR.Validity.IndexLaws
import P4bloIR.Externs

/-!
# Whole-program validity, declaratively

The rules the Python validator enforces (`impl/python/p4blo/validator.py`),
stated as relations over the program and the index `Index.build` makes of
it. `Validity.Check` decides them; `P4bloIR.Progress` uses them.

The rules come in the validator's categories. Names are the index's
(`Index.build`) plus the small namespaces it does not cover. Types are
well formed when their names resolve and the zero-value recursion of
`Value.zero` cannot run out (`tyDeep`), which is how a struct that contains
itself is excluded. Expressions, lvalues, arguments and statements are
typed in a context (`Ctx`): a block's scope, its kind, and the action whose
body it is, if any. Statement placement is part of each statement's rule.
Side conditions that no typing judgment needs, such as the aliasing rule,
the acyclic call graph and the table-entry tie rules, are boolean
functions, and `Valid` requires them to hold.

`ValueHas` is the run-time counterpart of a type: what the progress proof
maintains about every variable.
-/

namespace P4bloIR.Validity

open Std (HashMap)

-- ---------------------------------------------------------------------------
-- Equality of the IR's enums
-- ---------------------------------------------------------------------------

instance : LawfulBEq Direction where
  eq_of_beq {a b} := by cases a <;> cases b <;> decide
  rfl {a} := by cases a <;> decide

instance : LawfulBEq BlockKind where
  eq_of_beq {a b} := by cases a <;> cases b <;> decide
  rfl {a} := by cases a <;> decide

instance : LawfulBEq MatchKind where
  eq_of_beq {a b} := by cases a <;> cases b <;> decide
  rfl {a} := by cases a <;> decide

-- ---------------------------------------------------------------------------
-- Types
-- ---------------------------------------------------------------------------

/-- The nesting bound `Value.zero` and `widthOf` use. -/
def fuel (idx : Index) : Nat := idx.headerTypes.size + idx.structTypes.size + 2

/-- A header field's type: bits of positive width, or boolean. -/
def scalarField : Ty → Bool
  | .bits n => 0 < n
  | .boolean => true
  | _ => false

/-- A well-formed type whose zero value exists within `fuel` levels of
nesting: every name resolves, widths and stack sizes are positive, an enum
has a member, a header's fields are scalar. It follows the recursion of
`Value.zeroWith`, so a struct that contains itself runs out of fuel. -/
def tyDeep (idx : Index) : Nat → Ty → Bool
  | 0, _ => false
  | _ + 1, .bits n => 0 < n
  | _ + 1, .boolean => true
  | _ + 1, .error => true
  | _ + 1, .enumType n => match idx.enumTypes[n]? with
    | some e => !e.members.isEmpty
    | none => false
  | f + 1, .header n => match idx.headerTypes[n]? with
    | some h => h.fields.all fun fl => scalarField fl.type && tyDeep idx f fl.type
    | none => false
  | f + 1, .struct n => match idx.structTypes[n]? with
    | some s => s.fields.all fun fl => tyDeep idx f fl.type
    | none => false
  | f + 1, .stack h size => 0 < size && tyDeep idx f (.header h)

/-- A type is well formed when `tyDeep` holds at the index's own bound. -/
def TyOk (idx : Index) (ty : Ty) : Prop := tyDeep idx (fuel idx) ty = true

instance : Decidable (TyOk idx ty) := by unfold TyOk; infer_instance

/-- The type of field `f` of a header or struct type. -/
def fieldType? (idx : Index) : Ty → String → Option Ty
  | .header n, f => (idx.headerTypes[n]?.bind fun h => h.fields.find? (·.name == f)).map (·.type)
  | .struct n, f => (idx.structTypes[n]?.bind fun s => s.fields.find? (·.name == f)).map (·.type)
  | _, _ => none

/-- What emit accepts: a header, a stack, or a struct of those. -/
def emittable (idx : Index) : Nat → Ty → Bool
  | 0, _ => false
  | _ + 1, .header _ => true
  | _ + 1, .stack _ _ => true
  | f + 1, .struct n => match idx.structTypes[n]? with
    | some s => s.fields.all fun fl => emittable idx f fl.type
    | none => false
  | _ + 1, _ => false

-- ---------------------------------------------------------------------------
-- Values
-- ---------------------------------------------------------------------------

mutual
/-- A run-time value of a type: the kind and width agree, a header or
struct carries its declaration's name and one value per declared field,
and a stack has exactly its declared size. Header validity, enum members
and a stack's next index are unconstrained. -/
def ValueHas (idx : Index) : Value → Ty → Prop
  | .bits b, .bits n => b.width = n
  | .bool _, .boolean => True
  | .enum t _, .enumType n => t = n
  | .error _, .error => True
  | .header t _ fs, .header n =>
    t = n ∧ ∃ h, idx.headerTypes[n]? = some h ∧ FieldsHave idx h.fields fs
  | .struct t fs, .struct n =>
    t = n ∧ ∃ s, idx.structTypes[n]? = some s ∧ FieldsHave idx s.fields fs
  | .stack t es _, .stack h size => t = h ∧ es.length = size ∧ ElemsHave idx h es
  | _, _ => False

/-- One value per field, in order, of the field's type. -/
def FieldsHave (idx : Index) : List Field → List Value → Prop
  | [], [] => True
  | f :: fs, v :: vs => ValueHas idx v f.type ∧ FieldsHave idx fs vs
  | _, _ => False

/-- Every element a header of type `h`. -/
def ElemsHave (idx : Index) (h : String) : List Value → Prop
  | [] => True
  | v :: vs => ValueHas idx v (.header h) ∧ ElemsHave idx h vs
end

-- ---------------------------------------------------------------------------
-- Contexts
-- ---------------------------------------------------------------------------

/-- Where a statement or expression stands: a block's scope and kind, and
the action whose body it is. -/
structure Ctx where
  index : Index
  scope : BlockScope
  kind : BlockKind
  action : Option Action := none

/-- The declaration a name denotes here: an action param first, then the
block's params and locals. -/
def Ctx.var? (c : Ctx) (name : String) : Option VarDecl :=
  match c.action.bind fun a => a.params.find? (·.name == name) with
  | some p => some (.param p)
  | none => c.scope.vars[name]?

/-- Locals, `out` and `inout` params may be written; `in` and
directionless params may not. -/
def writable : VarDecl → Bool
  | .var _ => true
  | .param p => p.direction == .out || p.direction == .inout

-- ---------------------------------------------------------------------------
-- Literals and expressions
-- ---------------------------------------------------------------------------

/-- A literal of a type: a bits value that fits a positive width, a member
of a declared enum, or a declared error. -/
inductive LitTyped (idx : Index) : Literal → Ty → Prop
  | bits : 0 < w → v < 2 ^ w → LitTyped idx (.bits w v) (.bits w)
  | boolean : LitTyped idx (.boolean b) .boolean
  | enumMember : idx.enumTypes[t]? = some e → m ∈ e.members →
      LitTyped idx (.enumMember t m) (.enumType t)
  | error : n ∈ idx.program.errors → LitTyped idx (.error n) .error

/-- The result type of a binary operator (proto, `BinaryOp`). -/
def binaryType : BinaryOp → Ty → Ty → Option Ty
  | .add, .bits n, .bits m | .sub, .bits n, .bits m | .mul, .bits n, .bits m
  | .addSat, .bits n, .bits m | .subSat, .bits n, .bits m | .bitAnd, .bits n, .bits m
  | .bitOr, .bits n, .bits m | .bitXor, .bits n, .bits m =>
    if n = m then some (.bits n) else none
  | .shl, .bits n, .bits _ | .shr, .bits n, .bits _ => some (.bits n)
  | .concat, .bits n, .bits m => some (.bits (n + m))
  | .eq, a, b | .ne, a, b => if a = b then some .boolean else none
  | .lt, .bits n, .bits m | .le, .bits n, .bits m | .gt, .bits n, .bits m
  | .ge, .bits n, .bits m => if n = m then some .boolean else none
  | .and, .boolean, .boolean | .or, .boolean, .boolean => some .boolean
  | _, _, _ => none

/-- The casts the IR allows: bits to bits, boolean to `bit<1>`, `bit<1>` to
boolean. -/
def castOk : Ty → Ty → Bool
  | .bits _, .bits _ => true
  | .boolean, .bits 1 => true
  | .bits 1, .boolean => true
  | _, _ => false

/-- Expression typing (validator, `type_of`). -/
inductive ExprTyped (c : Ctx) : Expr → Ty → Prop
  | literal : LitTyped c.index lit t → ExprTyped c (.literal lit) t
  | var : c.var? x = some d → ExprTyped c (.var x) d.type
  | member : ExprTyped c base bt → fieldType? c.index bt f = some t →
      ExprTyped c (.member base f) t
  | index : ExprTyped c base (.stack h n) → ExprTyped c i (.bits w) →
      ExprTyped c (.index base i) (.header h)
  | lastIndex : c.kind = .parser → ExprTyped c s (.stack h n) →
      ExprTyped c (.lastIndex s) (.bits 32)
  | not : ExprTyped c e .boolean → ExprTyped c (.unary .not e) .boolean
  | complement : ExprTyped c e (.bits w) → ExprTyped c (.unary .complement e) (.bits w)
  | negate : ExprTyped c e (.bits w) → ExprTyped c (.unary .negate e) (.bits w)
  | binary : ExprTyped c l a → ExprTyped c r b → binaryType op a b = some t →
      ExprTyped c (.binary op l r) t
  | cast : ExprTyped c e a → TyOk c.index to → castOk a to = true →
      ExprTyped c (.cast to e) to
  | slice : ExprTyped c e (.bits w) → lo ≤ hi → hi < w →
      ExprTyped c (.slice e hi lo) (.bits (hi - lo + 1))
  | isValid : ExprTyped c h (.header n) → ExprTyped c (.isValid h) .boolean
  | mux : ExprTyped c cnd .boolean → ExprTyped c a t → ExprTyped c b t →
      ExprTyped c (.mux cnd a b) t
  | lookahead : c.kind = .parser → TyOk c.index ty →
      (ty matches .bits _ | .boolean | .header _) → ExprTyped c (.lookahead ty) ty

/-- Lvalue typing (validator, `type_of_lvalue`): the root is writable, and
`stack.next` is no general lvalue. -/
inductive LValueTyped (c : Ctx) : LValue → Ty → Prop
  | var : c.var? x = some d → writable d = true → LValueTyped c (.var x) d.type
  | member : LValueTyped c base bt → fieldType? c.index bt f = some t →
      LValueTyped c (.member base f) t
  | index : LValueTyped c base (.stack h n) → ExprTyped c i (.bits w) →
      LValueTyped c (.index base i) (.header h)

-- ---------------------------------------------------------------------------
-- Calls
-- ---------------------------------------------------------------------------

/-- Whether a parameter is written back: `out` and `inout`. -/
def isOut : Direction → Bool
  | .out | .inout => true
  | _ => false

/-- One argument against its parameter: an expression of the parameter's
type for `in` and directionless, a writable lvalue for `out` and `inout`. -/
inductive ArgTyped (c : Ctx) : Arg → Param → Prop
  | input : isOut p.direction = false → ExprTyped c e p.type → ArgTyped c (.expr e) p
  | output : isOut p.direction = true → LValueTyped c lv p.type → ArgTyped c (.lvalue lv) p

/-- Arguments against parameters, one each, in order. -/
inductive ArgsTyped (c : Ctx) : List Arg → List Param → Prop
  | nil : ArgsTyped c [] []
  | cons : ArgTyped c a p → ArgsTyped c as ps → ArgsTyped c (a :: as) (p :: ps)

/-- One step of the static storage path an lvalue names. -/
inductive Step
  | name (s : String)
  | index (n : Nat)
  | unknown
  deriving BEq, DecidableEq, Repr

/-- The storage path of an lvalue (validator, `lvalue_access`): the
variable, then each field, and each index when it is a bits literal. -/
def access : LValue → List Step
  | .var x => [.name x]
  | .member b f => access b ++ [.name f]
  | .index b i => access b ++ [match i with | .literal (.bits _ v) => .index v | _ => .unknown]
  | .next s => access s ++ [.unknown]

/-- Two paths may alias when they agree wherever both are known (validator,
`may_alias`). -/
def mayAlias : List Step → List Step → Bool
  | x :: xs, y :: ys =>
    (x == .unknown || y == .unknown || x == y) && mayAlias xs ys
  | _, _ => true

/-- No two lvalue arguments of one call may alias (validator, `check_args`). -/
def noAlias (args : List Arg) : Bool :=
  let paths := args.filterMap fun | .lvalue lv => some (access lv) | .expr _ => none
  go [] paths
where
  go (seen : List (List Step)) : List (List Step) → Bool
    | [] => true
    | b :: rest => !(seen.any (mayAlias · b)) && go (seen ++ [b]) rest

/-- The result of an extern call against the method's return type. -/
inductive ResultTyped (c : Ctx) : Option Ty → Option LValue → Prop
  | none : ResultTyped c none none
  | some : LValueTyped c lv t → ResultTyped c (some t) (some lv)

-- ---------------------------------------------------------------------------
-- Statements
-- ---------------------------------------------------------------------------

mutual
/-- Statement typing, placement included (validator, `check_stmt`). -/
inductive StmtTyped (c : Ctx) : Stmt → Prop
  | assign : LValueTyped c t ty → ExprTyped c v ty → StmtTyped c (.assign t v)
  | conditional : ExprTyped c cnd .boolean → StmtsTyped c yes → StmtsTyped c no →
      StmtTyped c (.conditional cnd yes no)
  | apply : c.kind = .control → c.action = none → c.scope.tables[t]? = some tbl →
      (∀ lv, hit = some lv → LValueTyped c lv .boolean) → StmtTyped c (.apply t hit)
  | callAction : c.kind = .control → c.scope.actions[a]? = some act →
      ArgsTyped c args act.params → noAlias args = true → StmtTyped c (.callAction a args)
  | callBlock : c.action = none → c.index.blocks[b]? = some blk → blk.kind = c.kind →
      ArgsTyped c args blk.params → noAlias args = true → StmtTyped c (.callBlock b args)
  | callExtern : c.index.externInstances[inst]? = some i →
      c.index.externTypes[i.externType]? = some et →
      et.methods.find? (·.name == m) = some meth →
      ArgsTyped c args meth.params → noAlias args = true →
      ResultTyped c meth.returns result → StmtTyped c (.callExtern inst m args result)
  | setValid : LValueTyped c lv (.header n) → StmtTyped c (.setValid lv)
  | setInvalid : LValueTyped c lv (.header n) → StmtTyped c (.setInvalid lv)
  | push : LValueTyped c lv (.stack h size) → 0 < count → StmtTyped c (.push lv count)
  | pop : LValueTyped c lv (.stack h size) → 0 < count → StmtTyped c (.pop lv count)
  | extractNext : c.kind = .parser → LValueTyped c s (.stack h size) →
      StmtTyped c (.extract (.next s))
  | extract : c.kind = .parser → (∀ s, target ≠ .next s) → LValueTyped c target (.header n) →
      StmtTyped c (.extract target)
  | advance : c.kind = .parser → ExprTyped c e (.bits 32) → StmtTyped c (.advance e)
  | verify : c.kind = .parser → ExprTyped c cnd .boolean → err ∈ c.index.program.errors →
      StmtTyped c (.verify cnd err)
  | emit : c.kind = .deparser → ExprTyped c e t → emittable c.index (fuel c.index) t = true →
      StmtTyped c (.emit e)

/-- Every statement of a list typed. -/
inductive StmtsTyped (c : Ctx) : List Stmt → Prop
  | nil : StmtsTyped c []
  | cons : StmtTyped c s → StmtsTyped c ss → StmtsTyped c (s :: ss)
end

-- ---------------------------------------------------------------------------
-- Parser states
-- ---------------------------------------------------------------------------

/-- A transition target: a state of this parser, accept or reject. -/
def TargetOk (c : Ctx) : Target → Prop
  | .state n => c.scope.states[n]? ≠ none
  | .accept | .reject => True

/-- The types a select key may have. -/
def selectable : Ty → Bool
  | .bits _ | .boolean | .enumType _ | .error => true
  | _ => false

/-- A key set against its key's type (validator, `check_key_set`). -/
inductive KeySetTyped (idx : Index) (key : Ty) : KeySet → Prop
  | exact : LitTyped idx lit key → KeySetTyped idx key (.exact lit)
  | masked : (key matches .bits _) → LitTyped idx v key → LitTyped idx m key →
      KeySetTyped idx key (.masked v m)
  | range : (key matches .bits _) → LitTyped idx lo key → LitTyped idx hi key →
      KeySetTyped idx key (.range lo hi)
  | dontCare : KeySetTyped idx key .dontCare

/-- Key sets against key types, one each, in order. -/
inductive KeySetsTyped (idx : Index) : List Ty → List KeySet → Prop
  | nil : KeySetsTyped idx [] []
  | cons : KeySetTyped idx t s → KeySetsTyped idx ts ss → KeySetsTyped idx (t :: ts) (s :: ss)

/-- Select keys and their types, one each, each selectable. -/
inductive SelectKeysTyped (c : Ctx) : List Expr → List Ty → Prop
  | nil : SelectKeysTyped c [] []
  | cons : ExprTyped c e t → selectable t = true → SelectKeysTyped c es ts →
      SelectKeysTyped c (e :: es) (t :: ts)

/-- A transition (validator, `check_state`). -/
inductive TransitionTyped (c : Ctx) : Transition → Prop
  | direct : TargetOk c t → TransitionTyped c (.direct t)
  | select : keys ≠ [] → SelectKeysTyped c keys tys →
      (∀ cs ∈ cases, KeySetsTyped c.index tys cs.sets ∧ TargetOk c cs.target) →
      TransitionTyped c (.select keys cases)

/-- A parser state. -/
def StateTyped (c : Ctx) (s : State) : Prop :=
  StmtsTyped c s.body ∧ TransitionTyped c s.transition

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

/-- Literal arguments against parameters (action data, constructor args). -/
inductive LitArgsTyped (idx : Index) : List Literal → List Param → Prop
  | nil : LitArgsTyped idx [] []
  | cons : LitTyped idx a p.type → LitArgsTyped idx as ps → LitArgsTyped idx (a :: as) (p :: ps)

/-- An action call a table makes: a listed action of this block, with
literal data of its parameters' types. -/
def CallTyped (c : Ctx) (t : Table) (call : ActionCall) : Prop :=
  call.action ∈ t.actions ∧
    ∃ act, c.scope.actions[call.action]? = some act ∧ LitArgsTyped c.index call.args act.params

/-- Table keys and their widths: every key is bits (docs/ir-semantics.md,
"Keys are bits"). -/
inductive KeysTyped (c : Ctx) : List Key → List Nat → Prop
  | nil : KeysTyped c [] []
  | cons : ExprTyped c k.expr (.bits w) → KeysTyped c ks ws → KeysTyped c (k :: ks) (w :: ws)

/-- The name a host uses for a key: `Key.name`, else the dotted path of
the key expression when it is one (`ir.key_name`). -/
def dottedPath : Expr → Option String
  | .var x => some x
  | .member b f => (dottedPath b).map (· ++ "." ++ f)
  | _ => none

def keyName (k : Key) : Option String :=
  if k.name.isEmpty then dottedPath k.expr else some k.name


/-- A key pattern, for the tie rules on const entries (validator,
`KeyPattern`). -/
inductive Pattern
  | exact (value : Nat)
  | lpm (value prefixLen width : Nat)
  | ternary (value mask : Nat)

def Pattern.lpmMask (prefixLen width : Nat) : Nat := (2 ^ prefixLen - 1) <<< (width - prefixLen)

/-- Whether some key value matches both patterns. -/
def Pattern.overlap : Pattern → Pattern → Bool
  | .exact a, .exact b => a == b
  | .lpm av ap aw, .lpm bv bp bw =>
    let m := Pattern.lpmMask ap aw &&& Pattern.lpmMask bp bw
    av &&& m == bv &&& m
  | .ternary av am, .ternary bv bm =>
    let m := am &&& bm
    av &&& m == bv &&& m
  | _, _ => false

/-- Whether two patterns match the same key values. -/
def Pattern.same : Pattern → Pattern → Bool
  | .exact a, .exact b => a == b
  | .lpm av ap aw, .lpm bv bp bw =>
    ap == bp && av &&& Pattern.lpmMask ap aw == bv &&& Pattern.lpmMask bp bw
  | .ternary av am, .ternary bv bm => am == bm && av &&& am == bv &&& bm
  | _, _ => false

/-- A key value against its key and width: the right kind, in range, and
canonical (validator, `key_pattern`). -/
def pattern? (k : Key) (w : Nat) : KeyValue → Option Pattern
  | .exact v => if k.matchKind == .exact && v < 2 ^ w then some (.exact v) else none
  | .lpm v p =>
    if k.matchKind == .lpm && v < 2 ^ w && p ≤ w && v &&& ((2 ^ w - 1) ^^^ Pattern.lpmMask p w) == 0
    then some (.lpm v p w) else none
  | .ternary v m =>
    if k.matchKind == .ternary && v < 2 ^ w && m < 2 ^ w && v &&& ((2 ^ w - 1) ^^^ m) == 0
    then some (.ternary v m) else none

/-- The patterns of an entry, when every key value is well formed. -/
def patterns? (keys : List Key) (ws : List Nat) (vals : List KeyValue) : Option (List Pattern) :=
  if keys.length == vals.length && ws.length == vals.length then
    ((keys.zip ws).zip vals).mapM fun ((k, w), v) => pattern? k w v
  else none

/-- A table has a ternary key. -/
def ternary (t : Table) : Bool := t.keys.any (·.matchKind == .ternary)

/-- Whether two const entries tie: in a ternary table, one priority and
overlapping keys; in any other, the same keys. -/
def ties (ternary : Bool) (a b : Nat × List Pattern) : Bool :=
  if ternary then a.1 == b.1 && (a.2.zip b.2).all fun (x, y) => x.overlap y
  else (a.2.zip b.2).all fun (x, y) => x.same y

/-- No two const entries tie (validator, `check_table`), given each
entry's priority and patterns. -/
def entriesDistinct (ternary : Bool) : List (Nat × List Pattern) → Bool
  | [] => true
  | a :: rest => rest.all (fun b => !ties ternary a b) && entriesDistinct ternary rest

/-- The priority and patterns of every const entry whose key values are
well formed. -/
def entryPatterns (t : Table) (ws : List Nat) : List (Nat × List Pattern) :=
  t.constEntries.filterMap fun e => (patterns? t.keys ws e.keys).map (e.priority, ·)

/-- A const entry (validator, `check_entry`). -/
def EntryTyped (c : Ctx) (t : Table) (ws : List Nat) (e : Entry) : Prop :=
  CallTyped c t e.action ∧ (ternary t = false → e.priority = 0) ∧
    (patterns? t.keys ws e.keys).isSome

/-- A table (validator, `check_table`). -/
structure TableTyped (c : Ctx) (t : Table) : Prop where
  widths : ∃ ws, KeysTyped c t.keys ws ∧
    (∀ e ∈ t.constEntries, EntryTyped c t ws e) ∧
    entriesDistinct (ternary t) (entryPatterns t ws) = true
  keyNames : (t.keys.filterMap keyName).Nodup
  oneLpm : ((t.keys.map (·.matchKind)).filter (· == .lpm)).length ≤ 1
  noMix : (!((t.keys.map (·.matchKind)).contains .lpm &&
    (t.keys.map (·.matchKind)).contains .ternary)) = true
  actions : t.actions ≠ [] ∧ t.actions.Nodup
  actionsExist : ∀ a ∈ t.actions, ∃ act, c.scope.actions[a]? = some act ∧
    ∀ q ∈ act.params, q.direction = .none
  defaultAction : ∀ call, t.defaultAction = some call → CallTyped c t call

-- ---------------------------------------------------------------------------
-- Blocks
-- ---------------------------------------------------------------------------

/-- Names of one small namespace: non-empty and distinct. -/
def NamesOk (names : List String) : Prop := (∀ n ∈ names, n ≠ "") ∧ names.Nodup

instance : Decidable (NamesOk names) := by unfold NamesOk; infer_instance

/-- The callees of `callBlock` statements, through conditionals. -/
def blockCalls : Stmt → List String
  | .callBlock b _ => [b]
  | .conditional _ yes no => yes.flatMap blockCalls ++ no.flatMap blockCalls
  | _ => []

/-- The callees of `callAction` statements, through conditionals. -/
def actionCalls : Stmt → List String
  | .callAction a _ => [a]
  | .conditional _ yes no => yes.flatMap actionCalls ++ no.flatMap actionCalls
  | _ => []

/-- Whether every path from `n` along `edges`, within `nodes`, ends within
`fuel` steps. A cycle never ends. -/
def ends (nodes : List String) (edges : String → List String) : Nat → String → Bool
  | 0, _ => false
  | f + 1, n => (edges n).all fun m => !nodes.contains m || ends nodes edges f m

/-- No cycle among `nodes` (validator, `report_cycles`): a path without a
repeated node has at most `nodes.length` edges. -/
def acyclic (nodes : List String) (edges : String → List String) : Bool :=
  nodes.all (ends nodes edges (nodes.length + 1))

/-- The blocks a block calls. -/
def blockCallees (b : Block) : List String :=
  b.body.flatMap blockCalls ++ b.states.flatMap fun s => s.body.flatMap blockCalls

/-- The actions an action calls. -/
def actionCallees (a : Action) : List String := a.body.flatMap actionCalls

/-- The context of a block's body. -/
def Ctx.ofBlock (idx : Index) (sc : BlockScope) (b : Block) : Ctx :=
  { index := idx, scope := sc, kind := b.kind }

/-- An action (validator, `check_action`). -/
def ActionTyped (c : Ctx) (a : Action) : Prop :=
  (a.name = "NoAction" → a.body = [] ∧ a.params = []) ∧
    (∀ q ∈ a.params, TyOk c.index q.type) ∧
    StmtsTyped { c with action := some a } a.body

/-- A block's shape by kind (validator, `check_block`). -/
def ShapeOk (sc : BlockScope) (b : Block) : Prop :=
  match b.kind with
  | .parser => b.states ≠ [] ∧ sc.states[b.startState]? ≠ none ∧ b.body = [] ∧
      b.actions = [] ∧ b.tables = []
  | .control | .deparser => b.states = [] ∧ b.startState = ""

/-- A block, typed in its scope. -/
structure BlockTyped (idx : Index) (sc : BlockScope) (b : Block) : Prop where
  params : ∀ q ∈ b.params, q.direction ≠ .none ∧ TyOk idx q.type
  locals : ∀ v ∈ b.locals, TyOk idx v.type
  shape : ShapeOk sc b
  actions : ∀ a ∈ b.actions, ActionTyped (Ctx.ofBlock idx sc b) a
  actionsAcyclic : acyclic (b.actions.map (·.name))
    (fun n => ((b.actions.find? (·.name == n)).map actionCallees).getD []) = true
  tables : ∀ t ∈ b.tables, TableTyped (Ctx.ofBlock idx sc b) t
  states : ∀ s ∈ b.states, StateTyped (Ctx.ofBlock idx sc b) s
  body : StmtsTyped (Ctx.ofBlock idx sc b) b.body

-- ---------------------------------------------------------------------------
-- Programs
-- ---------------------------------------------------------------------------

/-- core.p4's errors, in order. -/
def coreErrors : List String :=
  ["NoError", "PacketTooShort", "NoMatch", "StackOutOfBounds", "HeaderTooShort",
   "ParserTimeout", "ParserInvalidArgument"]

/-- The parameters an exported block must have, by kind: its direction and
whether it is the headers (`true`) or the metadata type. -/
def exportSignature : BlockKind → List (Direction × Bool)
  | .parser => [(.out, true), (.inout, false)]
  | .control => [(.inout, true), (.inout, false)]
  | .deparser => [(.in, true)]

/-- An exported block's params match its kind's signature. -/
def signatureOk (p : Program) (b : Block) : Bool :=
  let want := exportSignature b.kind
  b.params.length == want.length &&
    (b.params.zip want).all fun (q, d, h) =>
      q.direction == d && decide (q.type = .struct (if h then p.headers else p.metadata))

/-- An extern type (validator, `check_extern_types`). -/
def ExternTypeOk (idx : Index) (et : ExternType) : Prop :=
  NamesOk (et.constructorParams.map (·.name)) ∧
    (∀ q ∈ et.constructorParams, q.direction = .in ∧ TyOk idx q.type) ∧
    NamesOk (et.methods.map (·.name)) ∧
    ∀ m ∈ et.methods, NamesOk (m.params.map (·.name)) ∧
      (∀ q ∈ m.params, q.direction ≠ .none ∧ TyOk idx q.type) ∧
      (∀ t, m.returns = some t → TyOk idx t)

/-- The whole program is valid, and `idx` is its index. -/
structure Valid (p : Program) (idx : Index) : Prop where
  index : Index.build p = .ok idx
  errors : coreErrors.isPrefixOf p.errors = true
  headers : ∀ h ∈ p.headerTypes, NamesOk (h.fields.map (·.name)) ∧
    ∀ f ∈ h.fields, scalarField f.type = true
  structs : ∀ s ∈ p.structTypes, NamesOk (s.fields.map (·.name)) ∧
    TyOk idx (.struct s.name)
  enums : ∀ e ∈ p.enumTypes, NamesOk e.members ∧ e.members ≠ []
  headersType : idx.structTypes[p.headers]? ≠ none
  metadataType : idx.structTypes[p.metadata]? ≠ none
  externTypes : ∀ et ∈ p.externTypes, ExternTypeOk idx et
  externInstances : ∀ i ∈ p.externInstances, ∃ et, idx.externTypes[i.externType]? = some et ∧
    LitArgsTyped idx i.args et.constructorParams
  blocks : ∀ b ∈ p.blocks, ∃ sc, idx.scopes[b.name]? = some sc ∧ BlockTyped idx sc b
  exportRoles : (p.exports.map (·.role)).Nodup
  exports : ∀ e ∈ p.exports, ∃ b, idx.blocks[e.block]? = some b ∧ signatureOk p b = true
  blocksAcyclic : acyclic (p.blocks.map (·.name))
    (fun n => ((p.blocks.find? (·.name == n)).map blockCallees).getD []) = true

end P4bloIR.Validity
