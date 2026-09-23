import P4blo.FieldExpressions

/-! Read-only header targets. These paths observe independent source validity
bits, never scalar writable locations. No parser, initializer, global validity
or new expression/command semantics is supplied by this module. -/

namespace P4blo.Fields

/-- A header endpoint, possibly nested within aggregates. Unlike scalar Path,
this type has no update or lvalue operation. -/
inductive HeaderPath : Shape → Type
  | here : HeaderPath (.aggregate .header name fields)
  | field : Slot fields child → HeaderPath child → HeaderPath (.aggregate kind name fields)

def HeaderPath.get : HeaderPath shape → Data shape → Bool
  | .here, .aggregate valid _ => valid
  | .field slot path, .aggregate _ fields => path.get (fields.get slot)

/-- Actual member spelling followed by one validity read at the endpoint. -/
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

theorem HeaderPath.typed (path : HeaderPath shape) (hi : shape.IndexAgrees index)
    (hb : P4bloIR.FieldTyping.Path index scope base shape.toIR) :
    P4bloIR.FieldTyping.Typed index scope (path.expr base) .boolean := by
  induction path generalizing base with
  | here => exact .isValid hb hi.1
  | @field fields child kind name slot path ih =>
    have hfields : P4bloIR.FieldTyping.FieldsOf index
        (Shape.aggregate kind name fields).toIR fields.fields := by
      cases kind with
      | header => exact .header hi.1
      | struct => exact .struct hi.1
    exact ih (slot.indexAgrees hi.2) (.member ⟨slot.name, child.toIR⟩ hb hfields slot.mem)

/-- Read-only header location. It cannot be passed to Place or Ref.set. -/
inductive HeaderRef (roots : Layout)
  | mk {shape : Shape} : Slot roots shape → HeaderPath shape → HeaderRef roots

def HeaderRef.get : HeaderRef roots → Store roots → Bool
  | .mk root path, store => path.get (store.get root)

def HeaderRef.expr : HeaderRef roots → P4bloIR.Expr
  | .mk root path => path.expr (.var root.name)

/-- Concrete exact root bridge. The public reference law uses the actual
Index and action-first frame agreement, not a supplied evaluation callback. -/
theorem HeaderRef.evaluate (ref : HeaderRef roots) (store : Store roots) (run : P4bloIR.Run)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches store run.frame) :
    (P4bloIR.evaluate ref.expr).run run = (.ok (.bool (ref.get store)), run) := by
  cases ref with
  | mk root path =>
    apply path.evaluate (store.get root) run (root.indexAgrees hi)
    simp [P4bloIR.evaluate, P4bloIR.readVar, P4bloIR.ScalarTyping.run_bind, hf root]

/-- Actual block declarations and nominal header-kind agreement are separate
from value agreement; successful typing is not whole-program validity. -/
theorem HeaderRef.typed (ref : HeaderRef roots) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees index) (hd : RootDeclares roots scope) :
    P4bloIR.FieldTyping.Typed index scope ref.expr .boolean := by
  cases ref with
  | mk root path =>
    obtain ⟨decl, hfind, hname, htype⟩ := hd root
    have hn := hw.2.1 _ root.mem
    have hpath : P4bloIR.FieldTyping.Path index scope (.var root.name) _ :=
      .var root.name decl hn hfind hname
    rw [htype] at hpath
    exact path.typed (root.indexAgrees hi) hpath

end P4blo.Fields
