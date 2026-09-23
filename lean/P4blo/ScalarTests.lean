import P4blo.ScalarExamples

namespace P4blo.ScalarTests

open Scalar
open scoped Scalar

-- These are compile-time rejection tests. Each must fail to elaborate,
-- independently of whether a downstream IR validator would reject it.
example : True := by
  fail_if_success have bad : Expr (.bits 0) := bits[0, 0]
  trivial

example : True := by
  fail_if_success have bad : Expr (.bits 8) := bits[8, 256]
  trivial

example : True := by
  fail_if_success have bad : Expr (.bits 8) := bits[8, 1] + bits[7, 1]
  trivial

example : True := by
  fail_if_success have bad : Expr .boolean := bits[8, 1] === bits[7, 1]
  trivial

example : True := by
  fail_if_success have bad : Expr (.bits 8) := Expr.mux bits[1, 1] bits[8, 1] bits[8, 2]
  trivial

example : True := by
  fail_if_success have bad : Expr (.bits 8) := Expr.mux (.boolean true) bits[8, 1] bits[7, 1]
  trivial

example : Expr (.bits 8) := Expr.mux (.boolean true) bits[8, 1] bits[8, 2]

example : True := by
  fail_if_success have bad : Ref [("x", .bits 8)] (.bits 7) := .here
  trivial

example : True := by
  fail_if_success have bad : Ref [] (.bits 8) := .here
  trivial

example : True := by
  fail_if_success have bad : ExprIn ScalarExamples.inputs (.bits 8) := .mux ScalarExamples.x ScalarExamples.x ScalarExamples.y
  trivial

-- Symbolic literals require ordinary kernel-checked proof arguments.
example (w n : Nat) (hw : 0 < w) (hn : n < 2 ^ w) : Expr (.bits w) :=
  bits w n hw hn

private def single : Context := [("x", .bits 8)]
private def nineteen : Env single := .cons 19 .nil
private def shadow : P4bloIR.Frame := { nineteen.frame with
  action := some "test", actionVars := some (({} : Std.HashMap String P4bloIR.Value).insert
    "x" (.bits (P4bloIR.Bits.wrap 8 42))) }

-- Kernel-checked nonvacuity, and premise failures that the preservation
-- theorem must not silently turn into claims about malformed executions.
example : FrameMatches nineteen nineteen.frame := nineteen.frame_matches (by decide)
example : ¬FrameMatches nineteen { scope := default, vars := {} } := by
  intro h
  have impossible := h .here
  simp [P4bloIR.Frame.read?, Ref.name] at impossible
example : ¬FrameMatches nineteen shadow := by
  intro h
  have impossible := h .here
  simp [shadow, P4bloIR.Frame.read?, Ref.name, nineteen, toValue,
    P4bloIR.Bits.wrap] at impossible
  change (42 : Nat) = 19 at impossible
  contradiction
example : FrameMatches (.cons 42 .nil : Env single) shadow := by
  intro t ref
  cases ref with
  | here =>
    simp [shadow, P4bloIR.Frame.read?, Ref.name, Env.get, toValue, P4bloIR.Bits.wrap]
    rfl
  | there ref => cases ref
example : ¬FrameMatches nineteen
    { nineteen.frame with vars := (({} : Std.HashMap String P4bloIR.Value).insert
      "x" (.bits (P4bloIR.Bits.wrap 7 19))) } := by
  intro h
  have impossible := h .here
  simp [P4bloIR.Frame.read?, Ref.name, nineteen, Env.frame, toValue,
    P4bloIR.Bits.wrap] at impossible

private def observed : P4bloIR.Value → Option Nat
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
    let initial : P4bloIR.Run := { index := default, frame := default }
    let (actual, _) := (P4bloIR.evaluate (lower c.expression)).run initial
    unless actual.toOption.bind observed == some answer do
      throw (IO.userError s!"lowered known answer failed: {c.name}")
  let openExpected := [19, 7, 26, 1, 19, 7, 1, 0]
  unless openExpected.length == ScalarExamples.openCases.length do
    throw (IO.userError "open scalar examples and known answers differ in length")
  for (c, answer) in ScalarExamples.openCases.zip openExpected do
    unless observed (toValue (denoteIn c.environment c.expression)) == some answer do
      throw (IO.userError s!"open source known answer failed: {c.name}")
    let initial : P4bloIR.Run := { index := default, frame := c.environment.frame }
    let (actual, _) := (P4bloIR.evaluate (lower c.expression)).run initial
    unless actual.toOption.bind observed == some answer do
      throw (IO.userError s!"open lowered known answer failed: {c.name}")
  let env := ScalarExamples.values 19 7 true
  let shadowed := { env.frame with
    action := some "test", actionVars := some (({} : Std.HashMap String P4bloIR.Value).insert
      "x" (.bits (P4bloIR.Bits.wrap 8 42))) }
  let initial : P4bloIR.Run := { index := default, frame := shadowed }
  let (actual, _) := (P4bloIR.evaluate (lower ScalarExamples.x)).run initial
  unless actual.toOption.bind observed == some 42 do
    throw (IO.userError "action binding must shadow block binding")
  unless (bits? 0 0).isNone && (bits? 8 256).isNone && (bits? 1 2).isNone do
    throw (IO.userError "invalid dynamic literals must be rejected")
  unless (bits? 8 255).isSome && (bits? 1 0).isSome do
    throw (IO.userError "fitting positive-width dynamic literals must be accepted")
  IO.println s!"{expected.length + openExpected.length} Lean eDSL known answers, action shadowing and 9 negative typing checks passed"

end P4blo.ScalarTests
