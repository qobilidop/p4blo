# Total statement codec

2026-09-23. Implementation follows [the reviewed plan](stmt-codec-plan.md)
at base `1d1168c`. Worktree: `/Users/qobilidop/my/work/p4blo-stmt-codec`.
The baseline and [final implementation review](reviews/stmt-codec.md) are
independently clear. All scoped post-campaign gates below pass.

## Independent old-decoder baseline

Before changing production `Json.lean`, the registered test-only endpoint
gained `stmt` and an explicit constructor-matching descriptor. Its tags,
branch order and argument observations do not use `Stmt.toJson`. Python
fixtures independently describe all fourteen constructors, asymmetric nested
branches, omission/default cases, optional fields, argument order and exact
first-error paths. `CodecKind` is the sole shared Python harness change.

The unchanged partial decoder at `1d1168c` passed:

- `nix develop -c scripts/check-lean.sh`: exit 0, both packages, default
  audits and native tests (`/tmp/p4blo-stmt-baseline-lean.log`).
- `nix develop -c uv run pytest tests/test_codec_leaves.py tests/test_codec_expr.py tests/test_codec_lvalue.py tests/test_codec_stmt.py -q`:
  495 passed, exit 0 (`/tmp/p4blo-stmt-baseline-focused.log`).
- Ruff format/check and Pyright for the new fixture: exit 0.

The complete source of captured requests is `tests.test_codec_stmt.requests`:
28 canonical constructor cases, 42 exact malformed cases, 9 normalization
cases, all 79 requests distinct. The baseline stores raw byte stdin, stdout,
stderr and exit status for every request, plus exact expected JSON and source
SHA-256 hashes. Every capture was checked against strict `same_json` first.
Artifact `.artifacts/codec/stmt-baseline.json`: 104543 bytes, SHA-256
`303a5bb6b682463d1029951070bb16120bf8c343c38a774d0eafccc89d95979e`.
The artifact is intentionally ignored local evidence, not a tracked golden
generated from the implementation. Production `Json.lean`'s recorded hash
can be checked against `git show 1d1168c:ir/P4bloIR/Json.lean`.
Independent [baseline review](reviews/stmt-codec-baseline.md) is clear;
the total decoder and proof campaign require a separate final review.

Reconstruct in a checkout of the old production decoder with these frozen
test-only fixture/endpoint changes applied, first building both Lean packages.
Run the following Python through `nix develop -c uv run python` with the
worktree root as its scoped working directory (adjust the absolute root for
a new isolated reproduction):

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_stmt import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-stmt-codec')
old_json = subprocess.check_output(
    ['git', 'show', '1d1168c:ir/P4bloIR/Json.lean'], cwd=root)
assert (root / 'ir/P4bloIR/Json.lean').read_bytes() == old_json
path = root / '.artifacts/codec/stmt-baseline.json'
assert not path.exists(), 'Never overwrite retained old-decoder evidence'
rows = []
for request, expected in requests():
    raw = (json.dumps(request, separators=(',', ':')) + '\n').encode()
    result = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')],
                            input=raw, capture_output=True, timeout=10, check=False)
    assert result.returncode == 0 and not result.stderr
    assert same_json(loads(result.stdout.decode('utf-8')), expected)
    rows.append(dict(request=request, expected=expected, stdin_hex=raw.hex(),
                     stdout_hex=result.stdout.hex(), stderr_hex=result.stderr.hex(),
                     returncode=result.returncode))
assert len(rows) == 79
assert len({json.dumps(r['request'], sort_keys=True) for r in rows}) == 79
artifact = dict(format='p4blo.stmt-baseline.v0', base=subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), sources={
    p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in [
        'ir/P4bloIR/Json.lean', 'ir/Tests/CodecLaws.lean', 'tests/test_codec_stmt.py']}, rows=rows)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(artifact, indent=2) + '\n')
