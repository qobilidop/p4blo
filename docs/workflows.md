# Workflows

How to build, check and change p4blo, for a person or an agent who has
never seen it. Every command below runs from the repository root inside
the flake (`direnv allow` once, or prefix with `nix develop -c`).

## Gates

`main` is green when all of these pass, and four workflows run them on
every push: Python and schema, Lean, and one per oracle. Run them
locally before pushing, and check exit codes, not output.

| Gate | Command | Expected |
|---|---|---|
| Python and schema | `scripts/check.sh` | ends with `all checks passed`, exit 0 |
| Lean | `scripts/check-lean.sh` | both packages build, each audit/test driver passes, exit 0 |
| Lean vs Python | `P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees` | all conformance suites; missing or broken Lean is a failure |
| Oracle | `uv run pytest tests/test_oracle.py` | every `test_vector_passes_on_the_oracle` passes; skips without the oracle binary (see below) |
| BMv2 oracle | `uv run pytest tests/test_oracle_bmv2.py` | every `test_vector_passes_on_bmv2` passes, `register_bounds/bounds.stf` a strict `xfail` for the divergence `tests/oracle/bmv2/README.md` analyses; skips without Docker or the `p4blo-bmv2` image |
| Printer goldens under p4c | part of `scripts/check.sh` | runs when Docker is up, skips otherwise |
| Workflows parse and lint | `actionlint`, part of `scripts/check.sh` | exit 0; a workflow that does not parse never runs |

A larger differential sweep, for a change to either interpreter:

```
uv run python -m p4blo.drt tests/corpus/<program> 2000 --seed <n> --lean ir/.lake/build/bin/p4blo-lean
```

Use `--save <directory>` to retain a failed experiment. Its JSON bundle
contains the actual program and every request from fresh extern state;
replay it with `uv run python -m p4blo.drt.replay <bundle.json>`. STF files
beside it are single-packet excerpts, not standalone stateful reproductions.
The CLI fails on matching errors as well as divergences for campaigns of
generated valid inputs. Every Lean request has a timeout, including writes
to a peer that stops reading. Local tests may skip an absent binary unless
`P4BLO_REQUIRE_LEAN=1`; an existing but broken binary is always a failure.
Build Lean first, then run the Python gate: rebuilding and testing in the
same worktree concurrently can remove the executable while a test needs it.
New real-Lean tests use the shared `lean_binary` fixture and names beginning
with `test_lean_agrees`; CI discovers them across the complete test tree.

The active assurance roadmap is [verification.md](verification.md). Keep
proved properties, tested agreement and open obligations separate in every
checkpoint. Passing differential tests is not a proof of equivalence.
Lean treats warnings as errors. Its default `ProofAudit` target checks the
transitive axiom sets of advertised theorems; `sorry`, custom axioms and
native-evaluation escapes cannot silently replace those proofs. Update an
audit expectation only after reviewing the changed trust boundary.

The fixed execution-claim experiment is in [certificates.md](certificates.md).
`python -m p4blo.drt.certificate create` executes production Python and
writes a claim; `verify` asks the compiled Lean checker to accept or reject
it. This is distinct from ordinary differential fuzzing and is not a
standalone proof term or universal equivalence claim.

`tests/test_drt_programs.py` changes expressions inside validated programs,
not just packets for a fixed corpus. It includes systematic operator/width
boundaries and 200 deterministic, shrinking Hypothesis examples. Failures
write concrete program/input bundles under `.artifacts/drt/` (override with
`P4BLO_DRT_FAILURE_DIR`), replayable with the same command above. Selected
semantic mutation campaigns and exact patches are kept in `notes/mutations/`.
`tests/test_drt_stateful_programs.py` varies widths, independent register and
counter capacities, arithmetic, conditional effects and write ordering. It
compares complete packet sequences, including every extern cell after each
request, with 100 shrinking campaigns and deterministic boundary cases.
Both program and sequence contribute to its replay filename, so different
shrinking prefixes do not overwrite one another.
The Lean workflow uploads failure bundles for 14 days, including the hidden
`.artifacts` directory. Download them before that retention period expires
and promote confirmed minimal regressions into tracked tests or corpus data.

## Where every external input is pinned

