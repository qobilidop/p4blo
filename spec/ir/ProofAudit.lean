import P4bloIR
import P4bloIR.ScalarStatements
import P4bloIR.Validity.KindLaws
import P4bloIR.Validity.EntryLaws
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

/-- info: 'P4bloIR.DeviationLaws.header_equal_invalid' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.header_equal_invalid

/-- info: 'P4bloIR.DeviationLaws.header_equal_valid_invalid' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.header_equal_valid_invalid

/-- info: 'P4bloIR.DeviationLaws.header_equal_invalid_valid' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.header_equal_invalid_valid

/-- info: 'P4bloIR.DeviationLaws.header_equal_valid' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.header_equal_valid

/-- info: 'P4bloIR.DeviationLaws.evaluate_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_eq

/-- info: 'P4bloIR.DeviationLaws.evaluate_eq_invalid_headers' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_eq_invalid_headers

/-- info: 'P4bloIR.DeviationLaws.evaluate_eq_valid_invalid' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_eq_valid_invalid

/-- info: 'P4bloIR.DeviationLaws.evaluate_ne' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_ne

/-- info: 'P4bloIR.DeviationLaws.evaluate_ne_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_ne_eq

/-- info: 'P4bloIR.DeviationLaws.evaluate_ne_eq_error' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_ne_eq_error

/-- info: 'P4bloIR.DeviationLaws.equal_bits_iff' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.equal_bits_iff

/-- info: 'P4bloIR.DeviationLaws.equal_bool_iff' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.equal_bool_iff

/-- info: 'P4bloIR.DeviationLaws.equalList_cons' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.equalList_cons

/-- info: 'P4bloIR.DeviationLaws.equalList_scalar_iff' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.equalList_scalar_iff

/-- info: 'P4bloIR.DeviationLaws.header_equal_valid_iff' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.header_equal_valid_iff

/-- info: 'P4bloIR.DeviationLaws.zeroHeader_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.zeroHeader_eq

/-- info: 'P4bloIR.DeviationLaws.zero_bits' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.zero_bits

/-- info: 'P4bloIR.DeviationLaws.zero_boolean' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.zero_boolean

/-- info: 'P4bloIR.DeviationLaws.zero_error' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.zero_error

/-- info: 'P4bloIR.DeviationLaws.elementOf_out_of_range' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.elementOf_out_of_range

/-- info: 'P4bloIR.DeviationLaws.evaluate_index_out_of_range' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_index_out_of_range

/-- info: 'P4bloIR.DeviationLaws.readLValue_index_out_of_range' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.readLValue_index_out_of_range

/-- info: 'P4bloIR.DeviationLaws.writeLValue_index_out_of_range' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.writeLValue_index_out_of_range

/-- info: 'P4bloIR.DeviationLaws.writeLValue_member_out_of_range' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.writeLValue_member_out_of_range

/-- info: 'P4bloIR.DeviationLaws.evaluate_lastIndex' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_lastIndex

/-- info: 'P4bloIR.DeviationLaws.lastIndex_empty' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.lastIndex_empty

/-- info: 'P4bloIR.DeviationLaws.lastIndex_nonempty' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.lastIndex_nonempty

/-- info: 'P4bloIR.DeviationLaws.evaluate_last_empty' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_last_empty

/-- info: 'P4bloIR.DeviationLaws.evaluate_last_nonempty' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_last_nonempty

/-- info: 'P4bloIR.DeviationLaws.pushFront_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.pushFront_eq

/-- info: 'P4bloIR.DeviationLaws.pushFront_spec' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.pushFront_spec

/-- info: 'P4bloIR.DeviationLaws.pushFront_clamp' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.pushFront_clamp

/-- info: 'P4bloIR.DeviationLaws.popFront_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.popFront_eq

/-- info: 'P4bloIR.DeviationLaws.popFront_spec' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.popFront_spec

/-- info: 'P4bloIR.DeviationLaws.popFront_clamp' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.popFront_clamp

/-- info: 'P4bloIR.DeviationLaws.evaluate_shl_large' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_shl_large

/-- info: 'P4bloIR.DeviationLaws.evaluate_shr_large' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.evaluate_shr_large

/-- info: 'P4bloIR.DeviationLaws.wrap_zero_value' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.wrap_zero_value

/-- info: 'P4bloIR.DeviationLaws.write_fits' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.write_fits

/-- info: 'P4bloIR.DeviationLaws.toBytes_padded' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.toBytes_padded

/-- info: 'P4bloIR.DeviationLaws.enterState_revisit' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.enterState_revisit

/-- info: 'P4bloIR.DeviationLaws.enterState_first' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.enterState_first

/-- info: 'P4bloIR.DeviationLaws.enterState_again' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.enterState_again

/-- info: 'P4bloIR.DeviationLaws.step_state_revisit' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.step_state_revisit

/-- info: 'P4bloIR.DeviationLaws.step_advances' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.step_advances

/-- info: 'P4bloIR.DeviationLaws.reaches_advances' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.reaches_advances

/-- info: 'P4bloIR.DeviationLaws.reaches_cursor_le' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.reaches_cursor_le

/-- info: 'P4bloIR.DeviationLaws.recorded_empty' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.recorded_empty

/-- info: 'P4bloIR.DeviationLaws.recorded_of_advances' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.recorded_of_advances

/-- info: 'P4bloIR.DeviationLaws.reaches_recorded' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.reaches_recorded

