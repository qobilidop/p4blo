import P4blo.HeaderFields
import P4blo.Scalar
import P4bloIR.FieldTyping

namespace P4blo.Fields


/-- Read leaves are distinct from writable scalar locations. Operators and
their meaning still live once in Scalar.ExprWith. -/
inductive Read (roots : Layout) : Scalar.Ty → Type
  | scalar : Ref roots t → Read roots t
  | headerValid : HeaderRef roots → Read roots .boolean

instance : Coe (Ref roots t) (Read roots t) := ⟨Read.scalar⟩

def Read.get : Read roots t → Store roots → Scalar.Meaning t
  | .scalar ref, store => ref.get store
  | .headerValid ref, store => ref.get store

def Read.expr : Read roots t → P4bloIR.Expr
  | .scalar ref => ref.expr
  | .headerValid ref => ref.expr

theorem Read.typed (read : Read roots t) (hw : RootWellFormed roots)
    (hi : roots.IndexAgrees index) (hd : RootDeclares roots scope) :
    P4bloIR.FieldTyping.Typed index scope read.expr t := by
  cases read with
  | scalar ref => exact ref.typed hw hi hd
  | headerValid ref => exact ref.typed hw hi hd

theorem Read.evaluate (read : Read roots t) (store : Store roots) (run : P4bloIR.Run)
    (hi : roots.IndexAgrees run.index) (hf : FrameMatches store run.frame) :
    (P4bloIR.evaluate read.expr).run run = (.ok (Scalar.toValue (read.get store)), run) := by
  cases read with
  | scalar ref => exact ref.evaluate store run hi hf
  | headerValid ref => exact ref.evaluate store run hi hf

abbrev Expr (roots : Layout) := Scalar.ExprWith (Read roots)

def HeaderRef.isValid (ref : HeaderRef roots) : Expr roots .boolean := .read (.headerValid ref)

def denote (store : Store roots) (expression : Expr roots t) : Scalar.Meaning t :=
  Scalar.denoteWith (fun ref => ref.get store) expression

def lower (expression : Expr roots t) : P4bloIR.Expr :=
  Scalar.lowerWith (fun ref => ref.expr) expression

theorem HeaderRef.denote_isValid (ref : HeaderRef roots) (store : Store roots) :
    denote store ref.isValid = ref.get store := rfl

theorem HeaderRef.lower_isValid (ref : HeaderRef roots) : lower ref.isValid = ref.expr := rfl

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
