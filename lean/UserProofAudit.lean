import P4blo.Scalar
import P4blo.ScalarCommands
import P4blo.Fields

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
