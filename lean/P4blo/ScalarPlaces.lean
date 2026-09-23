import P4blo.ScalarContext
import P4bloIR.ScalarStatements

/-! Finite declaration modes and writable scalar places. Modes describe
source permissions, and a separate agreement premise connects them to real
declarations; no runtime permission enforcement is invented here. -/

namespace P4blo.Scalar

inductive Mode
  | local
  | param (direction : P4bloIR.Direction)
  deriving DecidableEq

def Mode.declaration (mode : Mode) (name : String) (t : Ty) : P4bloIR.VarDecl :=
  match mode with
  | .local => .var ⟨name, Ty.toIR t⟩
  | .param direction => .param ⟨name, Ty.toIR t, direction⟩

def Mode.writable (mode : Mode) : Bool :=
  P4bloIR.ScalarStatements.writable (mode.declaration "" .boolean)

inductive Modes : Context → Type
  | nil : Modes []
  | cons : Mode → Modes rest → Modes ((name, t) :: rest)

def Modes.get : Modes ctx → Ref ctx t → Mode
  | .cons mode _, .here => mode
  | .cons _ rest, .there ref => rest.get ref

structure Place (modes : Modes ctx) (t : Ty) where
  ref : Ref ctx t
  writable : (modes.get ref).writable = true

def Modes.declarations : Modes ctx → Std.HashMap String P4bloIR.VarDecl
  | .nil => {}
  | .cons (name := name) (t := t) mode rest =>
    rest.declarations.insert name (mode.declaration name t)

def Modes.params : Modes ctx → List P4bloIR.Param
  | .nil => []
  | .cons (name := name) (t := t) mode rest => match mode with
    | .local => rest.params
    | .param direction => ⟨name, Ty.toIR t, direction⟩ :: rest.params

def Modes.locals : Modes ctx → List P4bloIR.Var
  | .nil => []
  | .cons (name := name) (t := t) mode rest => match mode with
    | .local => ⟨name, Ty.toIR t⟩ :: rest.locals
    | .param _ => rest.locals

/-- Every source binding resolves to its exact name/type/direction declaration. -/
def Modes.Agrees (modes : Modes ctx) (scope : P4bloIR.BlockScope) : Prop :=
  ∀ {t} (ref : Ref ctx t), scope.var? ref.name = some ((modes.get ref).declaration ref.name t)

def Modes.scope (modes : Modes ctx) : P4bloIR.BlockScope :=
  { block := { (default : P4bloIR.Block) with
      name := "scalar", kind := .control, params := modes.params, locals := modes.locals }
    vars := modes.declarations }

theorem Modes.declarations_get (modes : Modes ctx)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) (ref : Ref ctx t) :
    modes.declarations[ref.name]? = some ((modes.get ref).declaration ref.name t) := by
  induction ref with
  | here => cases modes; simp [Modes.declarations, Ref.name, Modes.get]
  | @there rest t binding ref ih =>
    have hn : ref.name ≠ binding.1 := by
      intro h
      have hm : ref.name ∈ rest.map Prod.fst := List.mem_map.mpr ⟨_, ref.mem, rfl⟩
      exact (List.nodup_cons.mp hw.1).1 (h ▸ hm)
    cases modes with
    | cons mode tail =>
      simpa [Modes.declarations, Ref.name, Modes.get, Std.HashMap.getElem?_insert,
        hn, Ne.symm hn] using ih tail (context_tail hw)

theorem Modes.scope_agrees (modes : Modes ctx)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) : modes.Agrees modes.scope := by
  intro t ref
  simpa [Modes.scope, P4bloIR.BlockScope.var?] using modes.declarations_get hw ref

/-- A concrete related declaration/value frame. Global index/program
validity and Frame.forBlock's zero initialization remain separate claims. -/
def Modes.frame (modes : Modes ctx) (env : Env ctx) : P4bloIR.Frame :=
  { env.frame with scope := modes.scope }

theorem Modes.frame_matches (modes : Modes ctx) (env : Env ctx)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) : FrameMatches env (modes.frame env) := by
  intro t ref
  simpa [Modes.frame, Env.frame, P4bloIR.Frame.read?] using env.values_get hw ref

theorem Place.canAssign {modes : Modes ctx} (place : Place modes t)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) (hd : modes.Agrees scope) :
    P4bloIR.ScalarStatements.canAssign ctx scope place.ref.name t = true := by
  simp only [P4bloIR.ScalarStatements.canAssign, hw, ite_true, place.ref.lookup hw, hd place.ref]
  have h := place.writable
  cases hm : modes.get place.ref <;> cases t <;>
    simp_all [Mode.declaration, Mode.writable, P4bloIR.VarDecl.name, P4bloIR.VarDecl.type,
      Ty.toIR, P4bloIR.ScalarStatements.irType, P4bloIR.ScalarStatements.writable]

end P4blo.Scalar