| Input | Pin | Update by |
|---|---|---|
| nixpkgs (Python, uv, buf, protoc, elan, Node, opam) | `flake.lock` | `nix flake update` |
| Python packages | `uv.lock` | `uv lock --upgrade-package <name>` |
| Lean toolchain | `ir/lean-toolchain`, `lean/lean-toolchain` (must match) | edit both; user package depends on local `../ir`, manifests committed |
| P4-SpecTec | `P4_SPECTEC_COMMIT` in `tests/oracle/build.sh` | edit; the CI cache key reads it |
| opam package universe | `OPAM_REPO_COMMIT` in `tests/oracle/build.sh` | edit together with the commit above |
| p4c for typechecking | index digest of `ghcr.io/qobilidop/p4lang-builds/p4c` in `tests/test_printer.py` | `docker buildx imagetools inspect ghcr.io/qobilidop/p4lang-builds/p4c:<tag>` |
| GitHub Actions | commit SHAs in `.github/workflows/*.yml` | `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`; `actionlint` checks the files parse |
| p4c test-suite sources | copies under `tests/corpus/*/` with SPDX headers | not updated; they are the vectors |

Nothing else is downloaded at build or test time. The `uv sync` path
without Nix gets the same Python packages but not the same interpreter,
`buf` or `protoc`; it is a convenience, not the reproducible path.

## The oracle locally

```
nix develop .#oracle -c tests/oracle/build.sh        # ~6 minutes the first time; prints the binary path
P4BLO_ORACLE_DIR=~/.cache/p4blo/p4-spectec uv run pytest tests/test_oracle.py -v
uv run python tests/oracle/run.py -v tests/corpus/forwarder/forwarder.txtpb tests/corpus/forwarder/*.stf
```

`tests/oracle/README.md` says what the simulator can and cannot check and how
`tests/oracle/run.py` translates the STF dialect for it.

## Changing things

**A closed behavior.** Write it in `docs/semantics.md` first, then
implement it in `python/p4blo/interp/` and `ir/P4blo/` together, with a
test on each side, and run the Lean-versus-Python gate. A divergence
between the two interpreters that turns out to be an unlisted open
behavior is resolved by adding it to the doc, not by patching one side.

**The schema.** Edit `ir/proto/p4blo/v0/p4blo.proto`, run `buf lint` and
`buf generate` (the generated files are committed), mirror the change in
`ir/P4blo/IR.lean` and `Json.lean`, update the validator's rules and
`docs/coverage.md`, then regenerate every corpus golden from its eDSL
source (`uv run python tests/corpus/<name>/<name>.py > tests/corpus/<name>/<name>.txtpb`)
and the printer goldens (`P4BLO_UPDATE_GOLDENS=1 uv run pytest tests/test_printer.py`).
Record the decision in `docs/decisions.md`.

**A corpus program.** Create `tests/corpus/<name>/` with `<name>.py` (the
source, in the typed eDSL `p4blo.edsl`; `tests/corpus/forwarder/forwarder.py`
is the model), `<name>.txtpb` (its output), `README.md` (source, what
was elaborated away, what is deferred, in the style of the others), and
`*.stf` vectors in the dialect `python/p4blo/stf.py` documents.
Type-check the source with `uv run pyright tests/corpus/<name>/<name>.py`: a
misspelled field, state, action or table, an unequal width, or a
`concat` used without `as_` is an error there before the build runs.
`tests/test_pyright.py` guards those static rules, with a file under
`tests/pyright/must_fail/` per mistake and its expected diagnostic.
`tests/test_corpus.py` picks the directory up by itself: it validates,
rebuilds the golden from the source, replays every vector under the
switch, and checks the filter's fate decisions. Then run the oracle and
the Lean-versus-Python gates, and add a row to `docs/status.md`. Programs from p4c's test suite are
listed with their fitness in `docs/notes/corpus-candidates.md`; the
sources are in p4c under `testdata/p4_16_samples/`.

**An extern.** Add its implementation under `python/p4blo/externs/` with
a `Shape`, register it in `default_registry`, add the Lean model in
`ir/P4blo/Externs.lean`, the printer's v1model form in
`python/p4blo/printer.py`, and a typed family class in
`python/p4blo/edsl/externs.py`: a subclass of `Extern` whose methods
are signatures with `In`/`Out`/`InOut` parameters, beside `Register`,
`Counter` and `Checksum16`, from which the IR `ExternType` is derived.
The dynamic form for generated programs is a helper in
`python/p4blo/edsl/core/externs.py`. Pin the two models with a corpus
program whose vectors observe the extern.

**An architecture.** A Python module under `python/p4blo/arch/` with a
`run(loaded, entries, ingress_port, packet)` method, no P4 in it; the
contract vocabulary is the table in `docs/design.md`, and the rules
every architecture follows are in the same section and in
`docs/decisions.md` ("Architecture rules", "Port rules"). If the Lean
switch must follow, change `ir/P4blo/Switch.lean` in the same commit.

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
