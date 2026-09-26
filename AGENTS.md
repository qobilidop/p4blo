# AGENTS.md

The entry point for anyone, human or agent, working in this repository.
It is written so that work can be resumed without any memory of how it
was done: everything needed is in the files named here.

## What this is

p4blo: P4's semantic core as an IR, architecture-free, with an
independent Lean semantics validated against a runnable reference.

## Where things live

Documentation is split by what it describes, not by who reads it:

- `docs/` describes the artifact: what p4blo is, what it means, what it
  covers, how to use it, how to check and change it, and the evidence for
  its claims. It is written for people and will be published on its own,
  so nothing in it links into `.agents/` (a test enforces this).
- `.agents/` describes the work: where it stands, what was decided and
  why, what is parked, and the procedures agents follow. It is committed
  narrative state, never runtime state; logs and artifacts stay in the
  ignored `.artifacts/`.
- Nothing dated goes into `docs/`: no checkpoint prose, no run
  transcripts, no plans. A reference page cites a revision and links the
  evidence; the run itself is recorded in `.agents/status.md` and git.

| File | Holds |
|---|---|
| `.agents/status.md` | current state, last checked evidence, open threads, next step |
| `.agents/decisions.md` | the decisions in force, by topic, each with its reason and date |
| `.agents/roadmap.md` | the research backlog beyond the completed scopes |
| `.agents/notes/` | live working notes: parked-work inventories, plans they cite, campaign recipes |
| `.agents/reviews/` | independent review reports for the current work, until the next compaction |
| `.agents/skills/` | Agent Skills (`<name>/SKILL.md`), the cross-agent location; `.claude/skills` is a symlink to it, which Claude Code loads through but `claude plugin validate` does not, so validate the real path |

`.agents/` is a hidden directory. Searches with `rg`, `fd` and similar
tools skip it unless told to include hidden files; `git grep` does not.

Everything that was ever written is in git. `.agents/status.md` names
the archive commit, the tree just before each compaction, so an archived
note is one command away: `git show <archive commit>:.agents/notes/<name>.md`
(`docs/notes/` at the first archive commit).
The first compaction's archive commit is `9e8f7d47`. The repository
creates no git tags.

## Read first, in this order

1. `.agents/status.md`: where the work stands and what is open. Three
   finite scopes, assurance milestone 1, the application collection and
   the architecture-free IR semantics scope, are complete and frozen;
   maintenance does not reopen parked proofs. The status file names any
   active engineering work. The example-guided authoring and CI-efficiency
   scopes and core-only assurance simplification are complete. Retired
   application/architecture proofs are historical, not continuation work. Independent blocks and optional BlockLibrary bundles are
   documented in `docs/python-edsl.md`; architecture assembly stays separate.
   `docs/assurance.md`
   states the claim, the input domain and exact evidence boundaries; do
   not infer broader guarantees from counts.
2. `.agents/decisions.md`: what is decided and why. Overrule an entry by
   rewriting it in place with the new date and reason.
3. `docs/design.md`: what the project is, the four claims, how each is
   tested, what is out of scope.
4. `docs/workflows.md`: the gates, where every external input is pinned,
   and how to make each kind of change.
5. `docs/ir-semantics.md` and `spec/ir/proto/p4blo/v0/p4blo.proto` when touching
   meaning or syntax, `docs/arch-supports.md` when touching what an
   architecture or extern family decides; `docs/p4-spec-coverage.md` for what P4 constructs are in.

## Environment

Use the environment setup in `README.md#development`. Python examples work
with `uv sync --locked`; `.python-version` selects Python 3.13. Additional
schema, Lean and oracle tools are needed only for their respective gates.
Write ordinary commands in current documentation. Keep optional environment
setup centralized in the README instead of repeating wrappers or assuming a
specific package manager. Preserve actual historical command transcripts.

```
scripts/check.sh                                   # every Python and schema check CI runs
scripts/check-lean.sh                              # core proofs and executable adapter tests
P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees # Lean versus Python
uv run python scripts/check-assurance.py           # finite adversarial acceptance, after Lean
tests/oracle/build.sh                              # the P4-SpecTec oracle, once
uv run pytest tests/external/test_oracle.py        # corpus vectors on that oracle
docker build -t p4blo-bmv2 tests/oracle/bmv2       # the BMv2 oracle image, once
uv run pytest tests/external/test_oracle_bmv2.py   # corpus vectors on BMv2
```

