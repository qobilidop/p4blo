import P4blo.Scalar
import P4blo.ForwarderTables
import P4blo.HeaderFields
import P4blo.ScalarCommands
import P4blo.Fields
import P4blo.FieldExpressions
import P4blo.FieldCommandExamples
import P4blo.NamedFields
import P4blo.ForwardPolicy
import P4blo.SourceZero
import P4blo.InitialFrames
import P4blo.InitialFrameTests
import P4blo.GuardedForwardPolicy
import P4blo.CommandPrefixTests
import P4blo.CallEntryTests
import P4blo.CallBodyEntryTests
import P4blo.CallInitializerTests
import P4blo.CallReturnTests
import P4blo.GuardedCallPrefixTests
import P4blo.GuardedControlCallTests
import P4blo.ForwarderTests
import P4blo.FieldActionWriteTests
import P4blo.ForwarderAction

/-- info: 'P4blo.ForwarderAction.observe_restore' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.observe_restore

/-- info: 'P4blo.ForwarderAction.restore_observe' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.restore_observe

/-- info: 'P4blo.ForwarderAction.body_identity' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.body_identity

/-- info: 'P4blo.ForwarderAction.entry' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.entry

/-- info: 'P4blo.ForwarderAction.before_return' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.before_return

/-- info: 'P4blo.ForwarderAction.source_steps' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.source_steps

/-- info: 'P4blo.ForwarderAction.run_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.run_correct

/-- info: 'P4blo.ForwarderAction.result_matches' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.result_matches

/-- info: 'P4blo.ForwarderAction.changes_only_vars' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.changes_only_vars

/-- info: 'P4blo.ForwarderAction.preserves_outside' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.preserves_outside

/-- info: 'P4blo.ForwarderAction.populated_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderAction.populated_correct

/-- info: 'P4blo.Fields.FrameMatches.set_unshadowed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.FrameMatches.set_unshadowed

/-- info: 'P4blo.Fields.Ref.write_unshadowed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.write_unshadowed

/-- info: 'P4blo.Fields.Ref.write_matches_unshadowed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.write_matches_unshadowed

/-- info: 'P4blo.FieldActionWriteTests.active_write' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.FieldActionWriteTests.active_write

/-- info: 'P4blo.Forwarder.index_built' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Forwarder.index_built

/-- info: 'P4blo.Forwarder.frame_built' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Forwarder.frame_built

/-- info: 'P4blo.Forwarder.frame_block' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Forwarder.frame_block

/-- info: 'P4blo.Forwarder.frame_no_action' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Forwarder.frame_no_action

/-- info: 'P4blo.Forwarder.invalid_guard' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Forwarder.invalid_guard

/-- info: 'P4blo.Forwarder.invalid_ipv4_control_unchanged' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Forwarder.invalid_ipv4_control_unchanged

/-- info: 'P4blo.ForwarderTests.concrete_invalid' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTests.concrete_invalid

/-- info: 'P4blo.GuardedControlCall.body_prefix' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCall.body_prefix

/-- info: 'P4blo.GuardedControlCall.index_built' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCall.index_built

/-- info: 'P4blo.GuardedControlCall.block_lookup' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCall.block_lookup

/-- info: 'P4blo.GuardedControlCall.source_steps' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCall.source_steps

/-- info: 'P4blo.GuardedControlCall.call_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCall.call_correct

/-- info: 'P4blo.GuardedControlCall.changes_only_vars' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCall.changes_only_vars

/-- info: 'P4blo.GuardedControlCall.result_lookup' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCall.result_lookup

/-- info: 'P4blo.GuardedControlCall.preserves_outside' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCall.preserves_outside

/-- info: 'P4blo.GuardedControlCallTests.concrete_call' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedControlCallTests.concrete_call

/-- info: 'P4blo.GuardedCallPrefix.initializers_eq' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.GuardedCallPrefix.initializers_eq

/-- info: 'P4blo.GuardedCallPrefix.selected_body' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.GuardedCallPrefix.selected_body

