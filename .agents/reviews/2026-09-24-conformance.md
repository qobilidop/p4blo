# Review: B3, the exported conformance corpus

Commit reviewed: `e304c61` (merge of `work/conformance-corpus`, `fde0ec0..1fb2bd8` on `8c674fc`), exercised in the worktree `/Users/qobilidop/my/work/p4blo-wt/conformance-corpus`. The conformance paths are identical between `1fb2bd8` and `e304c61`.
Date: 2026-09-24. Read-only review. Both worktrees were left clean (`git status --porcelain` is empty). The scratch scripts are `rv_*.py` in the reviewer's scratchpad.

## Summary

The corpus does what it claims. Both checks pass on all 87 fixtures (check-python in about 0.4 s, check-lean in about 2.4 s). Two exports into scratch directories match each other and the tracked fixtures byte for byte, also under a different `PYTHONHASHSEED`. Both checks still pass with every generator monkeypatched to raise. Every corruption that changes an answer an implementation can observe is caught by `check_python`. Every change to a reply's bytes is caught by `check_lean`.

The review found no semantic false pass. It confirmed these weaknesses:

- Dropping steps from a fixture, or emptying it, passes both checks.
- `export` deletes any `*.json` in its target directory.
- An invalid fixture program crashes `check-python` instead of being reported.
- The only way to refresh answers is a full export. That export also reruns the generators, so once `work/guided-generation` lands, a re-export will rewrite all 36 family fixtures. The README's "every changed line is a changed answer" would then be false.
- The drift warning already fires on `main`: proof-only commits after `662746e` changed the source digest.
- The corpus contains no error replies and no multi-output replies, so those contract branches are specified but never exercised.
- The state format is not specified outside Python code.

## Confirmed defects

1. **Truncated fixtures pass both checks.** Drop the last step, or all steps (`steps: []`), of `stf-corpus-forwarder-forward` and write it canonically. Both `check_python_fixture` and `check_lean_fixture` return `[]` (scratch `rv_corrupt.py`, cases "drop the last step" and "drop all steps"). `loads` accepts an empty `steps` (`impl/python/p4blo/conformance.py:214-224`). The membership test compares only names (`tests/test_conformance.py:31-33`). A bad merge-conflict resolution or a hand-deleted line therefore goes unnoticed.
   - Fix: reject empty `steps` in `loads`.
   - Fix: make the membership test also compare each fixture's step count with `len(input.cases)`. That still uses only repository data. It does not make the checks depend on generators beyond what the membership test already runs.
2. **`export --dir X` deletes every `*.json` in X that is not an input** (`conformance.py:400-402`).
   - Reproducer (`rv_foot`): a directory holding `spectec-rules.json`, exported with one input, is left with only `stf-corpus-forwarder-forward.json`. A mistyped `--dir tests/oracle` would delete tracked oracle data.
   - Fix: delete only files that `load()` recognizes as `p4blo.conformance` fixtures, or refuse a directory that holds other JSON.
3. **An invalid program in a fixture crashes `check-python`.** `arch.load` raises `p4blo.validator.ValidationError`, which subclasses `Exception`, not `ValueError` (`validator.py:143`). `check_python_fixture` catches only `(ValueError, ProtocolError)` (`conformance.py:458-463`), and `main` catches the same set (`conformance.py:516`).
   - Reproducer: set `program.blocks` to `[]` and run `python -m p4blo.conformance check-python --dir <copy>`. The result is a traceback, and the remaining fixtures are never checked. `check_lean_fixture` reports the same file cleanly ("Lean did not answer: exit 1: ... exports no 'parser' block").
   - In pytest this still fails, so nothing passes falsely. Fix: add `ValidationError` to the caught set. The same applies to a non-JSON file: `load` sits outside the `try` in `check_python`/`check_lean`, so one bad file aborts the loop.
4. **A re-export cannot refresh answers without regenerating inputs.** `export` is the only writer (`conformance.py:381-403`), and it reruns `inputs.inputs()`: the STF replay, `generate` and `materialize`.
   - `work/guided-generation` adds `control` and `parser` to `FAMILIES`, and `materialize` picks the family by `seed % len(FAMILIES)` (`tests/oracle/generated.py:358-362`). The first semantic re-export after that branch lands will therefore change the program and requests of every `family-*` fixture.
   - The README's review rule ("review the diff: every changed line is a changed answer", `tests/conformance/README.md:63-68`) would then be false. Generator drift would hide inside a semantics re-export.
   - Fix: add a `refresh` command that re-answers the tracked requests and rewrites replies and the header. That is `check_lean_fixture`'s logic, but writing the result. Keep `export` for deliberate input changes, in separate commits. The comment "Six seeds per family" (`tests/conformance/inputs.py:35`) and "36 seeds" in `docs/assurance.md` become approximate once there are 8 families.

## Corruption matrix

Unless noted, each corruption was written canonically to a scratch copy of one fixture. The matrix is `rv_corrupt.py` plus `rv_prog.py`.

