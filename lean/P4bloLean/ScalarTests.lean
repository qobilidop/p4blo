import P4bloLean.ScalarExamples

namespace P4bloLean.ScalarTests

open Scalar
open scoped Scalar

-- These are compile-time rejection tests. Each must fail to elaborate,
-- independently of whether a downstream IR validator would reject it.
example : True := by
  fail_if_success have bad := bits[0, 0]
  trivial

example : True := by
  fail_if_success have bad := bits[8, 256]
  trivial

example : True := by
  fail_if_success have bad := bits[8, 1] + bits[7, 1]
  trivial

example : True := by
  fail_if_success have bad := bits[8, 1] === bits[7, 1]
  trivial

example : True := by
  fail_if_success have bad := Expr.mux bits[1, 1] bits[8, 1] bits[8, 2]
  trivial

example : True := by
  fail_if_success have bad := Expr.mux (.boolean true) bits[8, 1] bits[7, 1]
  trivial

-- Symbolic literals require ordinary kernel-checked proof arguments.
example (w n : Nat) (hw : 0 < w) (hn : n < 2 ^ w) : Expr (.bits w) :=
  bits w n hw hn

private def observed : P4blo.Value → Option Nat
  | .bits b => some b.value
  | .bool b => some (if b then 1 else 0)
  | _ => none

def run : IO Unit := do
  let expected := [0, 255, 26, 0, 0, 1, 1, 0, 19, 7, 0, 1, 46]
  unless expected.length == ScalarExamples.cases.length do
    throw (IO.userError "scalar examples and independent known answers differ in length")
  for (c, answer) in ScalarExamples.cases.zip expected do
    unless observed (toValue (denote c.expression)) == some answer do
      throw (IO.userError s!"source known answer failed: {c.name}")
    let initial : P4blo.Run := { index := default, frame := default }
    let (actual, _) := (P4blo.evaluate (lower c.expression)).run initial
    unless actual.toOption.bind observed == some answer do
      throw (IO.userError s!"lowered known answer failed: {c.name}")
  unless (bits? 0 0).isNone && (bits? 8 256).isNone && (bits? 1 2).isNone do
    throw (IO.userError "invalid dynamic literals must be rejected")
  unless (bits? 8 255).isSome && (bits? 1 0).isSome do
    throw (IO.userError "fitting positive-width dynamic literals must be accepted")
  IO.println s!"{expected.length} Lean eDSL known answers and 6 negative typing checks passed"

end P4bloLean.ScalarTests
