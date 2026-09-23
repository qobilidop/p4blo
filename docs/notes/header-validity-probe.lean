import P4blo.FieldExpressions

/-! Isolated feasibility probe, not production API or a default build target. -/
namespace HeaderValidityProbe
open P4blo
open P4blo.Fields

inductive HeaderPath : Shape → Type
  | here : HeaderPath (.aggregate .header name fields)
  | field : Slot fields child → HeaderPath child → HeaderPath (.aggregate kind name fields)

def HeaderPath.get : HeaderPath shape → Data shape → Bool
  | .here, .aggregate valid _ => valid
  | .field slot path, .aggregate _ fields => path.get (fields.get slot)

def HeaderPath.expr : HeaderPath shape → P4bloIR.Expr → P4bloIR.Expr
  | .here, base => .isValid base
  | .field slot path, base => path.expr (.member base slot.name)

theorem HeaderPath.evaluate (path : HeaderPath shape) (data : Data shape) (run : P4bloIR.Run)
    (hi : shape.IndexAgrees run.index)
    (hb : (P4bloIR.evaluate base).run run = (.ok data.toValue, run)) :
    (P4bloIR.evaluate (path.expr base)).run run = (.ok (.bool (path.get data)), run) := by
  induction path generalizing base with
  | here =>
    cases data
    simp [HeaderPath.expr, HeaderPath.get, P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind,
      hb, Data.toValue, P4bloIR.FieldLaws.pack, Validity.toBool,
      P4bloIR.expectHeader, P4bloIR.Value.expectHeader, P4bloIR.liftExcept,
      P4bloIR.ScalarTyping.run_map] <;> rfl
  | field slot path ih =>
    cases data with
    | aggregate valid fields =>
      apply ih (fields.get slot) (slot.indexAgrees hi.2)
      simpa [P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind, hb] using
        fields.fieldOf slot valid run hi.1

inductive Read (roots : Layout) : Scalar.Ty → Type
  | scalar : Ref roots t → Read roots t
  | probeFlag : Bool → Read roots .boolean

instance : Coe (Ref roots t) (Read roots t) := ⟨Read.scalar⟩
abbrev Expr (roots : Layout) := Scalar.ExprWith (Read roots)

example (ref : Ref roots t) : Expr roots t := .read ref
example (ref : Ref roots (.bits 8)) : Expr roots (.bits 8) :=
  .add (.read ref) (.read ref)
example : HeaderPath (.aggregate .header "Empty" .nil) := .here
example : True := by
  fail_if_success have bad : HeaderPath (.aggregate .struct "S" .nil) := .here
  trivial
example : True := by
  fail_if_success have bad : HeaderPath (.scalar .boolean) := .here
  trivial

#print axioms HeaderPath.evaluate
end HeaderValidityProbe
