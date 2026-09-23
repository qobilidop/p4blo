import P4blo.Scalar
import P4blo.HeaderFields
import P4blo.ScalarCommands
import P4blo.Fields
import P4blo.FieldExpressions
import P4blo.FieldCommandExamples
import P4blo.NamedFields
import P4blo.ForwardPolicy
import P4blo.SourceZero
import P4blo.GuardedForwardPolicy

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
