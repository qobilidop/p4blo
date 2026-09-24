# Milestone 1 release-evidence review

2026-09-23. Independent read-only audit of frozen code-gate revision
`3148a52f2212238da00fe76ebe8eab81d86b6023` in the new detached
`p4blo-milestone-release` worktree. Revision and clean tracked status checked.
No builds, production edits or active campaign-binary use by this reviewer.

## Completed local gate evidence: CLEAR

Read locked-sync, both-Lean, oracle-preflight, full, required and JUnit-audit
logs under `/tmp/p4blo-milestone-release-*.log`. Both Lean package builds,
default audits and native suites complete successfully (627 spec checks).
The full script reaches `all checks passed` after Python, formatting, lint,
types, schema generation/drift and workflow checks. Exact process exit results
are integrator-reported; the complete logs and JUnit contents corroborate
their successful gate outcomes.

Independently parsed `.artifacts/release/full.xml` and `required.xml` rather
than relying on the owner's aggregate summary:

- Full: **4799** cases, **4793** passes, no failures/errors, exactly five
  `pytest.xfail` outcomes and one ordinary `pytest.skip`.
- Required: **2886** cases, all passed, all names start `test_lean_agrees`;
  no skip/xfail/failure/error. Deselected count 1913 is recorded in its log.
- The sole ordinary skip is
  `tests.test_xdp_build::test_xdp_original_compiles_and_passes_offline_negative_checks`,
  with exact message `optional XDP compile image unavailable`.
- Exact expected discrepancies: SpecTec CRC known answers `[original-p4]`
  and `[printed-ir]`; SpecTec firewall route miss `[original]` and `[printed]`;
  BMv2 `test_vector_passes_on_bmv2[register_bounds/bounds.stf]`. Their recorded
  reasons match the documented CRC-padding, table-mask and register-read
  boundaries. The corrected BMv2 classifier's actual-pytest error/changed/
  known/corrected-output controls are present and pass.

Meaningful external/application nodes are present and pass, not silently
skipped: all 17 corpus vectors on SpecTec; all 17 on BMv2 except the one exact
register discrepancy; both original/printed CRC BMv2 answers and three
SpecTec passing CRC controls; six original-firewall prefix-state BMv2 profiles
and six SpecTec packet profiles; 20 original firewall boundary/persistence
BMv2 profiles; three generated original-firewall BMv2 sequences; and the
actual forwarder-apply BMv2 profile. Six printer `test_golden[...]` cases all
pass; source inspection confirms those call real `p4test`, whose availability
paths would have appeared as skips. There are no hidden P4/printer availability
skips. Preflight records the pinned SpecTec revision and executable hash and
availability of the immutable BMv2 image.

The complete Lean-authored forwarder (50), firewall (128), quickstart (6),
Program codec (127) and Entries codec/host (112) module cases are individually
present with successful outcomes. This checks concrete coverage identities,
not universal correctness or exhaustive semantic combinations.

The draft `notes/milestone-1-completion.md` matches inspected local counts,
commands and exception scope. It correctly pins the code revision rather
than relabeling results as tests of later documentation bookkeeping, and
distinguishes a clean project checkout from rebuilding external tools.

## Pending at this review checkpoint

The finite campaign in `.artifacts/assurance/release` and remote CI are still
active. Neither is claimed complete here. Reviewer has not consumed or
rebuilt active scratch binaries. Final disposition for the complete release
requires the campaign's detector/restoration/provenance outcomes and exact
revision CI results, to be appended after the integrator releases them.

## Completed finite campaign: CLEAR

The integrator released the scratch tree only after the campaign exited 0.
Independent post-run inspection/replay is logged at
`/tmp/p4blo-milestone-independent-campaign.log`. `result.json` records passed,
no error and all 26 distinct expected phases. Checked every original-checkout
provenance hash and every scratch source hash against the restored source;
the checkout remains clean at the same frozen revision. Reconstructed all
three exact mutation-source hashes in memory from their anchored recipes.
No source change or rebuild was made during this review.

Inspected successful actual CRC, paired-codec and paired-observer build logs,
unchanged audit target invocations and final restored build. The selected
Python catalogue JUnit contains exactly ten passing expected test identities,
without skips/errors. The codec transcript shows the actual parser/control
mapping error, then the deliberately weakened observer's matching reply;
native output and stderr contain exactly the six intended constructor/observer
anchor failures (two of each), not an arbitrary crash. Restored native/codec
phases pass. These are distinguished from build/setup failures.

Checked tracked input reconstruction against all three pinned fingerprints,
retained artifact hashes, complete Program/configuration/request identities,
ports and seed. The saved CRC fault records completed requests 0–3, precisely
divergences 1, 2 and 3, and no protocol error; the reviewed campaign's live
detector requires unchanged packets/no errors or diagnostics and state-only
disagreements before accepting that phase. This reviewer did not rerun a live
mutation; its compiled phase results and checked detector were inspected.

Independently replayed the three baseline bundles on the final restored
scratch binary: 1 + 1 + 4 requests all agree, with no errors. Replayed the
same retained CRC-fault bundle: all four now agree. This confirms the retained
input is still executable and restoration removes its discrepancy, without
inventing additional distinct inputs or claiming exhaustive mutation coverage.

All local release evidence is now independently CLEAR. Remote CI remains
pending with the integrator at this checkpoint; this report does not claim
those active workflows succeeded. No reviewer consumers remain.

## Integrator remote closure

After the independent local review, the integrator checked all five remote
workflow conclusions at the same exact revision: CI `35960620942`, Lean
`35960620935`, P4-SpecTec `35960620865`, BMv2 `35960620846` and XDP
`35960620983` all completed successfully. The completion report links those
runs. This is integrator-observed remote evidence, not a claim that the
reviewer reran CI. No remaining acceptance obligation is open.