```

This is finite native compatibility evidence. The later checked unfolding
law states the original recurrence with ordinary helpers, not equality to
the former opaque partial constant. Neither establishes universal raw-text
or Python equivalence, duplicate-text-key behavior, runtime resource bounds,
whole-program validity or execution semantics.

## Logical result and design boundary

`Stmt.decode` is now the actual total, size-decreasing decoder. Only its
oneof dispatch and two recursive conditional-array calls use bound-carrying
helpers. The fourteen recognized tags and callback field order are unchanged.
`JsonBounds.array_mem_lt` supplies real membership descent; `arrayBounded`
uses `Array.attach.mapIdxM`, not a synthetic initializer or assumed indexing
equality. Its erasure proof reduces actual array traversal to the pinned
`List.mapIdxM.go`, keeping order, indices and first failure. Missing/null
list fields do not invoke a callback. `listFieldBounded_erasure` and
`Stmt.decode_unfold` recover the ordinary helper recurrence for all inputs.

`CodecLaws.StmtRepresentable` constrains only embedded Expr/LValue/Arg syntax
and uint32 push/pop counts. It does not require valid types, resolved names,
nonempty names, positive widths/counts, argument directions/arity, or feasible
stack operations. Optional roots and every member of both branch lists are
accounted for. `stmt_roundtrip` uses the generated nested Stmt/List induction,
with member hypotheses quantified over every diagnostic path. The generic
array lemma is discharged by existing Arg laws or nested induction, not a
whole-statement callback assumption. Fourteen constructor component laws
cover string/list omission, optional none/some and count zero/nonzero.

The default codec audit now checks the actual decoder, unfolding, array bound,
both erasure lemmas, encoded-array lemma, universal theorem and a constructive
kernel witness. The latter contains all fourteen constructors and nested
conditionals in both branches, unresolved/empty names, zero widths/counts,
huge decimal values and reversed slices. Separate kernel controls reject
push/pop overflow, overflow in a nested branch, and overflow inside an extern
argument. No native decision tactic or extra axiom is used; all eight new
advertised audit roots report the standard three axioms only.

Implementation confidence: high after the complete universal proof, exact old
recurrence comparison and finite raw-byte compatibility. Revisit if a new
statement constructor, encoding omission rule or pinned array implementation
changes. The proof does not establish raw textual JSON parsing, duplicate
keys, protobuf binary equivalence, unlimited physical recursion resources,
whole-program codec validity or execution correctness.

## Compiling adversarial challenges

Each fault is applied alone in this isolated implementation worktree with no
active binary consumers, then restored before the next. Clean implementation
SHA-256 values before the campaign:

- `Json.lean`: `0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`
- `CodecLaws.lean`: `4a30dac813bb325ff941b2e69a3cf928479774d26639aeacbee9cab94a175db2`

Copies are retained under `.artifacts/codec/stmt-campaign/*.clean.lean`.
The following is a source-level reproduction recipe, not a packet DRT claim.
Start with the final clean implementation, apply only the stated delta,
build the specified targets, run the tests, and reverse that delta before
rebuilding/restoring. Never apply these intentional faults to an integration
branch.

1. **One-sided branch encoder:** in `Stmt.toJson`'s conditional, replace
   `ofList "then" (thenBranch.map Stmt.toJson), ofList "otherwise" (otherwise.map Stmt.toJson)`
   with the same expression exchanging only `thenBranch` and `otherwise`.
   `lake +leanprover/lean4:v4.34.0 build P4bloIR.Json` exits 0;
   `build P4bloIR.CodecLaws` exits 1 at `stmt_conditional`'s checked body
   equality. This is proof rejection of a compiling actual encoder, not
   runtime detection or a termination failure. Restoration build exits 0.
   Logs `/tmp/p4blo-stmt-fault-branch-encoder-{build,proof,restored}.log`.
2. **Paired validity tags:** swap `Stmt.setValid`/`Stmt.setInvalid` on the
   two recognized tag callbacks in actual `Stmt.decode` AND its advertised
   `decode_unfold`; swap the corresponding encoder tag strings. Do not
   change descriptors, fixtures or laws. `build CodecProofAudit codec-leaves`
   exits 0: universal roundtrip and all audited axioms still pass. Statement
   Python tests reject 5 responses (102 pass); native self-test exits 1 at
   the unequal-branch and direct valid-tag anchors. All 5 saved requests
   reproduce the live mismatches and pass after restoration.
3. **Paired branch mapping:** make the one-sided encoder swap above; swap
   `"then"`/`"otherwise"` in the two bound-carrying calls in actual decoder
   and the ordinary calls in its unfolding statement. Also swap only these
   two diagnostic-path strings in `stmt_conditional`'s local body equality.
   The universal theorem statement, predicates, remaining proof and all
   independent fixtures stay unchanged. `build CodecProofAudit codec-leaves`
   exits 0. Python rejects 4 responses (103 pass), including unequal branch
   descriptors and simultaneous malformed branch errors; native self-test
   exits 1. All 4 saved requests fail live and pass after restoration.
4. **One-based array paths:** change only `Decode.at_` from
   `s!"{path}[{i}]"` to `s!"{path}[{i + 1}]"`. All audited proofs and the
   endpoint compile (exit 0), but 7 exact diagnostic tests fail (100 pass),
   including later indices, nested branch paths and argument arrays. Native
   self-test exits 1. All 7 raw mismatches reproduce live and pass restored.
5. **Null no longer defaults:** in actual `Decode.get?`, change only
   `| some Json.null | none => pure none` to `| none => pure none`. This
   deliberately changes the shared underlying default helper, not just one
   test fixture. Proofs/audits and endpoint still compile (exit 0), but 9
   statement tests fail (98 pass), including null branch arrays, optional
   fields, count and string defaults, and null selected kinds. Native tests
   also exit 1. All 9 raw mismatches reproduce live and pass restored.
6. **Missing repeated fields reject:** change the `none` branch in ordinary
   `listField` and the `.ok none` branch in `listFieldBounded` from empty
   success to `fail (sub path key) "missing repeated field"`. Remove only
   the now-unused `pure, Except.pure` simp arguments in
   `listFieldBounded_erasure`. With that linter-only adjustment, actual Json
   builds (exit 0), including erasure and decoder unfolding. The unchanged
   roundtrip component laws reject empty conditionals and calls (exit 1).
   Logs `/tmp/p4blo-stmt-fault-missing-{build3,proof3}.log`. The initial
   `build`/`build2` attempts failed only unused-simp lint and are **not**
   semantic detections. No native execution is claimed for this proof-killed
   fault. All three edited lines and both simp arguments were restored;
   final Json and law hashes exactly match the clean values above.

For each paired runtime fault, commands after its successful build are:

```text
P4BLO_CODEC_FAILURE_DIR=/Users/qobilidop/my/work/p4blo-stmt-codec/.artifacts/codec/stmt-campaign/NAME nix develop -c uv run pytest tests/test_codec_stmt.py -q
/Users/qobilidop/my/work/p4blo-stmt-codec/ir/.lake/build/bin/codec-leaves --self-test
```

Use `NAME=tags`, `branches`, `index` or `null`. Logs are
`/tmp/p4blo-stmt-fault-NAME-{build,tests,native,restored-build}.log`.
Runtime artifacts are the unchanged shared codec harness format
`p4blo.codec-leaf.v0`, plus `NAME/live-raw.json` retaining exact stdin/stdout/
stderr bytes and status from an additional live replay. Every replay row is
matched to the tracked `requests()` independent expected answer; none is
accepted merely because the native encoder decodes its own output.

Retained raw-bundle inventory (relative to
`/Users/qobilidop/my/work/p4blo-stmt-codec/.artifacts/codec/stmt-campaign`):

| Raw bundle | Rows / unique requests / leaf artifacts | SHA-256 |
|---|---|---|
| `tags/live-raw.json` | 5 / 5 / 5 | `4a6cbd47344c5cd2f81f7cf262ea405461052bd4a2ec55195ad23cdd8f328ad1` |
| `branches/live-raw.json` | 4 / 4 / 4 | `d87bd23cebfe397b73b9658e22fe31dc9997d0777af168fe83c552aee6eddcad` |
| `index/live-raw.json` | 7 / 7 / 7 | `ffcd88cb753d4c5cc02fb7c44f5f5532857446677ae4cb11cdeeb760184ee269` |
| `null/live-raw.json` | 9 / 9 / 9 | `d21e05f767e4236a7844668024eb5bc444a0dbfc2dfddaf6f7e3d9abc374f045` |

These are 25 campaign observations of **20 distinct requests across
campaigns**, not 25 distinct inputs. Each row's companion leaf artifact is
in the same folder, named `leaf-DIGEST.json`, where `DIGEST` is the first 24
hex characters of SHA-256 over `json.dumps(request, sort_keys=True).encode()`.
This gives an exact reconstruction map for all 25 retained leaf artifacts.
The live bundle additionally retains the exact byte transcripts omitted from
successful parsed leaf envelopes.

Frozen baseline source identity at `5cbbc85`:

- Actual partial decoder `ir/P4bloIR/Json.lean`:
  `44449c41e178a79dcc4d5a566dc4c89827b0810048b553bac7c7fbf293824b9c`.
- Independent descriptor/endpoint reply `ir/Tests/CodecLaws.lean`:
  `9884c677819836448bc84ebf66f0525cb5a44923e51b92e070b706f5414725fd`.
  The final file adds only kernel witnesses; its hash is
  `59bf1db5948808aa8962f491ad5aae7f2c70a17a361b767be57a348b8b2f907f`.
- Independent Python fixture `tests/test_codec_stmt.py`:
  `bf11a391258edc127b3a991e2bea53e74d42cb13efb8e87e23e964f072df0f3f`,
  unchanged in the final candidate. Its 79 `requests()` pairs also remain
  unchanged, independently checked row-for-row during final replay.

The executable driver is the unchanged `ir/Tests/CodecLeaves.lean`; it invokes
the `stmt` reply in `Tests.CodecLaws`, which calls actual `Stmt.decode` and
independent `stmtValue` plus actual re-encoding. The shared Python observer
is `tests/test_codec_leaves.py`; only its `CodecKind` type gained `stmt`.

To reproduce live byte capture after each failing pytest run, run this through
`nix develop -c uv run python` at the worktree root, selecting the appropriate
name. It requires a nonempty fault directory and checks every expected answer
against the tracked fixture before it saves anything:

```python
import json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_stmt import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-stmt-codec')
name = 'tags'  # branches, index, null for their respective live faults
folder = root / '.artifacts/codec/stmt-campaign' / name
files = sorted(folder.glob('leaf-*.json'))
assert files
known = {json.dumps(r, sort_keys=True): e for r, e in requests()}
rows = []
for file in files:
    saved = loads(file.read_text())
    request, expected = saved['request'], saved['expected']
    assert same_json(known[json.dumps(request, sort_keys=True)], expected)
    raw = (json.dumps(request) + '\n').encode()
    result = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')],
                            input=raw, capture_output=True, timeout=10, check=False)
    assert result.returncode == saved['returncode'] == 0 and result.stderr == b''
    assert same_json(loads(result.stdout.decode()), saved['actual'])
    assert not same_json(saved['actual'], expected)
    rows.append(dict(request=request, expected=expected, stdin_hex=raw.hex(),
                     stdout_hex=result.stdout.hex(), stderr_hex=result.stderr.hex(),
                     returncode=result.returncode))
(folder / 'live-raw.json').write_text(json.dumps(rows, indent=2) + '\n')
```

After reversing the fault and rebuilding, replay **all retained raw rows**,
not a count or a hand-selected example. Preserve the live files unchanged:

```python
import json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_stmt import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-stmt-codec')
known = {json.dumps(r, sort_keys=True): e for r, e in requests()}
for name, count in [('tags', 5), ('branches', 4), ('index', 7), ('null', 9)]:
    rows = loads((root / '.artifacts/codec/stmt-campaign' / name / 'live-raw.json').read_text())
    assert len(rows) == count > 0
    for row in rows:
        assert same_json(known[json.dumps(row['request'], sort_keys=True)], row['expected'])
        raw = bytes.fromhex(row['stdin_hex'])
        assert same_json(loads(raw.decode()), row['request'])
        assert type(row['returncode']) is int and row['returncode'] == 0
        assert bytes.fromhex(row['stderr_hex']) == b''
        assert not same_json(loads(bytes.fromhex(row['stdout_hex']).decode()), row['expected'])
        result = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')],
                                input=raw, capture_output=True, timeout=10, check=False)
        assert result.returncode == 0 and result.stderr == b''
        assert same_json(loads(result.stdout.decode()), row['expected'])
```

For the separate **old baseline** exact replay, first check the artifact hash
listed above, its `p4blo.stmt-baseline.v0` format and exactly 79 rows. Check
every recorded source SHA against `git show 5cbbc85:PATH`, not against the
later implementation: the decoder and native proof witnesses intentionally
changed after capture. Zip all rows strictly with current `requests()` and
compare both request and expected using `same_json`. Decode `stdin_hex` and
require the original compact JSON + LF bytes for that request. Require each
saved stdout to parse strictly to its expected answer and saved status/stderr
to be exactly integer zero/empty bytes. Invoke the current endpoint with those
stdin bytes; assert status, stdout **bytes** and stderr **bytes** exactly equal
the saved row. This checks source provenance and current fixture identity
separately from old-versus-new finite behavior.

## Verification status

The first clean total implementation passed both Lean packages/default
audits/native tests (`/tmp/p4blo-stmt-total-lean.log`, exit 0), all 495 focused
codec tests (`/tmp/p4blo-stmt-total-focused.log`, exit 0), and all 79 old
responses byte-for-byte. All four runtime fault sets were replayed live and
after individual restoration: 25 total source-matched saved observations.
Final post-campaign results, with production/test sources frozen and no
overlapping rebuilds:

- Both packages, default audits and native suites: exit 0, including 498 IR
  native checks (`/tmp/p4blo-stmt-final-lean.log`).
- Focused old/new codec suite: 495 passed, exit 0
  (`/tmp/p4blo-stmt-final-focused.log`).
- Required discovery, `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees -q`:
  692 passed, 1526 deselected, exit 0 in 67.44s
  (`/tmp/p4blo-stmt-final-required.log`). This isolated base does not contain
  other agents' later integrated tests; root's combined count may be higher.
- Final original-source-hash check and all 79 exact old transcript replays,
  plus all 25 saved live fault observations replayed restored: exit 0
  (`/tmp/p4blo-stmt-final-replay.log`). Baseline artifact hash is unchanged.
- Ruff and Pyright for the new fixture/shared type: exit 0; diff whitespace
  check passes. No `sorry`, `admit` or native proof escape occurs in the
  reviewed codec/test modules.

Root owns the integrated ordinary full gate. No Docker build, external
oracle rebuild or global cleanup was performed.

The independent final reviewer reran 495 focused cases, 72 codec-native checks,
498 full IR checks and the user native suite; queried all eight new audit
roots; replayed all 79 original byte transcripts after old-source identity
checks; and inspected/replayed all 25 retained live-fault observations. The
review also compared the full original recurrence, inspected all six actual
fault logs and verified restored clean production hashes. All checks passed;
no candidate edits or rebuilds were made by the reviewer.