Keep `main` green on all of them; check exit codes, not output. Four
validation workflows run them in CI: Python and schema, Lean and two P4 oracles.
Python/schema always run. Specialist jobs skip only proven narrative-only
changes under `scripts/ci-scope.py`; executable/parsed docs and uncertain
changes run full CI. The Lean differential collection is split into two
complete, disjoint shards. See `docs/workflows.md` for applicability.
Docker with the pinned p4c image also typechecks the printer's goldens
when available and is skipped otherwise. `docs/workflows.md` has the
full gates table, every pin, and the procedure for each kind of change.
Build Lean before running differential tests; never rebuild its executable
concurrently with tests in the same worktree. New real-Lean conformance
tests use the shared `lean_binary` fixture and `test_lean_agrees` name prefix
so the required CI gate discovers them without a hand-maintained file list.

## Conventions

- **Agent instructions live in `AGENTS.md` alone.** Never create `CLAUDE.md`
  or `CLAUDE.local.md`; Claude-specific notes belong in `.claude/rules/`.
  Keep this entry point current when the active scope or workflow changes.
- **Name the project P4-SpecTec.** SpecTec alone is a different project.
  Distinguish P4 program IR from the specification's IL, AL and SL when
  discussing interfaces or coverage. Preserve literal upstream names,
  protocol fields and historical records when they use older terminology.
- **Make invariants executable at their boundary.** Prefer a small
  structural check over another reminder when a mistake is mechanically
  detectable. A checker needs a negative case showing that the forbidden
  change fails. Preserve independent semantic implementations: copying
  P4-SpecTec algorithms into both p4blo interpreters weakens the oracle.
- **Pure Python.** No dependency of the `p4blo` package may ship
  native code, and nothing newer than Python 3.13 is used.
- **Generated code is committed.** `impl/python/p4blo/v0/*_pb2.py*` and
  `impl/python/p4blo/arch/v0/*_pb2.py*` come from `buf generate`. Never edit
  them; edit the schemas and regenerate.
  CI checks a fresh generation's inventory and bytes against both the
  index and working tree. Stage new deliverables before the full gate;
  a clean diff of tracked files alone cannot detect omitted outputs.
- **Keep generated artifacts small and reproducible.** Tracked files
  must be at most 5 MiB in both the index and working tree, enforced by
  `scripts/check-file-sizes.py` through the structure tests. No exceptions.
  Prefer reproducible generation, small losslessly compressed snapshots
  with raw-content checksums, or checksum-pinned external artifacts.
  Consider history growth as well as checkout size; reducing size does
  not authorize rewriting published history. Logs stay in `.artifacts/`.
