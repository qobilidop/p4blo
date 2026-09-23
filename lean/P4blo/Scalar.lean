import P4blo.ScalarContext

/-!
# Typed scalar construction

One context-indexed source AST with independent Fin/Bool environments.
`Expr` and `denote` retain the closed interface as specializations. Open
lowering preserves exact source meaning under explicit value agreement;
neither value agreement nor scalar typing certifies an entire program.
-/

namespace P4blo.Scalar

inductive ExprIn (ctx : Context) : Ty → Type
  | bits {width : Nat} (positive : 0 < width) (value : Fin (2 ^ width)) :
      ExprIn ctx (.bits width)
  | boolean (value : Bool) : ExprIn ctx .boolean
  | read : Ref ctx t → ExprIn ctx t
  | add {width : Nat} : ExprIn ctx (.bits width) → ExprIn ctx (.bits width) → ExprIn ctx (.bits width)
  | eqBits {width : Nat} : ExprIn ctx (.bits width) → ExprIn ctx (.bits width) → ExprIn ctx .boolean
  | mux {t : Ty} : ExprIn ctx .boolean → ExprIn ctx t → ExprIn ctx t → ExprIn ctx t

abbrev Expr := ExprIn []

namespace Expr
abbrev bits := @ExprIn.bits []
abbrev boolean := @ExprIn.boolean []
abbrev add := @ExprIn.add []
abbrev eqBits := @ExprIn.eqBits []
abbrev mux := @ExprIn.mux []
end Expr

def denoteIn (env : Env ctx) : ExprIn ctx t → Meaning t
  | .bits _ value => value
  | .boolean value => value
  | .read ref => env.get ref
  | .add left right =>
    ⟨((denoteIn env left).val + (denoteIn env right).val) % 2 ^ _,
      Nat.mod_lt _ (Nat.two_pow_pos _)⟩
  | .eqBits left right => (denoteIn env left).val == (denoteIn env right).val
  | .mux condition yes no => if denoteIn env condition = true then denoteIn env yes else denoteIn env no

def denote (e : Expr t) : Meaning t := denoteIn .nil e

def lower : ExprIn ctx t → P4bloIR.Expr
  | .bits (width := width) _ value => .literal (.bits width value.val)
  | .boolean value => .literal (.boolean value)
  | .read ref => .var ref.name
  | .add left right => .binary .add (lower left) (lower right)
  | .eqBits left right => .binary .eq (lower left) (lower right)
  | .mux condition yes no => .mux (lower condition) (lower yes) (lower no)

theorem lower_typed_in (e : ExprIn ctx t)
    (hw : P4bloIR.ScalarTyping.Context.WellFormed ctx) :
    P4bloIR.ScalarTyping.TypedIn ctx (lower e) t := by
  induction e with
  | bits positive value => exact .bits _ _ positive value.isLt
  | boolean value => exact .boolean value
  | read ref => exact .var (ref.lookup hw)
  | add _ _ hl hr => exact .binary .add hl hr (by simp [P4bloIR.ScalarTyping.binaryType])
  | eqBits _ _ hl hr => exact .binary .eq hl hr (by simp [P4bloIR.ScalarTyping.binaryType])
  | mux _ _ _ hc hl hr => exact .mux hc hl hr

theorem lower_typed (e : Expr t) : P4bloIR.ScalarTyping.Typed (lower e) t :=
  lower_typed_in e (by simp [P4bloIR.ScalarTyping.Context.WellFormed])

/-- Exact source value and the entire Run, not merely result typing. The
frame relation uses real action-layer precedence and does not assume zero
for a missing variable. Declarations/whole-program validity are separate. -/
theorem evaluate_lower_in (e : ExprIn ctx t) (env : Env ctx) (run : P4bloIR.Run)
    (hf : FrameMatches env run.frame) :
    (P4bloIR.evaluate (lower e)).run run = (.ok (toValue (denoteIn env e)), run) := by
  have hb (b : P4bloIR.Bits) : P4bloIR.expectBits (.bits b) = pure b := rfl
  have hbool (b : Bool) : P4bloIR.expectBool (.bool b) = pure b := rfl
  induction e with
  | bits positive value =>
    simp [lower, P4bloIR.evaluate, P4bloIR.literalValue, P4bloIR.Literal.toValue,
      P4bloIR.ScalarTyping.run_pure, P4bloIR.Bits.wrap, denoteIn, toValue,
      Nat.mod_eq_of_lt value.isLt]
  | boolean value => rfl
  | read ref =>
    simp [lower, P4bloIR.evaluate, P4bloIR.readVar, P4bloIR.ScalarTyping.run_bind,
      hf ref, denoteIn]
  | add left right hl hr =>
    simp [lower, P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind,
      hl, hr, toValue, hb, P4bloIR.bitsBinary,
      denoteIn, P4bloIR.Bits.wrap]
  | eqBits left right hl hr =>
    simp [lower, P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind,
      P4bloIR.ScalarTyping.run_map, hl, hr,
      denoteIn, toValue]
  | mux condition yes no hc hl hr =>
    cases h : denoteIn env condition <;>
      simp [lower, P4bloIR.evaluate, P4bloIR.ScalarTyping.run_bind, hc,
        hl, hr, hbool, denoteIn, toValue, h]

/-- The original closed computation equality follows from the same open
theorem; there is no second closed evaluator or parallel source AST. -/
theorem evaluate_lower (e : Expr t) :
    P4bloIR.evaluate (lower e) = pure (toValue (denote e)) := by
  funext run
  have h := evaluate_lower_in e .nil run (by intro t ref; cases ref)
  simpa [P4bloIR.M.run, ExceptT.run, StateT.run, Id.run, denote,
    pure, ExceptT.pure, ExceptT.mk, StateT.pure] using h

theorem evaluate_lower_run (e : Expr t) (run : P4bloIR.Run) :
    (P4bloIR.evaluate (lower e)).run run = (.ok (toValue (denote e)), run) := by
  rw [evaluate_lower]
  rfl

def bitsIn {ctx : Context} (width value : Nat) (positive : 0 < width := by decide)
    (fits : value < 2 ^ width := by decide) : ExprIn ctx (.bits width) :=
  .bits positive ⟨value, fits⟩

def bits (width value : Nat) (positive : 0 < width := by decide)
    (fits : value < 2 ^ width := by decide) : Expr (.bits width) :=
  bitsIn width value positive fits

def bits? (width value : Nat) : Option (Expr (.bits width)) :=
  if hp : 0 < width then
    if hv : value < 2 ^ width then some (.bits hp ⟨value, hv⟩) else none
  else none

instance : Add (ExprIn ctx (.bits width)) := ⟨ExprIn.add⟩

scoped syntax "bits[" term "," term "]" : term
scoped macro_rules
  | `(bits[$width, $value]) => `(P4blo.Scalar.bitsIn $width $value)

scoped infix:50 " === " => ExprIn.eqBits

end P4blo.Scalar
