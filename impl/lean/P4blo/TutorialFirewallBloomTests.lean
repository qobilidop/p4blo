import P4blo.TutorialFirewallBloom
import P4blo.TutorialFirewallTests

namespace P4blo.TutorialFirewallBloomTests
open P4bloIR P4bloIR.Execution TutorialFirewall

private def bits (width value : Nat) : Value := .bits (Bits.wrap width value)

private def sameFrame (a b : Frame) : Bool :=
  GuardedCallPrefixTests.sameScope a.scope b.scope &&
  GuardedCallPrefixTests.sameMap (· == ·) a.vars b.vars && a.action == b.action &&
  match a.actionVars, b.actionVars with
  | none, none => true
  | some x, some y => GuardedCallPrefixTests.sameMap (· == ·) x y
  | _, _ => false

private def sameRun (a b : Run) : Bool :=
  sameFrame a.frame b.frame && GuardedCallPrefixTests.sameShared a b

/-- Expected cells use literal enumeration, not the proved update helper or
the runtime register method. All unselected values are observed. -/
def expected (cells : Array Nat) (position : Nat) : Array Nat :=
  cells.mapIdx (fun i value => if i == position then 1 else value)

def initial (one two : Array Nat) (p q : Nat) (overlay : Bool) : Run := Id.run do
  let base := TutorialFirewallTests.initial true true false true 2
  let vars := (base.frame.vars.insert "reg_pos_one" (bits 32 p)).insert "reg_pos_two" (bits 32 q)
  let frame := if overlay then
    { base.frame with
      vars := (vars.insert "reg_pos_one" (.bool true)).insert "reg_pos_two" (.bool false)
      action := some "position-overlay"
      actionVars := some (Std.HashMap.ofList [
        ("reg_pos_one", bits 32 p), ("reg_pos_two", bits 32 q), ("sibling", bits 13 99)]) }
    else { base.frame with vars }
  return { base with frame, externs := ⟨(base.externs.instances.insert "bloom_filter_1"
    (.register 1 one)).insert "bloom_filter_2" (.register 1 two)⟩ }

def run : IO Unit := do
  let arrays := [(#[], #[]), (#[0], #[0]), (#[1], #[1]),
    (#[1, 0, 0, 1], #[0, 1, 0]),
    -- Arbitrary natural storage is native-only, not Python Bits(1, n).
    (#[3, 0, 7, 1], #[9, 1, 0]),
    (Array.replicate 4096 0, Array.replicate 4096 1)]
  let positions := [(0, 0), (1, 2), (3, 1), (4095, 4095), (4096, 4096),
    (0xffffffff, 0xffffffff), (1, 1)]
  let mut count := 0
  for (one, two) in arrays do
    for (p, q) in positions do
      for overlay in [false, true] do
        let before := initial one two p q overlay
        let firstExpected := { before with externs := ⟨before.externs.instances.insert
          "bloom_filter_1" (.register 1 (expected one p))⟩ }
        let finalExpected := { firstExpected with externs := ⟨firstExpected.externs.instances.insert
          "bloom_filter_2" (.register 1 (expected two q))⟩ }
        -- This extra statement must stay pending; it faults if executed.
        let tail : List Work := [.statement (.callAction "missing-sentinel" [])]
        match step { work := .statement insertBloom[0]! :: tail, run := before } with
        | .inr next =>
          unless sameRun next.run firstExpected && next.fault.isNone &&
              next.work.length == 1 do
            throw (IO.userError "first Bloom write changed full state or pending work")
          match next.work with
          | [.statement (.callAction "missing-sentinel" [])] => pure ()
          | _ => throw (IO.userError "first Bloom write changed pending syntax")
        | .inl _ => throw (IO.userError "first Bloom write completed pending work")
        let (outcome, final) := (execute insertBloom).run before
        unless outcome.isOk && sameRun final finalExpected do
          throw (IO.userError "Bloom insertion differs from independent whole-state answer")
        count := count + 1
  unless count == 84 do throw (IO.userError "missing Bloom insertion profiles")
  IO.println "84 whole Bloom insertion states and first-write boundaries passed (14 native-only)"

end P4blo.TutorialFirewallBloomTests
