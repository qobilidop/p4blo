import P4blo.ScalarTyping

/-!
# Typed closed scalar construction

This is a deliberately small source language, not a wrapper declaring raw IR
well formed. Its compositional meaning uses finite naturals and booleans and
does not call the IR evaluator. Lowering preserves that exact value and every
component of any initial interpreter run. Variables and programs are outside
this theorem; they require a typed-frame relation and additional obligations.
-/

namespace P4bloLean.Scalar

abbrev Ty := P4blo.ScalarTyping.ScalarTy

/-- Width positivity and literal bounds are checked at construction. -/
inductive Expr : Ty → Type
  | bits {width : Nat} (positive : 0 < width) (value : Fin (2 ^ width)) :
      Expr (.bits width)
  | boolean (value : Bool) : Expr .boolean
  | add {width : Nat} : Expr (.bits width) → Expr (.bits width) → Expr (.bits width)
  | eqBits {width : Nat} : Expr (.bits width) → Expr (.bits width) → Expr .boolean
  | mux {t : Ty} : Expr .boolean → Expr t → Expr t → Expr t

/-- Source values are independent of `P4blo.Value` and the evaluator. -/
abbrev Meaning : Ty → Type
  | .bits width => Fin (2 ^ width)
  | .boolean => Bool

def denote : Expr t → Meaning t
  | .bits _ value => value
  | .boolean value => value
  | .add left right =>
    ⟨((denote left).val + (denote right).val) % 2 ^ _, Nat.mod_lt _ (Nat.two_pow_pos _)⟩
  | .eqBits left right => (denote left).val == (denote right).val
  | .mux condition yes no => if denote condition = true then denote yes else denote no

/-- The value correspondence, not an implementation of source evaluation. -/
def toValue : {t : Ty} → Meaning t → P4blo.Value
  | .bits width, value => .bits ⟨width, value.val, value.isLt⟩
  | .boolean, value => .bool value

def lower : Expr t → P4blo.Expr
  | .bits (width := width) _ value => .literal (.bits width value.val)
  | .boolean value => .literal (.boolean value)
  | .add left right => .binary .add (lower left) (lower right)
  | .eqBits left right => .binary .eq (lower left) (lower right)
  | .mux condition yes no => .mux (lower condition) (lower yes) (lower no)

/-- Every lowered term belongs to the specification's typed scalar fragment. -/
theorem lower_typed (e : Expr t) : P4blo.ScalarTyping.Typed (lower e) t := by
  induction e with
  | bits positive value => exact .bits _ _ positive value.isLt
  | boolean value => exact .boolean value
  | add _ _ hl hr => exact .binary .add hl hr (by simp [P4blo.ScalarTyping.binaryType])
  | eqBits _ _ hl hr => exact .binary .eq hl hr (by simp [P4blo.ScalarTyping.binaryType])
  | mux _ _ _ hc hl hr => exact .mux hc hl hr

/-- Exact meaning preservation, stronger than just the type of the result. -/
theorem evaluate_lower (e : Expr t) :
    P4blo.evaluate (lower e) = pure (toValue (denote e)) := by
  induction e with
  | bits positive value =>
    simp [lower, P4blo.evaluate, P4blo.literalValue, P4blo.Literal.toValue,
      P4blo.Bits.wrap, denote, toValue, Nat.mod_eq_of_lt value.isLt]
  | boolean value => rfl
  | add left right hl hr =>
    have hb (b : P4blo.Bits) : P4blo.expectBits (.bits b) = pure b := rfl
    simp [lower, P4blo.evaluate, hl, hr, toValue, hb, P4blo.bitsBinary,
      denote, P4blo.Bits.wrap]
  | @eqBits width left right hl hr =>
    simp only [lower, P4blo.evaluate, hl, hr, pure_bind]
    change (pure (P4blo.Value.bool
      ((width == width) && ((denote left).val == (denote right).val))) : P4blo.M _) = _
    simp [denote, toValue]
  | mux condition yes no hc hl hr =>
    have hb (b : Bool) : P4blo.expectBool (.bool b) = pure b := rfl
    cases h : denote condition <;>
      simp [lower, P4blo.evaluate, hc, hl, hr, hb, denote, toValue, h]

/-- All state, not only selected observations, is unchanged. -/
theorem evaluate_lower_run (e : Expr t) (run : P4blo.Run) :
    (P4blo.evaluate (lower e)).run run = (.ok (toValue (denote e)), run) := by
  rw [evaluate_lower]
  rfl

/-- Explicit proofs support symbolic widths and values. Concrete authors may
use `bits[width, value]`, which discharges these obligations by decision. -/
def bits (width value : Nat) (positive : 0 < width := by decide)
    (fits : value < 2 ^ width := by decide) : Expr (.bits width) :=
  .bits positive ⟨value, fits⟩

/-- Dynamic inputs fail explicitly; invalid literals are never silently wrapped. -/
def bits? (width value : Nat) : Option (Expr (.bits width)) :=
  if hp : 0 < width then
    if hv : value < 2 ^ width then some (.bits hp ⟨value, hv⟩) else none
  else none

instance : Add (Expr (.bits width)) := ⟨Expr.add⟩

scoped syntax "bits[" term "," term "]" : term
scoped macro_rules
  | `(bits[$width, $value]) => `(P4bloLean.Scalar.bits $width $value)

scoped infix:50 " === " => Expr.eqBits

end P4bloLean.Scalar
