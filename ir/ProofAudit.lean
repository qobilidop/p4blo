import P4bloIR

/-- info: 'P4bloIR.Value.equal_bits' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.Value.equal_bits

/-- info: 'P4bloIR.Value.equal_bool' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.Value.equal_bool

/-!
# The checked trust boundary

This default build target checks the transitive axiom sets of advertised
theorems. A `sorry`, custom axiom, or native-evaluation escape changes the
diagnostic and fails the build. Standard Lean foundational axioms are
explicitly recorded; a legitimate smaller set requires reviewing this file.
This does not prove that the statements express the intended P4 semantics.
-/

/-- info: 'P4bloIR.ScalarTyping.Typed.sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarTyping.Typed.sound

/-- info: 'P4bloIR.ScalarTyping.check_sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarTyping.check_sound

/-- info: 'P4bloIR.ScalarTyping.checkIn_typed' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.ScalarTyping.checkIn_typed

/-- info: 'P4bloIR.ScalarTyping.checkIn_complete' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarTyping.checkIn_complete

/-- info: 'P4bloIR.ScalarTyping.check_complete' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarTyping.check_complete

/-- info: 'P4bloIR.ScalarTyping.TypedIn.sound_run' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarTyping.TypedIn.sound_run

/-- info: 'P4bloIR.ScalarTyping.checkIn_sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarTyping.checkIn_sound

/-- info: 'P4bloIR.extract_emit' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.extract_emit

/-- info: 'P4bloIR.Execution.drive.eq_def' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Execution.drive.eq_def

/-- info: 'P4bloIR.Execution.Finishes.sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Execution.Finishes.sound

/-- info: 'P4bloIR.Execution.run_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Execution.run_eq

/-- info: 'P4bloIR.ScalarLaws.addSat_overflow' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.addSat_overflow

/-- info: 'P4bloIR.ScalarLaws.subSat_underflow' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.subSat_underflow

/-- info: 'P4bloIR.ScalarLaws.shl_large' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.shl_large

/-- info: 'P4bloIR.ScalarLaws.shr_large' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.shr_large

/-- info: 'P4bloIR.ScalarLaws.max_value' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.max_value

/-- info: 'P4bloIR.ScalarLaws.evaluate_addSat_overflow' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.evaluate_addSat_overflow

/-- info: 'P4bloIR.ScalarLaws.evaluate_subSat_underflow' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.evaluate_subSat_underflow

/-- info: 'P4bloIR.ScalarLaws.and_false' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.and_false

/-- info: 'P4bloIR.ScalarLaws.or_true' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.or_true

/-- info: 'P4bloIR.ScalarLaws.mux_true' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.mux_true

/-- info: 'P4bloIR.ScalarLaws.mux_false' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarLaws.mux_false

/-- info: 'P4bloIR.ExecutionCertificate.bounded_finishes' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ExecutionCertificate.bounded_finishes

/-- info: 'P4bloIR.ExecutionCertificate.bounded_sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ExecutionCertificate.bounded_sound

/-- info: 'P4bloIR.ExecutionCertificate.check_sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ExecutionCertificate.check_sound
