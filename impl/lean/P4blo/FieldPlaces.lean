import P4blo.FieldExpressions
import P4blo.ScalarPlaces

/-! Root declaration modes for aggregate storage. Permission belongs to the
root, not the selected leaf. Actual declarations are checked separately
from operational frame agreement; action storage remains outside this API. -/

namespace P4blo.Fields

inductive Modes : Layout → Type
  | nil : Modes .nil
  | cons : Scalar.Mode → Modes rest → Modes (.cons name shape rest)

def Modes.get : Modes roots → Slot roots shape → Scalar.Mode
  | .cons mode _, .here => mode
  | .cons _ rest, .there root => rest.get root

def Modes.getRef (modes : Modes roots) : Ref roots t → Scalar.Mode
  | .mk root _ => modes.get root

structure Place (modes : Modes roots) (t : Scalar.Ty) where
  ref : Ref roots t
  writable : (modes.getRef ref).writable = true

def Place.read {modes : Modes roots} (place : Place modes t) : Expr roots t := .read place.ref

def Modes.declarations : Modes roots → Std.HashMap String P4bloIR.VarDecl
  | .nil => {}
  | .cons (name := name) (shape := shape) mode rest =>
    rest.declarations.insert name (mode.declarationIR name shape.toIR)

def Modes.params : Modes roots → List P4bloIR.Param
  | .nil => []
  | .cons (name := name) (shape := shape) mode rest => match mode with
    | .local => rest.params
    | .param direction => ⟨name, shape.toIR, direction⟩ :: rest.params

def Modes.locals : Modes roots → List P4bloIR.Var
  | .nil => []
  | .cons (name := name) (shape := shape) mode rest => match mode with
    | .local => ⟨name, shape.toIR⟩ :: rest.locals
    | .param _ => rest.locals

/-- Exact name, nominal/scalar type and direction of every actual root. -/
def Modes.Agrees (modes : Modes roots) (scope : P4bloIR.BlockScope) : Prop :=
  ∀ {shape} (root : Slot roots shape),
    scope.var? root.name = some ((modes.get root).declarationIR root.name shape.toIR)

def Modes.scope (modes : Modes roots) : P4bloIR.BlockScope :=
  { block := { (default : P4bloIR.Block) with
      name := "fields", kind := .control, params := modes.params, locals := modes.locals }
    vars := modes.declarations }

theorem Modes.declarations_get (modes : Modes roots)
    (hw : (roots.fields.map P4bloIR.Field.name).Nodup) (root : Slot roots shape) :
    modes.declarations[root.name]? = some ((modes.get root).declarationIR root.name shape.toIR) := by
  induction root with
  | here => cases modes; simp [Modes.declarations, Slot.name, Modes.get]
  | @there rest shape name headShape root ih =>
    have hn : root.name ≠ name := by
      intro h
      exact (List.nodup_cons.mp hw).1 (h ▸ List.mem_map.mpr ⟨_, root.mem, rfl⟩)
    cases modes with
    | cons mode tail =>
      simpa [Modes.declarations, Slot.name, Modes.get, Std.HashMap.getElem?_insert,
        hn, Ne.symm hn] using ih tail (List.nodup_cons.mp hw).2

theorem Modes.scope_agrees (modes : Modes roots) (hw : RootWellFormed roots) :
    modes.Agrees modes.scope := by
  intro shape root
  simpa [Modes.scope, P4bloIR.BlockScope.var?] using modes.declarations_get hw.1 root

theorem Modes.Agrees.declares {modes : Modes roots} {scope : P4bloIR.BlockScope} (hd : modes.Agrees scope) :
    RootDeclares roots scope := by
  intro shape root
  exact ⟨_, hd root, Scalar.Mode.declarationIR_name _ _ _, Scalar.Mode.declarationIR_type _ _ _⟩

/-- Constructive exact value/declaration witness, not a proof of arbitrary
whole-program initialization by Index.build or Frame.forBlock. -/
def Modes.frame (modes : Modes roots) (store : Store roots) : P4bloIR.Frame :=
  { store.frame with scope := modes.scope }

theorem Modes.frame_matches (modes : Modes roots) (store : Store roots) (hw : RootWellFormed roots) :
    FrameMatches store (modes.frame store) := by
  intro shape root
  simpa [Modes.frame, Record.frame, P4bloIR.Frame.read?] using store.bindings_get root hw.1

theorem Path.writable_typed (path : Path shape t) (hi : shape.IndexAgrees index)
    (hb : P4bloIR.FieldTyping.WritablePath index scope base shape.toIR) :
    P4bloIR.FieldTyping.WritablePath index scope (path.lvalue base) (Scalar.Ty.toIR t) := by
  induction path generalizing base with
  | scalar => exact hb
  | @field fields child t kind name slot path ih =>
    have hfields : P4bloIR.FieldTyping.FieldsOf index
        (Shape.aggregate kind name fields).toIR fields.fields := by
      cases kind with
      | header => exact .header hi.1
      | struct => exact .struct hi.1
    exact ih (slot.indexAgrees hi.2) (.member ⟨slot.name, child.toIR⟩ hb hfields slot.mem)

theorem Place.typed {modes : Modes roots} (place : Place modes t) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees index) (hd : modes.Agrees scope) :
    P4bloIR.FieldTyping.WritablePath index scope place.ref.lvalue (P4bloIR.ScalarStatements.irType t) := by
  obtain ⟨ref, permission⟩ := place
  cases ref with
  | mk root path =>
    have hroot : P4bloIR.FieldTyping.WritablePath index scope (.var root.name) _ :=
      .var root.name ((modes.get root).declarationIR root.name _) (hw.2.1 _ root.mem)
        (hd root) (Scalar.Mode.declarationIR_name _ _ _) (by
          rw [Scalar.Mode.declarationIR_writable]
          exact permission)
    rw [Scalar.Mode.declarationIR_type] at hroot
    have ht : Scalar.Ty.toIR t = P4bloIR.ScalarStatements.irType t := by cases t <;> rfl
    rw [← ht]
    exact path.writable_typed (root.indexAgrees hi) hroot

end P4blo.Fields
