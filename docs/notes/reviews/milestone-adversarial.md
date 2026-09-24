# Finite adversarial command review

2026-09-23. Independent integrator review of the runner in
`work/milestone-adversarial`, based on `7bfdcca`. **CLEAR** for the finite
catalogue and fail-closed orchestration, subject to the final combined release
gates. No implementation changes were made by this reviewer in the candidate.

Read the entry script, complete runner, 21 orchestration tests and evidence
note. The three inputs are reconstructed from tracked fixtures, checked against
fixed fingerprints, and compared with independent expected packet/state
answers. Ten existing sensitivity cases are selected by exact node identity;
the JUnit gate rejects changed counts, renamed cases, skips and setup failures.
The new output directory refuses reuse. Full source, test, runner and lockfile
provenance is recorded and checked again after the experiment.

Faults change only a fresh spec source copy. CRC32 XOR one must compile into
the actual interpreter and yield exactly three state-only divergences without
packet/error/diagnostic differences. The paired BlockKind change builds the
unchanged roundtrip audits. Corrupting the independent descriptor then makes
the selected weak equality survive, while six exact native literal/constructor
failures are required. An arbitrary crash or build failure cannot count as a
kill. Source restoration uses exact original bytes in `finally`; final success
also requires restored builds, native anchors and the saved input replays.

Two earlier review requests are resolved: provenance now covers both engines
and the Python fixtures/tools, and timeout cleanup handles the process-exit
race and signal denial while always attempting bounded reaping. Failure to
reap or denial is reported as cleanup uncertainty. The subprocess group belongs
to that command's new session; no global cleanup is performed. The note correctly
warns that a failed experiment can retain a faulty scratch binary even after
source restoration, so only a fully passing run attests the rebuilt result.

Independent checks executed against frozen candidate sources/binaries:

- All 21 orchestration tests passed, exit 0, including wrong detector outcome,
  restoration, duplicate output, skip/count/identity and timeout controls.
- Checked final JUnit identities and the three complete-input fingerprints.
- Replayed all three baseline inputs on the restored scratch interpreter:
  six requests agree. Replayed the retained CRC-fault input bundle on that
  restored interpreter: all four requests agree.
- Inspected the final run's phase results and native diagnostic: baseline and
  restored builds/audits succeed; actual CRC build succeeds before its three
  disagreements; paired codec/observer builds succeed; exactly the six intended
  native anchors fail. The owner ran the complete final campaign; this review
  did not independently rerun every live mutation.

No remaining implementation blocker found. Main owns the final independent
clean-checkout campaign, integration with later codec fixtures and the required
full gates. This catalogue is finite sensitivity evidence; no mutation score or
universal correctness claim follows from it.