- **Lean owns abstract syntax and meaning; protobuf owns wire syntax.**
  The IR spec is the `spec/ir/` Lake package (`p4blo-ir`, imports `P4bloIR`)
  and holds nothing architectural: no ports, no packet fate, no concrete
  externs. The executable architecture adapter `spec/arch/` (`p4blo-arch`,
  imports `P4bloArch`) depends on it and supplies the switch, the extern
  families and the `p4blo-lean` endpoint. This adapter is tested, without
  architecture-specific proof guarantees. Python is the authoring surface;
  there is no separate Lean authoring/application package. In each package,
  client imports live under `<Root>/`, gate-only tests/audits/fixtures under
  `<Root>Test/` as one default-target library, and at the root only the root
  module, Lake's files, `README.md` and at most one `Main.lean`, plus schemas
  under `spec/ir/proto/` and `spec/arch/proto/` (`docs/design.md`, "The Lean
  packages"). Core library validity is decided by a checker proved sound;
  progress is proved under its explicit environment and machine premises.
  The generic `ExternContract` remains an assumption, without a proof that
  the supplied architecture discharges it. Termination and whole-library
  codec composition remain open. Formal assurance is scoped to core IR;
  do not revive application, architecture or typed-source proofs or the
  retired execution-certificate experiment without a new user scope.
  A closed behavior is written in `docs/ir-semantics.md` first (or `docs/arch-supports.md` when an
  architecture or extern family owns it) and implemented in both
  interpreters second.
- **Corpus programs** live under `tests/corpus/<name>/` with their eDSL
  source, golden, README and STF vectors;
  `tests/programs/test_corpus.py` picks new ones up by itself. Sources
  are written in the typed eDSL (`p4blo.edsl`), are type-checked by
  pyright in CI, and must rebuild their golden byte for byte.
- **Public application examples** follow the application section of
  `docs/workflows.md`, with canonical
  Python source under `examples/` and verification assets under
  `tests/examples/`. Shared checks discover canonical sources and require
  goldens, vectors and demos; both oracle catalogs include example vectors.
  Wire new checks into CI explicitly. Preserve upstream regression programs
  in `tests/corpus/`.
- **Every decision the design does not settle** goes in
  `.agents/decisions.md`, under its topic, with its reason and date, and
  with a confidence and revisit trigger when uncertain. Do not restate what
  the design or semantics documents already settle.
- **`.agents/status.md` is updated at every checkpoint**, including its
  open threads: the exact checks run, skipped gates, remaining obligations
  and the next concrete step. A fresh agent must be able to resume from the
  repository alone; conversation history and temporary files are not
  handoff documentation.
- **Commits** follow the usual git conventions (Chris Beams' seven
  rules; the kernel's "describe your changes"). One logical change per
  commit: if the subject wants an "and" or a semicolon, split it. The
  subject is imperative, capitalized, at most 50 characters, no final
  period, and completes "If applied, this commit will ...". A blank
  line, then a body wrapped at 72 columns that says what the diff
  cannot: the problem, why this change and not another, and what a
  reader must know afterwards. Do not restate the diff; omit the body
  when the subject says it all. Agent commits end with a
  `Co-Authored-By: <agent> <email>` trailer after a blank line.
  Read recent commits before writing new ones and break work into
  reasonably sized, independently understandable changes. For every
  Codex-authored commit, immediately before committing run
  `"${CODEX_HOME:-$HOME/.codex}/bin/coauthor"` in the active session and
  append its output unchanged. If it fails, stop and report the failure;
  never guess or hard-code the model.
  Size commits by a coherent, independently reviewable outcome, not a line
  quota or one file per commit. Include related tests and documentation;
  separate mechanical moves and reusable API changes from application policy.
  Once notes are archived, the commit log is the only narrative of how
  the work went, so the body matters.
- **PRs are optional during the personal-project phase.** The user
  authorizes committing, pushing and integrating completed, checked work
  autonomously, including substantive changes, without a PR. Use feature
  branches and worktrees when useful for isolation, review or parked work;
  direct commits to `main` are also allowed. Inspect the branch and remote,
  preserve unrelated changes, and never force-push or bypass repository protections. Obtain independent
  review of the final patch and run the full local gate before pushing;
  record unavailable gates as such. After pushing, verify applicable remote
  CI on the exact integrated `main` revision before declaring the work
  complete. Feature-branch pushes may checkpoint unfinished work; they do
  not replace validation of the integrated revision. Fix failures promptly
  with follow-up commits. A local pass is not remote CI, and a skip is not
  a pass. Use a PR when explicitly requested or
  required by repository protections; then require final-head review and
  applicable remote CI before merge, and re-check its head SHA.
- **When a PR is used, write it for a reader without the conversation.**
  Lead with the problem and resulting behavior, explain the approach and consequential
  tradeoffs, then give validation commands/results and meaningful limits.
  Link supporting evidence without making the links carry all context.
  Scale detail to the diff; omit empty template sections and progress
  diaries. Re-read the staged diff, commit message and final PR description
  before submission; update the description when scope changes.
  Include one short AI-disclosure sentence naming the authoring agent and
  model verified by the active-session coauthor helper. Distinguish
  AI-agent review from human review; never invent attribution.
- **Preserve meaningful commits when merging.** Use a merge commit for
  coherent commits whose rationale and identities are worth retaining;
  squash WIP/fixup sequences with a considered final message preserving
  rationale and coauthor attribution. Rebase-and-merge only with an explicit
  linear-history preference. Choose per PR, and keep merge-strategy prose
  out of the PR description unless requested. Do not bypass protections.
- **Continue autonomously within the requested direction.** Make scoped
  design decisions without waiting for feedback and record their reasons
  for later review. Prefer reversible steps to waiting for feedback.
  Complete the finite scope you were given, then stop; `.agents/roadmap.md`
  is backlog, not a to-do list, and universal Python correctness and full
  application/pipeline proofs are explicit non-goals.
- **Challenge verification adversarially.** Introduce deliberate semantic
  faults in isolated worktrees on both the Python and Lean sides. Record
  which conformance tests kill each mutant, investigate survivors, and
  improve coverage before repeating. A failure to build is not a test
  that detected a semantic inconsistency. Never merge intentional faults.

## Working with agents

Each sub-agent gets its own git worktree (`git worktree add`), owns a
disjoint set of files named in its brief, builds against an explicit
committed base revision, and hands back with the checks that its
change can affect green: lint and types, the test modules that cover its
files, and the Lean gate when it touched a Lean package. It runs the
full gate only when the change is cross-cutting (a path move, the wire
or pipe protocol, a module many others import). The integrator combines
reviewed commits in batches, integrates them into `main`, and runs the
full gate once per batch before pushing. Verify applicable remote CI on
the exact pushed revision before closing the work, then remove the
worktrees. If a PR is required, follow the PR exception above.
Before splitting a public API change, agree concrete caller examples and
an acceptance case that would expose a false abstraction boundary. Follow
that case through source, wire types, validation, execution and proof premises;
a clean facade alone is not a boundary. Record cross-agent API signatures
and commit dependencies in the working note.
Before the first CI push, review the usage and design prose for universal
claims that belonged only to the old adapter, as well as moved names and paths.
When two slices depend on each other, hand off committed patches with
explicit pending checks, then validate the integrated batch; do not have
both agents wait for the other's green commit. Never amend a handed-off
commit: corrections are follow-up commits.
Spawn sub-agents when useful without waiting for permission; choose a
model appropriate to the task; create the worktree before delegating and
put its absolute path and file ownership in the brief. Sub-agents must
not edit the integrator's working tree.

After each build step an independent, read-only review agent looks for
confirmed defects with reproducers. Its report goes under
`.agents/reviews/` and its findings are fixed on the working branch before
integration. Record the reviewed revision or patch, commands and results,
confirmed findings with reproducers, and any checks the reviewer could not
run. Reviews stay there until the next compaction archives them.

Worktrees do not isolate external resources: use distinct Docker image
tags and `P4BLO_BMV2_IMAGE` per implementation worktree, and never
rebuild the shared oracle image while another agent's tests use it.
Coordinate other mutable caches, ports and fixtures explicitly; immutable
pinned caches may be shared. Freeze the entire tracked tree during a
provenance-checked assurance experiment: its inventory includes documentation,
so even a concurrent note edit invalidates the run.

Unfinished work is never left as an uncommitted worktree. Commit it to
its branch as a work-in-progress commit whose message says what it holds
and what it lacks, push the branch, and remove the worktree; the
parked-proof inventory points at branches. Retain a branch only after
comparing its content with `main`; a branch whose commits are merged or
whose files are byte-identical to what `main` has is deleted, not kept
"in case". Uncommitted drafts on one machine were the most fragile thing
in this repository for a day.

## Checkpoints and compaction

At each checkpoint, update `.agents/status.md`, any changed decision, and
this file when scope or navigation changes. Record the current iteration,
unresolved findings, active branch or worktree, durable evidence and the
next action.

Two rules learned the hard way. First, the full gate runs before a step
is pushed, not a subset: the structural and link tests passed on the day
the codec tests looked for their endpoint in the wrong package, and only
`scripts/check.sh` found it. Second, when directories move, search for
the path in every spelling, not only with a slash: `"ir"` in a
`git ls-files` call, `-d lean` in a command, and `parents[N]` in a path
computation all broke silently after a move, and
`tests/structure/test_package_layout.py` and
`tests/structure/test_boundaries.py` exist to pin the paths and the
import graph a gate depends on. Historical records under `.agents/reviews/`
keep the paths they were written with; exclude them from rewrites.

When a milestone closes, or when the resume read (status, decisions,
roadmap and live notes) grows past roughly a thousand lines, compact
`.agents/` with the `compact-agent-state` skill in `.agents/skills/`.
Compaction removes history and keeps truth: every decision still in
force with its reason and date, the current evidence with commit hashes
that still resolve, open threads and known discrepancies, and anything a
test or a `docs/` file references. It changes no claim. The previous
tree's commit is recorded first, the compaction is reviewed
independently against that commit, and notes that turn out to describe the
artifact rather than the work are promoted into `docs/` instead of
being archived.

## Resuming

Read the files above in order. Nothing needed to continue the work lives
outside the repository; local worktrees and `.artifacts/` are convenience,
not evidence. If `.agents/status.md` says nothing is active, ask for a
scope before starting one.
