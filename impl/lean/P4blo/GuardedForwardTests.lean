import P4blo.GuardedForwardPolicy
import P4bloArch.Externs

namespace P4blo.GuardedForwardTests

open Fields ForwardPolicy GuardedForwardPolicy

structure Case where
  name : String
  ttl : Fin 256
  ethernetValid : Bool
  ipv4Valid : Bool
  hit : Bool

def cases : List Case :=
  [false, true].flatMap fun ev =>
  [false, true].flatMap fun iv =>
  [false, true].flatMap fun hit =>
  ([0, 1, 2, 255] : List (Fin 256)).map fun ttl =>
    ⟨s!"guard-{ev}-{iv}-{hit}-{ttl.val}", ttl, ev, iv, hit⟩

/-- Asymmetric independent input, not the fixed exporter wrapper store. -/
def input (c : Case) (drop : Bool) : Snapshot :=
  ⟨0x112233445566, 0x778899aabbcc, 0x86dd, c.ethernetValid,
    c.ttl, 17, 0xfedc, c.ipv4Valid, 509, drop, 0x9876, c.hit,
    0x123456789abc, 0xcba987654321, 511, 213⟩

/-- Finite independent expected answers: explicit successor-boundary table,
not either policy function or command denotation. -/
def expected (c : Case) : Snapshot :=
  let s := input c true
  match c.ethernetValid, c.ipv4Valid, c.hit, c.ttl.val with
  | true, true, true, 2 =>
      { s with dst := 0x123456789abc, src := 0xcba987654321, ttl := 1, port := 511, drop := false }
  | true, true, true, 255 =>
      { s with dst := 0x123456789abc, src := 0xcba987654321, ttl := 254, port := 511, drop := false }
  | _, _, _, _ => s

-- These anchors survive coordinated edits to authored code and policy.
example : GuardedForwardPolicy.policy (input ⟨"", 2, false, true, true⟩ false) =
    input ⟨"", 2, false, true, true⟩ true := by decide +kernel
example : GuardedForwardPolicy.policy (input ⟨"", 2, true, false, true⟩ false) =
    input ⟨"", 2, true, false, true⟩ true := by decide +kernel
example : GuardedForwardPolicy.policy (input ⟨"", 2, true, true, true⟩ true) =
    expected ⟨"", 2, true, true, true⟩ := by decide +kernel

/-- Concrete nonvacuity witness for the new theorem, at every input store. -/
theorem initialized_correct (source : Store FieldCommandExamples.roots) :
    ∃ final, (P4bloIR.execute guardedForward.lower).run (FieldCommandExamples.initial source) =
        (.ok (), final) ∧
      FrameMatches (restore (GuardedForwardPolicy.policy (observe source))) final.frame := by
  obtain ⟨_, final, executed, hm, _, _, _⟩ :=
    GuardedForwardPolicy.execute_policy source (FieldCommandExamples.initial source)
      FieldCommandExamples.indexAgrees
      (FieldCommandExamples.modes.scope_agrees FieldCommandExamples.rootWF)
      (FieldCommandExamples.initial_matches source) ⟨rfl, rfl⟩
  exact ⟨final, executed, hm⟩

def run : IO Unit := do
  for c in cases do
    for priorDrop in [false, true] do
      let source := input c priorDrop
      let want := expected c
      unless GuardedForwardPolicy.policy source == want do
        throw (IO.userError s!"independent guarded policy: {c.name}")
      unless observe (guardedForward.denote (restore source)) == want do
        throw (IO.userError s!"independent guarded source: {c.name}")
      let initial := FieldCommandExamples.initial (restore source)
      let (result, final) := (P4bloIR.execute guardedForward.lower).run initial
      match result with
      | .error _ => throw (IO.userError s!"guarded execution: {c.name}")
      | .ok () => pure ()
      for root in ["hdr", "meta", "route", "scratch"] do
        unless final.frame.read? root == (restore want).bindings[root]? do
          throw (IO.userError s!"guarded exact root {root}: {c.name}")
      unless final.frame.read? "outside" == initial.frame.read? "outside" &&
          final.packet.map (fun p => (p.data, p.value, p.cursor)) ==
            initial.packet.map (fun p => (p.data, p.value, p.cursor)) &&
          final.emitter.map (fun e => (e.value, e.width)) ==
            initial.emitter.map (fun e => (e.value, e.width)) &&
          final.visits == initial.visits &&
          final.index.program == initial.index.program &&
          final.frame.scope.block == initial.frame.scope.block &&
          final.frame.action.isNone && final.frame.actionVars.isNone &&
          final.entries.any (fun e => e.defaults[("untouched", "table")]? ==
            some (some ⟨"action", []⟩)) &&
          (final.externs.instances["untouched-register"]?).any (fun state => state.register? == some (8, #[3, 9, 27])) do
        throw (IO.userError s!"guarded unrelated state: {c.name}")
  IO.println "64 guarded forwarding policy/source/runtime complete-state answers passed"

end P4blo.GuardedForwardTests
