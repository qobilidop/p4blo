# Status

Last updated: 2026-09-26. **No active engineering work.**

The cleanup corrects stale test paths, selection guidance, the p4c gate
command and the conformance fixture schema reference. Runtime code, schemas,
fixtures, pinned oracle inputs and parked recovery branches are unchanged.
The read-only inventory audit found no confirmed dead implementation files;
large generated files and the website example copy are checked deliverables.
Independent [review](reviews/repository-cleanup.md) found no defects.
Required-Lean `scripts/check.sh` passed 5,007 tests with no skips or expected
failures in 99.52 seconds, plus lint/type/schema/generation/workflow checks.
The temporary audit and review worktrees were removed. Native oracle execution
and Lean builds were not rerun locally for these prose-only changes; the
conservative scope classifier required full remote CI for test README edits.
Exact-main `3678eaaf3025665f1ca89c9ab78a4aada93463f1` passed all four workflows:
[Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36259566190),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36259566332),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36259566261), and
[BMv2/p4c](https://github.com/qobilidop/p4blo/actions/runs/36259566324).
All specialist jobs ran. The following checkpoint changes this evidence note only.

Serialization decision: retain Protobuf as the IR wire schema and its specified
JSON profile for Lean, with generated bindings for current Python and future
frontends. Abstract syntax and meaning remain in Lean. The decision is recorded
in the register and the representation boundary clarified in `docs/design.md`.
This documentation checkpoint changes no implementation, schema or assurance claim.
Independent [review](reviews/serialization-decision.md) found no defects. The
required-Lean full local gate passed 5,007 tests with no skips or expected
failures, plus lint/type/schema/generation checks.

Terminology follow-up: retain codec for encoder/decoder pairs and encode/decode
for their operations. The convention is recorded in AGENTS and the codec guide;
stale pre-refactor test-layout wording in the decisions register is corrected.
This is documentation-only; no code, test inventory or spec/ changes.
Validation: required-Lean `scripts/check.sh` passed all 5,007 tests and its
lint/type/schema/generation checks; no skips or expected failures.

Test organization is complete on main `b89910353f783b7fa3bb0fa09a748fab0937538c`.
Python package tests live beside the package at `impl/python/tests/`; root
suites cover conformance, oracles, programs, repository checks and support.
All original cases and fixture answers survive; spec/ is unchanged. Independent
Parser, Control and Deparser blocks and scoped v1model remain the architecture
set. Formal assurance still targets architecture-free core IR. Parked proof
and roadmap items are not instructions to resume without a new scope.

Archive before this compaction: `3c3ed799dc01c0113b8dbcb0f0862d4fb0f1b6dd`.
It retains the completed plan, reviews, exact input/case audits and local/remote
validation records, including the fixed import-cache and mutation-recipe findings.
Earlier archives: `d2f9dbd6fefacc80da40d4f6fba294c819cd4d28`,
`34ce204e4a8be7633133a715e10c9ac6a8b891b1`,
`9fc6c19febf839fa56873be10788b515c4e29ae9`,
`26c93485861bc5442076a1060fcc8d1743952702`, and
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6`.
Recover with `git show <archive>:.agents/notes/<name>.md`
(`docs/notes/` at the first archive). No tags are created. Local logs/builds
are conveniences, never required handoff evidence.

## Completed scopes

| Scope | Revision / evidence |
|---|---|
| Assurance milestone 1 | `3148a52`; [historical release evidence](../docs/assurance.md#release-evidence) |
| Python application collection | `c94336d`; [router, firewall, load balancer](../examples/README.md) |
| Website / VLAN gateway | `38d740e`, simplified `090fb68`, migrated `516cbdf`; [website](https://qobilidop.github.io/p4blo/) |
| Architecture-free IR semantics | `26c9348`; [semantics](../docs/ir-semantics.md), [ledger](../docs/ledger-xref.md), [coverage](../docs/p4-spec-coverage.md) |
| Engineering practices / eDSL library boundary | `264fd63` / `f6c3a6e`, PRs #1/#2; [authoring](../docs/python-edsl.md) |
| CI speed / runner cleanup / scope efficiency | `fffbac7`, `5de0d9e`, `967e0a3`, PRs #3/#4/#5; evidence archived at `090fb68` |
| XDP retirement / optional PR policy | `da6f620` / `5ee52d9`; experiment recoverable at `b7860a5` |
| Core-only assurance simplification | `090fb68`; exact-main local/remote evidence archived at `d2f9dbd` |
| Minimal architectures / oracle discrepancies | `516cbdf`; [profile](../docs/arch-supports.md), [dispositions and minimal reproducers](../docs/oracle-discrepancies.md); evidence archived at `d2f9dbd` |
| Test organization | `b899103`; [test guide](../tests/README.md); exact-main local/remote evidence below |

Earlier milestones describe their own revisions, including proofs since retired.
Retired Lean authoring/application/architecture sources remain at `5ee52d9`.
Current claims are in [assurance](../docs/assurance.md); no execution certificates,
application proofs or concrete-architecture proof discharge are supplied.

## Four claims and boundaries

| Claim | Current boundary |
|---|---|
| Small, post-elaboration core | Twelve corpus programs and three applications without new core syntax. Nine supported originals have exact normalized projected IR comparisons; fourteen printer/importer round trips check stage structure and 100 STF plus 336 generated requests. Native checksum verification remains explicitly excluded. No general compiler or verified frontend claim. |
| Supports tested real programs | Python/Lean, P4-SpecTec and BMv2 tests preserve documented finite witnesses. CRC, table-mask, priority, register and egress dispositions have minimal reproductions. Other simulator limitations remain in assurance; a mismatch is never excused by an architecture-wide exception. |
| A block is a function; architecture is ordinary code | Arbitrary typed core blocks and optional BlockLibrary bundles remain independent. Flat BlockAssembly selects H/M and six v1model roles. The block runner selects one control; it never fuses stages. Registration creates fresh state and grants neither Lean nor printer support to arbitrary plugins. |
| Mechanized and agrees with reference | Sound core library checker and progress under stated premises, including a generic extern contract. Core semantic/codec laws and 157 rule tags/89 fixtures remain. No universal Python equivalence, termination or whole-library codec-composition theorem. |

## Last checked evidence

Final implementation `b89910353f783b7fa3bb0fa09a748fab0937538c` received
independent read-only AI-agent review, not human review. The archive above
holds `.agents/reviews/test-organization-final.md` and the mechanical review.
Confirmed moved-root selection, pre-deselection guard, cached Ruff import
classification and live mutation-recipe findings were fixed and checked.

- Collection preserves all 5,320 original case identities, modulo documented
  paths/two path parameters/one sharding-test rename. Six printer compilations
  are now separate cases; five boundary cases are added: 5,331 total. All 710
  detailed semantic cases remain. Shared support imports no test modules.
- All 89 fixed conformance fixtures retain their programs, 514 ordered requests,
  replies and provenance; only source-location labels moved. All 310 validator
  scenario names and deterministic protobuf hashes match the former capture.
  Core implementations, spec/ and native P4/STF inputs are unchanged.
- Required-Lean `scripts/check.sh` at b899103: 5,007 passed with no skips or
  expected failures; format/lint/types/schema/generation/workflow checks passed.
  Explicit first-party classification also passes `ruff check --no-cache`.
  `scripts/check-lean.sh` passed both unchanged specification packages.
- P4-SpecTec: 237 passed/15 precise expected failures, including fresh coverage
  after rebuilding the stale local probe. BMv2/p4c: 70 passed/two precise
  expected failures. No local oracle checks skipped. Coverage retains all
  2,296 item identities/hits and 6,167/14,475 hit instructions; 157 Lean rule tags.
- Frozen assurance at `74a678f` passed all 28 phases: ten Python faults, Lean
  CRC, paired codec/observer faults, independent anchors and restored baselines.
  Its three input hashes/six requests are unchanged. Subsequent changes are
  import order/configuration, optional recipe repair and narrative evidence.
  Local logs: `.artifacts/assurance/test-organization-final`.
- All 13 optional application/VLAN source faults were detected by independent
  Python and real-Lean expectations in an isolated d095104 worktree;
  every baseline/restored run passed. Current recipes stay in
  `.agents/notes/mutations/`; no application-proof claim follows.

Exact-main b899103 passed
[Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36225701275),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36225701488),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36225701448), and
[BMv2/p4c](https://github.com/qobilidop/p4blo/actions/runs/36225701446).
All specialist jobs ran. Each Python OS passed 2,840 ordinary cases; Lean's
complete disjoint shards passed 1,083 and 1,084. The 1,058 package cases require
no Lean, Docker or simulator. The unchanged website source deployed at d095104
([run](https://github.com/qobilidop/p4blo/actions/runs/36225143006)).
The following compaction changes narrative state only; its own validation is
recorded in the compaction review. This is finite evidence, not universal
correctness or a latency guarantee.

## Open threads (parked / backlog)

- Joint milestone with `p4-spectec-lean`: its rendering must answer every
  conformance fixture and block request before the simulation theorem. Its
  Nano-P4 pin `8c8e0c6f` differs from ours `2730cfd9`; its export should replace
  patch `0002`. [Design](../docs/design.md) owns interfaces; no duplicate rendering.
- Core termination C2, BlockLibrary codec composition C3, checker completeness,
  assignment preservation and generated table-invoked actions/parser-error
  copyback across host-changing sequences remain [backlog](roadmap.md).
  Concrete architecture/application proof extensions are retired.
- Printer declaration order: actions calling later declarations fail P4-SpecTec
  typing; order by dependency or require that order in validation.
- Two reachable P4-SpecTec rules remain unhit: `Expr_eval/non-default-abort`
  and `Copy_in_arg/abort`; coverage exclusions retain their inputs.
- Some Lean/Python module headers retain former semantics section names.
- Unique retired firewall-readback/forwarder-ingress drafts and review history
  remain on three pushed branches: [inventory](notes/parked-proofs.md),
  [local recovery archives](notes/worktree-cleanup.md). They predate the current
  layout/externs, are not landed evidence, and need no retained worktrees.
- Unconfirmed review points: checksum16 padding for non-multiples of 16;
  `<block>_inst` name collisions; error ordering when both entry and port are
  invalid. These have no oracle ruling yet.
- Text parsing, semantic-version policy, whole-program codec proofs, resource
  limits and unknown-field policy remain interchange questions.
- Flowlet time/randomness needs an independent oracle. XDP requires a concrete
  application and execution oracle before reconsideration. Flood/multicast is
  outside the profile. The p4c backend remains deferred; it would test claim 1
  and elaborations beyond the existing IL bridge.
- Nonblocking eDSL observation: reassignable public library settings can bypass
  constructor checks; no runtime bug demonstrated.
- Nonblocking CI observations: cache eviction costs cold builds; the stdlib guard
  uses Python 3.13 while Docker uses distro Python, with compatible imports today.

## Blocked / next action

Nothing is blocked or active. The repository documentation cleanup is complete;
all applicable local and exact-main remote gates passed. The three unique
pushed parked branches remain; parked work is not an instruction to resume.
Wait for a new scope.
