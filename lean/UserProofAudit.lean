import P4blo.Scalar

/-! Default build gate for the user library's advertised proof boundary.
Audit statements as well as axiom sets in review: standard foundations do
not guarantee that a theorem expresses its intended property. -/

/-- info: 'P4blo.Scalar.lower_typed' depends on axioms: [propext] -/
#guard_msgs in
#print axioms P4blo.Scalar.lower_typed

/-- info: 'P4blo.Scalar.evaluate_lower' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.evaluate_lower

/-- info: 'P4blo.Scalar.evaluate_lower_run' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4blo.Scalar.evaluate_lower_run
