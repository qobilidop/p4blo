# Status

Last updated: 2026-09-25. **Active: test organization refactor.**

User-authorized scope at base 0e55340, branch work/test-organization:
[ownership and acceptance](notes/test-organization.md). Keep spec/ unchanged,
preserve test responsibilities and reorganize Python, conformance, oracle,
program and repository checks. Mechanical moves are complete and independently reviewed: 5,320 cases
retained, spec/ and fixture answers unchanged, full required-Lean local gate
passed (4,798 passes/four expected failures). Next: helper extraction, mixed
suite separation and explicit markers; final oracle/assurance/remote gates
remain outstanding.
The completed implementation evidence below predates this refactor.

Minimal architectures and the discrepancy catalogue are complete on main
`516cbdf67519a1af360ac1d9f442e70133bf77b7`, with all applicable remote CI green.
Only independent Parser, Control and Deparser blocks and scoped v1model remain.
Formal assurance targets architecture-free core IR; architecture adapters,
externs, authoring and applications are tested executable code. No parked
proof or roadmap item is an instruction to continue without a new scope.

Archive before this compaction: `d2f9dbd6fefacc80da40d4f6fba294c819cd4d28`.
It contains the minimal-architecture plan, independent reviews, fixed findings,
mutation checks, exact input/answer audit and closure evidence. Earlier archives:
`34ce204e4a8be7633133a715e10c9ac6a8b891b1`,
`9fc6c19febf839fa56873be10788b515c4e29ae9`,
`26c93485861bc5442076a1060fcc8d1743952702`, and
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6`.
Recover with `git show <archive>:.agents/notes/<name>.md`
(`docs/notes/` at the first archive). No tags are created.
Local logs and build trees are conveniences, not required handoff evidence.

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
| Minimal architectures / oracle discrepancies | `516cbdf`; [profile](../docs/arch-supports.md), [dispositions and minimal reproducers](../docs/oracle-discrepancies.md); evidence below |

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

Final implementation `2bcd84e9233865511d4046cbaab6c361a8fff416` received
independent AI-agent review, not human review. Confirmed phase-index, aggregate
metadata, unused-table-key, generator-name and retired-flood-skip findings were
fixed before integration. The full report is
`.agents/reviews/minimal-architecture-2026-09-25.md` at archive `d2f9dbd`.
The checkpoint comment/report change integrated as `516cbdf` changes no behavior.

Local checks used the pinned `nix develop -c` environment:

- `scripts/check-lean.sh`: both packages, audits and native tests passed on the
  integrated Lean sources, unchanged through the final revision.
- `P4BLO_REQUIRE_LEAN=1 scripts/check.sh` at `2bcd84e`: exit 0; 4,798 passes,
  four expected failures, no skips; format/lint/types/schema/fresh generation
  and workflow checks passed.
- `P4BLO_REQUIRE_LEAN=1 uv run python scripts/check-assurance.py --output
  <new directory>` at frozen `2bcd84e`: all 28 phases passed, including ten
  Python faults, Lean CRC fault, paired codec/observer faults, independent
  anchors and restored baselines. Six requests and three deliberately revised
  program hashes remain. Local evidence `.artifacts/assurance/minimal-arch-final`.
- Corpus oracle modules: 146 passes/five expected failures. Other generated,
  frontend, native CRC/firewall/stage and coverage modules: 340 passes/eight
  expected failures, then ten repaired family/coverage checks passed. Final
  BMv2 driver module: 46 passes/two expected failures. Counts overlap.
- Independent Verify/Ingress swap faults were killed in Python and successfully
  compiled Lean; five emitted traces were wrong, two drops matched. Restored
  seven-request replay agreed completely, with no execution/protocol errors.

All 89 conformance fixtures retain their 514 ordered requests and every extern
state answer. Two former flood output lists become unicast; 118 coverage and
13 diagnostic observations plus three request-error strings change. All 710
semantic cases across seven detailed modules remain. Collection changes from
5,279 to 5,320: 28 retired Filter/flood-only cases, 54 renamed and 69 added.
The schema, core IR/proofs and core Python interpreter remain unchanged.
P4-SpecTec coverage retains 33 programs, 93 vectors, all 2,296 item identities
and hits, and 6,167/14,475 hit instructions; only call/vector counts change.

Exact integrated main `516cbdf67519a1af360ac1d9f442e70133bf77b7` passed
[Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36220833330),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36220833562),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36220833542),
[BMv2](https://github.com/qobilidop/p4blo/actions/runs/36220833512) and
[website deployment](https://github.com/qobilidop/p4blo/actions/runs/36220833313).
Specialist jobs actually ran. The longest workflow took 8m11s including setup
and queue time; this is one observation, not a latency guarantee.

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

Nothing is blocked. The active test organization scope is described above.
[Independent compaction review](reviews/minimal-architecture-compaction.md)
approved b81bd54 plus the repaired historical archive hash; all 65 decisions
and all open threads survive. Its full required-Lean local gate passed 4,798
cases with four expected failures and no skips. The follow-up is narrative
only; implementation evidence above is unchanged. All temporary worktrees
and integrated branches are removed; the three unique parked branches remain.
Complete the active refactor, review and applicable local/remote gates.
