# Retained validation evidence

Durable finite evidence, consolidated 2026-09-26. Retained for preservation and
comparison, not as a new execution claim. Current guarantees and premises belong
in [assurance](../../docs/assurance.md). Exact original records are recoverable
through [recovery](recovery.md); logs under `.artifacts/` are conveniences.

## Completed scope identities

| Scope | Revision / evidence |
|---|---|
| Assurance milestone 1 | `3148a52` (2026-09-23); original release transcript in `docs/assurance.md` at archive `de6aa7d` |
| Python application collection | `c94336d` (2026-09-24); public router, firewall and load balancer |
| Website / VLAN gateway | `38d740e`, simplified `090fb68`, migrated `516cbdf` |
| Architecture-free IR semantics | `26c9348` (2026-09-25); current semantics, ledger and coverage documents |
| Engineering practices / eDSL library boundary | `264fd63` / `f6c3a6e`, PRs #1/#2 |
| CI speed / runner cleanup / scope efficiency | `fffbac7`, `5de0d9e`, `967e0a3`, PRs #3/#4/#5; evidence archived at `090fb68` |
| XDP retirement / optional PR policy | `da6f620` / `5ee52d9` |
| Core-only assurance simplification | `090fb68`; exact-main evidence archived at `d2f9dbd` |
| Minimal architectures / oracle discrepancies | `516cbdf`; evidence archived at `d2f9dbd` |
| Test organization | `b89910353f783b7fa3bb0fa09a748fab0937538c`; checks below |

Earlier milestones describe their own revisions, including proofs later retired.
Their counts and old component names must not be presented as current guarantees.

## Test organization and adversarial checks

Independent read-only AI-agent review, not human review, covered `b899103`;
archive `3c3ed799dc01c0113b8dbcb0f0862d4fb0f1b6dd` retains original
`.agents/reviews/test-organization-final.md`, mechanical review, case/input audits
and fixed import-cache, moved-selection, pre-deselection and mutation-recipe findings.

- All 5,320 original case identities survived modulo documented paths/two path
  parameters/one sharding rename. Six printer compilations became separate cases;
  five boundary cases were added: 5,331 total, including all 710 detailed semantic
  cases. Shared support imports no test modules.
- All 89 fixture programs, 514 ordered requests, replies and provenance survived;
  only source labels moved. All 310 validator scenario names and deterministic
  protobuf hashes matched. Core implementations, spec/ and native inputs were unchanged.
- Required-Lean `scripts/check.sh`: 5,007 passed, no skips/expected failures;
  lint/format/types/schema/generation/workflow checks passed. Ruff also passed
  without cache. `scripts/check-lean.sh` passed both unchanged packages.
- P4-SpecTec: 237 passed/15 precise expected failures, with fresh coverage after
  rebuilding its stale local probe. BMv2/p4c: 70 passed/two precise expected
  failures; no local oracle skips. Coverage retained all 2,296 item identities/hits,
  6,167/14,475 hit instructions and 157 Lean rule tags.
- Frozen assurance at `74a678f` passed all 28 phases: ten Python faults, Lean CRC,
  paired codec/observer faults, independent anchors and restored baselines. Three
  input hashes/six requests were unchanged. Later changes were import/configuration,
  optional recipe repair and narrative evidence, not a new frozen experiment.
- All 13 optional application/VLAN faults were detected by independent Python and
  real-Lean expectations in isolated `d095104`; baseline/restored runs passed.
  [Recipes](mutations/) remain maintained inputs; this supplies no application proof.

Exact-main b899103 passed [Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36225701275),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36225701488),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36225701448) and
[BMv2/p4c](https://github.com/qobilidop/p4blo/actions/runs/36225701446); specialists ran.
Python OS jobs each passed 2,840 ordinary cases; Lean shards passed 1,083/1,084.
The 1,058 package cases needed no Lean, Docker or simulator. Unchanged website
source deployed at d095104 ([run](https://github.com/qobilidop/p4blo/actions/runs/36225143006)).

## Subsequent maintenance

The four original reports under historical `.agents/reviews/` at archive
`de6aa7d9437ffc65c413b0adda7d3f8c558f84f6` have no unresolved findings. Each was
independent read-only review by `minimal_arch_review`; none is human review.

- Test-organization compaction `a042baf1b5954284c312d73c79a1a925a96a6687` preserved
  all 66 decisions/reasons/dates, claim boundaries and parked work against `3c3ed799`.
  Reviewer ran two link tests and whitespace checks, not heavy gates/remote CI.
  Integrator full gate: 5,007 passed in 92.65 seconds.
- Serialization decision review against `9336becefe9b5f157e1d4c572596139dd09c1d1d`
  checked wire conversions, Lean JSON and assurance. Protobuf plus specified JSON
  remained one IR; future bindings were intention, no migration or stronger claim.
  Two link tests passed; integrator full gate: 5,007 passed in 95.11 seconds.
- Repository cleanup review against `d8b197be2dc3c09969e8b968aef93a0d50dc9445`
  checked paths, selections, all 89 BlockAssembly fixtures and two link tests;
  no runtime/native/remote gate run by reviewer. Integrator full gate: 5,007 passed
  in 99.52 seconds. Exact-main `3678eaaf3025665f1ca89c9ab78a4aada93463f1` passed
  [Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36259566190),
  [Lean](https://github.com/qobilidop/p4blo/actions/runs/36259566332),
  [P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36259566261) and
  [BMv2/p4c](https://github.com/qobilidop/p4blo/actions/runs/36259566324); specialists ran.
- Tend-repo review against `405b73b8007fea238bb05cd24fdd33ca800f801b` dry-ran
  review-only scope, hypothetical oversized-state compaction and native/generated
  input preservation. Actual state had 738 resume Markdown lines, three unique
  parked branches and approved reviews; the hypothetical scenario did not replace
  those facts. Reviewer performed metadata/reference/consumer inspection, no heavy
  gates. Integrator metadata validation and 5,007-test full gate passed (97.50 seconds).
  Exact-main de6aa7d passed all four workflows; status links those baseline runs.

These results identify finite witnesses, not universal correctness or stable CI latency.
