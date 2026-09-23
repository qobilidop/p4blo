import P4blo.Fields
import P4blo.Scalar
import P4bloIR.FieldTyping

namespace P4blo.Fields

/-- Root names and local shape restrictions; nominal consistency remains
the additional `IndexAgrees` premise. -/
def RootWellFormed (roots : Layout) : Prop :=
  (roots.fields.map P4bloIR.Field.name).Nodup ∧
  (∀ field ∈ roots.fields, field.name ≠ "") ∧ roots.LocallyWellFormed

/-- Exact actual block variable declarations, separate from runtime values. -/
def RootDeclares (roots : Layout) (scope : P4bloIR.BlockScope) : Prop :=
  ∀ {shape} (root : Slot roots shape), ∃ decl,
    scope.var? root.name = some decl ∧ decl.name = root.name ∧ decl.type = shape.toIR

theorem Slot.locallyWellFormed (slot : Slot fields shape) (hw : fields.LocallyWellFormed) :
    shape.LocallyWellFormed := by
  induction slot with
  | here => exact hw.1
  | there slot ih => exact ih hw.2

theorem Path.leaf_valid (path : Path shape t) (hw : shape.LocallyWellFormed) : t.Valid := by
  induction path with
  | @scalar scalarType => cases scalarType <;> exact hw
  | field slot path ih => exact ih (slot.locallyWellFormed hw.2.1)

theorem Path.typed (path : Path shape t) (hi : shape.IndexAgrees index)
    (hb : P4bloIR.FieldTyping.Path index scope base shape.toIR) :
    P4bloIR.FieldTyping.Path index scope (path.expr base) (Scalar.Ty.toIR t) := by
  induction path generalizing base with
  | scalar => exact hb
  | @field fields child t kind name slot path ih =>
    have hfields : P4bloIR.FieldTyping.FieldsOf index
        (Shape.aggregate kind name fields).toIR fields.fields := by
      cases kind with
      | header => exact .header hi.1
      | struct => exact .struct hi.1
    exact ih (slot.indexAgrees hi.2) (.member ⟨slot.name, child.toIR⟩ hb hfields slot.mem)

theorem Ref.typed (ref : Ref roots t) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees index) (hd : RootDeclares roots scope) :
    P4bloIR.FieldTyping.Typed index scope ref.expr t := by
  cases ref with
  | mk root path =>
    obtain ⟨decl, hfind, hname, htype⟩ := hd root
    have hn := hw.2.1 _ root.mem
    have hpath : P4bloIR.FieldTyping.Path index scope (.var root.name) _ :=
      .var root.name decl hn hfind hname
    rw [htype] at hpath
    apply P4bloIR.FieldTyping.Typed.read
    · have ht : Scalar.Ty.toIR t = P4bloIR.ScalarStatements.irType t := by cases t <;> rfl
      rw [← ht]
      exact path.typed (root.indexAgrees hi) hpath
    · exact path.leaf_valid (root.locallyWellFormed hw.2.2)

abbrev Expr (roots : Layout) := Scalar.ExprWith (Ref roots)

def denote (store : Store roots) (expression : Expr roots t) : Scalar.Meaning t :=
  Scalar.denoteWith (fun ref => ref.get store) expression

def lower (expression : Expr roots t) : P4bloIR.Expr :=
  Scalar.lowerWith (fun ref => ref.expr) expression

theorem lower_typed (expression : Expr roots t) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees index) (hd : RootDeclares roots scope) :
    P4bloIR.FieldTyping.Typed index scope (lower expression) t := by
  induction expression with
  | bits positive value => exact .bits _ _ positive value.isLt
  | boolean value => exact .boolean value
  | read ref => exact ref.typed hw hi hd
  | add _ _ hl hr => exact .binary .add hl hr (by simp [P4bloIR.ScalarTyping.binaryType])
  | eqBits _ _ hl hr => exact .binary .eq hl hr (by simp [P4bloIR.ScalarTyping.binaryType])
  | mux _ _ _ hc hy hn => exact .mux hc hy hn

/-- Concrete aggregate source/read correctness: the final statement uses
only the real Index and frame correspondence, not abstract leaf callbacks. -/
theorem evaluate_lower (expression : Expr roots t) (store : Store roots) (run : P4bloIR.Run)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches store run.frame) :
    (P4bloIR.evaluate (lower expression)).run run = (.ok (Scalar.toValue (denote store expression)), run) := by
  apply Scalar.evaluate_lower_with
  intro u ref
  exact ref.evaluate store run hi hf

end P4blo.Fields
