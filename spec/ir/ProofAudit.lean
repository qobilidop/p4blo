import P4bloIR
import P4bloIR.ScalarStatements
import Tests.ScalarStatements

/-- info: 'P4bloIR.PlainCallReturn.copyBack_three' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallReturn.copyBack_three

/-- info: 'P4bloIR.PlainCallReturn.dispatch_return' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallReturn.dispatch_return

/-- info: 'P4bloIR.PlainCallReturn.return_steps' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallReturn.return_steps

/-- info: 'P4bloIR.PlainCallReturn.return_step' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallReturn.return_step

/-- info: 'P4bloIR.PlainCallReturn.returned_lookup' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallReturn.returned_lookup

/-- info: 'P4bloIR.PlainCallReturn.returned_preserves' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallReturn.returned_preserves

/-- info: 'P4bloIR.PlainCallReturn.returned_scope' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallReturn.returned_scope

/-- info: 'P4bloIR.PlainCallReturn.returned_blockFrame' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallReturn.returned_blockFrame


/-- info: 'P4bloIR.PlainCallEntry.dispatch_entry' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallEntry.dispatch_entry

/-- info: 'P4bloIR.PlainCallEntry.entry_steps' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallEntry.entry_steps

/-- info: 'P4bloIR.PlainCallEntry.argument_out' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallEntry.argument_out

/-- info: 'P4bloIR.PlainCallEntry.unknown_block' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallEntry.unknown_block

/-- info: 'P4bloIR.PlainCallEntry.wrong_arity' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.PlainCallEntry.wrong_arity


/-- info: 'P4bloIR.FieldLaws.Declared.fields_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.FieldLaws.Declared.fields_eq

/-- info: 'P4bloIR.FieldLaws.Declared.position' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.FieldLaws.Declared.position

/-- info: 'P4bloIR.FieldLaws.fieldOf_pack' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.FieldLaws.fieldOf_pack

/-- info: 'P4bloIR.FieldLaws.setField_pack' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.FieldLaws.setField_pack

/-- info: 'P4bloIR.FieldLaws.read_declared' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.FieldLaws.read_declared

/-- info: 'P4bloIR.FieldLaws.update_declared' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.FieldLaws.update_declared

/-- info: 'P4bloIR.ScalarStatements.writeVar_block' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarStatements.writeVar_block

/-- info: 'P4bloIR.ScalarStatements.writeVar_block_unshadowed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarStatements.writeVar_block_unshadowed

/-- info: 'P4bloIR.ScalarStatements.readVar_action' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarStatements.readVar_action

/-- info: 'P4bloIR.ScalarStatements.writeVar_action' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.ScalarStatements.writeVar_action

/-- info: 'ScalarStatementTests.unshadowed_witness' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms ScalarStatementTests.unshadowed_witness

/-- info: 'P4bloIR.Execution.Steps.finishes' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Execution.Steps.finishes

/-- info: 'P4bloIR.Execution.Steps.execute' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Execution.Steps.execute

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

/-- info: 'P4bloIR.Frame.forBlock_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Frame.forBlock_correct

/-- info: 'P4bloIR.Frame.forBlock_initialized' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Frame.forBlock_initialized

/-- info: 'P4bloIR.Frame.forBlock_missing' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Frame.forBlock_missing
