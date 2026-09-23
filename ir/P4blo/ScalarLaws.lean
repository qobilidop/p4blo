import P4blo.Eval

/-!
# Scalar boundary laws for the executable semantics

These laws concern the values returned by the actual `bitsBinary` and
`evaluate`, complementing `ScalarTyping`'s type-safety theorem. Saturation and
large shifts return a specified bit value. Short-circuit laws place no
assumption on the unselected expression: it may read an absent variable or
fault on packet lookahead. Equality of computations includes their faults and
state effects, not only their eventual value.

The bits operators below have no equal-width hypothesis: their implementation
always uses the left width, so the stated laws also hold for malformed pairs.
A type checker separately enforces matching widths where the IR requires it.
-/

namespace P4blo.ScalarLaws

/-- Overflowing saturation returns the largest value at the left width,
rather than wrapping around. -/
theorem addSat_overflow (x y : Bits) (overflow : 2 ^ x.width ≤ x.value + y.value) :
    bitsBinary .addSat x y = pure (.bits (Bits.max x.width)) := by
  have bound : 2 ^ x.width - 1 ≤ x.value + y.value := by omega
  simp [bitsBinary, Nat.min_eq_right bound, Bits.max]

/-- Saturating subtraction at or below zero returns exactly zero. -/
theorem subSat_underflow (x y : Bits) (underflow : x.value ≤ y.value) :
    bitsBinary .subSat x y = pure (.bits (Bits.wrap x.width 0)) := by
  simp [bitsBinary, Nat.sub_eq_zero_of_le underflow]

/-- A left shift by the width or more is zero, even when the shift count
has a different bit width. -/
theorem shl_large (x amount : Bits) (large : x.width ≤ amount.value) :
    bitsBinary .shl x amount = pure (.bits (Bits.wrap x.width 0)) := by
  simp [bitsBinary, Nat.not_lt_of_ge large]

/-- A right shift by the width or more is zero. -/
theorem shr_large (x amount : Bits) (large : x.width ≤ amount.value) :
    bitsBinary .shr x amount = pure (.bits (Bits.wrap x.width 0)) := by
  simp [bitsBinary, Nat.not_lt_of_ge large]

/-- The maximum used in `addSat_overflow` has the actual numeric value
`2^width - 1`; wrapping does not alter it. -/
theorem max_value (width : Nat) : (Bits.max width).value = 2 ^ width - 1 := by
  have positive := Nat.two_pow_pos width
  simp [Bits.max, Bits.wrap, Nat.mod_eq_of_lt (show 2 ^ width - 1 < 2 ^ width by omega)]

private theorem expectBool_bool (b : Bool) : expectBool (.bool b) = pure b := rfl
private theorem expectBits_bits (b : Bits) : expectBits (.bits b) = pure b := rfl

/-- Lift the overflow value law through expression evaluation, so its
guarantee also covers the evaluator's operator dispatch and operand narrowing. -/
theorem evaluate_addSat_overflow (left right : Expr) (x y : Bits)
    (hl : evaluate left = pure (.bits x)) (hr : evaluate right = pure (.bits y))
    (overflow : 2 ^ x.width ≤ x.value + y.value) :
    evaluate (.binary .addSat left right) = pure (.bits (Bits.max x.width)) := by
  simpa [evaluate, hl, hr, expectBits_bits] using addSat_overflow x y overflow

/-- Lift the underflow value law through the actual expression evaluator. -/
theorem evaluate_subSat_underflow (left right : Expr) (x y : Bits)
    (hl : evaluate left = pure (.bits x)) (hr : evaluate right = pure (.bits y))
    (underflow : x.value ≤ y.value) :
    evaluate (.binary .subSat left right) = pure (.bits (Bits.wrap x.width 0)) := by
  simpa [evaluate, hl, hr, expectBits_bits] using subSat_underflow x y underflow

/-- False on the left prevents all evaluation of the right operand. No
typing, successful-evaluation, or state assumptions on `right` are needed. -/
theorem and_false (left right : Expr) (h : evaluate left = pure (.bool false)) :
    evaluate (.binary .and left right) = pure (.bool false) := by
  simp [evaluate, h, expectBool_bool]

/-- True on the left prevents all evaluation of the right operand. -/
theorem or_true (left right : Expr) (h : evaluate left = pure (.bool true)) :
    evaluate (.binary .or left right) = pure (.bool true) := by
  simp [evaluate, h, expectBool_bool]

/-- Selecting the then branch preserves its exact computation, even its
fault behavior; the otherwise branch is unrestricted. -/
theorem mux_true (condition yes no : Expr) (h : evaluate condition = pure (.bool true)) :
    evaluate (.mux condition yes no) = evaluate yes := by
  simp [evaluate, h, expectBool_bool]

/-- Selecting the otherwise branch preserves its exact computation. -/
theorem mux_false (condition yes no : Expr) (h : evaluate condition = pure (.bool false)) :
    evaluate (.mux condition yes no) = evaluate no := by
  simp [evaluate, h, expectBool_bool]

end P4blo.ScalarLaws
