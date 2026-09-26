# AGENTS.md

Repository policy and resume entry point for humans and agents. p4blo is P4's
architecture-free semantic core as an IR, with independent Lean semantics
validated against a runnable Python reference. [Design](docs/design.md) owns
architecture; [assurance](docs/assurance.md) owns delivered guarantees and limits.

## Where information belongs

| Owner | Responsibility |
|---|---|
| `README.md` | public introduction, current capability summary, setup and reading map |
| `docs/` | artifact design, contracts, usage, assurance and development procedures |
| `.agents/status.md` | current scope, checked revision, validation, obligations and next step |
| `.agents/decisions.md` | cross-cutting choices, reasons, dates and revisit conditions |
| `.agents/roadmap.md` | deferred research and its entry conditions, not execution authorization |
| `.agents/notes/` | topic-specific rationale, investigations, plans and review evidence |
| `.agents/notes/recovery.md` | archive commits, retired branches and local recovery boundaries |
| `.agents/skills/` | maintained procedures; policy remains in this file |

Public docs must stand on their own and never link into `.agents/`. Keep
checkpoint prose, dated run transcripts and plans in working state; reference
pages cite immutable revisions and link evidence. Logs/builds belong in ignored
`.artifacts/`, not committed narrative state. Checked recipes and skills are
maintained artifacts, not disposable notes.

Organize notes by topic. Start with one file; add a topic directory only for
independently useful supporting material. Each note says whether it is active,
paused or durable and why it remains. Put reviews beside their topic, in a
section or separate file as needed. Git history archives completed notes;
create no tags or accumulating archive folders. Preserve live obligations and
recovery instructions before deleting history from the working set.

`.agents/` is hidden: use hidden-file searches or `git grep`. Skills live once
in `.agents/skills/`; `.claude/skills` is its committed symlink. Claude Code
loads through that link, but `claude plugin validate` does not; validate the
real path. Never create `CLAUDE.md` or `CLAUDE.local.md`; Claude-specific notes
belong in `.claude/rules/`. Keep this entry point current when navigation changes.

## Read first

1. `.agents/status.md`: active scope and immediate obligations.
2. `.agents/decisions.md`: current choices and pointers to detailed rationale.
3. `docs/design.md` and `docs/assurance.md`: intended system versus actual claims.
4. `docs/workflows.md`: applicable gates, pinned inputs and change procedures.
5. For meaning/syntax changes, `docs/ir-semantics.md` and
   `spec/ir/proto/p4blo/v0/p4blo.proto`; for architecture/extern behavior,
   `docs/arch-supports.md`; for supported constructs, `docs/p4-spec-coverage.md`.

Follow links to the relevant topic, not every archived report. Resume from
committed files, not chat history or temporary worktrees. If nothing is active,
ask for a scope before starting one. Roadmap and retired proofs are not a queue.

## Environment and validation

