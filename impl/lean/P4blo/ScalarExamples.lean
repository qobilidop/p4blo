import P4blo.Scalar

/-! Authored examples shared by the Lean tests and JSON fixture exporter.
Expected results live in the tests, not in this exporter or the lowerer. -/

namespace P4blo.ScalarExamples

open Scalar
open scoped Scalar

structure Case where
  name : String
  type : Ty
  expression : Expr type

def cases : List Case := [
  ⟨"zero", .bits 8, bits[8, 0]⟩,
  ⟨"maximum", .bits 8, bits[8, 255]⟩,
  ⟨"add", .bits 8, bits[8, 19] + bits[8, 7]⟩,
  ⟨"wrap", .bits 8, bits[8, 255] + bits[8, 1]⟩,
  ⟨"one-bit-wrap", .bits 1, bits[1, 1] + bits[1, 1]⟩,
  ⟨"wide", .bits 65, bits[65, 36893488147419103231] + bits[65, 2]⟩,
  ⟨"equal", .boolean, bits[8, 7] === bits[8, 7]⟩,
  ⟨"unequal", .boolean, bits[8, 7] === bits[8, 8]⟩,
  ⟨"yes", .bits 8, .mux (.boolean true) bits[8, 19] bits[8, 7]⟩,
  ⟨"no", .bits 8, .mux (.boolean false) bits[8, 19] bits[8, 7]⟩,
  ⟨"bool-yes", .boolean, .mux (.boolean true) (.boolean false) (.boolean true)⟩,
  ⟨"bool-no", .boolean, .mux (.boolean false) (.boolean false) (.boolean true)⟩,
  ⟨"nested", .bits 8,
    .mux ((bits[8, 255] + bits[8, 1]) === bits[8, 0])
      (bits[8, 17] + bits[8, 29]) bits[8, 99]⟩]

def inputs : Context := [("x", .bits 8), ("y", .bits 8), ("choose", .boolean)]
def x : ExprIn inputs (.bits 8) := .read .here
def y : ExprIn inputs (.bits 8) := .read (.there .here)
def choose : ExprIn inputs .boolean := .read (.there (.there .here))

def values (a b : Fin 256) (c : Bool) : Env inputs := .cons a (.cons b (.cons c .nil))

structure OpenCase where
  name : String
  type : Ty
  expression : ExprIn inputs type
  environment : Env inputs

def openCases : List OpenCase := [
  ⟨"read-x", .bits 8, x, values 19 7 true⟩,
  ⟨"read-y", .bits 8, y, values 19 7 true⟩,
  ⟨"read-add", .bits 8, x + y, values 19 7 true⟩,
  ⟨"read-wrap", .bits 8, x + y, values 255 2 false⟩,
  ⟨"read-yes", .bits 8, .mux choose x y, values 19 7 true⟩,
  ⟨"read-no", .bits 8, .mux choose x y, values 19 7 false⟩,
  ⟨"read-equal", .boolean, x === y, values 7 7 false⟩,
  ⟨"read-unequal", .boolean, x === y, values 19 7 true⟩]

example : P4bloIR.ScalarTyping.Context.WellFormed inputs := by decide

end P4blo.ScalarExamples