/-- info: 'P4bloIR.DeviationLaws.enterState_advanced' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.enterState_advanced

/-- info: 'P4bloIR.DeviationLaws.enterState_no_consumption' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.enterState_no_consumption

/-- info: 'P4bloIR.DeviationLaws.reaches_state_revisit' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.reaches_state_revisit

/-- info: 'P4bloIR.DeviationLaws.prefixLength_eq' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.prefixLength_eq

/-- info: 'P4bloIR.DeviationLaws.prefixLength_single' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.prefixLength_single

/-- info: 'P4bloIR.DeviationLaws.rank_lpm' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.rank_lpm

/-- info: 'P4bloIR.DeviationLaws.keyValueMatches_exact' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.keyValueMatches_exact

/-- info: 'P4bloIR.DeviationLaws.keyValueMatches_lpm' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.keyValueMatches_lpm

/-- info: 'P4bloIR.DeviationLaws.keyValueMatches_ternary' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.keyValueMatches_ternary

/-- info: 'P4bloIR.DeviationLaws.lookup_hit' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.lookup_hit

/-- info: 'P4bloIR.DeviationLaws.lookup_miss' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.lookup_miss

/-- info: 'P4bloIR.DeviationLaws.lookup_longest_prefix' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.lookup_longest_prefix

/-- info: 'P4bloIR.DeviationLaws.lookup_longest_lpm' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.DeviationLaws.lookup_longest_lpm

/-- info: 'P4bloIR.Build.index_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Build.index_eq

/-- info: 'P4bloIR.Build.addAll_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Build.addAll_ok

/-- info: 'P4bloIR.Build.scope_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Build.scope_ok

/-- info: 'P4bloIR.Build.index_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Build.index_ok

/-- info: 'P4bloIR.Build.build_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Build.build_ok

/-- info: 'P4bloIR.Validity.checkExpr_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.checkExpr_ok

/-- info: 'P4bloIR.Validity.checkLValue_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.checkLValue_ok

/-- info: 'P4bloIR.Validity.checkStmt_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.checkStmt_ok

/-- info: 'P4bloIR.Validity.checkTable_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.checkTable_ok

/-- info: 'P4bloIR.Validity.checkBlock_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.checkBlock_ok

/-- info: 'P4bloIR.Validity.check_sound' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.check_sound

/-- info: 'P4bloIR.Validity.evaluate_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.evaluate_ok

/-- info: 'P4bloIR.Validity.readLValue_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.readLValue_ok

/-- info: 'P4bloIR.Validity.writeLValue_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.writeLValue_ok

/-- info: 'P4bloIR.Validity.resolveLValue_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.resolveLValue_ok

/-- info: 'P4bloIR.Validity.copyIn_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.copyIn_ok

/-- info: 'P4bloIR.Validity.copyBack_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.copyBack_ok

/-- info: 'P4bloIR.Validity.forBlock_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.forBlock_ok

/-- info: 'P4bloIR.Validity.callExtern_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.callExtern_ok

/-- info: 'P4bloIR.Validity.extract_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.extract_ok

/-- info: 'P4bloIR.Validity.emitValue_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.emitValue_ok

/-- info: 'P4bloIR.Validity.select_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.select_ok

/-- info: 'P4bloIR.Validity.dispatch_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.dispatch_ok

/-- info: 'P4bloIR.Validity.blockReturn_unwind' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.blockReturn_unwind

/-- info: 'P4bloIR.Validity.progress' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.progress

/-- info: 'P4bloIR.Validity.Steps.machineOk' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Steps.machineOk

/-- info: 'P4bloIR.Validity.finishes_documented' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.finishes_documented

/-- info: 'P4bloIR.Validity.drive_documented' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.drive_documented

/-- info: 'P4bloIR.Validity.initial_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.initial_ok

/-- info: 'P4bloIR.Validity.entryFrame_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.entryFrame_ok

/-- info: 'P4bloIR.Validity.build_instOk' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.build_instOk

/-- info: 'P4bloIR.Validity.lookup_succeeds' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.lookup_succeeds

/-- info: 'P4bloIR.Validity.lookup_action' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.lookup_action

/-- info: 'P4bloIR.Validity.build_installedOk' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.build_installedOk

/-- info: 'P4bloIR.Validity.dispatch_np' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.dispatch_np

/-- info: 'P4bloIR.Validity.progress_outside_parser' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.progress_outside_parser

/-- info: 'P4bloIR.Validity.Steps.machineOkNP' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Steps.machineOkNP

/-- info: 'P4bloIR.Validity.finishes_outside_parser' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.finishes_outside_parser

/-- info: 'P4bloIR.Validity.finishes_kind' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.finishes_kind

/-- info: 'P4bloIR.Validity.parse_error_is_parser' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.parse_error_is_parser

/-- info: 'P4bloIR.Validity.Entry.runParser_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Entry.runParser_eq

/-- info: 'P4bloIR.Validity.Entry.runControl_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Entry.runControl_eq

/-- info: 'P4bloIR.Validity.Entry.runDeparser_eq' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Entry.runDeparser_eq

/-- info: 'P4bloIR.Validity.Entry.finishes_runOk' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Entry.finishes_runOk

/-- info: 'P4bloIR.Validity.Entry.runParser_documented' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Entry.runParser_documented

/-- info: 'P4bloIR.Validity.Entry.runControl_documented' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Entry.runControl_documented

/-- info: 'P4bloIR.Validity.Entry.runDeparser_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloIR.Validity.Entry.runDeparser_ok