/-- info: 'P4blo.GuardedCallPrefix.locals_typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedCallPrefix.locals_typed

/-- info: 'P4blo.GuardedCallPrefix.source_prefix' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedCallPrefix.source_prefix

/-- info: 'P4blo.GuardedCallPrefixTests.concrete_prefix' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedCallPrefixTests.concrete_prefix

/-- info: 'P4blo.CallEntry.WithBody.index_built' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.WithBody.index_built

/-- info: 'P4blo.CallEntry.WithBody.block_lookup' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.WithBody.block_lookup

/-- info: 'P4blo.CallEntry.WithBody.scope_block' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.WithBody.scope_block

/-- info: 'P4blo.CallEntry.WithBody.initialized' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.WithBody.initialized

/-- info: 'P4blo.CallEntry.source_entry_with_body' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.source_entry_with_body

/-- info: 'P4blo.CallBodyEntryTests.concrete_entry' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallBodyEntryTests.concrete_entry

/-- info: 'P4blo.CallInitializers.steps' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallInitializers.steps

/-- info: 'P4blo.CallInitializers.source_steps' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallInitializers.source_steps

/-- info: 'P4blo.CallInitializers.body_typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallInitializers.body_typed

/-- info: 'P4blo.CallInitializerTests.concrete_prefix' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallInitializerTests.concrete_prefix

/-- info: 'P4blo.CallInitializerTests.concrete_typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallInitializerTests.concrete_typed
/-- info: 'P4blo.CallReturnTests.concrete_return' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallReturnTests.concrete_return

/-- info: 'P4blo.GuardedForwardPolicy.authored_policy' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedForwardPolicy.authored_policy

/-- info: 'P4blo.GuardedForwardPolicy.source_policy' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedForwardPolicy.source_policy

/-- info: 'P4blo.GuardedForwardPolicy.source_invalid' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedForwardPolicy.source_invalid

/-- info: 'P4blo.GuardedForwardPolicy.execute_policy' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.GuardedForwardPolicy.execute_policy

/-- info: 'P4blo.CallEntry.index_built' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.index_built

/-- info: 'P4blo.CallEntry.initialized' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.initialized

/-- info: 'P4blo.CallEntry.source_entry' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.source_entry

/-- info: 'P4blo.CallEntryTests.concrete_entry' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntryTests.concrete_entry

/-- info: 'P4blo.CallEntry.bad_extra_built' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.bad_extra_built

/-- info: 'P4blo.CallEntry.bad_extra_zero' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.bad_extra_zero

/-- info: 'P4blo.CallEntry.bad_extra_premise' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CallEntry.bad_extra_premise


/-- info: 'P4blo.Fields.Shape.zeroWith_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Shape.zeroWith_correct

/-- info: 'P4blo.Fields.Layout.zeroWith_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Layout.zeroWith_correct

/-- info: 'P4blo.Fields.Shape.zero_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Shape.zero_correct

/-- info: 'P4blo.Fields.Read.typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Read.typed

/-- info: 'P4blo.Fields.Read.evaluate' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Read.evaluate

/-- info: 'P4blo.Fields.HeaderRef.denote_isValid' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Fields.HeaderRef.denote_isValid

/-- info: 'P4blo.Fields.HeaderRef.lower_isValid' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Fields.HeaderRef.lower_isValid

/-- info: 'P4blo.Fields.HeaderPath.evaluate' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.HeaderPath.evaluate

/-- info: 'P4blo.Fields.HeaderPath.typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.HeaderPath.typed

/-- info: 'P4blo.Fields.HeaderRef.evaluate' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.HeaderRef.evaluate

/-- info: 'P4blo.Fields.HeaderRef.typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.HeaderRef.typed

/-- info: 'P4blo.Fields.Ref.resolve_sound' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.resolve_sound

/-- info: 'P4blo.Fields.Ref.named_sound' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.named_sound

/-- info: 'P4blo.Fields.Ref.named_expr' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.named_expr

