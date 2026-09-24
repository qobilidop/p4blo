import P4blo.ForwardPolicy

/-! A separately named policy for already-parsed, route-selected inputs.
Invalid Ethernet or IPv4 sets only drop. This does not change the original
stored-value rewrite or establish parsing, routing, checksum or packet fate. -/

namespace P4blo.GuardedForwardPolicy

open Fields
open FieldCommandExamples (roots modes forward)
open ForwardPolicy (Snapshot observe restore)

def ethernet : HeaderRef roots := .mk .here (.field .here .here)
def ipv4 : HeaderRef roots := .mk .here (.field (.there .here) .here)

def guardedForward : Cmd modes :=
  let reject := Cmd.assign FieldCommandExamples.drop (.boolean true)
  Cmd.ite ethernet.isValid (Cmd.ite ipv4.isValid forward reject) reject

/-- Independent application intent: conjunction of the two stored validity
bits precedes the independent natural-number hit/TTL policy. -/
def policy (s : Snapshot) : Snapshot :=
  if s.ethernetValid && s.ipv4Valid then ForwardPolicy.policy s
  else { s with drop := true }

set_option maxRecDepth 4096 in
set_option backward.isDefEq.respectTransparency false in
theorem authored_policy (s : Snapshot) :
    observe (guardedForward.denote (restore s)) = policy s := by
  cases s with
  | mk dst src et ev ttl protocol checksum iv port drop sentinel hit rd rs rp scratch =>
    cases ev <;> cases iv
    · rfl
    · rfl
    · rfl
    · exact ForwardPolicy.authored_policy _

/-- Invalid inputs are included, not eliminated by a validity premise. -/
theorem source_policy (store : Store roots) :
    guardedForward.denote store = restore (policy (observe store)) := by
  have h := congrArg restore (authored_policy (observe store))
  simpa only [ForwardPolicy.restore_observe] using h

/-- Explicit full-state invalid branch, including all invalid stored fields. -/
theorem source_invalid (store : Store roots)
    (invalid : (observe store).ethernetValid = false ∨ (observe store).ipv4Valid = false) :
    guardedForward.denote store = restore { observe store with drop := true } := by
  rw [source_policy]
  rcases invalid with he | hi
  · simp [policy, he]
  · simp [policy, hi]

/-- Actual body execution under concrete declarations, root permissions and
exact initialized frame agreement; no arbitrary correctness callbacks. -/
theorem execute_policy (store : Store roots) (initial : P4bloIR.Run)
    (hi : roots.IndexAgrees initial.index)
    (hd : modes.Agrees initial.frame.scope)
    (hf : FrameMatches store initial.frame)
    (hb : P4bloIR.ScalarStatements.BlockFrame initial.frame) :
    P4bloIR.FieldTyping.BodyTyped initial.index initial.frame.scope guardedForward.lower ∧
    ∃ final, (P4bloIR.execute guardedForward.lower).run initial = (.ok (), final) ∧
      FrameMatches (restore (policy (observe store))) final.frame ∧
      modes.Agrees final.frame.scope ∧
      P4bloIR.ScalarStatements.ChangesOnlyVars initial final ∧
      P4bloIR.ScalarStatements.PreservesOutside guardedForward.targets initial final := by
  obtain ⟨typed, final, executed, hm, declarations, _, changes, outside⟩ :=
    guardedForward.execute_correct store initial FieldCommandExamples.rootWF hi hd hf hb
  exact ⟨typed, final, executed, source_policy store ▸ hm, declarations, changes, outside⟩

end P4blo.GuardedForwardPolicy
