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

Everything that was ever written is in git. The tag
`agents-archive/<date>` marks the tree just before each compaction, so
an archived note is one command away:
`git show agents-archive/2026-09-24:docs/notes/<name>.md`.

## Read first, in this order

1. `.agents/status.md`: where the work stands and what is open. Both
   finite scopes, assurance milestone 1 and the application collection,
   are complete; nothing is
   active, and neither completion reopens parked proofs. `docs/assurance.md`
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
   architecture or extern family decides; `docs/coverage.md` for what P4 constructs are in.

## Environment

Use the environment setup in `README.md#development`. Python examples work
with `uv sync --locked`; `.python-version` selects Python 3.13. Additional
schema, Lean and oracle tools are needed only for their respective gates.
Write ordinary commands in current documentation. Keep optional environment
setup centralized in the README instead of repeating wrappers or assuming a
specific package manager. Preserve actual historical command transcripts.

```
scripts/check.sh                                   # every Python and schema check CI runs
scripts/check-lean.sh                              # both Lean packages, audits and tests
P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees # Lean versus Python
uv run python scripts/check-assurance.py           # finite adversarial acceptance, after Lean
tests/oracle/build.sh                                  # the P4-SpecTec oracle, once
uv run pytest tests/test_oracle.py                 # corpus vectors on that oracle
docker build -t p4blo-bmv2 tests/oracle/bmv2             # the BMv2 oracle image, once
uv run pytest tests/test_oracle_bmv2.py            # corpus vectors on BMv2
docker build -t p4blo-xdp-build tests/oracle/xdp    # compile-only XDP profile
P4BLO_REQUIRE_XDP_BUILD=1 uv run pytest tests/test_xdp_build.py # offline XDP gate
```

Keep `main` green on all of them; check exit codes, not output. Five
workflows run them in CI: Python and schema, Lean, two P4 oracles and the
compile-only XDP profile. The latter is not a kernel execution oracle.
Its missing local image is an explicit skip; its dedicated CI requires it.
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
- **Pure Python.** No dependency of the `p4blo` package may ship
  native code, and nothing newer than Python 3.13 is used.
- **Generated code is committed.** `impl/python/p4blo/v0/*_pb2.py*` come
  from `buf generate`. Never edit them; edit the schema and regenerate.
  CI fails on drift.
- **Lean owns abstract syntax and meaning; protobuf owns wire syntax.**
  The IR spec is the `spec/ir/` Lake package (`p4blo-ir`, imports `P4bloIR`)
  and holds nothing architectural: no ports, no packet fate, no concrete
  externs. The reference architecture spec `spec/arch/` (`p4blo-arch`,
  imports `P4bloArch`) depends on it and supplies the switch, the extern
  families and the `p4blo-lean` endpoint. The `impl/lean/` user package
  (`p4blo`, imports `P4blo`) depends on both, never the reverse. Whole-program validity and codec proofs remain work in progress,
  not guarantees supplied by this organization. A closed behavior is
  written in `docs/ir-semantics.md` first (or `docs/arch-supports.md` when an
  architecture or extern family owns it) and implemented in both
  interpreters second.
- **Corpus programs** live under `tests/corpus/<name>/` with their eDSL
  source, golden, README and STF vectors; `tests/test_corpus.py` picks
  new ones up by itself. Sources are written in the typed eDSL
  (`p4blo.edsl`), are type-checked by pyright in CI, and must rebuild
  their golden byte for byte.
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
- **Commit and push autonomously.** The user authorizes committing and
  pushing completed, checked work without a separate permission prompt.
  Inspect the branch and remote first, preserve unrelated changes, and
  never force-push or bypass failing gates. Record unavailable gates
  explicitly rather than presenting skips as successful checks.
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
disjoint set of files named in its brief, builds against interfaces
already committed on `main`, and finishes with the gates green. The
integrator merges on `main`, reruns the gates and removes the worktree.
Spawn sub-agents when useful without waiting for permission; choose a
model appropriate to the task; create the worktree before delegating and
put its absolute path and file ownership in the brief. Sub-agents must
not edit the integrator's working tree.

After each build step an independent, read-only review agent looks for
confirmed defects with reproducers. Its report goes under
`.agents/reviews/` and its findings are fixed on `main`. Reviews stay
there until the next compaction archives them.

Worktrees do not isolate external resources: use distinct Docker image
tags and `P4BLO_BMV2_IMAGE` per implementation worktree, and never
rebuild the shared oracle image while another agent's tests use it.
Coordinate other mutable caches, ports and fixtures explicitly; immutable
pinned caches may be shared.

## Checkpoints and compaction

At each checkpoint, update `.agents/status.md`, any changed decision, and
this file when scope or navigation changes. Record the current iteration,
unresolved findings, active branch or worktree, durable evidence and the
next action.

When a milestone closes, or when the resume read (status, decisions,
roadmap and live notes) grows past roughly a thousand lines, compact
`.agents/` with the `compact-agent-state` skill in `.agents/skills/`.
Compaction removes history and keeps truth: every decision still in
force with its reason and date, the current evidence with commit hashes
that still resolve, open threads and known discrepancies, and anything a
test or a `docs/` file references. It changes no claim. The previous
tree is tagged `agents-archive/<date>` first, the compaction is reviewed
independently against that tag, and notes that turn out to describe the
artifact rather than the work are promoted into `docs/` instead of
being archived.

## Resuming

Read the files above in order. Nothing needed to continue the work lives
outside the repository; local worktrees and `.artifacts/` are convenience,
not evidence. If `.agents/status.md` says nothing is active, ask for a
scope before starting one.
