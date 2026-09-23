import P4blo

/-!
# The checked trust boundary

This default build target checks the transitive axiom sets of advertised
theorems. A `sorry`, custom axiom, or native-evaluation escape changes the
diagnostic and fails the build. Standard Lean foundational axioms are
explicitly recorded; a legitimate smaller set requires reviewing this file.
This does not prove that the statements express the intended P4 semantics.
-/

/-- info: 'P4blo.ScalarTyping.Typed.sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarTyping.Typed.sound

/-- info: 'P4blo.ScalarTyping.check_sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarTyping.check_sound

/-- info: 'P4blo.extract_emit' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.extract_emit
