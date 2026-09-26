# Status

Last updated: 2026-09-25. **Minimal architectures complete.**

Integrated main `516cbdf67519a1af360ac1d9f442e70133bf77b7` passed every
applicable remote workflow with specialist jobs actually running:
[Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36220833330),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36220833562),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36220833542),
[BMv2](https://github.com/qobilidop/p4blo/actions/runs/36220833512), and
[website](https://github.com/qobilidop/p4blo/actions/runs/36220833313).
The scope is closed. Remaining checkpoint prose below is historical and will
be compacted against this committed archive point. No implementation work is
active; the three unique parked branches remain historical.

The user authorized core block execution plus scoped v1model, retiring the
custom Filter/Switch. Branch `work/minimal-arch`, base `14e6f44`.
[Scope and shared contract](notes/minimal-architectures.md).

Current iteration: implementations and binding integrated through `562e571`,
docs through `8e80f65`, frontend tests `999c35e`, callers `c87d64a` and
conformance `4fbe19d`. Python profile indexing and Lean
whole-metadata validation findings are repaired. The six-stage witness passes
Python and P4-SpecTec; the portable checksum/deparser witness passes both
external oracles. Two native egress discrepancies are precisely classified;
[the catalog](../docs/oracle-discrepancies.md) states adopted behavior and reason.
All 89 conformance fixtures pass Python and Lean after deliberate re-export: all
514 requests and every extern-state answer survive; two former flood outputs,
118 coverage observations and 13 diagnostics change. Both independent stage-order
faults were semantically killed and restored; [review](reviews/minimal-architecture-2026-09-25.md).
The first required-Lean Python run had 4,791 passes, four xfails and three stale
path/diagnostic expectations, fixed in c87d64a. The full script initially found
one Markdown code formatting issue, fixed in the current tree. A repeat full
gate passed: 4,798 tests, four xfails, no skips; all format/lint/types/schema/
generation/workflow checks passed. The remaining oracle batch passed 340 with
eight xfails and exposed two failures: a core generator-family key accidentally
renamed to ingress, and stale coverage call/vector counts (both fixed at
cd1e06e; focused replay 10 passed). Fresh measurement preserves all 2,296 items
and every hit/instruction count. Independent review also found a retired BMv2
flood skip, fixed and independently reviewed at 2bcd84e (two new negative
tests pass; full BMv2 module 46 passed, two xfails). Final full required-Lean
gate at 2bcd84e passed 4,798 cases with four xfails, no skips. Frozen assurance
at that clean revision passed all 28 phases. Final independent review approves
the implementation; all 710 detailed semantic cases remain. Remote integration
and exact-main CI are the remaining obligations, followed by closure/compaction.
The evidence below describes the preceding completed scope, not this work.


Core-only assurance
simplification is complete and integrated into `main` at
`090fb6813600cbd56bc375a6ff6cdc81b893bb4d`; all applicable remote CI passed.
The roadmap remains backlog; retired application/architecture proofs are not
a continuation queue. The current scope changes tested adapters only.

Formal assurance now targets the architecture-free core IR. Python supplies
public authoring, examples, validation, interpretation and the P4 importer.
Two Lean packages remain: `spec/ir` owns core syntax/meaning/proofs;
`spec/arch` supplies tested executable adapters and the `p4blo-lean` endpoint.
Lean authoring/applications, concrete architecture proofs and execution
certificates are retired. Core progress still assumes a generic extern
contract; no concrete architecture discharge is claimed.

Archive before this compaction:
`34ce204e4a8be7633133a715e10c9ac6a8b891b1`. It contains the simplification,
CI-efficiency and XDP plans/reviews, final implementation evidence and earlier
checkpoints. Retired feature sources remain at
`5ee52d90f19d5d5a81bf972a115298ae167e691b`.
Earlier archives: `9fc6c19febf839fa56873be10788b515c4e29ae9`,
`26c93485861bc5442076a1060fcc8d1743952702` and
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6`.
Recover with `git show <archive>:.agents/notes/<name>.md`
(`docs/notes/` at the first archive). Local logs are conveniences, not
portable evidence. No tags are created.

## Completed scopes

| Scope | Result / revision | Evidence |
|---|---|---|
| Assurance milestone 1 | complete, `3148a52` | [historical release evidence](../docs/assurance.md#release-evidence) |
| Python application collection | complete, `c94336d` | [router, firewall, load balancer](../examples/README.md) |
| Website / VLAN gateway | published, `38d740e`; simplified at `090fb68` | [website](https://qobilidop.github.io/p4blo/) |
| Architecture-free IR semantics | complete, `26c9348` | [semantics](../docs/ir-semantics.md), [ledger](../docs/ledger-xref.md), [coverage](../docs/p4-spec-coverage.md) |
| Engineering practices | merged, `264fd63`, PR #1 | [workflows](../docs/workflows.md) |
| Example-guided eDSL / library boundary | merged, `f6c3a6e`, PR #2 | [authoring guide](../docs/python-edsl.md) |
| CI speed and runner cleanup | merged, `fffbac7` / `5de0d9e`, PRs #3 / #4 | archived final reviews and buffered-stdin regression evidence |
| CI efficiency | merged, `967e0a3`, PR #5 | measurements and review archived at `090fb68` |
| XDP retirement | merged, `da6f620`, PR #7 | review archived at `090fb68`; experiment recoverable from `b7860a5` |
| Optional PR policy | complete, `5ee52d9` | [workflows](../docs/workflows.md); archived independent review |
| Core-only assurance simplification | complete, `090fb68` | local and remote evidence below; review archived at this revision |

Earlier semantic milestones describe their recorded revisions, including
proofs since retired. Current guarantees are in [assurance](../docs/assurance.md).
Independent blocks and optional BlockLibrary bundles have arbitrary block
counts/signatures and declarations; architecture bindings select H/M roots
and exports. Flat BlockAssembly preserves old payloads. Registration is
explicit and creates fresh per-instance state; Python registration grants
neither Lean semantics nor printer support. Scalar/six-block and custom-extern
witnesses test beyond the reference switch. Python application goldens and
behavior are unchanged.

## Four claims

| Claim | Status and boundary |
|---|---|
| Small, post-elaboration core | Twelve corpus programs and three applications without a new core construct. The P4-SpecTec IL frontend reproduces six original P4 goldens byte for byte; 98 of 191 pinned v1model programs with vectors run from source. No general P4 compiler claim. |
| Supports tested real programs | Explicit discrepancies remain: BMv2 register/priority behavior, P4-SpecTec firewall masks, three block-level expected failures behind checked models, and classified source CRC/mask and generated-program simulator defects. Assurance records exact boundaries. |
| A block is a function; architecture is ordinary code | Frozen: supplied filter is 45 lines and switch 50, neither contains P4, every corpus program runs under both. Their H/M convention is not a core restriction. |
| Mechanized and agrees with reference | Sound core library checker; progress under stated execution premises, including an assumed generic extern contract. Architecture bindings/families are tested without formal discharge. Core semantic/codec laws and all 157 rule tags/89 fixtures remain. No application proof, universal Python equivalence, termination or whole-library codec-composition theorem. |

## Last checked evidence

Independent AI-agent review approved implementation
`f9cb19ee1b9afbb1b512a584eb147a01be331e03` and the three-file evidence
follow-up integrated as `090fb68`. It is not human review. One confirmed
finding, a lost firewall required-vector inventory assertion, was repaired
in `d848cf3`; removing `collisions.stf` fails the restored guard.
The full report is `.agents/reviews/core-simplification-2026-09-25.md` at
the archive revision.

At unchanged implementation `f9cb19e`, local commands exited 0:

- `scripts/check-lean.sh`: both Lean packages, audits and tests passed.
- `P4BLO_REQUIRE_LEAN=1 scripts/check.sh`: 4,785 passed, four expected
  failures, no skips; lint/format/types/schema/workflows/fresh generation passed.
- `P4BLO_REQUIRE_LEAN=1 uv run python scripts/check-assurance.py --output
  <new directory>`: all 28 phases passed with the tracked tree frozen.
  All ten Python fault cases, Lean CRC fault, paired codec/observer faults,
  independent anchors and restored baseline retain the original three input
  hashes/six requests. Local result: `.artifacts/assurance/simplify-f9cb19e`.
- `uv run pytest tests/programs/test_forwarder_apply_semantics.py::test_apply_packets_bmv2 -q`:
  one test passed, exercising all five forwarding profiles.

These commands ran in the pinned `nix develop -c` environment. The final
Markdown evidence follow-up passed link checks and independent review.
Exact integrated main `090fb6813600cbd56bc375a6ff6cdc81b893bb4d` passed
[Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36215857990),
[Lean](https://github.com/qobilidop/p4blo/actions/runs/36215858104),
[P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36215858109),
[BMv2](https://github.com/qobilidop/p4blo/actions/runs/36215858092) and
[website deployment](https://github.com/qobilidop/p4blo/actions/runs/36215857977).
All specialist validation jobs ran; these were not scope skips.

Independent old/new executable comparison preserved exit/stdout/stderr for
89 fixtures, 514 packet requests and 363 CLI pairs. Git comparison preserved
280 runtime/input/wire files byte for byte; the only additional retained
Python package edit is a provenance docstring. Exactly 486 collected cases
retired with their features (5,765 to 5,279); all 710 runtime cases in seven
mixed suites remain. 547 Python-only cases were honestly renamed, and real
Lean comparisons retain discovery prefixes. Main/codec axiom audits retain
140/48 declarations; removed pins name deleted declarations. Tracked Lean
source shrank from 163 files/33,694 physical lines to 81 files/21,432 lines,
including tests/comments/blanks; this is a size count, not an assurance or
latency estimate.

## Open threads (parked / backlog)

- Joint milestone with `p4-spectec-lean`: its executable rendering must answer
  every conformance fixture and block request before the simulation theorem.
  Its P4-SpecTec pin `8c8e0c6f` (Nano-P4 branch) and ours `2730cfd9` differ;
  its program export should replace patch `0002`. [Design](../docs/design.md)
  records the interfaces; this repository builds no duplicate rendering.
- Core termination C2 and codec composition through BlockLibrary C3 remain
  open; architecture codec proof obligations retire. See [roadmap](roadmap.md).
- Printer declaration order: an action calling a later declaration fails
  P4-SpecTec typing; order by dependency or require that order in validation.
- Two reachable P4-SpecTec rules remain unhit: `Expr_eval/non-default-abort`
  and `Copy_in_arg/abort`; inputs are in the coverage exclusions file.
- Some Lean/Python module headers still use former semantics section names.
- Firewall readback and forwarder ingress drafts are on three pushed parked
  branches; [inventory and gaps](notes/parked-proofs.md),
  readback plan archived at `090fb68`,
  [local recovery archives](notes/worktree-cleanup.md). They predate current
  layout/externs and are not landed evidence; no worktree needs retaining.
- Unconfirmed review points: checksum16 padding for non-multiples of 16;
  `<block>_inst` names unchecked against caller scope; Python/Lean error
  ordering when entry and port are both invalid. No oracle judgment yet.
- General core assignment preservation and generated table-invoked actions/
  parser-error copyback across sequences. Further concrete extern/application
  proofs are retired, not pending continuation work.
- Text parsing, semantic-version policy, whole-program codec proofs, resource
  limits and unknown-field policy remain interchange questions.
- Flowlet time/randomness needs an independent oracle. XDP is deferred until
  a concrete application and execution oracle justify it. BMv2 cannot observe
  `flood` until a corpus program declares it. The p4c
  backend remains deferred behind verification; it would test claim 1 and
  elaborations beyond the current IL bridge.
- Nonblocking eDSL review observation: public library settings are reassignable
  and can bypass constructor checks; no runtime bug was demonstrated.
- Nonblocking CI observations: cache eviction costs a cold build.
  The stdlib-only guard uses Python 3.13,
  while Docker scripts use distro Python; current imports are compatible.


[Independent compaction review](reviews/simplification-compaction-2026-09-25.md)
found no unresolved issues; implementation evidence above is unchanged.

## Blocked

Nothing. Implement and validate the minimal-architecture scope above.