/-- info: 'P4blo.Fields.Place.resolve_sound' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Place.resolve_sound

/-- info: 'P4blo.Fields.Place.named_sound' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Place.named_sound

/-- info: 'P4blo.Fields.Place.named_lvalue' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Place.named_lvalue

/-- info: 'P4blo.ForwardPolicy.observe_restore' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.ForwardPolicy.observe_restore

/-- info: 'P4blo.ForwardPolicy.restore_observe' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.ForwardPolicy.restore_observe

/-- info: 'P4blo.ForwardPolicy.authored_policy' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwardPolicy.authored_policy

/-- info: 'P4blo.ForwardPolicy.source_policy' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwardPolicy.source_policy

/-- info: 'P4blo.ForwardPolicy.execute_policy' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwardPolicy.execute_policy

/-- info: 'P4blo.Scalar.CmdWith.block_singleton' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Scalar.CmdWith.block_singleton

/-- info: 'P4blo.Scalar.CmdWith.denoteWith_block' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Scalar.CmdWith.denoteWith_block

/-- info: 'P4blo.Scalar.CmdWith.lowerWith_block' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Scalar.CmdWith.lowerWith_block

/-- info: 'P4blo.Scalar.Cmd.denote_block' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Scalar.Cmd.denote_block

/-- info: 'P4blo.Scalar.Cmd.lower_block' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Scalar.Cmd.lower_block

/-- info: 'P4blo.Fields.Cmd.denote_block' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Fields.Cmd.denote_block

/-- info: 'P4blo.Fields.Cmd.lower_block' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Cmd.lower_block

/-- info: 'P4blo.Fields.Modes.scope_agrees' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Modes.scope_agrees

/-- info: 'P4blo.Fields.Modes.frame_matches' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Modes.frame_matches

/-- info: 'P4blo.Fields.Place.typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Place.typed

/-- info: 'P4blo.Fields.Cmd.validities' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Cmd.validities

/-- info: 'P4blo.Fields.Cmd.steps' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Cmd.steps

/-- info: 'P4blo.Fields.Cmd.execute_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Cmd.execute_correct

/-- info: 'P4blo.FieldCommandExamples.correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.FieldCommandExamples.correct

/-- info: 'P4blo.Scalar.CmdWith.denoteWith_seq' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Scalar.CmdWith.denoteWith_seq

/-- info: 'P4blo.Scalar.CmdWith.lowerWith_seq' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Scalar.CmdWith.lowerWith_seq

/-- info: 'P4blo.Scalar.CmdWith.steps_with' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.CmdWith.steps_with

/-- info: 'P4blo.Scalar.evaluate_lower_with' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.evaluate_lower_with

/-- info: 'P4blo.Fields.Ref.typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.typed

/-- info: 'P4blo.Fields.lower_typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.lower_typed

/-- info: 'P4blo.Fields.evaluate_lower' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.evaluate_lower

/-- info: 'P4blo.Fields.nominal_fields_unique' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.nominal_fields_unique

/-- info: 'P4blo.Fields.nominal_kind_unique' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.nominal_kind_unique

/-- info: 'P4blo.Fields.Record.get_set' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Fields.Record.get_set

/-- info: 'P4blo.Fields.Record.toValues_set' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Record.toValues_set

/-- info: 'P4blo.Fields.Path.get_set' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Fields.Path.get_set

/-- info: 'P4blo.Fields.Path.validities_set' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Path.validities_set

/-- info: 'P4blo.Fields.Path.evaluate' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Path.evaluate

/-- info: 'P4blo.Fields.Path.readLValue' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Path.readLValue

/-- info: 'P4blo.Fields.Path.writeLValue' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Path.writeLValue

/-- info: 'P4blo.Fields.Record.frame_matches' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Record.frame_matches

/-- info: 'P4blo.Fields.Ref.evaluate' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.evaluate

/-- info: 'P4blo.Fields.Ref.get_set' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.get_set

