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

end P4blo.ScalarExamples
