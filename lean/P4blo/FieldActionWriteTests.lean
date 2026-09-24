import P4blo.FieldActionWrites

namespace P4blo.FieldActionWriteTests
open Fields P4bloIR

def boxFields : Layout := .cons "value" (.scalar (.bits 8)) .nil
def roots : Layout := .cons "holder" (.aggregate .struct "Box" boxFields)
  (.cons "shadow" (.scalar (.bits 8)) .nil)
def ref : Ref roots (.bits 8) := .mk .here (.field .here .scalar)
def store : Store roots := .cons (.aggregate () (.cons (.scalar 1) .nil))
  (.cons (.scalar 7) .nil)
def value (n : Nat) : Value := .bits (Bits.wrap 8 n)

def program : Program := { (default : Program) with structTypes := [⟨"Box", boxFields.fields⟩] }
def index : Index := (Index.build program).toOption.getD default
def active : Run :=
  { index
    frame := {
      scope := default
      vars := (({} : Std.HashMap String Value).insert "holder" (.struct "Box" [value 1]))
        |>.insert "shadow" (value 99) |>.insert "untouched" (.bool true)
      action := some "observed-action"
      actionVars := some ((({} : Std.HashMap String Value).insert "shadow" (value 7))
        |>.insert "sentinel" (value 23)) }
    visits := ({} : Std.HashMap (String × String) Nat).insert ("a", "b") 13 }

theorem built : Index.build program = .ok index := by cbv
theorem agrees : roots.IndexAgrees index := by cbv; simp
theorem frame_matches : FrameMatches store active.frame := by
  intro shape root
  cases root with
  | here => cbv
  | there root => cases root with
    | here => cbv
    | there root => cases root

/-- A genuine active action frame; the other modeled root is action-shadowed.
Its block-map decoy is an operational observation, not a valid declaration. -/
theorem active_write :
    ∃ final, (writeLValue ref.lvalue (value 2)).run active = (.ok (), final) ∧
      FrameMatches (ref.set store 2) final.frame ∧
      ScalarStatements.ChangesOnlyVars active final ∧
      ScalarStatements.PreservesOutside ["holder"] active final := by
  exact Ref.write_matches_unshadowed ref store 2 active agrees frame_matches (by decide) (by cbv)

example : ¬ ScalarStatements.BlockFrame active.frame := by simp [ScalarStatements.BlockFrame, active]
example : active.frame.actionVars.bind (·["shadow"]?) ≠ none := by cbv; simp
example : active.frame.vars["shadow"]? = some (value 99) := by cbv
example : active.frame.read? "shadow" = some (value 7) := by cbv

def run : IO Unit := do
  let (outcome, final) := (writeLValue ref.lvalue (value 2)).run active
  unless outcome.isOk && final.frame.vars["holder"]? == some (.struct "Box" [value 2]) &&
      final.frame.vars["shadow"]? == some (value 99) &&
      final.frame.read? "shadow" == some (value 7) &&
      final.frame.vars["untouched"]? == some (.bool true) &&
      final.frame.action == some "observed-action" &&
      final.frame.actionVars.map (·.toList) == active.frame.actionVars.map (·.toList) &&
      final.visits.toList == active.visits.toList do
    throw (IO.userError "unshadowed aggregate write damaged the active/block layer")
  let (shadowResult, shadowFinal) := (writeVar "shadow" (value 11)).run active
  unless shadowResult.isOk && shadowFinal.frame.read? "shadow" == some (value 11) &&
      shadowFinal.frame.vars["shadow"]? == some (value 99) &&
      shadowFinal.frame.vars["holder"]? == active.frame.vars["holder"]? &&
      shadowFinal.frame.action == some "observed-action" do
    throw (IO.userError "a shadowed root must write only the action layer")
  IO.println "Mixed unshadowed aggregate and shadowed action write witnesses passed"

end P4blo.FieldActionWriteTests