| Corruption | `check_python` | `check_lean` |
|---|---|---|
| Flip an output byte (builder's) | caught | caught |
| Change a register cell (builder's) | caught | caught |
| Drop one extern from a reply's `state` | caught | caught |
| Add an extern to `state` | caught | caught |
| Drop the last cell of a register | caught | caught |
| Change a register `width` | caught | caught |
| Change a diagnostic's text | **not caught** (by design: presence only) | caught |
| Remove a diagnostic | caught | caught |
| Add a diagnostic to a reply without one | caught | caught |
| Reorder outputs (synthetic second output) | caught | caught |
| Change an output port | caught | caught |
| Add a coverage tag | **not caught** (by design) | caught |
| Remove the `coverage` key | **not caught** (`parse_reply` tolerates an "older peer") | caught |
| Add an unknown key to a reply | **not caught** (`parse_reply` ignores extra keys) | caught |
| Replace outputs by an error | caught | caught |
| Error text differing only in a `Word: ` prefix | not caught (reasoned, not run: `normalize_error` strips the prefix on both sides; the corpus has no error replies) | caught |
| `ports` 4 to 2 or 1 on forwarder | caught | caught |
| `ports` 4 to 8 on forwarder | **neither** (unobservable: the output port stays valid) | **neither** |
| Reverse the step order (stateful) | caught | caught |
| Drop the last step, or all steps | **neither** (defect 1) | **neither** |
| Flip a request packet byte | caught | caught |
| Change `ingress_port` on forwarder | neither (unobservable: forwarder ignores it) | neither |
| Change a program literal (TTL decrement `1` to `2`; ethertype `2048` to `2054`) with the replies unchanged | caught | caught |
| Rename the program (top-level `name`) | neither (unobservable) | neither |
| Program made invalid (`blocks: []`) | crash (defect 3) | caught |
| `name` differs from the file stem | **neither** (the README says `name` is the stem; nothing enforces it) | neither |
| Edit the `source` header | neither (informative) | neither |
| Edit the `lean` header | neither (informative; see below) | neither |
| Hand formatting (builder's) | caught | caught ("not in canonical form") |

A golden or STF vector edited under `tests/corpus/` also goes undetected: the fixture keeps the old program and requests and keeps passing, and the membership test sees the same names. The design intends this (concrete inputs), but the README should say that a changed input is picked up only by an explicit export.

## Regeneration semantics

- `check_lean_fixture` (`conformance.py:406-433`) re-answers the recorded requests and rebuilds the file with `replace(fixture, steps=...)`. It keeps the recorded `lean` header, so the header does not take part in the byte comparison. Only `steps[].reply` can differ, plus canonical form.
- Tested: a scratch copy with `sources` set to `sha256:111…`. `check-lean` exited 0 with `0 problems`, and `main` printed the `note: the fixtures were answered by Lean sources … current sources are …` line (`conformance.py:513-515`).
- With `lean_provenance(root=...)` pointed at a scratch copy of `spec/`:
  - An unedited copy gives the tracked digest, and `lean_drift` returns `None`.
  - A comment appended to `spec/ir/P4bloIR.lean` makes `lean_drift` report drift.
- The wording matches the behavior: "reported not failed" in the test (`tests/test_conformance.py:137-142`), in the README (`README.md:68-70`) and in the module docstring (`conformance.py:30-35`). Two problems remain:
  - **The warning already fires on `main`.** The fixtures name `662746e` with digest `10d1df02…`. At `e304c61`, `spec/ir` hashes to `974e7b84…` because of `b6b8970`/`26f4908`/`d647d8a` (`DeviationLaws.lean`, `ProofAudit.lean`). The digest scope (`conformance.py:101-104`) includes proof-only files such as `ProofAudit.lean`, `CodecProofAudit.lean`, `*CodecProbe.lean` and `DeviationLaws.lean`. So every proof commit will keep this warning on, and a warning that is always on gets ignored. Either narrow the digest to the endpoint's import closure (`spec/arch/Main.lean`), or say plainly that the header is refreshed only at the next answer-changing export.
  - `test_changed_lean_sources_are_reported_not_failed` asserts nothing. It is a warning emitter, which is fine, but its name reads like a check.

## Determinism

`export` was run twice (`rv_exp1`, `rv_exp2`) and once with `PYTHONHASHSEED=7` (`rv_exp3`). The worktree's binary built 87 fixtures (2,741,654 bytes) each time. `diff -r` is empty for 1 vs 2 and 1 vs 3, and for 1 vs the tracked `tests/conformance/fixtures`.

No absolute paths, timestamps or map-order effects appear. `source` uses repository-relative paths, and the temporary `program.json` path never reaches the output.

## Independence

- With `p4blo.drt.generate.generate` (also as imported in `p4blo.drt.run` and `tests.conformance.inputs`) and `tests.oracle.generated.materialize` all monkeypatched to raise, `check_python` returns `[]` and `check_lean` returns `[]` on all 87 fixtures (`rv_indep.py`).
- The membership test uses only names. It does run every generator to compute those names (`inputs.inputs()`, 0.3 s), so a generator that crashes fails it, while a generator whose output changes does not.
- Family names depend only on the seed. On `family` and `tests/oracle/generated.py`: nothing checked depends on `materialize` at check time. The risk is at export time (defect 4).
  - Export also needs `generated.SWITCH_PORTS` (511) to keep meaning the switch the families were built for.
  - The `family`/`description` in `source` record which family a seed produced, so a reshuffle is visible in the diff but not separable from answer changes.

## Size

- 2,741,654 bytes in total: 185,928 bytes zlib-compressed, which is what git stores.
- Of the 282,845 register/counter cells in replies, 282,504 are `"0x0"`. The five firewall fixtures plus `family-seed05` are 1.86 MB.
- An exact sparse encoding per extern (`{"size": n, "nonzero": [[i, "0x…"], …]}`) saves 1,686,930 bytes and brings the corpus to about 1.05 MB with no loss of exactness. Emitting only the externs that changed since the previous step would shrink it further.
- Either change would make a fixture step no longer "exactly a line of the pipe protocol". The cleaner route is a sparse state encoding in the protocol itself, on both sides, or a fixture-only encoding that `outcomes()` expands.
- No size test exists. None of `tests/*.py` checks `st_size` or a budget. A budget test (for example, total under 4 MB and each file under 1 MB) would catch a new 8K-cell program multiplying the corpus.

## CI shape and a stale binary

- `test_lean_agrees_with_fixture` takes the session fixture `lean_binary` (`tests/conftest.py:14-28`). That is `default_lean_binary()`, the same `spec/arch/.lake/build/bin/p4blo-lean` the DRT tests use. `-k lean_agrees` in `.github/workflows/lean.yml:38-43` selects it and `test_lean_agrees_check_catches_a_changed_answer`, with `P4BLO_REQUIRE_LEAN=1`.
- The fixture only probes that the `run` mode exists. It does not check that the binary is current, so a binary built before a semantics change makes `check-lean` pass falsely.
- Worse, `export` with a stale binary writes stale answers under the **current** source digest (`lean_provenance` hashes sources, not the binary). The header would then vouch for sources that did not answer.
- In CI, `scripts/check-lean.sh` builds in the preceding step, so CI is safe. Locally nothing guards it.
- Fix: in `export` (and optionally in `lean_binary`), fail when `lake build --no-build p4blo-lean` in `spec/arch` reports that a rebuild is needed, or record the binary's lake hash (`p4blo-lean.hash`) next to the digest.

## Third-implementation readiness

As an implementer's contract, the README (`tests/conformance/README.md`) is close but not self-contained:

- The request/reply shapes are summarized, but "each exactly a line of the pipe protocol of `p4blo.drt.run`" refers to a Python docstring for the authoritative form.
- The `state` format is specified nowhere outside Python code (`p4blo.drt.state.decode`). A third implementation needs:
  - the per-kind field sets (`register`: `kind`, `width`, `values`; `counter`: `kind`, `values`; `checksum16`/`crc16`/`crc32`: `kind` only);
  - the canonical lowercase hex spelling (`hex(n)`, so `"0x0"` and not `"0x00"`, which `decode` rejects);
  - the cell order;
  - what counter values count.
- "Both sides report an error for the same reason" really means byte-equal English text after stripping one leading `Identifier: `, with Lean copying Python's sentences. The README does not say this. The corpus has 0 error replies out of 507, so this is untested as well as unspecified.
- When `diagnostic` is present (an architecture drop the program did not decide), and the switch's own rules (egress port out of range, and so on), are in `run.py`'s docstring and `docs/arch-supports.md`. The README links neither.
- There are no multi-output replies (0 of 507), so output ordering is contract-only.

Recommendation: give the README (or a `docs/` page, since this is the artifact) a normative section on request, reply and state fields, and cite `docs/arch-supports.md` for the switch.

## Cleanup requests

- `README.md:15` says `name` is the file's stem, but `load` does not enforce it. Check it in `load(path)`.
- `check_python_fixture` rewrites `describe()` with `.replace('Lean', 'fixture')` (`conformance.py:468`). That also rewrites any "Lean" inside packet or diagnostic text. Parametrize `Divergence.describe` with side labels instead.
- `inputs.py:35` "Six seeds per family" is true only while `len(FAMILIES) == 6`. Derive it or drop it.
- The drift test's name (see Regeneration semantics).
- Consider rejecting unknown reply keys in fixtures: `loads` could validate a reply's key set against the protocol, so `check_python` also sees a stray key.

## Anything else

- `decisions.md` was not on the branch. The "conformance corpus is Lean's answers on fixed inputs" entry arrived on `main` in `1f60a3d`. It says "a generator change never silently changes the corpus". That is true of the checks but not of the next export (defect 4).
- The claimed Python and Lean mutants are not reproducible from the repository. Neither the tests nor this review's scope recorded them. If they matter as evidence, record them under `.agents/status.md` with the commands.
- The module and tests read well. The sections are clear, the error messages name the fixture and request, and the corruption tests assert exact messages.
