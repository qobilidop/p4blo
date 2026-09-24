# Finite milestone adversarial catalogue

This is an executable sensitivity check, not a proof of Python correctness or
an attempt to replay every historical experiment. It uses only tracked source
fixtures. No prior `.artifacts` contents, external oracle, Docker build, or
network service is needed after the pinned development environment is present.

## Run from a clean checkout

```sh
nix develop -c uv sync --locked
nix develop -c scripts/check-lean.sh
nix develop -c uv run python scripts/check-assurance.py
```

Run these sequentially. Do not rebuild the checkout's Lean executables while
the catalogue is consuming them. The command can take several minutes: it
builds a **cache-free spec-only source copy**, then rebuilds each actual fault
and its restoration. The existing user-package exporters are consumed only by
the selected Python regressions; the scratch copy does not build that package.

The command prints a new `.artifacts/assurance/run-*` evidence directory and
returns zero only when every required phase passes. An explicit `--output
/absolute/new/directory` is supported but must not exist. Evidence is never
overwritten or automatically deleted, including on failure. The directory
contains raw stdout/stderr per subprocess, exact commands and exit codes,
JUnit results, complete replay inputs, exact anchored mutations, original spec
sources, source hashes, and `result.json`. Baseline and final provenance cover
all tracked files, including Python, tests, golden fixtures, Lean sources,
toolchains and lockfiles, plus these runner files before their first commit.
HEAD, dirty status and Python version are recorded. A mid-run source change
fails the command. Build failure, timeout, skipped/setup-error test, missing
mutation hit, unexpected native failure, or incomplete restoration is not a
successful sensitivity result.

## Fixed inventory

Three complete inputs are reconstructed from existing test helpers and pinned
by canonical SHA256 of Program, ordered requests, four ports and seed zero:

| Input | Requests | Input SHA256 |
| --- | ---: | --- |
| Empty forwarder table with drop default | 1 | `f3c078924462e5a2f0772f765e043a05acf2c4525a7f4714590121f0cfe7ffe2` |
| Overlapping /24 and /32 routes | 1 | `5bba09916c247a4498f17717f1190e306f8c2a36d7f13737738915870ecb1c39` |
| Stateful firewall connection sequence | 4 | `0978d83374dfda732b9fc57718d19e4c47e294b9ebcb95a953cf081f01ddfaf7` |

These are input fingerprints, **not** whole report-file hashes (which also
contain observed outcomes). Updating a helper does not quietly recapture the
expected fingerprint: the command fails until the changed input is reviewed
and the tracked constant deliberately updated. Python baseline packet/state
answers also use the existing independent literal/model expectations.

The ten selected pytest cases are fixed by full node names and checked again
through exact JUnit identities, with no skips/errors/failures permitted:

- Actual Python skipped default action and shortest-prefix selection: normal
  internal observations, retained whole-packet disagreement, live replay and
  restored agreement.
- Actual Bloom read alias, reversed write order, and a repaired intermediate
  side effect: independent intended positions and intermediate-state/order
  observations, not just final-cell equality.
- Header and struct copy aliasing: complete post-write observation and retained
  live/restored replay.
- Three ambiguous peer replies (outputs, state, diagnostic): duplicate JSON
  fields must not yield false agreement; complete inputs remain replayable.

These permanent tests already assert that their scoped faults actually execute.
They run against the untouched checkout's built Lean endpoint/exporters. Their
temporary replay files remain under the new evidence directory's `pytest-temp`.

## Actual Lean fault and paired observer challenge

1. Build the fresh spec copy's interpreter, `ProofAudit`, `CodecProofAudit`, and
   native codec endpoint. Run the native checks, all three input sequences and
   their saved replays successfully before any fault.
2. Change the actual `P4bloIR/Externs.lean` CRC32 result to XOR one. Build the
   **real interpreter executable successfully**. The firewall sequence must
   yield exactly three state-only disagreements on requests 1, 2, 3, preserving
   packets, with no errors/diagnostics. Save before asserting, replay the live
   fault, restore the source bytes, rebuild, and replay the **same saved faulty
   input bundle** to four agreements. This is runtime inconsistency detection,
   not a proof-build failure counted as a test kill.
