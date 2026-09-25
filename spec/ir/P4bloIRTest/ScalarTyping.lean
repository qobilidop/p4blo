import P4bloIRTest.Check

/-! Acceptance and rejection boundaries of the proved scalar checkers. -/

open P4bloIR

namespace ScalarTypingTests

private def bit (n v : Nat) : Expr := .literal (.bits n v)
private def bool (b : Bool) : Expr := .literal (.boolean b)

private def nested : Expr :=
  .mux (.unary .not (.binary .lt (bit 8 200) (bit 8 3)))
    (.slice (.binary .concat (bit 4 10) (bit 8 92)) 11 4)
    (.cast (.bits 8) (.binary .add (bit 16 65535) (bit 16 1)))

-- Kernel reduction establishes acceptance, then the public theorem supplies
-- the guarantee for an arbitrary run rather than a particular test fixture.
example (run : Run) : ∃ v,
    (evaluate nested).run run = (.ok v, run) ∧
      ScalarTyping.HasType v (.bits 8) :=
  ScalarTyping.check_sound (by decide) run

def tests : T Unit := do
  let infer := ScalarTyping.infer
  let ctx : ScalarTyping.Context := [("x", .bits 8), ("y", .bits 8), ("b", .boolean)]
  let inferIn := ScalarTyping.inferIn ctx
  check "context checker accepts variable" (inferIn (.var "x") == some (.bits 8))
  check "context checker accepts variable composition"
    (inferIn (.mux (.var "b") (.binary .add (.var "x") (.var "y")) (bit 8 0)) ==
      some (.bits 8))
  check "context checker rejects missing variable" (inferIn (.var "missing") == none)
  check "context checker rejects variable width mismatch"
    (inferIn (.binary .add (.var "x") (bit 7 1)) == none)
  check "context checker rejects variable kind mismatch"
    (inferIn (.binary .eq (.var "x") (.var "b")) == none)
  for bad in [[("", ScalarTyping.ScalarTy.boolean)], [("x", .bits 0)],
      [("x", .bits 8), ("x", .bits 8)], [("x", .bits 8), ("x", .boolean)]] do
    check "context checker rejects invalid unused context"
      (ScalarTyping.inferIn bad (bool true) == none)
  check "scalar checker accepts nested composition" (infer nested == some (.bits 8))
  check "checked nested expression runs in the actual evaluator"
    (match ((evaluate nested).run default).1 with
     | .ok v => v == .bits (Bits.wrap 8 165)
     | .error _ => false)
  check "scalar checker accepts a fitting maximum literal" (infer (bit 8 255) == some (.bits 8))
  check "scalar checker rejects an overflowing literal" (infer (bit 8 256) == none)
  check "scalar checker rejects zero-width bits" (infer (bit 0 0) == none)
  for op in [BinaryOp.add, .sub, .mul, .addSat, .subSat, .bitAnd, .bitOr, .bitXor] do
    check s!"scalar checker accepts bits {repr op}"
      (infer (.binary op (bit 8 3) (bit 8 7)) == some (.bits 8))
    check s!"scalar checker rejects unequal widths for {repr op}"
      (infer (.binary op (bit 8 3) (bit 9 7)) == none)
  for op in [BinaryOp.eq, .ne, .lt, .le, .gt, .ge] do
    check s!"scalar checker accepts comparison {repr op}"
      (infer (.binary op (bit 8 3) (bit 8 7)) == some .boolean)
    check s!"scalar checker rejects unequal comparison widths for {repr op}"
      (infer (.binary op (bit 8 3) (bit 9 7)) == none)
  for op in [BinaryOp.shl, .shr] do
    check s!"scalar checker accepts independent shift width for {repr op}"
      (infer (.binary op (bit 8 3) (bit 32 100)) == some (.bits 8))
  for op in [BinaryOp.and, .or, .eq, .ne] do
    check s!"scalar checker accepts boolean {repr op}"
      (infer (.binary op (bool false) (bool true)) == some .boolean)
  for op in [UnaryOp.complement, .negate] do
    check s!"scalar checker accepts unary bits {repr op}"
      (infer (.unary op (bit 8 3)) == some (.bits 8))
    check s!"scalar checker rejects unary boolean {repr op}"
      (infer (.unary op (bool false)) == none)
  check "scalar checker rejects not on bits" (infer (.unary .not (bit 1 0)) == none)
  check "scalar checker rejects mixed equality"
    (infer (.binary .eq (bit 1 0) (bool false)) == none)
  check "scalar checker rejects boolean ordering"
    (infer (.binary .lt (bool false) (bool true)) == none)
  check "scalar checker accepts bool to bit one"
    (infer (.cast (.bits 1) (bool true)) == some (.bits 1))
  check "scalar checker accepts bit one to bool"
    (infer (.cast .boolean (bit 1 1)) == some .boolean)
  check "scalar checker rejects bool to wider bits"
    (infer (.cast (.bits 8) (bool true)) == none)
  check "scalar checker rejects wider bits to bool"
    (infer (.cast .boolean (bit 8 1)) == none)
  check "scalar checker rejects zero-width cast"
    (infer (.cast (.bits 0) (bit 8 1)) == none)
  check "scalar checker rejects empty slice" (infer (.slice (bit 8 1) 2 3) == none)
  check "scalar checker rejects slice past width" (infer (.slice (bit 8 1) 8 0) == none)
  check "scalar checker accepts single-bit slice at upper bound"
    (infer (.slice (bit 8 128) 7 7) == some (.bits 1))
  check "scalar checker rejects nonboolean mux condition"
    (infer (.mux (bit 1 1) (bit 8 1) (bit 8 2)) == none)
  check "scalar checker rejects unequal mux branches"
    (infer (.mux (bool true) (bit 8 1) (bit 9 2)) == none)
  check "scalar checker rejects an unsupported unselected mux branch"
    (infer (.mux (bool true) (bit 8 1) (.lookahead (.bits 8))) == none)
  check "scalar checker checks the short-circuited operand"
    (infer (.binary .and (bool false) (.var "missing")) == none)
  for expr in [Expr.var "x", .member (.var "x") "f", .index (.var "s") (bit 8 0),
      .lastIndex (.var "s"), .isValid (.var "h"), .lookahead (.bits 8),
      .literal (.enumMember "E" "a"), .literal (.error "NoError")] do
    check s!"scalar checker explicitly rejects unsupported {repr expr}"
      (infer expr == none)

end ScalarTypingTests
