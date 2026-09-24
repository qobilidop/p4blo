# Workflows

How to build, check and change p4blo, for a person or an agent who has
never seen it. Every command below runs from the repository root after the
[development setup](../README.md#development). Python commands use `uv`;
Lean, schema, workflow and oracle checks additionally need the specialist
tools listed there. `uv` does not install those external tools.

## Gates

`main` is green when all of these pass, and five workflows run them on
every push: Python and schema, Lean, two P4 oracles and compile-only XDP. Run them
locally before pushing, and check exit codes, not output.

| Gate | Command | Expected |
|---|---|---|
| Python and schema | `scripts/check.sh` | ends with `all checks passed`, exit 0 |
| Lean | `scripts/check-lean.sh` | both packages build, each audit/test driver passes, exit 0 |
| Lean vs Python | `P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees` | all conformance suites; missing or broken Lean is a failure |
| Oracle | `uv run pytest tests/test_oracle.py` | every `test_vector_passes_on_the_oracle` passes; skips without the oracle binary (see below) |
| BMv2 oracle | `uv run pytest tests/test_oracle_bmv2.py` | every `test_vector_passes_on_bmv2` passes, `register_bounds/bounds.stf` a strict `xfail` for the divergence `tests/oracle/bmv2/README.md` analyses; skips without Docker or the `p4blo-bmv2` image |
| Original-source SpecTec probes | `uv run pytest tests/test_crc.py tests/test_firewall.py -k spectec` | passing controls plus four exact strict CRC/mask discrepancies; unrelated failures fail |
| Original-source BMv2 probes | `uv run pytest tests/test_crc.py tests/test_firewall.py tests/test_firewall_boundaries.py tests/test_firewall_generated.py -k bmv2` | CRC known answers, firewall packets and complete register arrays after connection/collision/truncation/generated-flow prefixes pass |
| Forwarding application BMv2 profile | `uv run pytest tests/test_lean_forwarder_apply.py::test_apply_packets_bmv2` | both overlapping-route orders and three defaults pass; dedicated BMv2 CI selects it explicitly and checks image availability first, without requiring Lean binaries |
| Printer goldens under p4c | part of `scripts/check.sh` | runs when Docker is up, skips otherwise |
| Workflows parse and lint | `actionlint`, part of `scripts/check.sh` | exit 0; a workflow that does not parse never runs |
| Original XDP compile profile | `P4BLO_REQUIRE_XDP_BUILD=1 uv run pytest tests/test_xdp_build.py` | pinned original compiles; offline ELF/BTF positive/negative checks pass without BPF syscalls; separate CI requires image, local missing image skips without required flag |

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
Prefer fresh build directories in new worktrees. Do not copy entire old
Lean caches across package/namespace moves: stale modules can shadow current
imports in standalone queries even when Lake's explicit build graph passes.
For a clean-build check, wait for all binary consumers to finish, move only
the two worktree-owned `.lake/build` directories to a recoverable temporary
location, verify their absence, rebuild both packages, and rerun required
DRT. Never move a source directory or shared toolchain as cache cleanup.
New real-Lean tests use the shared `lean_binary` fixture and names beginning
with `test_lean_agrees`; CI discovers them across the complete test tree.
In authored-program gates, retain differential failure bundles before a
Python-only known-answer assertion can exit. Keep independent known answers
after comparison: agreement alone misses valid-but-unintended source terms.
New external-oracle tests must also be selected by the job that builds that
oracle; ordinary Python CI can skip unavailable tools. Rebuild the BMv2 image
after driver changes. In concurrent worktrees use distinct image tags and
`P4BLO_BMV2_IMAGE`, never replace an image while another gate is using it.
For XDP build `docker build -t p4blo-xdp-build tests/oracle/xdp`; concurrent
trees use distinct tags and `P4BLO_XDP_BUILD_IMAGE`. This is compilation and
metadata checking only, with no kernel load/attach/map creation. The job
retains object/provenance and corresponding upstream archives for 14 days.
Exact pins, restrictions and the independently reviewed acceptance evidence
are in `tests/oracle/xdp/README.md`. If local disk capacity is insufficient,
use a reviewed isolated-branch CI experiment; never prune unrelated Docker
data or count an unavailable local gate as successful native execution.

What is claimed, for which programs, and what backs it is
[assurance.md](assurance.md). Keep proved properties, tested agreement and
open obligations separate in every checkpoint; passing differential tests
is not a proof of equivalence.
Lean treats warnings as errors. Its default `ProofAudit` target checks the
transitive axiom sets of advertised theorems; `sorry`, custom axioms and
native-evaluation escapes cannot silently replace those proofs. Update an
audit expectation only after reviewing the changed trust boundary.

The milestone's finite adversarial acceptance command is:

```sh
uv sync --locked
scripts/check-lean.sh
uv run python scripts/check-assurance.py
```

Run these sequentially from an unchanged checkout. The last command rebuilds
a fresh spec source copy, reconstructs three pinned complete inputs, runs ten
selected Python/observer regressions, and challenges actual Lean runtime and
codec behavior before restoring and replaying. It does not need old ignored
artifacts or exploratory worktrees. It creates a new evidence directory under
`.artifacts/assurance/`; `--output /absolute/new/directory` selects another new
location. Preserve `result.json` and its logs. Only exit 0 with status `passed`
is acceptance; build failures, skips, unexpected failures and incomplete
restoration fail the command. Do not edit sources or rebuild the checkout's
executables while it runs. The exact inventory, intentional observer survivor
and independent detector are in [assurance.md](assurance.md#adversarial-checks).
This supplements the ordinary gates; it is not a universal equivalence proof
or a requirement to rerun every historical mutation experiment.

The fixed execution-claim experiment is in [assurance.md](assurance.md#execution-certificates).
`python -m p4blo.drt.certificate create` executes production Python and
writes a claim; `verify` asks the compiled Lean checker to accept or reject
it. This is distinct from ordinary differential fuzzing and is not a
standalone proof term or universal equivalence claim.

`tests/test_drt_programs.py` changes expressions inside validated programs,
not just packets for a fixed corpus. It includes systematic operator/width
boundaries and 200 deterministic, shrinking Hypothesis examples. Failures
write concrete program/input bundles under `.artifacts/drt/` (override with
`P4BLO_DRT_FAILURE_DIR`), replayable with the same command above. The
source-fault campaign recipes for the applications are kept in
`.agents/notes/mutations/`; campaign reports are archived in git after
each compaction.
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

The separate `Website` workflow publishes only `website/` to
<https://qobilidop.github.io/p4blo/>. It runs for website/workflow changes on
`main` or manual dispatch on `main`, using the GitHub Actions Pages source.
It checks JavaScript syntax and the generated gateway source before uploading
and deploying the static files. Changes to the canonical gateway source or
renderer also trigger it; regenerate with
`uv run python scripts/render-website-example.py` before committing.
Pages publishing is separate from the five implementation-validation
workflows and supplies no additional semantic assurance. Preview instructions
and maintenance boundaries are in `website/README.md`.

| Input | Pin | Update by |
|---|---|---|
| Optional pinned development tools | [`flake.lock`](../flake.lock) | see [development setup](../README.md#development); review lock updates |
| Python packages | `uv.lock` | `uv lock --upgrade-package <name>` |
| Lean toolchain | `ir/lean-toolchain`, `lean/lean-toolchain` (must match) | edit both; user package depends on local `../ir`, manifests committed |
| P4-SpecTec | `P4_SPECTEC_COMMIT` in `tests/oracle/build.sh` | edit; the CI cache key reads it |
| opam package universe | `OPAM_REPO_COMMIT` in `tests/oracle/build.sh` | edit together with the commit above |
| p4c for typechecking | index digest of `ghcr.io/qobilidop/p4lang-builds/p4c` in `tests/test_printer.py` | `docker buildx imagetools inspect ghcr.io/qobilidop/p4lang-builds/p4c:<tag>` |
| GitHub Actions | commit SHAs in `.github/workflows/*.yml` | `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`; `actionlint` checks the files parse |
| p4c test-suite sources | copies under `tests/corpus/*/` with SPDX headers | not updated; they are the vectors |
| Original tutorial firewall | `tests/oracle/firewall.py` commit/path/SHA-256; vendored `firewall.p4` | review source/profile and update pin together; both oracle jobs run it directly |
| Original XDP feature build and libbpf | commits/archive SHA-256 in `tests/oracle/xdp/Dockerfile` | review source, ABI/profile and licenses; rerun required compile/negative gate |
| XDP build environment | Ubuntu image digest, dated authenticated archive snapshot and CA bundle SHA-256 in `tests/oracle/xdp/` | update together; retain compiler/package/dependency provenance and same-build object repeat check |

`uv.lock` fixes the Python dependency versions. The interpreter selection
and optional pinned external-tool setup are documented in
[development setup](../README.md#development). Specialist tools retain their
own version requirements and pins; installing Python dependencies does not
satisfy those requirements.

## The oracle locally

```
tests/oracle/build.sh                              # needs opam/GMP; prints the binary path
P4BLO_ORACLE_DIR=~/.cache/p4blo/p4-spectec uv run pytest tests/test_oracle.py -v
uv run python tests/oracle/run.py -v tests/corpus/forwarder/forwarder.txtpb tests/corpus/forwarder/*.stf
```

[The oracle README](../tests/oracle/README.md) lists its C/OCaml build
prerequisites, what the simulator can check, and how `tests/oracle/run.py`
translates the STF dialect. The build script creates the pinned OCaml switch;
`uv` manages only the Python replay driver and tests.

## Changing things

**A closed behavior.** Write it in `docs/ir-semantics.md` first, or in
`docs/arch-supports.md` when an architecture or extern family owns it, then
implement it in `python/p4blo/interp/` and `ir/P4bloIR/` together, with a
test on each side, and run the Lean-versus-Python gate. A divergence
between the two interpreters that turns out to be an unlisted open
behavior is resolved by adding it to the doc, not by patching one side.

**The schema.** Edit `ir/proto/p4blo/v0/p4blo.proto`, run `buf lint` and
`buf generate` (the generated files are committed), mirror the change in
`ir/P4bloIR/IR.lean` and `Json.lean`, update the validator's rules and
`docs/coverage.md`, then regenerate every corpus golden from its eDSL
source (`uv run python tests/corpus/<name>/<name>.py > tests/corpus/<name>/<name>.txtpb`)
and the printer goldens (`P4BLO_UPDATE_GOLDENS=1 uv run pytest tests/test_printer.py`).
Record the decision in `.agents/decisions.md`.

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
the Lean-versus-Python gates, and add a row to the corpus table in
`docs/assurance.md`. The sources are in p4c under
`testdata/p4_16_samples/`; the 2026-09-22 survey of that suite that chose
the current programs is archived in git as `docs/corpus-candidates.md`.

**An extern.** Add its implementation under `python/p4blo/externs/` with
a `Shape`, register it in `default_registry`, add the Lean model in
`ir/P4bloIR/Externs.lean`, the printer's v1model form in
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
`.agents/decisions.md` ("Architecture rules", "Port rules"). If the Lean
switch must follow, change `ir/P4bloIR/Switch.lean` in the same commit.

## Application development

Public applications live under `examples/<name>/` with `program.py` (the
complete typed eDSL; `build()` returns the IR), `demo.py` (host
configuration, packet sequence, results) and a README that states the
problem, the supported packet profile, the command, the expected results
and the limitations. Their verification lives under
`tests/examples/<name>/`: independent expectations, the generated golden
and STF vectors. `tests/examples/test_examples.py` discovers every
`examples/*/program.py` and requires the golden, exact vectors, the demo
output and generated real-Lean cases; pyright includes `examples`, and
both oracle catalogs pick up `tests/examples/*/*.stf`. Each program keeps
headers, parser, actions, tables, control and deparser together; extract
shared abstractions only when concrete usage shows a readability benefit.

An application is complete when it has a reviewed contract and runnable
demo; readable typed source; independent exact packet, fate and state
expectations; golden reconstruction; Python/Lean comparison and
applicable oracle evidence with precise exclusions; targeted deliberate
faults; and a fresh-reader review that runs and modifies the example
without conversation context. Setup or compilation failures do not count
as semantic fault detection, and agreement between implementations does
not replace intended-behavior checks. Work each application through this
loop:

1. Specify the application story, packet profile, host assumptions and failure
   behavior. Establish independent expected outcomes before relying on replay.
2. Build the smallest complete runnable scenario through public APIs. Record
   concrete authoring, configuration, inspection and diagnostic difficulties.
3. Challenge correctness with boundary and persistent-sequence tests,
   Python/Lean comparison, applicable oracles and targeted deliberate faults.
   Preserve reproducers and distinguish setup failures from detected faults.
4. Obtain independent read-only correctness and usability review after each
   build step. The reviewer runs the documented demo and tries a small policy
   modification using scratch copies or local configuration overrides in
   their isolated worktree, without editing canonical sources.
   Retain the report under `.agents/reviews/` and resolve confirmed findings.
5. Improve the responsible layer: application, eDSL, diagnostics, runtime or
   test infrastructure. Validate a reusable change with concrete usage. Record
   speculative opportunities as backlog rather than expanding acceptance.
6. Repeat affected checks/review, run required integration gates, and record
   the resulting revision, exact commands, skips and outstanding obligations.

A commit represents a coherent improvement that can be reviewed on its own
and leaves the project working. Keep behavior with its tests and explanation;
separate mechanical moves and reusable API changes from application policy.
Avoid both incomplete file-by-file commits and a collection-wide omnibus
commit. There is no line-count quota. Guidance:
[Google's small changes](https://google.github.io/eng-practices/review/developer/small-cls.html),
[review criteria](https://google.github.io/eng-practices/review/reviewer/looking-for.html),
and [Git's logical steps](https://git-scm.com/docs/gitworkflows).

At each checkpoint, update `.agents/status.md` (including Open threads), the
acceptance checklist and any changed decisions. Record the current iteration,
unresolved findings, active branch/worktree, durable evidence and next action.
Update `AGENTS.md` when scope or navigation changes. Another agent should be
able to resume from these files without chat history or temporary worktrees.

## Working with agents and resuming

Sub-agent coordination, review placement, checkpoints, compaction and
the reading order for resuming are in `AGENTS.md`; nothing needed to
continue the work lives outside the repository.