3. Swap parser/control in the actual `BlockKind.names` codec table. The coherent
   encoder/decoder pair must build `CodecProofAudit` and the endpoint; current
   universal Action/Block roundtrip laws remain in that build. An independently
   spelled parser input must decode to the wrong control constructor descriptor
   while its encoded wire remains unchanged.
4. Also swap parser/control in the test-only direct constructor descriptor.
   Build the endpoint and audits again. The same weak reply equality must now
   **survive**. Run the unmodified native literal anchors: exactly two failures
   each for literal constructor, direct kind observer, and complete mixed block
   constructor are required, with the exact expected native exception. A crash
   or arbitrary test failure does not satisfy this requirement. This demonstrates
   an explained observer survivor, closed by independent anchors; it does not
   assert that roundtrip proofs define the intended external enum vocabulary.
5. Restore both files exactly, rebuild all scratch targets/audits, rerun native
   checks, the independent codec response, and all three saved-input sequences.
   Verify every copied spec source and the original checkout provenance.

No proof statement, audit, import dependency, or native expected answer is
disabled to keep a faulty endpoint buildable. Mutation sources never touch
the checkout's production files. Each scratch source is restored in `finally`,
even if a check fails; a failed run may still leave a faulty scratch **binary**,
so only a complete passing result attests its restored rebuild. Subprocesses
start in their own session, have bounded timeouts, and on interruption are
signalled by their exact owned group and reaped with a bound. Signal denial or
unreaped leader fails visibly; no global process or Docker cleanup is used.

## Decision and confidence

2026-09-23: reuse ten strong, already reviewed regressions rather than build a
second mutation framework or automatically run every historical campaign.
Confidence is high for this bounded acceptance catalogue, not exhaustive
fault coverage. The three fingerprints intentionally overlap historical
retained inputs rather than claiming new distinct witnesses. Revisit a selected
case only when its input/API changes or a meaningful uncaught fault is found;
do not expand the milestone automatically. Scope is current IR v0 and the
documented four-port profile, not arbitrary JSON compatibility or universal
Python correctness. External oracle and CI gates remain separate acceptance
requirements.

## Validation checkpoint

Initial actual end-to-end run completed exit 0 at
`.artifacts/assurance/first/result.json`: fresh baseline, ten selected tests,
compiled CRC runtime mismatch, paired codec/observer build survival, six native
anchor failures, restored builds/audits/native checks and all clean replays.
This preceded final provenance stability and explicit same-bundle restored
replay hardening; the final command is rerun before integration. Initial
orchestration tests found only a test-path typo (`stmt.py` lives in `interp/`),
corrected without changing production code or treating it as mutant detection.
The final fresh-copy run at `.artifacts/assurance/final/result.json` completed
exit 0 with the final source, including exact all-code provenance stability and
explicit restored replay of the same saved CRC-fault input. It records all
mutation-source hashes and successful actual compiler phases separately from
runtime disagreement and the independent six native anchor failures. Logs:
`/tmp/p4blo-assurance-final.log` plus the retained evidence directory. No proof
or native-test dependency was removed for either compiling fault.

Final checks at this checkpoint (all exit 0):

- `scripts/check-lean.sh`: both packages, default proof audits, spec and user
  native tests; `/tmp/p4blo-assurance-lean.log`.
- New orchestration unit tests: **21 passed**; scoped Ruff, format and Pyright.
- Required real-Lean conformance: **2700 passed, 1839 deselected, no skips**,
  212.90 seconds; `/tmp/p4blo-assurance-drt.log`.
- `scripts/check.sh`: **4533 passed, five existing strict expected divergences,
  one optional local XDP-image skip**, 513.15 seconds; all formatting, lint,
  typing, schema regeneration/no-drift and workflow checks passed;
  `/tmp/p4blo-assurance-full.log`. No new skip or expected divergence was added.

Independent read-only review is **CLEAR**, recorded by the integrator at
`docs/notes/reviews/milestone-adversarial.md` (archived). The reviewer ran all 21 unit tests,
checked exact JUnit/input identities, independently replayed all three baseline
bundles (six requests) and the saved CRC fault after restoration (four requests),
and inspected the actual compiler/native-failure evidence. Those checks are
distinct from the two full catalogue executions above. The integrator will
also run the command from its final clean checkout; that is not claimed here
before it happens.
