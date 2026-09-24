# AGENTS.md

The entry point for anyone, human or agent, working in this repository.
It is written so that work can be resumed without any memory of how it
was done: everything needed is in the files named here.

## What this is

p4blo: P4's semantic core as an IR, architecture-free, with an
independent Lean semantics validated against a runnable reference.

## Read first, in this order

1. `docs/status.md`: where the work stands, per claim and per step, and
   the open threads. `docs/milestone-1.md` is the active finite definition
   of done; it supersedes older open-ended proof/application work lists.
   `docs/profile.md` and `docs/evidence.md` summarize its input domain and
   exact evidence boundaries; do not infer broader guarantees from counts.
2. `docs/decisions.md`: every choice made while building, dated, with
   its reason. Overrule one by adding a new entry that says so.
3. `docs/design.md`: what the project is, the four claims, how each is
   tested, what is out of scope.
4. `docs/workflows.md`: the gates, where every external input is
   pinned, and how to make each kind of change.
5. `docs/semantics.md` and `ir/proto/p4blo/v0/p4blo.proto` when touching
   meaning or syntax; `docs/coverage.md` for what P4 constructs are in.

## Environment

The Nix flake is the development environment and the only reproducible
path. With direnv, `cd` into the repository and everything is on the
path; without it, prefix commands with `nix develop -c`. Without Nix,
`uv sync` gives a working Python environment but not the pinned
interpreter, `buf`, `protoc` or `elan`.

```
scripts/check.sh                                   # every Python and schema check CI runs
scripts/check-lean.sh                              # both Lean packages, audits and tests
P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees # Lean versus Python
nix develop .#oracle -c tests/oracle/build.sh            # the P4-SpecTec oracle, once
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

- **Pure Python.** No dependency of the `p4blo` package may ship
  native code, and nothing newer than Python 3.13 is used.
- **Generated code is committed.** `python/p4blo/v0/*_pb2.py*` come
  from `buf generate`. Never edit them; edit the schema and regenerate.
  CI fails on drift.
- **Lean owns abstract syntax and meaning; protobuf owns wire syntax.**
  The spec is the `ir/` Lake package (`p4blo-ir`, imports `P4bloIR`). The
  `lean/` user package (`p4blo`, imports `P4blo`) imports it, never the reverse.
  Whole-program validity and codec proofs remain work
  in progress, not guarantees supplied by this organization. A closed
  behavior is written in `docs/semantics.md` first
  and implemented in both interpreters second.
- **Corpus programs** live under `tests/corpus/<name>/` with their eDSL
  source, golden, README and STF vectors; `tests/test_corpus.py` picks
  new ones up by itself. Sources are written in the typed eDSL
  (`p4blo.edsl`), are type-checked by pyright in CI, and must rebuild
  their golden byte for byte.
- **Every decision the design does not settle** becomes a dated entry
  in `docs/decisions.md`. `docs/status.md` is updated at every
  checkpoint, including its "Open threads". Record the exact checks run,
  skipped gates, remaining obligations and next concrete step. A fresh
  agent must be able to resume from the repository alone; conversation
  history and temporary files are not handoff documentation.
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
- **Commit and push autonomously.** The user authorizes committing and
  pushing completed, checked work without a separate permission prompt.
  Inspect the branch and remote first, preserve unrelated changes, and
  never force-push or bypass failing gates. Record unavailable gates
  explicitly rather than presenting skips as successful checks.
- **Continue autonomously within the requested direction.** Make scoped
  design decisions without waiting for feedback and record their reasons
  in `docs/decisions.md` for later review. Record confidence and a revisit
  trigger for uncertain choices. Follow `docs/milestone-1.md` for current
  acceptance (Python and Lean only); `docs/implementation.md` also contains
  future work, not mandatory completion criteria. Prefer reversible steps
  to waiting for feedback. Complete the finite acceptance checklist, then
  stop; do not automatically add every next possible proof. Universal Python
  correctness and full application/pipeline proofs are explicit non-goals.
- **Challenge verification adversarially.** Introduce deliberate semantic
  faults in isolated worktrees on both the Python and Lean sides. Record
  which conformance tests kill each mutant, investigate survivors, and
  improve coverage before repeating. A failure to build is not a test
  that detected a semantic inconsistency. Never merge intentional faults.
- **Sub-agents** work in their own worktree, own a disjoint set of
  files, build against interfaces already committed on `main`, and
  finish with the gates green. Integration happens on `main`. Each
  build step is followed by an independent read-only review, kept
  under `docs/notes/reviews/`. Details in `docs/workflows.md`.
  Spawn them when useful without waiting for permission; choose a model
  appropriate to the task's complexity. Create each worktree before
  delegating and include its absolute path and file ownership in the
  brief. Sub-agents must not edit the integrator's working tree.
  Worktrees do not isolate external resources: use distinct Docker image
  tags and `P4BLO_BMV2_IMAGE` per implementation worktree. Never rebuild the
  shared oracle image while another agent's tests use it. Coordinate other
  mutable caches, ports and fixtures explicitly; immutable pinned caches
  may be shared.
