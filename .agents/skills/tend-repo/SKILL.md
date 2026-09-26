---
name: tend-repo
description: Maintain p4blo by reconciling code, documentation and validation evidence, compacting working state when due, and preserving evidence-backed lessons. Use for repository upkeep or retrospective cleanup, not ordinary feature implementation or an unsolicited whole-repo rewrite.
---

# Tend repo

Leave p4blo easier to understand and resume, without growing its instructions
by default. Follow `AGENTS.md` for policy, environment, review and publication;
this skill supplies a maintenance procedure, not another policy source.
Paths below are relative to the repository root unless linked explicitly.

## Establish scope and evidence

Read the resume files in the order prescribed by `AGENTS.md`. Inspect the
working tree, current revision, relevant history, unresolved reviews and
active work before editing. Honor narrower requests such as “review only”,
“exclude spec/” or “compact working state”. For a proposal-only request,
describe changes and validation without applying changes or running gates.
Creating or improving this skill does not itself invoke a repository cleanup.

For general upkeep, assess consistency, compaction needs and lessons from
recent work. State a finite scope; start with recent changes and follow their
references and dependencies. Preserve unrelated or concurrent work. A clean
inventory is a valid result; do not manufacture deletions or new abstractions.

Distinguish observed facts, decisions, proposals and historical claims.
Compare recorded state with files, refs and actual check results. An old pass
does not validate a changed tree; a local pass, a remote pass and a skip are
separate evidence. Do not resolve conflicting authority by silently changing
policy, or turn the roadmap and parked proofs into implementation tasks.

## Reconcile the repository

Trace relevant claims to their implementation and validation:

- **Semantic boundaries:** use `docs/design.md`, `docs/ir-semantics.md`,
  `docs/arch-supports.md` and `docs/assurance.md` as owners. Check that prose
  distinguishes architecture-free core proofs from tested architecture,
  extern and application behavior, and finite agreement from universal claims.
- **Representations and generated files:** follow schema, codec and consumer
  boundaries. Protobuf wire syntax and its JSON profile for Lean describe one
  IR. Check regeneration and consumers before treating duplicated or large
  files as waste; generated bindings, goldens and the website source copy have
  reproducibility checks. Do not edit generated outputs as independent sources.
- **Tests and gates:** follow `tests/README.md` and `docs/workflows.md`. Check
  package tests beside Python, root cross-implementation/program/oracle checks,
  shared support, explicit dependency markers and actual CI selections. Paths,
  test names, fixture counts or a green subset alone do not establish coverage.
- **Oracles and evidence:** preserve pinned native inputs, minimal discrepancy
  reproducers and the rulings in `docs/oracle-discrepancies.md`. A comment-only
  edit in a patch or native input can still invalidate hashes and provenance.
  Do not normalize independent expected answers merely to restore agreement.
- **Navigation and work state:** check commands, imports, links, current refs,
  worktrees and CI against their recorded state. Separate current paths from
  intentionally historical transcripts, reviews and negative layout guards.

Fix confirmed maintenance drift within scope. For substantial semantic defects,
architectural choices or feature work, record evidence and a concrete follow-up
instead of hiding the change inside cleanup. Do not weaken a requirement or
inflate a guarantee to make documents agree. Use existing checks first.

Do not confuse repository cleanup with cache eviction. Ignored `.artifacts/`
may contain recovery archives; worktrees and branches may hold unique parked
work. Inspect consumers, ownership and recovery inventories before proposing
removal. Apply current authorization and AGENTS policy to deletion, publication,
pin changes and campaign execution; invocation supplies no additional authority.

## Compact working state when due

Inventory hidden `.agents/` files explicitly. Assess the milestone/read-budget
triggers in AGENTS; do not compact automatically during active engineering.
When due, use [compact-agent-state](../compact-agent-state/SKILL.md) for the
archive point, promotion, reconciliation, review and integration procedure.
Keep that procedure in one place rather than reimplementing it here.

Preserve open obligations, uncertainty, current decision reasons/dates and
recovery instructions. Skills and machine-consumed recipes are maintained
artifacts, not disposable completed notes. Before removing a redundant source,
check its consumers and preserve useful content with its topic owner. Durable
artifact knowledge belongs in `docs/` or beside code; public docs must remain
independent of `.agents/`. Keep exact evidence identities and review limits
without requiring ignored logs or session transcripts to resume.

## Learn without accumulating rules

Use actual diffs, review findings, failures and user corrections. Choose the
smallest lasting improvement and its existing owner:

| Evidence or lesson | Destination |
|---|---|
| Mechanically detectable regression | Existing test or checker, with a meaningful negative case |
| Stable cross-cutting rule | Concise AGENTS update |
| Design choice, reason and uncertainty | Decisions register; a live note for detailed ongoing work |
| Current obligation or deferred research | Status or roadmap |
| Behavior, guarantee, usage or implementation explanation | Owning public document or code |
| Demonstrated weakness in maintenance procedure | This skill, or the compaction skill when it owns the step |

Do not create a lessons journal or duplicate policy across these owners.
One incident may justify a regression check without justifying a universal
rule. Retain uncertainty when evidence is inconclusive. Change this skill
only when experience or the user supports it; explain the expected improvement
and check the changed behavior with a realistic scenario. Self-improvement
is optional for a run, never an endless completion condition.

## Validate and finish

Review the diff for lost obligations, changed claims, weakened tests and scope
expansion. Use the applicable gates in `docs/workflows.md` and the independent
review/publication requirements in AGENTS; do not maintain another gate list
here. For moves, check all path spellings and consumers, not just Markdown
links. For skill edits, validate metadata and references and exercise realistic
requests, including narrow or read-only scope.

Record actual results and unavailable checks in status, with exact revisions
and remote evidence where available. Preserve a clear next step if unfinished.
Stop when scoped maintenance and required validation/review are complete, or
when a material decision needs the user. Report what changed, what was checked
and any remaining follow-ups; do not claim exhaustive repository correctness.
