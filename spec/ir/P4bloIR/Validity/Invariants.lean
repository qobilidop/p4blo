import P4bloIR.Validity.Sound
import P4bloIR.Validity.Triple
import P4bloIR.Exec

/-!
# What a well-formed run keeps

The invariants the progress proof maintains, and the two contracts it
assumes from outside the IR.

The contracts are premises, stated as exactly what the step machine asks
of its environment. `ExternContract` is the architecture's extern
binding: a call on a bound instance with arguments of the declared types
succeeds, keeps the contract's state invariant, and returns values of the
declared types. `InstalledOk` is table installation: a lookup in a table
of the program succeeds and names an action of the table's block with
literal data of its parameters' types. Both fail, if they fail, at load or
installation, before any packet runs.

The invariants: a run's shared state fits the block kind (`RunOk`), a
context is a block of the valid program, with the action whose body runs
(`CtxOk`), and a frame holds a value of the declared type for every
variable the context sees (`FrameOk`). `LvOk` is lvalue typing as the
run-time needs it: an index is a bits expression or, once a call has
resolved it, a bits literal.
-/

namespace P4bloIR.Validity

open Std (HashMap)

/-- Values of the given types, one each, in order. -/
def ValuesHave (idx : Index) (vs : List Value) (ts : List Ty) : Prop :=
  Forall2 (fun v t => ValueHas idx v t) vs ts

/-- What an architecture's extern binding guarantees, for some invariant
of the extern state. -/
structure ExternContract (idx : Index) where
  inv : Externs → Prop
  call : ∀ (e : Externs) (name : String) (inst : ExternInstance) (et : ExternType) (meth : Method)
    (args : List Value), inv e → idx.externInstances[name]? = some inst →
    idx.externTypes[inst.externType]? = some et → meth ∈ et.methods →
    ValuesHave idx args (meth.params.map (·.type)) →
    ∃ e' res, e.call name meth.name args = .ok (e', res) ∧ inv e' ∧
      ValuesHave idx res.outs ((meth.params.filter (isOut ·.direction)).map (·.type)) ∧
      ∀ t, meth.returns = some t → ∃ v, res.returns = some v ∧ ValueHas idx v t

/-- Action data of the parameters' types, one literal each, in order. -/
def DataOk (idx : Index) (args : List Literal) (params : List Param) : Prop :=
  Forall2 (fun a (q : Param) => ValueHas idx (literalValue a) q.type) args params

/-- What table installation guarantees: every lookup in a table of the
program succeeds, and the action it selects is one of the table's block
with data of its parameters' types. -/
def InstalledOk (idx : Index) (inst : Installed) : Prop :=
  ∀ (n : String) (sc : BlockScope) (tn : String) (t : Table) (keys : List Bits), idx.scopes[n]? = some sc → sc.tables[tn]? = some t →
    keys.length = t.keys.length →
    ∃ m, inst.lookup (sc.block.name, t.name) keys = .ok m ∧
      ∀ call, m.action = some call → ∃ act, sc.actions[call.action]? = some act ∧
        DataOk idx call.args act.params

/-- A valid program, the block kind of the run, and the extern contract. -/
structure Global where
  p : Program
  idx : Index
  kind : BlockKind
  valid : Valid p idx
  externs : ExternContract idx

/-- The shared state of a run fits its block kind. -/
structure RunOk (G : Global) (r : Run) : Prop where
  index : r.index = G.idx
  packet : G.kind = .parser → r.packet.isSome
  emitter : G.kind = .deparser → r.emitter.isSome
  entries : G.kind = .control → ∃ inst, r.entries = some inst ∧ InstalledOk G.idx inst
  externs : G.externs.inv r.externs

/-- A context is a block of the program, of the run's kind, in its own
scope, with one of its actions when an action body runs. -/
structure CtxOk (G : Global) (c : Ctx) : Prop where
  index : c.index = G.idx
  kind : c.kind = G.kind
  block : G.idx.blocks[c.scope.block.name]? = some c.scope.block
  scope : G.idx.scopes[c.scope.block.name]? = some c.scope
  laws : Build.ScopeLaws c.scope.block c.scope
  typed : BlockTyped G.idx c.scope c.scope.block
  blockKind : c.scope.block.kind = G.kind
  action : ∀ a, c.action = some a → a ∈ c.scope.block.actions

/-- The action layer of a frame holds a typed value for exactly the
running action's params. -/
def LayerOk (idx : Index) : Option Action → Option (HashMap String Value) → Prop
  | none, avs => avs = none
  | some a, avs => ∃ m, avs = some m ∧ ∀ x, match a.params.find? (·.name == x) with
    | some q => ∃ v, m[x]? = some v ∧ ValueHas idx v q.type
    | none => m[x]? = none

/-- A frame holds a typed value for every variable its context sees. -/
structure FrameOk (c : Ctx) (f : Frame) : Prop where
  scope : f.scope = c.scope
  vars : ∀ (x : String) (d : VarDecl), c.scope.vars[x]? = some d → ∃ v, f.vars[x]? = some v ∧ ValueHas c.index v d.type
  layer : LayerOk c.index c.action f.actionVars

/-- An index as the run-time meets it: a bits expression, or a bits literal
once resolved. -/
def IdxOk (c : Ctx) (e : Expr) : Prop :=
  (∃ w, ExprTyped c e (.bits w)) ∨ ∃ w v, e = .literal (.bits w v)

/-- Lvalue typing as reads and writes need it (see `IdxOk`); writability
is not a run-time matter. -/
inductive LvOk (c : Ctx) : LValue → Ty → Prop
  | var : c.var? x = some d → LvOk c (.var x) d.type
  | member : LvOk c base bt → fieldType? c.index bt f = some t → LvOk c (.member base f) t
  | index : LvOk c base (.stack h n) → IdxOk c i → LvOk c (.index base i) (.header h)

theorem LValueTyped.lvOk (h : LValueTyped c lv t) : LvOk c lv t := by
  induction h with
  | var hd _ => exact .var hd
  | member _ hf ih => exact .member ih hf
  | index _ hi ih => exact .index ih (.inl ⟨_, hi⟩)

end P4bloIR.Validity
