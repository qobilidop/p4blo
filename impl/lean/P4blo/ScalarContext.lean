import P4bloIR.ScalarTyping
import Std.Data.HashMap.Lemmas

/-! Finite positional references and independent source environments.
Names are used only at the lowering/runtime correspondence boundary. -/

namespace P4blo.Scalar

abbrev Ty := P4bloIR.ScalarTyping.ScalarTy
abbrev Context := P4bloIR.ScalarTyping.Context

/-- Source values do not use the IR evaluator or its runtime value datatype. -/
abbrev Meaning : Ty → Type
  | .bits width => Fin (2 ^ width)
  | .boolean => Bool

def toValue : {t : Ty} → Meaning t → P4bloIR.Value
  | .bits width, value => .bits ⟨width, value.val, value.isLt⟩
  | .boolean, value => .bool value

theorem toValue_typed (value : Meaning t) : P4bloIR.ScalarTyping.HasType (toValue value) t := by
  cases t <;> constructor

/-- Positional membership, not a string accepted by an unchecked cast. -/
inductive Ref : Context → Ty → Type
  | here : Ref ((name, t) :: rest) t
  | there : Ref rest t → Ref (binding :: rest) t

def Ref.name : Ref ctx t → String
  | .here (name := name) => name
  | .there ref => ref.name

theorem Ref.mem (ref : Ref ctx t) : (ref.name, t) ∈ ctx := by
  induction ref with
  | here => simp [Ref.name]
  | there ref ih => exact List.mem_cons_of_mem _ ih

theorem context_tail (hw : P4bloIR.ScalarTyping.Context.WellFormed (binding :: rest)) :
    P4bloIR.ScalarTyping.Context.WellFormed rest := by
  exact ⟨(List.nodup_cons.mp hw.1).2, fun b hb => hw.2 b (List.mem_cons_of_mem _ hb)⟩

theorem Ref.lookup (ref : Ref ctx t) (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) :
    P4bloIR.ScalarTyping.Context.lookup ctx ref.name = some t := by
  induction ref with
  | here => simp [Ref.name, P4bloIR.ScalarTyping.Context.lookup]
  | @there rest t binding ref ih =>
    have hn : ref.name ≠ binding.1 := by
      intro h
      have hm : ref.name ∈ rest.map Prod.fst := List.mem_map.mpr ⟨_, ref.mem, rfl⟩
      exact (List.nodup_cons.mp hw.1).1 (h ▸ hm)
    cases binding
    simpa [Ref.name, P4bloIR.ScalarTyping.Context.lookup, hn] using ih (context_tail hw)

theorem exists_ref (found : P4bloIR.ScalarTyping.Context.lookup ctx name = some t) :
    ∃ ref : Ref ctx t, ref.name = name := by
  induction ctx with
  | nil => simp [P4bloIR.ScalarTyping.Context.lookup] at found
  | cons binding rest ih =>
    rcases binding with ⟨key, ty⟩
    simp only [P4bloIR.ScalarTyping.Context.lookup] at found
    split at found
    next h =>
      cases h
      cases Option.some.inj found
      exact ⟨.here, rfl⟩
    next _ =>
      obtain ⟨ref, h⟩ := ih found
      exact ⟨.there ref, h⟩

/-- Heterogeneous finite source values, one for each context binding. -/
inductive Env : Context → Type
  | nil : Env []
  | cons : Meaning t → Env rest → Env ((name, t) :: rest)

def Env.get : Env ctx → Ref ctx t → Meaning t
  | .cons value _, .here => value
  | .cons _ rest, .there ref => rest.get ref

def Env.values : Env ctx → Std.HashMap String P4bloIR.Value
  | .nil => {}
  | .cons (name := name) value rest => rest.values.insert name (toValue value)

theorem Env.values_get (env : Env ctx) (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx)
    (ref : Ref ctx t) : env.values[ref.name]? = some (toValue (env.get ref)) := by
  induction ref with
  | here => cases env; simp [Env.values, Ref.name, Env.get]
  | @there rest t binding ref ih =>
    have hn : ref.name ≠ binding.1 := by
      intro h
      have hm : ref.name ∈ rest.map Prod.fst := List.mem_map.mpr ⟨_, ref.mem, rfl⟩
      exact (List.nodup_cons.mp hw.1).1 (h ▸ hm)
    cases env with
    | cons value tail =>
      simpa [Env.values, Ref.name, Env.get, Std.HashMap.getElem?_insert, hn,
        Ne.symm hn] using ih tail (context_tail hw)

/-- Exact values under the actual action-first lookup. Declaration validity
is deliberately separate: this predicate alone cannot certify a program. -/
def FrameMatches (env : Env ctx) (frame : P4bloIR.Frame) : Prop :=
  ∀ {t} (ref : Ref ctx t), frame.read? ref.name = some (toValue (env.get ref))

theorem FrameMatches.typed {env : Env ctx} (h : FrameMatches env frame) :
    P4bloIR.ScalarTyping.FrameTyped ctx frame := by
  intro name t found
  obtain ⟨ref, hn⟩ := exists_ref found
  exact ⟨toValue (env.get ref), hn ▸ h ref, toValue_typed _⟩

/-- A concrete witness that every well-formed context/environment has a
related frame. No assertion of whole-program or declaration validity. -/
def Env.frame (env : Env ctx) : P4bloIR.Frame :=
  { scope := default, vars := env.values }

theorem Env.frame_matches (env : Env ctx)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) : FrameMatches env env.frame := by
  intro t ref
  simpa [Env.frame, P4bloIR.Frame.read?] using env.values_get hw ref

def Ty.toIR : Ty → P4bloIR.Ty
  | .bits width => .bits width
  | .boolean => .boolean

/-- Declaration agreement is additional to exact value agreement. This
includes the active action's declaration scope, just as runtime lookup does. -/
def Declares (ctx : Context) (frame : P4bloIR.Frame) : Prop :=
  ∀ {t} (ref : Ref ctx t), ∃ decl,
    frame.scope.var? ref.name frame.action = some decl ∧ decl.type = Ty.toIR t

end P4blo.Scalar
