import P4bloIR.ScalarTyping
import P4bloIR.Exec
import Std.Data.HashMap.Lemmas

/-! A scoped statement typing boundary and finite prefixes of the existing
execution machine. No alternate evaluator or runtime permission check. -/

namespace P4bloIR.ScalarStatements

open ScalarTyping

def irType : ScalarTy → Ty
  | .bits width => .bits width
  | .boolean => .boolean

/-- Mirrors the validator: locals, out and inout are writable; input and
directionless parameters are not. The runtime itself does not enforce this. -/
def writable : VarDecl → Bool
  | .var _ => true
  | .param param => match param.direction with
    | .out | .inout => true
    | .none | .«in» => false

/-- An executable scoped permission/type check, not whole-block validity. -/
def canAssign (ctx : Context) (scope : BlockScope) (name : String) (t : ScalarTy) : Bool :=
  if ctx.WellFormed then
    match Context.lookup ctx name, scope.var? name with
    | some found, some decl => decide (found = t) && decl.name == name &&
        decide (decl.type = irType t) && writable decl
    | _, _ => false
  else false

mutual
inductive Typed (ctx : Context) (scope : BlockScope) : Stmt → Prop
  | assign (permission : canAssign ctx scope name t = true)
      (value : TypedIn ctx expr t) : Typed ctx scope (.assign (.var name) expr)
  | conditional (condition : TypedIn ctx expr .boolean)
      (yes : BodyTyped ctx scope yesBody) (no : BodyTyped ctx scope noBody) :
      Typed ctx scope (.conditional expr yesBody noBody)

inductive BodyTyped (ctx : Context) (scope : BlockScope) : List Stmt → Prop
  | nil : BodyTyped ctx scope []
  | cons : Typed ctx scope stmt → BodyTyped ctx scope rest → BodyTyped ctx scope (stmt :: rest)
end

/-- No active action storage in this first writable fragment. -/
def BlockFrame (frame : Frame) : Prop := frame.action = none ∧ frame.actionVars = none

/-- Only the block-value map may change. This keeps all other Run and frame
fields exactly, without requiring equality of independently rebuilt maps. -/
def ChangesOnlyVars (initial final : Run) : Prop :=
  ∃ vars, final = { initial with frame := { initial.frame with vars } }

theorem ChangesOnlyVars.refl (run : Run) : ChangesOnlyVars run run := ⟨run.frame.vars, rfl⟩

theorem ChangesOnlyVars.trans (h₁ : ChangesOnlyVars first middle)
    (h₂ : ChangesOnlyVars middle last) : ChangesOnlyVars first last := by
  obtain ⟨a, rfl⟩ := h₁
  obtain ⟨b, rfl⟩ := h₂
  exact ⟨b, rfl⟩

theorem ChangesOnlyVars.scope (h : ChangesOnlyVars first last) :
    last.frame.scope = first.frame.scope := by obtain ⟨_, rfl⟩ := h; rfl

theorem ChangesOnlyVars.blockFrame (h : ChangesOnlyVars first last)
    (hb : BlockFrame first.frame) : BlockFrame last.frame := by
  obtain ⟨_, rfl⟩ := h
  exact hb

/-- Names absent from the possible write set retain their exact values. -/
def PreservesOutside (names : List String) (first last : Run) : Prop :=
  ∀ name, name ∉ names → last.frame.vars[name]? = first.frame.vars[name]?

theorem writeVar_block (run : Run) (hb : BlockFrame run.frame)
    (found : run.frame.read? name = some old) :
    (writeVar name value).run run =
      (.ok (), { run with frame := { run.frame with vars := run.frame.vars.insert name value } }) := by
  have hv : run.frame.vars[name]? = some old := by
    simpa [Frame.read?, hb.2] using found
  have hc : name ∈ run.frame.vars := by
    exact Std.HashMap.mem_iff_isSome_getElem?.mpr (by simp [hv])
  simp [writeVar, run_bind, Frame.write?, hb.2, hc, setFrame]
  rfl

end P4bloIR.ScalarStatements

namespace P4bloIR.Execution

/-- A finite prefix of actual successful machine transitions. It makes no
termination assertion about a continuation left at its endpoint. -/
inductive Steps : Machine → Machine → Prop
  | refl : Steps machine machine
  | next : step machine = .inr next → Steps next last → Steps machine last

theorem Steps.trans (first : Steps a b) (second : Steps b c) : Steps a c := by
  induction first with
  | refl => exact second
  | next h _ ih => exact .next h (ih second)

theorem Steps.finishes (trace : Steps first last) (finish : Finishes last result) :
    Finishes first result := by
  induction trace with
  | refl => exact finish
  | next h _ ih => exact .next h (ih finish)

theorem Steps.execute (trace : Steps { work := [.statements body], run := initial }
    { work := [], run := final }) :
    (P4bloIR.execute body).run initial = (.ok (), final) := by
  exact (trace.finishes (.done rfl)).sound

end P4bloIR.Execution
