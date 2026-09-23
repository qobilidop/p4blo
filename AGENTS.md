# AGENTS.md

The entry point for anyone, human or agent, working in this repository.
It is written so that work can be resumed without any memory of how it
was done: everything needed is in the files named here.

## What this is

p4blo: P4's semantic core as an IR, architecture-free, with an
independent Lean semantics validated against a runnable reference.

## Read first, in this order

1. `docs/status.md`: where the work stands, per claim and per step, and
   the open threads.
2. `docs/decisions.md`: every choice made while building, dated, with
   its reason. Overrule one by adding a new entry that says so.
3. `docs/design.md`: what the project is, the four claims, how each is
   tested, what is out of scope.
4. `docs/workflows.md`: the gates, where every external input is
   pinned, and how to make each kind of change.
5. `docs/semantics.md` and `proto/p4blo/v0/p4blo.proto` when touching
   meaning or syntax; `docs/coverage.md` for what P4 constructs are in.

## Environment

The Nix flake is the development environment and the only reproducible
path. With direnv, `cd` into the repository and everything is on the
path; without it, prefix commands with `nix develop -c`. Without Nix,
`uv sync` gives a working Python environment but not the pinned
interpreter, `buf`, `protoc` or `elan`.

```
scripts/check.sh                                   # every Python and schema check CI runs
cd lean && lake build && lake test                 # the Lean interpreter and theorem
uv run pytest tests/test_drt.py -k lean_agrees     # Lean versus Python
nix develop .#oracle -c oracle/build.sh            # the P4-SpecTec oracle, once
uv run pytest tests/test_oracle.py                 # corpus vectors on that oracle
docker build -t p4blo-bmv2 oracle/bmv2             # the BMv2 oracle image, once
uv run pytest tests/test_oracle_bmv2.py            # corpus vectors on BMv2
```

Keep `main` green on all of them; check exit codes, not output. Four
workflows run them in CI: Python and schema, Lean, and one per oracle.
Docker with the pinned p4c image also typechecks the printer's goldens
when available and is skipped otherwise. `docs/workflows.md` has the
full gates table, every pin, and the procedure for each kind of change.

## Conventions

- **Pure Python.** No dependency of the `p4blo` package may ship
  native code, and nothing newer than Python 3.13 is used.
- **Generated code is committed.** `python/p4blo/v0/*_pb2.py*` come
  from `buf generate`. Never edit them; edit the schema and regenerate.
  CI fails on drift.
- **The schema is normative for syntax; the Lean interpreter for
  meaning.** A closed behavior is written in `docs/semantics.md` first
  and implemented in both interpreters second.
- **Corpus programs** live under `corpus/<name>/` with their eDSL
  source, golden, README and STF vectors; `tests/test_corpus.py` picks
  new ones up by itself. Sources are written in the typed eDSL
  (`p4blo.edsl`), are type-checked by pyright in CI, and must rebuild
  their golden byte for byte.
- **Every decision the design does not settle** becomes a dated entry
  in `docs/decisions.md`. `docs/status.md` is updated at every
  checkpoint, including its "Open threads".
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
- **Sub-agents** work in their own worktree, own a disjoint set of
  files, build against interfaces already committed on `main`, and
  finish with the gates green. Integration happens on `main`. Each
  build step is followed by an independent read-only review, kept
  under `docs/notes/reviews/`. Details in `docs/workflows.md`.
