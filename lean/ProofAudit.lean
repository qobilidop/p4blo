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

/-- info: 'P4blo.Execution.drive.eq_def' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Execution.drive.eq_def

/-- info: 'P4blo.Execution.Finishes.sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Execution.Finishes.sound

/-- info: 'P4blo.Execution.run_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Execution.run_eq

/-- info: 'P4blo.ScalarLaws.addSat_overflow' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.addSat_overflow

/-- info: 'P4blo.ScalarLaws.subSat_underflow' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.subSat_underflow

/-- info: 'P4blo.ScalarLaws.shl_large' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.shl_large

/-- info: 'P4blo.ScalarLaws.shr_large' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.shr_large

/-- info: 'P4blo.ScalarLaws.max_value' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.max_value

/-- info: 'P4blo.ScalarLaws.evaluate_addSat_overflow' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.evaluate_addSat_overflow

/-- info: 'P4blo.ScalarLaws.evaluate_subSat_underflow' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.evaluate_subSat_underflow

/-- info: 'P4blo.ScalarLaws.and_false' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.and_false

/-- info: 'P4blo.ScalarLaws.or_true' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.or_true

/-- info: 'P4blo.ScalarLaws.mux_true' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.mux_true

/-- info: 'P4blo.ScalarLaws.mux_false' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ScalarLaws.mux_false
