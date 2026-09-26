# Workflows

How to build, check and change p4blo, for a person or an agent who has
never seen it. Every command below runs from the repository root after the
[development setup](../README.md#development). Python commands use `uv`;
Lean, schema, workflow and oracle checks additionally need the specialist
tools listed there. `uv` does not install those external tools.

## Gates

`main` is green when all applicable gates pass. Four validation workflows
run on pull requests and pushes to `main`: Python and schema, Lean and two P4
oracles. Python and schema always run. The specialist
jobs skip only when `scripts/ci-scope.py` proves the complete change is
narrative Markdown: root README/AGENTS, direct `docs/` Markdown, agent state,
notes or reviews. Quickstart, IR semantics and P4-spec coverage remain full
because specialist tests execute or parse them. Code, tests, schemas,
workflows, tools, unknown paths, mode changes and unavailable history all
require full CI. A skipped specialist job is not a specialist test pass.

Pull requests are classified from their merge base to the complete head;
a prose follow-up does not hide earlier code changes. Pushes compare the
before and after revisions. A failed classifier stays red and cannot skip
specialist jobs. Superseded PR runs cancel; pushes to `main` do not.
Run the full local gate before pushing, plus specialist gates affected by
the change; record unavailable tools and skipped checks explicitly. Remote
CI must pass on the exact integrated `main` revision before the work is
complete. If a PR is used, its final revision must pass before merge.
Check exit codes, not output.

| Gate | Command | Expected |
|---|---|---|
| Python and schema | `scripts/check.sh` | ends with `all checks passed`, exit 0 |
| Lean | `scripts/check-lean.sh` | both packages build in dependency order, core audits and both test drivers pass, exit 0 |
| Lean vs Python | `P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees` | all conformance suites; missing or broken Lean is a failure |
| Oracle | `uv run pytest tests/external/test_oracle.py` | every `test_vector_passes_on_the_oracle` passes; skips without the oracle binary (see below) |
| BMv2 oracle | `uv run pytest tests/external/test_oracle_bmv2.py` | every `test_vector_passes_on_bmv2` passes, `register_bounds/bounds.stf` a strict `xfail` for the divergence `tests/oracle/bmv2/README.md` analyses; skips without Docker or the `p4blo-bmv2` image |
| Oracle-driven suites locally | `P4BLO_ALL_TESTS=1 scripts/check.sh`, or `uv run pytest -m oracle` (the gate runs tests with `-n auto`; dedicated oracle jobs bound their worker count and keep coverage measurement serial) | `scripts/check.sh` alone deselects the `oracle` marker (the simulator, its probe, the IL export and BMv2 suites), which the oracle workflows run |
| Original-source SpecTec probes | `uv run pytest tests/unit/test_crc.py tests/programs/test_firewall.py -k spectec` | passing controls plus four exact strict CRC/mask discrepancies; unrelated failures fail |
| Original-source BMv2 probes | `uv run pytest tests/unit/test_crc.py tests/programs/test_firewall.py tests/programs/test_firewall_boundaries.py tests/programs/test_firewall_generated.py -k bmv2` | CRC known answers, firewall packets and complete register arrays after connection/collision/truncation/generated-flow prefixes pass |
| Forwarding application BMv2 profile | `uv run pytest tests/programs/test_forwarder_apply_semantics.py::test_apply_packets_bmv2` | both overlapping-route orders and three defaults pass; dedicated BMv2 CI selects it explicitly and checks image availability first, without requiring Lean binaries |
| Printer goldens under p4c | part of `scripts/check.sh` | runs when Docker is up, skips otherwise |
| Workflows parse and lint | `actionlint`, part of `scripts/check.sh` | exit 0; a workflow that does not parse never runs |
| Repository file sizes | `uv run python scripts/check-file-sizes.py`, also in the structure tests | every indexed blob and tracked working file is at most 5 MiB; stage new deliverables first |
| Generated protobuf files | `uv run python scripts/check-generated.py`, part of the local and schema CI gates | fresh output inventory and bytes equal both index and working tree; no missing, stale or untracked generated files |

A larger differential sweep, for a change to either interpreter:

```
uv run python -m p4blo.drt tests/corpus/<program> 2000 --seed <n> --lean spec/arch/.lake/build/bin/p4blo-lean
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
CI's Lean job restores main's compiled modules (`lib` and `ir`, not `bin`)
and runs only `lake build` and `lake test`, which reject an import whose
source is gone; a gate that queries Lean directly would need a clean build.
For a clean-build check, wait for all binary consumers to finish, move only
the worktree-owned `.lake/build` directories to a recoverable temporary
location, verify their absence, rebuild the packages, and rerun required
DRT. Never move a source directory or shared toolchain as cache cleanup.
New real-Lean tests use the shared `lean_binary` fixture and names beginning
with `test_lean_agrees`; CI discovers them across the complete test tree.
Two Lean jobs split this collection by a stable hash of the full test node ID
(`--ci-shard 1/2` and `--ci-shard 2/2`), then use pytest's load scheduler within
each runner. Their disjoint union is the full selection; no seed or case count
is reduced. Both jobs build both packages and audit the core before testing; only the
first saves main's compiled-module cache. Omit `--ci-shard` for the complete
local collection. Each shard retains its own failure replays.
In authored-program gates, retain differential failure bundles before a
Python-only known-answer assertion can exit. Keep independent known answers
after comparison: agreement alone misses valid-but-unintended source terms.
New external-oracle tests must also be selected by the job that builds that
oracle; ordinary Python CI can skip unavailable tools. Rebuild the BMv2 image
after driver changes. CI runs the generated P4-SpecTec suite and the BMv2
corpus/firewall/boundary/generated suites with four workers and load scheduling.
Each simulator input uses a private temporary directory, each BMv2 invocation
a separate container. The coverage probe and its measurement remain serial.
In concurrent worktrees use distinct image tags and
`P4BLO_BMV2_IMAGE`, never replace an image while another gate is using it.
If local disk capacity is insufficient, use a reviewed isolated-branch CI
experiment; never prune unrelated Docker data or count an unavailable local
gate as successful execution.

What is claimed, for which programs, and what backs it is
[assurance.md](assurance.md). Keep proved properties, tested agreement and
open obligations separate in every checkpoint; passing differential tests
is not a proof of equivalence.
The Lean gate builds with `lake build --wfail`, so any warning fails
the build, a `sorry` included. The core proof audits,
`spec/ir/P4bloIRTest/ProofAudit.lean` and `CodecProofAudit.lean`,
pin the transitive axiom sets
of advertised theorems with `#guard_msgs`, and every default `lake build`
checks them as modules of the test libraries; `sorry`, custom axioms and
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

`tests/drt/test_drt_programs.py` changes expressions inside validated programs,
not just packets for a fixed corpus. It includes systematic operator/width
boundaries and 200 deterministic, shrinking Hypothesis examples. Failures
write concrete program/input bundles under `.artifacts/drt/` (override with
`P4BLO_DRT_FAILURE_DIR`), replayable with the same command above. The
source-fault campaign recipes for the applications are kept in
`.agents/notes/mutations/`; campaign reports are archived in git after
each compaction.
`tests/drt/test_drt_stateful_programs.py` varies widths, independent register and
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
Pages publishing is separate from the four implementation-validation
workflows and supplies no additional semantic assurance. Preview instructions
and maintenance boundaries are in `website/README.md`.

| Input | Pin | Update by |
|---|---|---|
| Optional pinned development tools | [`flake.lock`](../flake.lock) | see [development setup](../README.md#development); review lock updates |
| Python packages | `uv.lock` | `uv lock --upgrade-package <name>` |
| Lean toolchain | `spec/ir/lean-toolchain` and `spec/arch/lean-toolchain` (must match) | edit both; architecture package depends on local `../ir`, manifests committed |
| P4-SpecTec | `P4_SPECTEC_COMMIT` in `tests/oracle/build.sh` | edit; the CI cache key reads it; then regenerate `tests/oracle/spectec-rules.json` with `scripts/spectec-rules.py` and re-check every `SpecTec:` citation in [ir-semantics.md](ir-semantics.md) (`tests/external/test_spectec_rules.py`) |
| opam package universe | `OPAM_REPO_COMMIT` in `tests/oracle/build.sh` | edit together with the commit above |
| p4c for typechecking | index digest of `ghcr.io/qobilidop/p4lang-builds/p4c` in `tests/unit/test_printer.py` | `docker buildx imagetools inspect ghcr.io/qobilidop/p4lang-builds/p4c:<tag>` |
| GitHub Actions | commit SHAs in `.github/workflows/*.yml` | `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`; `actionlint` checks the files parse |
| p4c test-suite sources | copies under `tests/corpus/*/` with SPDX headers | not updated; they are the vectors |
| Original tutorial firewall | `tests/oracle/firewall.py` commit/path/SHA-256; vendored `firewall.p4` | review source/profile and update pin together; both oracle jobs run it directly |

`uv.lock` fixes the Python dependency versions. The interpreter selection
and optional pinned external-tool setup are documented in
[development setup](../README.md#development). Specialist tools retain their
own version requirements and pins; installing Python dependencies does not
satisfy those requirements.

## The oracle locally

```
tests/oracle/build.sh                              # needs opam/GMP; prints the binary path
P4BLO_ORACLE_DIR=~/.cache/p4blo/p4-spectec uv run pytest tests/external/test_oracle.py -v
uv run python tests/oracle/run.py -v tests/corpus/forwarder/forwarder.txtpb tests/corpus/forwarder/*.stf
```

[The oracle README](../tests/oracle/README.md) lists its C/OCaml build
prerequisites, what the simulator can check, and how `tests/oracle/run.py`
translates the STF dialect. The build script creates the pinned OCaml switch;
`uv` manages only the Python replay driver and tests.

## Changing things

During the personal-project phase, changes do not require a pull request,
including substantive changes, tooling and policy. Use feature branches and
worktrees when useful, or commit directly to `main`. Integrate completed
feature branches locally and push `main`. Use a pull request when explicitly
requested or required by repository protections.
Keep each commit a coherent change with its tests and necessary
documentation; explain the prior problem and why the chosen approach
solves it. Stage new deliverables before the full local gate so checks of
the index see the intended submission. Review the staged diff and commit
message before committing.

When a PR is used, its description explains the problem, resulting behavior,
consequential tradeoffs and validation for a reader without the conversation. Distinguish
local checks from remote CI and name meaningful skips or limitations. Link
supporting evidence, but keep enough context in the description to make it
useful if a link disappears. Update it against the final diff after review.
These practices follow [Google's change-description guidance](https://google.github.io/eng-practices/review/developer/cl-descriptions.html),
[small-change guidance](https://google.github.io/eng-practices/review/developer/small-cls.html),
[Git's contribution guidance](https://git-scm.com/docs/SubmittingPatches)
and [GitHub's review guidance](https://docs.github.com/en/pull-requests/concepts/helping-others-review-your-changes).

Obtain independent review of the final patch, fix findings and run the full
local gate before pushing. After pushing, check applicable CI on the exact
integrated `main` SHA; a passing run for an earlier revision is not sufficient.
Feature-branch pushes can checkpoint unfinished work but do not replace
validation of the integrated revision.
Required jobs that are missing, pending, cancelled or skipped do not
establish a pass. Repair failures with follow-up commits and rerun affected
checks before declaring completion. Follow repository protections without
bypasses. For a PR, require final-head review and applicable CI before merge.
Prefer merge commits when the individual commits form a useful history;
squash a WIP/fixup sequence with a considered message. Agent coordination
and attribution rules are in `AGENTS.md`.

Generated artifacts must have a reproducible source and regeneration
command. The protobuf check generates into a temporary directory and
compares file names and bytes with both staged and working copies; it does
not repair the checkout while checking it. A test for a new guard should
demonstrate that an invalid candidate is rejected, not merely that today's
repository passes.

The 5 MiB per-file limit is a project budget, well below hosting limits.
Prefer reproducible generation, a small losslessly compressed snapshot
with its raw-content checksum, or a checksum-pinned external artifact.
Ignored logs and build outputs remain local. Review expected history growth
when updating snapshots; removing a large file later does not remove its
old blobs. See [GitHub's repository-size guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).
Published-history changes require explicit agreement on the affected refs.

**A closed behavior.** Write it in `docs/ir-semantics.md` first, or in
`docs/arch-supports.md` when an architecture or extern family owns it, then
implement it in `impl/python/p4blo/interp/` and `spec/ir/P4bloIR/` together, with a
test on each side, and run the Lean-versus-Python gate. A divergence
between the two interpreters that turns out to be an unlisted open
behavior is resolved by adding it to the doc, not by patching one side.
A change that alters one of Lean's recorded answers fails
`tests/drt/test_conformance.py`; once the doc states the new behavior,
refresh the fixtures with `uv run python -m p4blo.conformance refresh`
from committed Lean sources and review their diff, in which every changed
step line is a changed answer (`tests/conformance/README.md`).
After editing a ledger entry, regenerate its cross-reference table with
`uv run python scripts/ledger-xref.py`;
`tests/structure/test_ledger_xref.py` fails until it is current.

**The core schema.** Edit `spec/ir/proto/p4blo/v0/p4blo.proto`, run `buf lint` and
`buf generate` (the generated files are committed), mirror the change in
`spec/ir/P4bloIR/IR.lean` and `Json.lean`, update the validator's rules
(`impl/python/p4blo/validator/`, the module of the rule's group; a new
expression kind is typed in `validator/typer.py`, which the interpreter,
the printer and the STF reader also use), the printer
(`impl/python/p4blo/printer/`) and
`docs/p4-spec-coverage.md`, then regenerate every corpus golden from its eDSL
source (`uv run python tests/corpus/<name>/<name>.py > tests/corpus/<name>/<name>.txtpb`)
and the printer goldens (`P4BLO_UPDATE_GOLDENS=1 uv run pytest tests/unit/test_printer.py`).
Record the decision in `.agents/decisions.md`.

Architecture binding syntax lives separately in
`spec/arch/proto/p4blo/arch/v0/assembly.proto`. Mirror changes there in
`spec/arch/P4bloArch/Assembly.lean` and the architecture codecs, validators
and adapters, then run the same schema and affected compatibility gates.
Keep architecture choices outside the core schema and validity rules.

**A corpus program.** Create `tests/corpus/<name>/` with `<name>.py` (the
source, in the typed eDSL `p4blo.edsl`; `tests/corpus/forwarder/forwarder.py`
is the model), `<name>.txtpb` (its output), `README.md` (source, what
was elaborated away, what is deferred, in the style of the others), and
`*.stf` vectors in the dialect `impl/python/p4blo/stf.py` documents.
Type-check the source with `uv run pyright tests/corpus/<name>/<name>.py`: a
misspelled field, state, action or table, an unequal width, or a
`concat` used without `as_` is an error there before the build runs.
`tests/unit/test_pyright.py` guards those static rules, with a file under
`tests/pyright/must_fail/` per mistake and its expected diagnostic.
`tests/programs/test_corpus.py` picks the directory up by itself: it
validates, rebuilds the golden from the source, replays every vector
under v1model. Then run the oracle and
the Lean-versus-Python gates, and add a row to the corpus table in
`docs/assurance.md`. The upstream sources are in p4c under
`testdata/p4_16_samples/`; frontend fixtures retain the pinned originals.

**An extern.** A custom Python extern can live outside this package: declare
its typed interface, register an `Implementation` with a `Shape` and factory
in a local `Registry`, and pass that registry to the loader. The runnable
[custom extern example](../examples/custom_extern.py) and
[authoring guide](python-edsl.md#declare-register-bind) show the lifecycle.
Registration alone supplies neither Lean semantics nor P4 printing support.

To extend the supplied, cross-checked families, add the implementation under
`impl/python/p4blo/arch/externs/`, register it in `supplied_registry`, add the Lean model in
`spec/arch/P4bloArch/Externs.lean`, its v1model form in
`impl/python/p4blo/arch/v1model.py` (`print_extern_instance` and
`V1modelStmtPrinter`, which the block architecture shares), and a typed
family class in
`impl/python/p4blo/arch/externs/declarations.py`: a subclass of `Extern` whose methods
are signatures with `In`/`Out`/`InOut` parameters, beside `Register`,
`Counter` and `Checksum16`, from which the IR `ExternType` is derived.
The dynamic form for generated programs is a helper in
`impl/python/p4blo/arch/externs/declarations.py`. Pin the two models with a corpus
program whose vectors observe the extern.

**A test.** Put it in the directory of `tests/` whose README asks the
question it answers (`unit/`, `codec/`, `programs/`, `drt/`, `lean/`,
`external/` or `structure/`; `docs/design.md` maps them to the six
layers), never at the top of `tests/`, which
`tests/structure/test_package_layout.py` keeps free of test modules. A
test that compares with real Lean takes the `lean_binary` fixture and a
name starting with `test_lean_agrees`, so the required gate finds it in
any directory. A module that drives an external oracle is listed by its
file stem in `tests/conftest.py`'s `ORACLE_MODULES`, which marks it
`oracle`; since the marker is keyed by stem, a new module must not reuse
the stem of an oracle module in another directory.

**An architecture.** Ordinary code selects and invokes blocks, supplies
extern implementations, and defines its own contract and execution policy.
It may live outside p4blo. The optional supplied H/M adapter uses explicit
bindings, a registry, a metadata contract and role kinds; its usage is in
[the authoring guide](python-edsl.md). To use the supplied STF driver,
provide `run(loaded, entries, ingress_port, packet)`. The supported packet
profile is v1model, specified in `docs/arch-supports.md`. Change its Python
implementation and `spec/arch/P4bloArch/V1Model.lean` together. Preserve
independent block execution and native stage boundaries; unsupported features
must fail explicitly rather than silently becoming no-ops.

For an oracle disagreement, retain unchanged source and inputs, identify the
language or target contract, and record the selected behavior in
[the discrepancy catalog](oracle-discrepancies.md). Run its reduced paired
probes with `uv run pytest tests/external/test_oracle_discrepancies.py -q`;
a missing oracle is a skip, not a successful comparison. Characterization
checks require exact recorded answers and fail when an oracle changes.

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
   For an authoring API change, first write representative caller examples
   and a boundary counterexample: a block library must compile and validate a
   scalar-only control without inventing a packet pipeline or global H/M roots.
   Trace that witness through source, wire, validation and execution. Include
   multiple blocks of each kind so the example cannot hide a fixed pipeline.
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
   For behavior-preserving authoring changes, retain the existing IR goldens
   and compare both their text and binary form before considering new syntax.
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
