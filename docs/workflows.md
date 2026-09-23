# Workflows

How to build, check and change p4blo, for a person or an agent who has
never seen it. Every command below runs from the repository root inside
the flake (`direnv allow` once, or prefix with `nix develop -c`).

## Gates

`main` is green when all of these pass. CI runs the first three on every
push; run them locally before pushing and check exit codes, not output.

| Gate | Command | Expected |
|---|---|---|
| Python and schema | `scripts/check.sh` | ends with `all checks passed`, exit 0 |
| Lean | `cd lean && lake build && lake test` | `all tests passed`, exit 0 |
| Lean vs Python | `uv run pytest tests/test_drt.py -k lean_agrees` | 11 passed after `lake build`; skips only when the binary is missing |
| Oracle | `uv run pytest tests/test_oracle.py` | every `test_vector_passes_on_the_oracle` passes; skips without the oracle binary (see below) |
| Printer goldens under p4c | part of `scripts/check.sh` | runs when Docker is up, skips otherwise |

A larger differential sweep, for a change to either interpreter:

```
uv run python -m p4blo.drt corpus/<program> 2000 --seed <n> --lean lean/.lake/build/bin/p4blo-lean
```

## Where every external input is pinned

| Input | Pin | Update by |
|---|---|---|
| nixpkgs (Python, uv, buf, protoc, elan, Node, opam) | `flake.lock` | `nix flake update` |
| Python packages | `uv.lock` | `uv lock --upgrade-package <name>` |
| Lean toolchain | `lean/lean-toolchain` | edit; `lake-manifest.json` for lake deps (none) |
| P4-SpecTec | `P4_SPECTEC_COMMIT` in `oracle/build.sh` | edit; the CI cache key reads it |
| opam package universe | `OPAM_REPO_COMMIT` in `oracle/build.sh` | edit together with the commit above |
| p4c for typechecking | image digest in `tests/test_printer.py` | `docker pull p4lang/p4c && docker inspect --format '{{index .RepoDigests 0}}' p4lang/p4c` |
| GitHub Actions | commit SHAs in `.github/workflows/*.yml` | `gh api repos/<owner>/<repo>/git/ref/tags/<tag>` |
| p4c test-suite sources | copies under `corpus/*/` with SPDX headers | not updated; they are the vectors |

Nothing else is downloaded at build or test time. The `uv sync` path
without Nix gets the same Python packages but not the same interpreter,
`buf` or `protoc`; it is a convenience, not the reproducible path.

## The oracle locally

```
nix develop .#oracle -c oracle/build.sh        # ~6 minutes the first time; prints the binary path
P4BLO_ORACLE_DIR=~/.cache/p4blo/p4-spectec uv run pytest tests/test_oracle.py -v
uv run python oracle/run.py -v corpus/forwarder/forwarder.txtpb corpus/forwarder/*.stf
```

`oracle/README.md` says what the simulator can and cannot check and how
`oracle/run.py` translates the STF dialect for it.

## Changing things

**A closed behavior.** Write it in `docs/semantics.md` first, then
implement it in `python/p4blo/interp/` and `lean/P4blo/` together, with a
test on each side, and run the Lean-versus-Python gate. A divergence
between the two interpreters that turns out to be an unlisted open
behavior is resolved by adding it to the doc, not by patching one side.

**The schema.** Edit `proto/p4blo/v0/p4blo.proto`, run `buf lint` and
`buf generate` (the generated files are committed), mirror the change in
`lean/P4blo/IR.lean` and `Json.lean`, update the validator's rules and
`docs/coverage.md`, then regenerate every corpus golden from its eDSL
source (`uv run python corpus/<name>/<name>.py > corpus/<name>/<name>.txtpb`)
and the printer goldens (`P4BLO_UPDATE_GOLDENS=1 uv run pytest tests/test_printer.py`).
Record the decision in `docs/decisions.md`.

**A corpus program.** Create `corpus/<name>/` with `<name>.py` (the eDSL
source; `corpus/forwarder/forwarder.py` is the model), `<name>.txtpb`
(its output), `README.md` (source, what was elaborated away, what is
deferred, in the style of the others), and `*.stf` vectors in the
dialect `python/p4blo/stf.py` documents. `tests/test_corpus.py` picks
the directory up by itself: it validates, rebuilds the golden from the
source, replays every vector under the switch, and checks the filter's
fate decisions. Then run the oracle and the Lean-versus-Python gates,
and add a row to `docs/status.md`. Programs from p4c's test suite are
listed with their fitness in `docs/notes/corpus-candidates.md`; the
sources are in p4c under `testdata/p4_16_samples/`.

**An extern.** Add its implementation under `python/p4blo/externs/` with
a `Shape`, register it in `default_registry`, add the Lean model in
`lean/P4blo/Externs.lean`, the printer's v1model form in
`python/p4blo/printer.py`, and an eDSL helper in
`python/p4blo/edsl/core/externs.py`. Pin the two models with a corpus
program whose vectors observe the extern.

**An architecture.** A Python module under `python/p4blo/arch/` with a
`run(loaded, entries, ingress_port, packet)` method, no P4 in it; the
contract vocabulary is the table in `docs/design.md`, and the rules
every architecture follows are in the same section and in
`docs/decisions.md` ("Architecture rules", "Port rules"). If the Lean
switch must follow, change `lean/P4blo/Switch.lean` in the same commit.

## Working with agents

Each sub-agent gets its own git worktree (`git worktree add`), owns a
disjoint set of files named in its brief, builds against interfaces
already committed on `main`, and finishes with the gates green. The
integrator merges branches on `main`, reruns the gates, and removes the
worktree. After each build step an independent, read-only review agent
looks for confirmed defects with reproducers; its report is kept under
`docs/notes/reviews/` and its findings are fixed on `main`. Every
non-obvious choice becomes a dated entry in `docs/decisions.md`;
progress and open threads live in `docs/status.md`.

## Resuming

Read, in this order: `docs/status.md` (where things stand, open
threads), `docs/decisions.md` (what was decided and why), `docs/design.md`
(what the project is), then this file. The write-up in
`docs/writeup.md` is the narrative version. Nothing needed to continue
the work lives outside the repository.