Use [README development setup](README.md#development); ordinary commands assume
required tools on PATH. Keep optional setup there rather than repeating wrappers
or requiring a package manager. Preserve historical command transcripts.
`uv sync --locked` and `.python-version` select Python 3.13. No package dependency
may ship native code, and nothing newer than Python 3.13 is used.

[Workflows](docs/workflows.md) owns the gate table, pins and change procedures;
[the test guide](tests/README.md) owns test organization and selection commands.
Run `scripts/check.sh` before pushing, plus applicable specialist gates. Check
actual exit codes, not a log reader's result. Keep main green; record unavailable
gates and skips accurately. Python/schema always run remotely; specialist jobs
skip only changes proven narrative-only by `scripts/ci-scope.py`. Unknown or
parsed/executed inputs require full CI. A skip is not a pass.
If local disk capacity prevents a specialist gate, use a reviewed isolated-branch
CI experiment and record the local gate as unavailable, never successful. Do not
prune unrelated data to make it run.

Build Lean before differential tests; never rebuild the executable while tests
consume it in the same worktree. Use fresh caches after package moves; copied
modules can shadow renamed source. At most two heavy local jobs run together.
Real-Lean tests use the shared `lean_binary` fixture and `lean` marker; external
checks declare `spectec`, `bmv2` or `p4c`. Shared inputs/answers belong in support
modules, never imports from collected test modules. Preserve both complete,
disjoint Lean CI shards when changing selection or organization.

## Semantic and source conventions

- **Preserve independent implementations.** Make mechanically detectable
  invariants executable at their boundary, with a negative case showing the
  forbidden change fails. Copying P4-SpecTec algorithms into both interpreters
  weakens the oracle.
- **Use P4-SpecTec** for the project; SpecTec alone names a different project.
  Distinguish P4 program IR from specification IL, AL and SL. Preserve literal
  upstream names, protocol fields and historical records.
- **Use codec** for an encoder/decoder pair and encode/decode for operations.
  Serialization describes a process or representation, not alternate component
  or test-suite names.
- **Keep the core architecture-free.** Lean owns abstract syntax/meaning;
  protobuf owns wire syntax. Do not put ports, packet fate or concrete externs
  in `spec/ir/`. The supplied v1model adapter is tested executable code, not
  an architecture proof. Formal assurance targets core IR; do not revive
  application, architecture, typed-source proofs or execution certificates
  without a new user scope. Read exact proof premises in assurance; do not
  infer universal equivalence, termination or codec composition from counts.
- **Specify closed behavior first** in `docs/ir-semantics.md`, or in
  `docs/arch-supports.md` when architecture/extern contracts own it, then
  implement independently in both interpreters. Preserve minimal discrepancy
  reproducers and their contract-based rulings in `docs/oracle-discrepancies.md`.
- **Keep Lean library boundaries explicit.** Client imports live under `<Root>/`;
  gate-only tests/audits/fixtures under `<Root>Test/` as one default-target library.
  Package roots contain the root module, Lake files, README and at most one Main,
  plus the protobuf schema exceptions. Exact package names and dependencies are
  in Design's “The Lean packages”; layout/boundary tests enforce them.
- **Regenerate committed code.** `impl/python/p4blo/v0/*_pb2.py*` and
  `impl/python/p4blo/arch/v0/*_pb2.py*` come from `buf generate`; edit schemas,
  never generated files. Fresh generation must match inventory and bytes in
  both index and working tree. Stage new deliverables before the full gate.
- **Keep artifacts small and reproducible.** Every tracked file is at most
  5 MiB in index and working tree, with no exceptions. Prefer reproducible
  generation, compressed snapshots with raw checksums or pinned external data.
  Consider history growth; size cleanup does not authorize published-history
  rewriting. Such changes require explicit agreement on affected refs and
  disruption; never bypass protections. Logs stay in `.artifacts/`.
- **Corpus sources** under `tests/programs/corpus/` use the typed eDSL, pass
  pyright and rebuild goldens byte for byte; shared checks discover programs.
  Public application sources remain under `examples/`, verification assets
  under `tests/programs/examples/`. Follow the application workflow, preserve
  upstream regression inputs, and wire new checks into CI explicitly.
- **Challenge verification adversarially** in scoped correctness work: inject
  semantic faults on Python and Lean sides in isolated worktrees, record which
  tests kill them, investigate survivors and improve coverage. Build failures
  are not semantic detections. Never integrate deliberate faults. Retain
  independent expected answers; agreement and roundtrips alone are insufficient.

## Decisions, commits and publication

Record consequential unsettled choices with reason and date. Cross-cutting
choices go in Decisions; detailed constraints with their topic evidence. Include
confidence and a revisit trigger when uncertain. Supersede entries in place with
the new date/reason, preserving still-binding rationale. Do not duplicate policy
or settled design. Make reasonable scoped decisions autonomously, prefer
reversible steps and finish the finite request; do not expand into backlog.

Commits follow Chris Beams' seven rules and Git's contribution guidance. Use a
capitalized imperative subject of at most 50 characters, no final period; one
logical outcome per commit. After a blank line, wrap prose at 72 columns and
explain the problem, why this approach and consequential context; omit the body
only when the subject suffices. Read recent commits and the staged diff first.
Include related tests/docs, separate mechanical moves and reusable API changes
from application policy, and size by reviewable outcome rather than line count.
The log becomes the narrative after working notes are archived.

Every Codex commit must end with the trailer returned unchanged by
`"${CODEX_HOME:-$HOME/.codex}/bin/coauthor"`, run in the active session immediately
before that commit. If it fails, stop and report; never guess a model. Other
agent commits also require their `Co-Authored-By: <agent> <email>` trailer.

PRs are optional during this personal-project phase. The user authorizes
committing, pushing and integrating completed checked work autonomously,
including direct main commits. Use branches/worktrees when isolation helps.
Inspect branch/remote, preserve unrelated changes, never force-push or bypass
protections. Independent final-patch review and the full local gate precede
push; verify applicable remote CI on the exact integrated main SHA before
completion. Local results or feature-branch runs do not replace that check.
Fix failures with follow-up commits. WIP branch pushes checkpoint unfinished
work and record what remains unvalidated; they do not declare it integrated.

Use a PR when requested or required by protections. Require review and applicable
CI on its final revision, rechecking head SHA before merge. Write for a reader
without the conversation: problem/result, consequential approach/tradeoffs,
validation and limits. Links support rather than replace context. Scale detail,
omit boilerplate/progress diaries, and reread the description after scope changes.
Include one short AI disclosure naming the agent/model verified by the session
helper; distinguish AI-agent review from human review and never invent credit.

Preserve meaningful commits: merge coherent history; squash WIP/fixups with a
considered message preserving rationale and coauthors. Rebase-and-merge requires
an explicit linear-history preference. Keep strategy prose out of PR descriptions
unless requested. Never amend a handed-off commit; use a follow-up correction.

## Agent work and reviews

Spawn subagents when useful without waiting for permission; choose a suitable
model. Create each agent's worktree before delegating, name its absolute path,
explicit committed base and disjoint file ownership. Agents do not edit the
integrator's tree. Authors run lint/types/affected tests and the Lean gate when
changing Lean; full gates are needed for cross-cutting changes. The integrator
combines reviewed commits in batches and runs the full gate once per batch before
push, then checks exact-main CI and removes finished worktrees.

Before splitting an API change, agree concrete callers and a case exposing a
false boundary. Trace it through source, wire, validation, execution and proof
premises. Record shared API signatures and commit dependencies in the topic note.
For dependent slices, hand off committed patches with pending checks and validate
the integrated batch; do not wait cyclically for each other's green commit.
Before the first CI push, check usage/design prose for obsolete universal claims
and moved names/paths, not merely a clean facade.

After each build step, an independent read-only reviewer seeks confirmed defects
with reproducers. Record review beside the topic, with reviewed revision/patch,
reviewer identity and independence limits, commands/results, findings and checks
not run. Fix findings before integration. Preserve original verdicts and keep
later resolutions distinct. Archive only after preserving unresolved obligations.
For application changes, include independent correctness and usability review
after each build step: run the documented demo and try a small policy change in
an isolated scratch copy or local configuration, without editing canonical sources.
Record concrete authoring, configuration, inspection and diagnostic difficulties
from the smallest runnable scenario. Application completion requires a reviewed
contract, runnable demo, independent exact packet/fate/state expectations, exact
golden reconstruction, Python/Lean and applicable oracle checks with exclusions,
targeted source faults and fresh-reader review; Workflows owns the technical steps.

Worktrees do not isolate caches, ports or Docker. Use distinct image tags and
`P4BLO_BMV2_IMAGE` per implementation worktree; never rebuild an image while
another test uses it. Own and verify each Docker check container; clean only
task-owned artifacts and never prune globally. Coordinate mutable resources;
pinned immutable caches may be shared. Freeze all tracked files during
provenance-checked assurance runs:
even a concurrent note edit changes their inventory.

Never abandon unfinished work uncommitted. Commit WIP to its branch with what
it holds/lacks, push the branch and remove the worktree; record recovery refs.
Compare branches with main before retaining them: delete merged or byte-identical
branches rather than keeping them “in case”. Preserve unique parked work and its
known gaps; routine compaction does not authorize deleting recovery backups.

## Checkpoints and compaction

Update Status at every checkpoint: scope, checked revision, exact validation and
skips, unresolved obligations, active branch/worktree and next action. Topic notes
hold detailed evidence; Decisions holds changed choices. Keep resume information
in the repository, with local-only recovery limits explicitly distinguished from
published evidence.

Use [tend-repo](.agents/skills/tend-repo/SKILL.md) for general upkeep. When a
milestone closes or the resume read exceeds roughly a thousand lines, use
[compact-agent-state](.agents/skills/compact-agent-state/SKILL.md). Record the
pre-compaction archive commit, consolidate by topic, promote artifact knowledge
to its public owner and preserve every current choice/reason/date, open thread,
known discrepancy and evidence identity. Independently compare with the archive;
compaction changes no claim. Current status is a checkpoint, not a milestone log.

When moving paths, search every spelling, including fragments without slashes
and path computations (`parents[N]`). Existing layout and boundary tests protect
gate dependencies. Historical review records retain original paths; exclude their
text from rewrites or label archived identifiers explicitly.
