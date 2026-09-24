import P4blo.TutorialFirewallReadback
import P4blo.TutorialFirewallBloomTests

namespace P4blo.TutorialFirewallReadbackTests
open P4bloIR P4bloIR.Execution TutorialFirewall

private def bits (width value : Nat) : Value := .bits (Bits.wrap width value)
private def answer (cells : Array Nat) (position : Nat) : Value :=
  let raw := if h : position < cells.size then cells[position] else 0
  .bits ⟨1, raw % 2, Nat.mod_lt _ (by decide)⟩

private def sameFrame (a b : Frame) : Bool :=
  GuardedCallPrefixTests.sameScope a.scope b.scope &&
  GuardedCallPrefixTests.sameMap (· == ·) a.vars b.vars && a.action == b.action &&
  match a.actionVars, b.actionVars with
  | none, none => true
  | some x, some y => GuardedCallPrefixTests.sameMap (· == ·) x y
  | _, _ => false

private def sameRun (a b : Run) : Bool :=
  sameFrame a.frame b.frame && GuardedCallPrefixTests.sameShared a b

private def initial (one two : Array Nat) (p q : Nat) (positions first second : Bool) : Run := Id.run do
  let base := TutorialFirewallBloomTests.initial one two p q positions
  let active := base.frame.actionVars.getD (Std.HashMap.ofList [("sibling", bits 13 99)])
  let active := if first then active.insert "reg_val_one" (.bool true) else active
  let active := if second then active.insert "reg_val_two" (bits 17 42) else active
  return { base with frame := { base.frame with
    vars := (base.frame.vars.insert "reg_val_one" (.bool false)).insert "reg_val_two" (bits 17 23)
    action := some "readback-overlay", actionVars := some active } }

/-- The expected storage layer is supplied by the independent case, not
discovered through the production frame read/write or the proved helper. -/
private def expected (frame : Frame) (name : String) (value : Value) (action : Bool) : Frame :=
  if action then { frame with actionVars := some ((frame.actionVars.getD {}).insert name value) }
  else { frame with vars := frame.vars.insert name value }

private def queue (work : List Work) (remaining : List Stmt) : Bool := match work with
  | [.statements body, .statement (.callAction "missing-readback-sentinel" [])] => body == remaining
  | _ => false

private def checkCase (before : Run) (one two : Array Nat) (p q : Nat) (first second : Bool) : IO Unit := do
  let start : Machine := { run := before, work := [
    .statements checkBloom, .statement (.callAction "missing-readback-sentinel" [])] }
  let firstExpected := { before with frame := expected before.frame "reg_val_one" (answer one p) first }
  let finalExpected := { firstExpected with
    frame := expected firstExpected.frame "reg_val_two" (answer two q) second }
  let firstEnd ← IO.ofExcept (GuardedCallPrefixTests.advance 2 start)
  unless sameRun firstEnd.run firstExpected && firstEnd.fault.isNone &&
      queue firstEnd.work [checkBloom[1]!, checkBloom[2]!] do
    throw (IO.userError "first read/copy-back changed full state or pending syntax")
  let short ← IO.ofExcept (GuardedCallPrefixTests.advance 3 start)
  unless sameRun short.run firstExpected && short.fault.isNone do
    throw (IO.userError "second read executed one step too soon")
  match short.work with
  | [.statement actual, .statements [condition], .statement (.callAction "missing-readback-sentinel" [])] =>
    unless actual == checkBloom[1]! && condition == checkBloom[2]! do
      throw (IO.userError "one-short readback queue changed")
  | _ => throw (IO.userError "one-short readback queue shape changed")
  let final ← IO.ofExcept (GuardedCallPrefixTests.advance 4 start)
  unless sameRun final.run finalExpected && final.fault.isNone &&
      queue final.work [checkBloom[2]!] do
    throw (IO.userError "two-read prefix changed state, conditional or continuation")
  -- Normal completion of the actual first two statements is a separate
  -- observation; the three-statement check itself has not completed here.
  let (outcome, completed) := (execute (checkBloom.take 2)).run before
  unless outcome.isOk && sameRun completed finalExpected do
    throw (IO.userError "two actual reads did not complete normally")

def run : IO Unit := do
  let arrays := [(#[], #[]), (#[0], #[0]), (#[1], #[1]),
    (#[1, 0, 0, 1], #[0, 1, 0]), (#[2, 3, 7, 0], #[3, 2, 7]),
    (Array.replicate 4096 0, Array.replicate 4096 1)]
  let positions := [(0, 0), (1, 2), (3, 1), (4095, 4095), (4096, 4096),
    (0xffffffff, 0xffffffff), (1, 1)]
  let mut count := 0
  for (one, two) in arrays do
    for (p, q) in positions do
      for overlay in [false, true] do
        for first in [false, true] do
          for second in [false, true] do
            checkCase (initial one two p q overlay first second) one two p q first second
            count := count + 1
  unless count == 336 do throw (IO.userError "readback profile inventory changed")
  checkCase (Bloom.initializedRun #[1] #[0]) #[1] #[0] 0 0 false false
  IO.println "337 readback profiles and exact first/one-short/two-read boundaries passed (56 native-only)"

end P4blo.TutorialFirewallReadbackTests
