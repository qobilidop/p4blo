# Status

Last updated: 2026-09-25. **Active: simplify formal assurance to the core IR.**
The user approved removing Lean authoring/application proofs, concrete
architecture proofs and the execution-certificate experiment. Preserve the
core IR proofs, executable architecture adapters, Python authoring/examples,
wire formats and independent oracle/differential testing. Integration branch:
`work/simplify-core`, based on `5ee52d90f19d5d5a81bf972a115298ae167e691b`.
[Scope, ownership and acceptance](notes/simplify-core.md). Implementation
and final independent review are complete at `f9cb19e`. Both Lean packages
passed; the full required-Lean gate passed 4,785 tests with four expected
failures and no skips. Frozen adversarial replay passed all 28 phases;
the retained BMv2 forwarding profile passed. Integrated-main CI remains
pending before closing this scope. [Review](reviews/core-simplification-2026-09-25.md).

The user
has made PRs optional for this personal-project phase. Feature branches
remain available when useful, and direct commits to `main` are allowed;
PRs are used for explicit requests or repository protections. Independent
review, the full local gate before push and applicable remote CI on the
integrated `main` revision remain required. This policy checkpoint updates
AGENTS, workflow documentation and the compaction procedure. Independent
review found no confirmed defects; the full required-Lean local gate passed
with 5,271 tests and four expected failures, no skips. Review details are in
[the policy review](reviews/optional-pr-policy-2026-09-25.md). Remote results
are recorded by GitHub Actions against the policy commit; the local result
alone does not establish remote success.

The simplification audit is complete and implementation is authorized.
The optional-PR policy at `5ee52d9` passed all four validation workflows;
feature branches remain useful and no PR is required for this scope.

