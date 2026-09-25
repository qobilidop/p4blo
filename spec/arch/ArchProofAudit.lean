import P4bloArch.ContractLaws
import ArchTests.NonVacuity

/-!
The axioms of the reference architecture's proofs, printed and pinned as
`spec/ir/P4bloIRTest/ProofAudit.lean` pins the IR's: each depends on Lean's three
standard axioms and nothing else (no `sorryAx`, no `Lean.ofReduceBool`
from `native_decide`). A new or changed dependency fails the build.
-/

/-- info: 'P4bloArch.Contract.matchShape_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloArch.Contract.matchShape_ok

/-- info: 'P4bloArch.Contract.stateFits_of' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloArch.Contract.stateFits_of

/-- info: 'P4bloArch.Contract.call_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloArch.Contract.call_ok

/-- info: 'P4bloArch.Contract.bind_inv' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloArch.Contract.bind_inv

/-- info: 'P4bloArch.Contract.bind_contract' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloArch.Contract.bind_contract

/-- info: 'P4bloArch.Contract.bind_exists_contract' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms P4bloArch.Contract.bind_exists_contract

/-- info: 'ArchTests.Csum16.check_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms ArchTests.Csum16.check_ok

/-- info: 'ArchTests.Csum16.control_start_ok' depends on axioms: [propext, Classical.choice, Quot.sound] -/
#guard_msgs in
#print axioms ArchTests.Csum16.control_start_ok
