# Assurance milestone 1 scope review

Final scope review: CLEAR after two narrow documentation corrections.
This approves the finite acceptance boundary, not milestone completion.

Read the pending main changes to AGENTS.md, milestone-1.md, status.md,
decisions.md, implementation.md and verification.md, plus the new parked-proofs
handoff. Inspected relevant existing coverage, codec, conformance and execution
interfaces read-only. No implementation, tests, builds or proof expansion.

## Finite acceptance and claim

The six checkboxes and three closeout batches bound the work to the current
syntax/runtime/schema profile at 54e3c65, the existing corpus and two runnable
flagship applications. They distinguish tested Python/Lean conformance,
selected Lean proofs and independent external observations. No mutation/test
count is presented as a probability or universal correctness claim. The
milestone does not trigger a protobuf version migration.

AGENTS now explicitly says to complete this checklist and stop. Status and
the two broader roadmap documents explicitly defer their older open-ended
obligations to the new boundary. Optional Export/Program composition cannot
become an open-ended release blocker. Complete validator, termination,
application/pipeline and frontend proofs remain non-blockers. Existing
universal component proofs remain valuable without requiring the next theorem.

The adversarial criterion selects a finite catalogue rather than demanding
every historical experiment rerun. It still requires meaningful classification
of setup failures, equivalent/undetected faults, and independently reproduced
sensitivity. Clean-checkout reproduction cannot rely on ignored artifacts or
temporary worktrees alone. The usability criterion is concrete existing
two-language author/run paths, not an invitation to redesign either eDSL.

## Findings resolved

1. The first draft status still called readback/ingress active. The revised
   entries explicitly park both, linked to parked-proofs.md. Independently
   checked worktree HEADs/status against that handoff: readback b3defb4 has the
   three untracked drafts; ingress 9a12253 retains uncommitted source,
   registrations/exporter/tests. Unexecuted or failing Python work is labeled;
   standalone/native success is not represented as final acceptance. No release
   result depends on these local trees.
2. The original invalid-configuration sentence could imply transactional
   rollback of execution faults. It now applies specifically to host
   configurations rejected by decode, validation or installation before packet
   execution, and explicitly disclaims rollback after execution errors in an
   accepted program. This matches the intended boundary without changing
   existing partial-state/error semantics.

XDP remains an existing separately reported experiment, not P4-profile
evidence. Current status attributes four successful P4-related workflows and
the failing upstream-dependent XDP job separately. It does not call all CI
green, disable the check or turn unavailability into passing evidence. CI
results are root-attributed; this review did not fetch or rerun them.

## Closeout guidance, not added scope

The matrix should pin actual executable tests per semantic family, not use the
old corpus prose as current evidence: coverage.md still calls established
programs "in flight" and says the corpus lacks operations now used by the
firewall. Updating that summary is documentation closeout, not a language gap.

The current input profile must explicitly distinguish canonical protobuf JSON
from arbitrary accepted JSON: Python's public parser and Lean's adapter do not
have identical unknown-field/alias behavior. Record and test the chosen current
boundary rather than promising unrestricted ProtoJSON equivalence or creating
a new compatibility/version framework.

Missing evidence should lead to a small fixture/regression or explicit scoped
qualification. It must not silently broaden into new parser, call, table or
Bloom proof projects. The parked proofs stay parked. A separate finite evidence
audit can map existing checks and identify any concrete uncovered risk.

No remaining scope blocker found. Completion still requires checking off the
accepted evidence, interchange, usability and final-gate tasks on a named final
revision; this review approves no checkbox merely because its plan is sound.
