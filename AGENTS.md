# AGENTS.md

Instructions for anyone, human or agent, working in this repository.

## What this is

p4blo: P4's semantic core as an IR, architecture-free, with an
independent Lean semantics validated against a runnable reference.
Read `docs/design.md` before changing anything; it is the source of
truth for what the project is and is not. `docs/status.md` says where
the work stands. `docs/decisions.md` records every choice with its
reason; add a dated entry there whenever you decide something the
design doc does not already settle.

## Environment

The Nix flake is the development environment. With direnv, `cd` into
the repository and everything is on the path. Without direnv, prefix
commands with `nix develop -c`. Without Nix, `uv sync` gives a working
Python environment but not `buf`, `protoc` or `elan`.

```
uv sync --locked          # install Python packages into .venv
uv run pytest             # tests
uv run ruff check .       # lint
uv run ruff format .      # format
uv run pyright            # type check
buf lint                  # schema lint
buf generate              # regenerate python/p4blo/v0 from proto/
```

CI runs exactly these commands inside the flake on Linux and macOS.
Keep `main` green.

Optional: with Docker running, `docker run --rm -v "$PWD":/w p4lang/p4c
p4test /w/<file>.p4` typechecks a printed program; the printer tests
use it when available and skip otherwise.

## Conventions

- **Pure Python.** No dependency of the `p4blo` package may ship
  native code, and nothing newer than Python 3.13 is used.
- **Generated code is committed.** `python/p4blo/v0/*_pb2.py*` come
  from `buf generate`. Never edit them; edit the schema and regenerate.
  CI fails on drift.
- **The schema is normative for syntax.** Change `proto/p4blo/v0/
  p4blo.proto` deliberately, and expect every golden under `corpus/`
  to need regeneration afterwards.
- **Closed behaviors go in `docs/semantics.md`.** If the interpreter
  has to choose what P4 leaves open, the choice is written there
  first and implemented second.
- **Tests live under `tests/`.** One file per concern. Corpus
  programs live under `corpus/<program>/` with their goldens and STF
  vectors beside them.
- **Commits** are small, human-readable chunks with a subject line
  under 72 characters and a body that says why. Agent commits end
  with a `Co-Authored-By: <agent> <email>` trailer.
- **Sub-agents** work in their own worktree, own a disjoint set of
  files, build against interfaces already committed on `main`, and
  finish with a green test run. Integration happens on `main`.
