# Assurance milestone 1 release evidence

Completed 2026-09-23. All items in the accepted finite checklist are satisfied.
No mandatory work remains for this milestone; the broader research roadmap
and parked proof drafts do not extend it automatically.

## Frozen revision and environment

Code-gate revision: `3148a52f2212238da00fe76ebe8eab81d86b6023`. A new detached
worktree at `/Users/qobilidop/my/work/p4blo-milestone-release` started with no
Python environment, Lean build directories or retained experiment artifacts.
All commands use the pinned Nix development environment. Installed toolchains
and external oracle caches are shared; this is a clean project checkout,
not a claim that every external tool was rebuilt from source on a new machine.
Later completion bookkeeping must remain documentation-only and must not
relabel these results as execution at that newer revision.

P4-SpecTec preflight checked executable availability, source HEAD and build
stamp at `2730cfd9e74048bb5439da0f8afcef124079a064`. The local executable's
SHA-256 is `c75a2129d08a91f266ca8377919de7de26cc384b2724ee333ca96886d92867bb`.
BMv2 runs use immutable local image
`sha256:2b255b539b7c7dab31460422150d577990a2572c8caab253479839f27dc81b0d`.
No image, oracle pin or security restriction was changed for acceptance.

## Commands and results

Commands below run from the clean worktree. Builds finish before executable
consumers; no checkout executable is rebuilt during conformance tests.

| Gate | Command | Result |
|---|---|---|
| Locked environment | `nix develop -c uv sync --locked` | exit 0 |
| Both Lean packages | `nix develop -c scripts/check-lean.sh` | exit 0; default audits, 627 spec checks and user-package tests pass |
| Python/schema/workflows | `P4BLO_REQUIRE_LEAN=1 nix develop -c scripts/check.sh` | exit 0; 4793 passed, five exact expected discrepancies, one optional local XDP skip (515.47 s); all static/schema/workflow checks pass |
| Required conformance | `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees -q` | exit 0; 2886 passed, 1913 deselected, no skips (224.01 s) |
| Finite adversarial acceptance | `nix develop -c uv run python scripts/check-assurance.py` | exit 0; fresh builds, all selected detections and restored replays pass |

The full gate additionally sets `P4BLO_BMV2_IMAGE` to the immutable ID above
and `PYTEST_ADDOPTS='--junitxml=<worktree>/.artifacts/release/full.xml -ra'`.
Required conformance uses `--junitxml=<worktree>/.artifacts/release/required.xml`.
These reports distinguish ordinary skips, exact expected discrepancies and
passing P4/printer/oracle nodes. A count alone is not acceptance.

Local logs are `/tmp/p4blo-milestone-release-{sync,lean,oracle-preflight,full,required}.log`.
The finite command reconstructs its complete selected inputs from tracked
fixtures; reproduction does not require those old logs or any old worktree.
The [catalogue](milestone-adversarial.md) documents output/provenance and all
required mutation, detector and restoration outcomes.

The final campaign used `--output <worktree>/.artifacts/assurance/release`.
Its `result.json` reports `passed` with no error. Ten exact selected Python/
observer regressions pass. The actual compiled CRC fault produces three
state-only divergences; replaying that same retained input after restoration
returns four agreements. The paired codec and observer faults compile with
the unchanged roundtrip audits; weak equality survives as intended, while
exactly six independent native anchors reject the wrong mapping. Final
source restoration, proof audits, native controls, independent codec answer
and all three input replays pass. No build failure is counted as a detection.
The original checkout remains unchanged and its complete recorded source
hashes match. Log: `/tmp/p4blo-milestone-release-assurance.log`.
The independent release review (`notes/reviews/milestone-release.md`, archived) is CLEAR for
all local evidence: it checked exact JUnit identities, source/mutant hashes,
actual detector transcripts and independently replayed the three baseline
inputs and the same retained CRC-fault input after restoration.

## Exceptions and CI

The complete JUnit inventory was checked: 4799 full-suite cases contain
exactly 4793 passes and the six exceptions below. The separate required
conformance report contains 2886 passing `test_lean_agrees` cases and no
skips, errors or failures. No P4 oracle or printer availability skip occurred.

- Ordinary skip: `test_xdp_original_compiles_and_passes_offline_negative_checks`,
  exactly `optional XDP compile image unavailable`.
- Precise expected discrepancies: CRC known answers on P4-SpecTec for
  `original-p4` and `printed-ir`; firewall route miss for `original` and
  `printed`; BMv2 `register_bounds/bounds.stf`. Their exception classifiers
  do not admit an unrelated oracle failure.

Remote CI for the pushed code-gate revision:

| Workflow | Run | Result |
|---|---|---|
| CI (Python Linux/macOS and schema) | [35960620942](https://github.com/qobilidop/p4blo/actions/runs/35960620942) | passed |
| Lean | [35960620935](https://github.com/qobilidop/p4blo/actions/runs/35960620935) | passed |
| P4-SpecTec | [35960620865](https://github.com/qobilidop/p4blo/actions/runs/35960620865) | passed |
| BMv2 | [35960620846](https://github.com/qobilidop/p4blo/actions/runs/35960620846) | passed |
| XDP compile profile | [35960620983](https://github.com/qobilidop/p4blo/actions/runs/35960620983) | passed |

XDP is a separate compile-only experiment, not evidence of kernel execution
or this milestone's P4 semantics. Its local skip is not counted as a pass;
the separate required remote build passes at this exact revision.

## Claim and stopping boundary

This milestone establishes reproducible tested conformance for the documented
[current profile](../profile.md), selected audited Lean proofs, independent
example/oracle answers and sensitivity to the reviewed intentional faults.
It is not a proof of universal Python equivalence, all-P4 expressiveness,
whole-program validity, resource safety or complete application correctness.
The [evidence matrix](../evidence.md) links the separate evidence kinds.

The implementation closes top-level Program/Export/Entries tests, rejected-
host state preservation, the two-language quickstart and the finite acceptance
command. Review exposed and closed two strict-type observer gaps and one broad
oracle expected-failure marker. Further readback/ingress proofs remain parked
as recorded in [parked-proofs.md](../notes/parked-proofs.md); they are not release work.