XDP removal
is complete: [PR #7](https://github.com/qobilidop/p4blo/pull/7) merged as
`da6f6202e3014b195bba864844f9923d1223ddd7` after independent review and all
final-head checks passed. The workflow, container sources, inspector and
dedicated tests are gone; current commands, pins and structural inventories
are updated. The P4 interpreters, schemas, proofs and oracle inputs are unchanged.
Historical XDP evidence stays historical; only a short revisit condition
remains in the roadmap. The eDSL, closure and CI-efficiency scopes also remain
complete. Ask for a new scope; the roadmap is backlog.

Archive before this compaction: `9fc6c19febf839fa56873be10788b515c4e29ae9`.
It includes the final eDSL reflection, implementation plans and reviews.
Earlier archives: `26c93485861bc5442076a1060fcc8d1743952702` and
`9e8f7d47e582de3d9813d4d0d4d91c152efdb2b6`. Recover a note with
`git show <archive>:.agents/notes/<name>.md` (`docs/notes/` at the first).
Logs in `.artifacts/` are conveniences, not portable evidence.

## Completed scopes

| Scope | Result / revision | Evidence |
|---|---|---|
| Assurance milestone 1 | complete, `3148a52` | [assurance](../docs/assurance.md#release-evidence) |
| Python application collection | complete, `c94336d` | [router, firewall, load balancer](../examples/README.md) |
| Website / VLAN gateway walkthrough | published, `38d740e` | [website](https://qobilidop.github.io/p4blo/) |
| Architecture-free IR semantics | complete, `26c9348` | [semantics](../docs/ir-semantics.md), [ledger](../docs/ledger-xref.md), [coverage](../docs/p4-spec-coverage.md) |
| Engineering practices | merged, `264fd63`, PR #1 | [workflows](../docs/workflows.md); archived engineering-practices note/review |
| Example-guided eDSL / library boundary | merged, `f6c3a6e`, PR #2 | [authoring guide](../docs/python-edsl.md); archived reflection and library-boundary review |
| CI speed | merged, `fffbac7`, PR #3 | [workflow](../.github/workflows/lean.yml); archived ci-speed and ci-speed-final reviews |
| CI efficiency | merged, `967e0a3`, PR #5 | [measurements](notes/ci-efficiency.md), [independent review](reviews/ci-efficiency-2026-09-25.md) |
| XDP retirement | merged, `da6f620`, PR #7 | [independent review](reviews/xdp-removal-2026-09-25.md); removed experiment recoverable from `b7860a5` |

The completed semantic milestones describe their recorded revisions.
This simplification retires authoring/application/architecture proof scopes;
retained core proofs keep their original premises and no new proof is opened.
The eDSL scope supplies architecture-free Python/protobuf/Lean BlockLibrary,
with arbitrary block counts/signatures and declarations; architecture bindings
own H/M roots and exports, and an optional flat BlockAssembly preserves old
payloads. Core validity/progress retain their premises; architecture bindings
remain tested runtime checks without a formal soundness claim. Registration is explicit; binding creates fresh per-instance state. Custom
extern and six-block witnesses test beyond the reference switch. The three applications
retain exact text/binary goldens and behavior, using ordinary readability
helpers. Python registration grants neither Lean semantics nor printer support.

## Four claims

| Claim | Status and boundary |
|---|---|
| Small, post-elaboration core | Green for twelve corpus programs and three applications without a new core construct. The P4-SpecTec IL frontend reproduces six original P4 goldens byte for byte; 98 of 191 pinned v1model programs with vectors run from source (`tests/oracle/frontend-census.json`). No general P4 compiler claim. |
| Supports tested real programs | Green with explicit discrepancies: BMv2 register/priority differences, P4-SpecTec mask failure on the printed firewall, three block-level expected failures behind checked models, and classified original-source CRC/mask and generated-program simulator defects. See assurance for exact input/evidence boundaries. |
| A block is a function; architecture is ordinary code | Frozen: the supplied filter is 45 lines and switch 50, neither contains P4, every corpus program runs under both. Their H/M convention is not a core restriction. |
| Mechanized and agrees with reference | Sound core library checker; progress under the [stated execution premises](../docs/assurance.md), including an assumed generic extern contract. Architecture bindings/families are tested, without formal discharge. Core semantic/codec laws and all 157 rule tags/89 fixtures remain. No application proof, universal Python equivalence, termination or whole-library codec-composition theorem. |

## Last checked evidence

All hashes below resolve. Earlier reviews are available at the archive point;
AI-agent review is independent of the author, not human review.
The [closure review](reviews/closure-2026-09-25.md) compares the compacted
state at `9bd5434` with the archive and separately approves cleanup `a31ff19`.

- XDP removal final head `c3d8a76e6c1d7e68851ecffd8dab04b661ff96c2`:
  independent review approved; all seven validation jobs and three scope jobs
  passed: [Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36210833516),
  [Lean](https://github.com/qobilidop/p4blo/actions/runs/36210833804),
  [P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36210833820),
  [BMv2](https://github.com/qobilidop/p4blo/actions/runs/36210833677).
  Full required-Lean local gate exited 0: 5,271 passed, four expected failures,
  no skips. All 154 structure tests also passed. All 3,045 Lean cases remain;
  the 19 removed collection entries are XDP's 17 tests and its two structural
  registrations. No local Lean/Docker rebuild or assurance mutation rerun was
  needed for unchanged semantics; remote specialist gates all ran and passed.

- CI-efficiency final head `e4c1d759549dfa3c8518184e2a9b4818993071fd`:
  independent review approved; all eight validation jobs and four scope jobs
  passed remotely: [Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36207118848),
  [Lean](https://github.com/qobilidop/p4blo/actions/runs/36207118970),
  [P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36207118915),
  [BMv2](https://github.com/qobilidop/p4blo/actions/runs/36207118971),
  [XDP](https://github.com/qobilidop/p4blo/actions/runs/36207118925).
  Full required-Lean local gate exited 0: 5,289 passed, one optional local XDP
  skip, four expected failures. Remote Lean shards passed 1,509 + 1,536 cases.
  Observed job times: Lean maximum 521 to 256 s, BMv2 393 to 252 s,
  P4-SpecTec 643 to 556 s. These are individual run comparisons, not latency
  guarantees. Python/schema always run; only proven narrative-only changes
  skip specialist jobs. XDP's remote compile pass is not kernel execution.

- Closure follow-up `a31ff19`: the post-merge macOS
  [run](https://github.com/qobilidop/p4blo/actions/runs/36203599815) exposed a
  buffered-stdin close error masking ProtocolError after peer exit. A narrow
  cleanup fix has a deterministic real-pipe regression that independently
  fails old code and passes the repair. Full required-Lean local gate exited
  0: 5200 passed, one optional XDP skip, four expected failures. The incident
  does not invalidate PR #3's successful final-head checks; its post-merge run
  is distinct. PR #4 merged as `5de0d9e` after independent review and all seven
  checks passed on final head `e5cf214`: Python/schema, Lean, both P4 oracles
  and the compile-only XDP profile. Its temporary branches/worktrees are removed.

- eDSL final head `26d3f38`, merged by PR #2: all seven remote checks passed:
  [Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36201014298),
  [Lean](https://github.com/qobilidop/p4blo/actions/runs/36201014346),
  [P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36201014311),
  [BMv2](https://github.com/qobilidop/p4blo/actions/runs/36201014332),
  [XDP](https://github.com/qobilidop/p4blo/actions/runs/36201014286).
  Full local gate: 5199 passed, one optional local XDP-image skip, four
  expected failures. The bare-Python coverage build and fresh coverage
  measurement also passed (nine coverage tests).
- CI-speed final head `30c567c`, merged by PR #3: independent final-head
  review found no confirmed defects; all seven remote checks passed:
  [Python/schema](https://github.com/qobilidop/p4blo/actions/runs/36202637770),
  [Lean](https://github.com/qobilidop/p4blo/actions/runs/36202637944),
  [P4-SpecTec](https://github.com/qobilidop/p4blo/actions/runs/36202637833),
  [BMv2](https://github.com/qobilidop/p4blo/actions/runs/36202637772),
  [XDP](https://github.com/qobilidop/p4blo/actions/runs/36202637734).
  Local Lean and full gate passed with the same 5199/1/4 counts.
  Remote differential time was 428 s versus the prior 851 s; cold build
  335 s. PR #4 at `c8e5b46` then completed the Lean build/audit/test stage
  in 32 s after cache restore ([run](https://github.com/qobilidop/p4blo/actions/runs/36204465410));
  this timing is stage evidence, not a claim that that whole run passed.
- Fresh closure checks on the tree recorded by `9fc6c19`:
  `scripts/check-lean.sh` and `P4BLO_REQUIRE_LEAN=1 scripts/check.sh` exited
  0; 5199 passed, one optional XDP skip, four expected failures. A second
  full `scripts/check.sh` after the prose fixes also passed with those counts.
  No semantics changed; local oracle and mutation gates were not repeated.
- Implementation `37356009137d7f1bad5a284c01d59eace1841726`: all three
  Lean packages/audits, full gate (5195/1/4), and all 89 retained conformance
  fixtures reproduced unchanged answers. Original fixture provenance is
  retained; the changed semantics-source digest is reported, not answer drift.
- Frozen `70b51cdd28b331832fc9a6182b60218e68be38a6`: main P4-SpecTec/BMv2
  corpus suites passed 79 tests with two documented expected failures;
  `scripts/check-assurance.py` exited 0 for Python faults, Lean CRC fault,
  paired codec/observer faults, independent anchors and restored baselines.
  Independent boundary review approved this implementation with 43 focused
  passes, including scalar/six-block acceptance and nine malformed bindings.
  On equivalent adapter commit `f6ec9ef`, block oracle 67 passed/3 xfailed,
  frontend 98 passed, main P4-SpecTec corpus 35 passed.
- Earlier successful assurance at `58275b8` covered the pre-extension API,
  not the final split. The attempt invalidated by concurrent tracked edits
  never counted as a pass. Historical evidence for the frozen semantic scope
  remains at archive `26c9348` and in [assurance](../docs/assurance.md).

The closure reflection records the actual architectural counterexamples,
shared-API/dependency coordination, immutable migration anchors, frozen
assurance trees, conceptual documentation sweeps and bare-interpreter checks.
These lessons are enforced or prescribed in AGENTS.md, workflows and boundary
tests. The recovery corrected a stale post-merge status; authentication errors
in the prior Codex session were not repository build failures.

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
  [readback plan](notes/firewall-readback-next.md),
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

## Blocked

Nothing. Finish the simplification scope in the working note; do not reopen
retired application proofs or unrelated roadmap work.