/-- info: 'P4blo.Fields.Ref.write_matches' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.write_matches

/-- info: 'P4blo.Fields.Ref.validities_set' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Ref.validities_set

/-! Default build gate for the user library's advertised proof boundary.
Audit statements as well as axiom sets in review: standard foundations do
not guarantee that a theorem expresses its intended property. -/

/-- info: 'P4blo.Scalar.lower_typed' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.lower_typed

/-- info: 'P4blo.Scalar.evaluate_lower' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.evaluate_lower

/-- info: 'P4blo.Scalar.evaluate_lower_run' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.evaluate_lower_run

/-- info: 'P4blo.Scalar.lower_typed_in' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.lower_typed_in

/-- info: 'P4blo.Scalar.evaluate_lower_in' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.evaluate_lower_in

/-- info: 'P4blo.Scalar.Env.frame_matches' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.Env.frame_matches

/-- info: 'P4blo.Scalar.FrameMatches.typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.FrameMatches.typed

/-- info: 'P4blo.Scalar.Modes.scope_agrees' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.Modes.scope_agrees

/-- info: 'P4blo.Scalar.Modes.frame_matches' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.Modes.frame_matches

/-- info: 'P4blo.Scalar.Place.canAssign' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.Place.canAssign

/-- info: 'P4blo.Scalar.Env.get_set' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Scalar.Env.get_set

/-- info: 'P4blo.Scalar.FrameMatches.set' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.FrameMatches.set

/-- info: 'P4blo.Scalar.Cmd.denote_seq' does not depend on any axioms -/
#guard_msgs in
#print axioms P4blo.Scalar.Cmd.denote_seq

/-- info: 'P4blo.Scalar.Cmd.lower_seq' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Scalar.Cmd.lower_seq

/-- info: 'P4blo.Scalar.Cmd.lower_typed' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.Cmd.lower_typed

/-- info: 'P4blo.Scalar.Cmd.steps' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.Cmd.steps

/-- info: 'P4blo.Scalar.Cmd.execute_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.Cmd.execute_correct

/-- info: 'P4blo.Fields.Layout.initialize' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Layout.initialize

/-- info: 'P4blo.Fields.Modes.scope_covers' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Modes.scope_covers

/-- info: 'P4blo.Fields.Modes.initialize' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Modes.initialize

/-- info: 'P4blo.InitialFrameTests.actualIndex_built' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.InitialFrameTests.actualIndex_built

/-- info: 'P4blo.InitialFrameTests.forward_initialized' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.InitialFrameTests.forward_initialized

/-- info: 'P4blo.InitialFrameTests.forward_expected' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.InitialFrameTests.forward_expected

/-- info: 'P4blo.InitialFrameTests.extras_initialized' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.InitialFrameTests.extras_initialized

/-- info: 'P4blo.Scalar.CmdWith.steps_prefix_with' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.CmdWith.steps_prefix_with

/-- info: 'P4blo.Scalar.Cmd.steps_prefix' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.Cmd.steps_prefix

/-- info: 'P4blo.Fields.Cmd.steps_prefix' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Fields.Cmd.steps_prefix

/-- info: 'P4blo.CommandPrefixTests.prefix_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.CommandPrefixTests.prefix_correct

/-- info: 'P4blo.ForwarderTables.installed_built' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.installed_built

/-- info: 'P4blo.ForwarderTables.installed_index' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.installed_index

/-- info: 'P4blo.ForwarderTables.installed_entries' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.installed_entries

/-- info: 'P4blo.ForwarderTables.installed_default' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.installed_default

/-- info: 'P4blo.ForwarderTables.installed_other_entries' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.installed_other_entries

/-- info: 'P4blo.ForwarderTables.installed_other_defaults' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.installed_other_defaults

/-- info: 'P4blo.ForwarderTables.lookup_correct' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.lookup_correct

/-- info: 'P4blo.ForwarderTables.restore_default' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.restore_default

/-- info: 'P4blo.ForwarderTables.order_independent' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.ForwarderTables.order_independent
