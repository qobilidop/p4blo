# Table declaration codecs

2026-09-23. Implementation follows the accepted [table plan](table-codec-next.md)
and its independent review. The independently observed baseline was committed
first as `964052372fa66eea04fd146bf7f742401fec49ce`; four universal wire-only laws
now compose the actual codecs without changing production Json bytes.

Independent [baseline review](reviews/table-codec-baseline.md) is clear:
235 focused tests, 106 native codec checks, all 181 historical raw rows,
82 public protobuf successes and all eleven source hashes independently checked.

## Frozen test-only baseline

Production base: `58bb072b243f1d328b883a3fc62e75345f07967f`. Actual Json retains
SHA-256 `0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`.
No production encoder/decoder, runtime, schema, generated code, corpus or
user-package source changes. The historical unregistered TableCodecProbe is
unchanged and is not counted as production coverage.

New test endpoint labels are **table_key**, **action_call**, **entry**, **table**.
Existing **key** still means KeyValue; no old request inventory or reply changes.
Tests.TableCodec observes every field directly, reusing independent Expr,
Literal and KeyValue descriptions but matching all three MatchKind constructors
itself, never consulting MatchKind.names, protoName or encoded JSON.

Twenty new native checks independently anchor literal match-kind meanings and
the direct observer; all three accepted Entry action defaults; Table absent/null
versus present-empty default; false/true const flags; unequal argument/string/
entry order; expression-before-kind, keys-before-actions, default-before-flag
errors; and a later nested entry index. They are default-registered and also
run by the codec executable's self-test.

The frozen ordered Python requests cover all four messages, every Expr,
Literal and KeyValue family, all match kinds, arbitrary/duplicate/empty/
unresolved names, mixed key kinds and mismatched arity, noncanonical mask/value
combinations, zero/max bounds and large decimal values. All combinations of
const flag and absent/empty/nonempty default are constructive successes.
The fixtures are wire-only: no validator, Index.build or table execution
is invoked. Successful outputs pass public protobuf dump/load in minimal
Program wrappers, with explicit empty-message presence retained.

Crucial existing behavior is preserved: Entry action missing, null and {} all
decode to the same empty call, but its canonical encoder emits action:{}.
Table absent/null default is none, while {} is some empty call. Wrong bool,
message and array types, omitted/null/empty repeated fields, simultaneous errors,
later/nested indices, and propagated Expr/Literal/KeyValue/priority/size overflow
have exact independent answers. Unknown keys are observed as current ignored
input, not a compatibility guarantee. The shared strict same_json/duplicate-
rejecting loads/process harness remains unchanged except its kind type union.

## Baseline checks and provenance

Fresh worktree caches/environment. The complete both-package/default-audit/native
gate exits 0, **540 spec checks**, before endpoint consumers. Command:

```text
nix develop -c /Users/qobilidop/my/work/p4blo-table-codec/scripts/check-lean.sh
```

Log: `/tmp/p4blo-table-baseline-lean.log`. Focused six-codec-file suite exits
0: **1049 passed**, including **235 new table checks**, in 18.32 seconds:

```text
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_codec_leaves.py tests/test_codec_expr.py tests/test_codec_lvalue.py tests/test_codec_stmt.py tests/test_codec_declarations.py tests/test_codec_tables.py -q
```

Log: `/tmp/p4blo-table-baseline-focused.log`. Scoped Ruff format/check and
Pyright pass. Initial development corrected a provisional count and Python
tuple-list type inference; those failed checks are not semantic fault evidence.
No prior evidence artifacts are copied or modified. Required/full integration
and proof/fault gates remain later obligations.

`tests/test_codec_tables.py::requests()` is the complete ordered **181 unique
request** inventory: **82 successful observations / 99 exact errors**. The
baseline raw artifact retains each compact-plus-LF
input, raw stdout/stderr/status and independently authored expected result.
Source hashes cover actual syntax/Json/bounds, existing descriptors, new
descriptors/dispatch, shared Python fixture helpers, new fixtures and schema.
Capture refuses changed production bytes and existing output before running
children, rechecks source hashes afterwards, and uses strict loads for responses.
No recorded artifact command is executed.

Capture exits 0: `.artifacts/codec/table-baseline.json`, 320705 bytes,
SHA-256 `d801a79376f9bf2f786a176b3173535f851b391aeac947a48951d0e7148cc40c`.
All 82 successful canonical outputs additionally pass the public protobuf
wrapper; log `/tmp/p4blo-table-baseline-capture.log` records the complete
eleven-file source hash map also retained inside the artifact.

### Exact capture/reconstruction

Run in the reviewed baseline checkout with its freshly built endpoints. Set
the task-specific absolute root accordingly. Never overwrite the original;
reconstruct in a separate checkout if it still exists. Artifact contents have
no timestamps or local paths, so frozen sources reproduce exact bytes.

```bash
P4BLO_TABLE_ROOT=/Users/qobilidop/my/work/p4blo-table-codec nix develop -c uv run python - <<'PY'
import hashlib, json, os, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_tables import requests, protobuf_value, test_table_baseline_contract
from tests.test_codec_leaves import same_json
root = Path(os.environ['P4BLO_TABLE_ROOT']).resolve()
old_json = '0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e'
assert hashlib.sha256((root / 'ir/P4bloIR/Json.lean').read_bytes()).hexdigest() == old_json
base = subprocess.run(['git', '-C', str(root), 'show', '58bb072:ir/P4bloIR/Json.lean'], check=True, capture_output=True).stdout
assert hashlib.sha256(base).hexdigest() == old_json
out = root / '.artifacts/codec/table-baseline.json'
assert not out.exists(), 'never overwrite baseline evidence'
test_table_baseline_contract()
source_paths = ['ir/P4bloIR/IR.lean', 'ir/P4bloIR/Json.lean', 'ir/P4bloIR/JsonBounds.lean', 'ir/Tests/CodecLaws.lean', 'ir/Tests/DeclarationCodec.lean', 'ir/Tests/TableCodec.lean', 'ir/Tests/CodecLeaves.lean', 'tests/test_codec_leaves.py', 'tests/test_codec_expr.py', 'tests/test_codec_tables.py', 'ir/proto/p4blo/v0/p4blo.proto']
sources = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths}
rows = []
for request, expected in requests():
    stdin = (json.dumps(request, separators=(',', ':')) + '\n').encode()
    run = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')], input=stdin, capture_output=True, timeout=10)
    assert run.returncode == 0 and run.stderr == b''
    assert same_json(loads(run.stdout.decode()), expected), (request, run.stdout, expected)
    if 'encoded' in expected:
        _, canonical = protobuf_value(request['kind'], expected['encoded'])
        assert same_json(canonical, expected['encoded'])
    rows.append({'request': request, 'expected': expected, 'stdin': stdin.decode(), 'stdout': run.stdout.decode(), 'stderr': run.stderr.decode(), 'returncode': run.returncode})
assert len(rows) == 181
assert sources == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths}
artifact = {'format': 'p4blo.table-codec.baseline.v0', 'production_base': '58bb072', 'sources': sources, 'rows': rows}
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('x') as stream:
    stream.write(json.dumps(artifact, indent=2) + '\n')
print('rows', len(rows), 'successes', sum('encoded' in r['expected'] for r in rows))
print('bytes', out.stat().st_size, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest())
print(json.dumps(sources, indent=2))

PY
```

Future replay checks source hashes against this baseline's historical commit,
then separately matches all 181 current request/expected pairs. Kernel witnesses
may later change the test module; that is not permission to overwrite original
evidence or compare old source hashes to changed current modules.

## Universal laws and trust boundary

`P4bloIR.TableCodecLaws` stays in the existing `P4bloIR.CodecLaws` namespace.
Each law quantifies every path and every value satisfying only these bounds:

- Key: its existing Expr representability.
- ActionCall: existing Literal representability for every argument.
- Entry: existing KeyValue representability for every key, ActionCall
  representability, and uint32 priority.
- Table: every Key, optional ActionCall and Entry above, plus uint32 size.

Absent defaults add no premise. All strings, list order, match-kind combinations,
const flags, noncanonical values/masks, mixed/unequal arities and empty/zero
values stay unrestricted. No successful-decoder callback, type/lookup/validation
assumption or new codec is supplied. Existing Expr/Literal/KeyValue and generic
array laws discharge the recursive members.

The first Table attempt split every field-presence combination and hit the
default 200000-heartbeat limit. Rather than raise that limit, the final proof
factors actual `Json.mkObj` lookup: Std TreeMap's proved insertMany lookup is
the last matching field, followed by actual get?'s null-as-absent behavior.
Private omission lemmas handle each scalar/list/optional group independently.
The two generated Option matcher heads are explicitly unfolded before applying
these lemmas; this is proof elaboration plumbing, not a decoder change. The
standalone module then builds in approximately 0.7 seconds. Failed intermediate
proof attempts are development failures, not adversarial detections.

`tables_roundtrip` is a kernel-checked constructive instance of all four laws,
including both arbitrary const flags and absent/present-empty/nonempty defaults.
Its table deliberately contains zero-width oversized decimal values, an invalid
slice of an unresolved zero stack, duplicate names, mixed key kinds, unequal
entry arities, noncanonical masks, maximum uint32 bounds and zero size. Fifteen
kernel examples reject all selected direct/propagated overflow families. Public
exports and five default audit roots check precisely the usual standard axioms
`propext`, `Classical.choice`, `Quot.sound`; there is no native-decide escape.

Confidence is high in this bounded composition. Revisit the private lookup
plumbing if Lean changes its TreeMap/Json representation or match elaboration;
revisit predicates only with a separately reviewed wire-schema change. No
text/binary protobuf theorem, universal Python parity, semantic validity,
table-selection/execution or full Program codec theorem follows here.

## Checked candidate and isolated campaigns

Both-package/default-audit/native gate: exit 0, **540 spec checks**,
`/tmp/p4blo-table-laws-lean.log`. Six-codec focused suite: **1049 passed**,
exit 0, `/tmp/p4blo-table-laws-focused.log`. Required conformance discovery:
**1295 passed / 1696 deselected**, exit 0 in 100.92 seconds,
`/tmp/p4blo-table-laws-required.log`. These run after both Lean packages build;
no executable is rebuilt during its consumers.

Campaigns use `/Users/qobilidop/my/work/p4blo-table-codec-faults`, based on
the immutable baseline commit, with the new unchanged TableCodecLaws module
added as an explicit proof target. Its runtime endpoint/public imports/audit
registrations intentionally remain at reviewed baseline `9640523`, so a new
proof rejection does not prevent native observation. No proof is admitted or
weakened to build the executable; candidate default imports/witnesses remain
intact in the clean candidate tree. Every live artifact records this exact
source-layer distinction. No interpreter runtime or schema source is changed.

### Exact fault and observer recipes

Use one fault at a time in the isolated tree above. Build actual Json first:

```text
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.Json
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.TableCodecLaws
```

Run these with the fault tree's `ir` as the per-command working directory.
Check each exit code separately. If the proof target rejects the fault, it is
not required for the reviewed baseline runtime endpoint, which builds using:

```text
nix develop -c lake +leanprover/lean4:v4.34.0 build codec-leaves p4blo-lean
```

In each successful endpoint build, ordinary shared-fixture Python conformance
checks and native anchors run as follows (set campaign to kind/flag/order/default):

```text
P4BLO_REQUIRE_LEAN=1 P4BLO_CODEC_FAILURE_DIR=/Users/qobilidop/my/work/p4blo-table-codec/.artifacts/codec/table-campaign/kind/harness nix develop -c uv run pytest tests/test_codec_tables.py -q
/Users/qobilidop/my/work/p4blo-table-codec-faults/ir/.lake/build/bin/codec-leaves --self-test
```

1. **One-sided array order:** only `ActionCall.toJson` changes
   `c.args.map Literal.toJson` to `c.args.reverse.map Literal.toJson`.
   Actual Json builds; unchanged law rejects the exact nonempty argument-array
   equality for empty/nonempty action names. No runtime claim for this fault.
2. **Paired match-kind table:** actual `MatchKind.names` swaps just the two
   constructor associations `("MATCH_KIND_EXACT", .exact)` and
   `("MATCH_KIND_LPM", .lpm)` to `.lpm` and `.exact`, respectively.
   Actual encode/decode still share this table. All four unchanged law proofs
   and the baseline default audit target build; independent semantics do not agree.
3. **Paired const flag:** only Table decoding changes
   `constDefaultAction := ← boolField path j "const_default_action"` to
   `constDefaultAction := !(← boolField path j "const_default_action")`;
   its encoder changes `ofBool "const_default_action" t.constDefaultAction`
   to `ofBool "const_default_action" (!t.constDefaultAction)`.
   This inverts both explicit values and omitted-default meaning. The unchanged
   proof's stronger field-body factoring rejects it, not evidence that paired
   roundtrip itself is false. A separate kernel probe under the actual mutant
   confirms both flags roundtrip for otherwise empty tables:

   ```lean
   import P4bloIR.Json
   open P4bloIR
   example (path : String) (flag : Bool) :
       Table.decode path (Table.mk "" [] [] none flag [] 0).toJson =
         .ok (Table.mk "" [] [] none flag [] 0) := by
     cases flag <;> rfl
   ```

4. **First-error order:** in actual `Table.decode`, move reading the const flag
   before reading the optional default (keep all prior name/key/action reads and
   all later entry/size reads unchanged). The exact replacement is shown below.
5. **Present-empty default loss:** only actual Table decoding changes
   `defaultAction := ← optField path j "default_action" ActionCall.decode` to
   `defaultAction := (← optField path j "default_action" ActionCall.decode).filter
     (fun a => a != ActionCall.mk "" [])`.
   This drops some-empty but leaves absent and nonempty values alone.
   For exact source-hash reconstruction, the original first-line indentation is
   nine spaces and the new continuation has eleven spaces before `(fun a`.

Fault 4's complete decoder replacement (the adjacent `open Decode in` remains):

```lean
def Table.decode (path : String) (j : Json) : Dec Table := do
  let name ← strField path j "name"
  let keys ← listField path j "keys" Key.decode
  let actions ← listField path j "actions" str
  let constDefaultAction ← boolField path j "const_default_action"
  let defaultAction ← optField path j "default_action" ActionCall.decode
  let constEntries ← listField path j "const_entries" Entry.decode
  let size ← uint32Field path j "size"
  pure { name, keys, actions, defaultAction, constDefaultAction, constEntries, size }
```

With only fault 2 live, corrupt the Python `record` fixture's else branch by
inserting immediately after `value[key] = child`:

```python
if key == "match_kind":
    value[key] = {"MATCH_KIND_EXACT": "MATCH_KIND_LPM", "MATCH_KIND_LPM": "MATCH_KIND_EXACT"}.get(child, child)
```

All **235 ordinary Python checks pass**, but two independent native literal
anchors still fail. Restore Python exactly; still under fault 2, independently
swap just the output strings of `.exact`/`.lpm` in Lean test `matchKindValue`.
Rebuild the endpoint: all **235 ordinary Python checks pass** again, but native
checks reject both literal meanings and both direct observations (four failures).
Restore the observer and real shared enum table before any other campaign.
These are deliberately demonstrated false assurances, not correctness results.
Unlike the prior Direction campaign, the ordinary packet preflight does not
block these table campaigns; no direct-test-body fallback is used.

### Source-matched live raw capture

Run the following with the fault tree as working directory through
`nix develop -c uv run python -`, setting `P4BLO_TABLE_CAMPAIGN` to
`kind`, `flag`, `order`, or `default`. Run before any paired observer/fixture
challenge and before restoration. It checks all 181 independent requests,
retains only genuine strict mismatches, refuses overwrite, records the exact
production/proof/test source identities, and immediately replays every retained
raw transcript against the still-live compiled fault. Artifacts are ignored data,
not scripts to execute. No original baseline bytes or expected answers change.

```python
import hashlib, json, os, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_tables import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-table-codec')
fault = Path('/Users/qobilidop/my/work/p4blo-table-codec-faults')
name = os.environ['P4BLO_TABLE_CAMPAIGN']
baseline = loads((root / '.artifacts/codec/table-baseline.json').read_text())
fixtures = requests()
assert len(fixtures) == len(baseline['rows']) == 181
for (request, expected), old in zip(fixtures, baseline['rows'], strict=True):
    assert same_json(request, old['request']) and same_json(expected, old['expected'])
rows = []
for request, expected in fixtures:
    stdin = json.dumps(request, separators=(',', ':')) + '\n'
    run = subprocess.run([str(fault / 'ir/.lake/build/bin/codec-leaves')], input=stdin, text=True, capture_output=True, timeout=10)
    assert run.returncode == 0 and run.stderr == ''
    actual = loads(run.stdout)
    if not same_json(actual, expected):
        rows.append({'request': request, 'expected': expected, 'actual': actual, 'stdin': stdin, 'stdout': run.stdout, 'stderr': run.stderr, 'returncode': run.returncode})
assert rows
sources = {p: hashlib.sha256((fault / p).read_bytes()).hexdigest() for p in ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/TableCodecLaws.lean', 'ir/Tests/TableCodec.lean', 'tests/test_codec_tables.py', 'ir/P4bloIR.lean', 'ir/CodecProofAudit.lean']}
out = root / '.artifacts/codec/table-campaign' / name / 'live-raw.json'
out.parent.mkdir(parents=True, exist_ok=True)
artifact = {'format': 'p4blo.table-codec.campaign.v0', 'campaign': name, 'baseline_commit': '964052372fa66eea04fd146bf7f742401fec49ce', 'sources': sources, 'rows': rows}
with out.open('x') as stream:
    stream.write(json.dumps(artifact, indent=2) + '\n')
for row in rows:
    replay = subprocess.run([str(fault / 'ir/.lake/build/bin/codec-leaves')], input=row['stdin'], text=True, capture_output=True, timeout=10)
    assert (replay.returncode, replay.stdout, replay.stderr) == (row['returncode'], row['stdout'], row['stderr'])
print(name, 'live raw mismatches', len(rows), 'bytes', out.stat().st_size, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest())

```

### Results, retained inventory and restoration

All five actual codec mutations build `P4bloIR.Json` successfully before proof
or runtime observations. Results are distinct kinds of evidence:

| Actual fault | Unchanged four-law target | Ordinary Python checks | Native failures |
| --- | --- | --- | --- |
| Reversed ActionCall args | rejects nonempty-array equality | not run | not run |
| Paired MatchKind table | passes | 29 fail / 206 pass | 2 |
| Paired const flag | rejects stronger field-body rewrite | 23 fail / 212 pass | 6 |
| Error order | passes | 2 fail / 233 pass | 1 |
| Present-empty default loss | rejects exact option equality | 2 fail / 233 pass | 1 |

The flag rejection is not a disproof of all paired roundtrips: the separate
empty-table/both-flags kernel probe exits 0. Error-order proof survival is
expected because successful roundtrips do not constrain malformed-input error
selection. Native const-flag failures include defaults/order checks that also
observe the now-wrong flag; they are not six distinct field faults. Every
runtime row below is a clean status-0/empty-stderr semantic mismatch, not an
endpoint crash, failed build, lint problem or preflight error.

Logs are `/tmp/p4blo-table-fault-<campaign>-<stage>.log`: `reverse` has `json`
and `proof`; `kind` has `json`, combined law/baseline-audit/endpoint `build`,
`tests`, `native`, `raw`; `flag`, `order`, `default` each have `json`, `proof`,
`build`, `tests`, `native`, `raw`. `flag-coherence.log` records its finite kernel
probe. Paired challenges use `paired-fixture-{tests,native}.log` and
`paired-observer-{build,tests,native}.log` under the same prefix. An initial
fault-tree build used misspelled target names and stopped before compilation;
that setup correction is not a fault detection.

Retained under `.artifacts/codec/table-campaign/`:

| Raw bundle | Observations | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `kind/live-raw.json` | 29 | 236792 | `c290100c93bc0c32826b4281877304889d23bee584ebbd36567af010c686c3cf` |
| `flag/live-raw.json` | 23 | 227201 | `2e45ea9d8e13088059b68130e5c166fee935c66b5a54325958cc51435bf9202f` |
| `order/live-raw.json` | 2 | 1985 | `cda11a83fb6b5be7f8947b98c5bbcc6e71db2d729eb89509a7403d477177ba3a` |
| `default/live-raw.json` | 2 | 3085 | `c89fc8e4eb74de5db86bd02c2a458530e6922026a04489f84b67553276e2f52e` |

Each raw row has a corresponding ordinary shared-harness view at
`<campaign>/harness/leaf-<digest>.json`, where digest is the first 24 hex
characters of SHA-256 of `json.dumps(request, sort_keys=True).encode()`.
Thus the four bundles and deterministic map identify every one of the 56
views without a directory-dependent glob inventory. Each view retains the
same request/expected/actual/status/stderr; do not execute its recorded command.
The replay below prints every view's actual content hash, checks its deterministic
filename and correspondence, and distinguishes repeated observations of one
request across faults from distinct requests.

After restoring Json and both challenged observation sources, restore the new
candidate witness/public/audit source layers too; no intentional fault remains.
Rebuild the four-law target, default codec audit and both endpoints before
replay. Run the following in the candidate through `nix develop -c uv run python -`:

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_tables import requests, protobuf_value
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-table-codec')
fault = Path('/Users/qobilidop/my/work/p4blo-table-codec-faults')
baseline_commit = '964052372fa66eea04fd146bf7f742401fec49ce'
baseline = loads((root / '.artifacts/codec/table-baseline.json').read_text())
fixtures = requests()
assert len(fixtures) == len(baseline['rows']) == 181
key = lambda value: json.dumps(value, sort_keys=True)
expected = {key(request): answer for request, answer in fixtures}
old_rows = {key(row['request']): row for row in baseline['rows']}
assert len(expected) == len(old_rows) == 181
for path, recorded in baseline['sources'].items():
    source = subprocess.run(['git', '-C', str(root), 'show', f'{baseline_commit}:{path}'], check=True, capture_output=True).stdout
    assert hashlib.sha256(source).hexdigest() == recorded, path
for (request, answer), old in zip(fixtures, baseline['rows'], strict=True):
    assert same_json(request, old['request']) and same_json(answer, old['expected'])
    assert old['stdin'] == json.dumps(request, separators=(',', ':')) + '\n'
    assert old['returncode'] == 0 and old['stderr'] == ''
    assert same_json(loads(old['stdout']), answer)
    for tree in [root, fault]:
        run = subprocess.run([str(tree / 'ir/.lake/build/bin/codec-leaves')], input=old['stdin'], text=True, capture_output=True, timeout=10)
        assert (run.returncode, run.stdout, run.stderr) == (0, old['stdout'], '')
    if 'encoded' in answer:
        _, canonical = protobuf_value(request['kind'], answer['encoded'])
        assert same_json(canonical, answer['encoded'])
print('historical source hashes and both endpoints: 181 exact baseline rows, 82 public protobuf successes')
seen, count = set(), 0
for name in ['kind', 'flag', 'order', 'default']:
    folder = root / '.artifacts/codec/table-campaign' / name
    data = (folder / 'live-raw.json').read_bytes()
    artifact = loads(data.decode())
    assert artifact['baseline_commit'] == baseline_commit and artifact['campaign'] == name
    assert artifact['sources']['ir/P4bloIR/TableCodecLaws.lean'] == hashlib.sha256((root / 'ir/P4bloIR/TableCodecLaws.lean').read_bytes()).hexdigest()
    for path, digest in artifact['sources'].items():
        if path not in ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/TableCodecLaws.lean']:
            old = subprocess.run(['git', '-C', str(root), 'show', f'{baseline_commit}:{path}'], check=True, capture_output=True).stdout
            assert hashlib.sha256(old).hexdigest() == digest
    assert len(list((folder / 'harness').glob('leaf-*.json'))) == len(artifact['rows'])
    for row in artifact['rows']:
        request_key = key(row['request'])
        assert request_key in expected and same_json(row['expected'], expected[request_key])
        assert not same_json(row['actual'], row['expected'])
        assert same_json(loads(row['stdout']), row['actual'])
        assert row['stdin'] == json.dumps(row['request'], separators=(',', ':')) + '\n'
        assert row['returncode'] == 0 and row['stderr'] == ''
        filename = 'leaf-' + hashlib.sha256(request_key.encode()).hexdigest()[:24] + '.json'
        view_path = folder / 'harness' / filename
        view = loads(view_path.read_text())
        for field in ['request', 'expected', 'actual', 'returncode', 'stderr']:
            assert same_json(view[field], row[field])
        for tree in [root, fault]:
            run = subprocess.run([str(tree / 'ir/.lake/build/bin/codec-leaves')], input=row['stdin'], text=True, capture_output=True, timeout=10)
            assert (run.returncode, run.stdout, run.stderr) == (0, old_rows[request_key]['stdout'], '')
        seen.add(request_key)
        count += 1
        print(view_path.relative_to(root), hashlib.sha256(view_path.read_bytes()).hexdigest())
    print(name, 'rows', len(artifact['rows']), 'bytes', len(data), 'sha256', hashlib.sha256(data).hexdigest())
for path in ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/TableCodecLaws.lean', 'ir/Tests/TableCodec.lean', 'tests/test_codec_tables.py', 'ir/P4bloIR.lean', 'ir/CodecProofAudit.lean']:
    assert (root / path).read_bytes() == (fault / path).read_bytes(), path
    print('restored', path, hashlib.sha256((root / path).read_bytes()).hexdigest())
print('live observations', count, 'distinct requests', len(seen), 'both restored endpoints agree')

```

Restored proof/default codec audit/endpoints build exits 0:
`/tmp/p4blo-table-fault-restored-build.log`. The ordinary fault-tree focused
suite exits 0 (**235 passed**), and native self-test exits 0 (**106 checks**):
`/tmp/p4blo-table-fault-restored-{tests,native}.log`. The full replay exits 0,
`/tmp/p4blo-table-restored-replay.log`: all **181 historical exact transcripts**
and **56 live observations / 52 distinct requests**, with both clean endpoints
agreeing and all 56 harness views matched. This log lists every view's content
hash. Exact in-memory application of the four documented runtime patches also
reproduces every recorded mutant Json source hash, checked in
`/tmp/p4blo-table-mutant-sources.log`:

- kind: `f32e2f6c914629a00efa899bc273b85ba1e46e265a7b741c8bea1181c33307e3`
- flag: `267e75959122ee5d9fc14702790f472a8d4754b2e00c0242bf161640aaf50208`
- order: `21849d1de9f8d597dd57e9cb42800bdf532eee13e7012e838b6aecfd9e7f216f`
- default: `da4cd6e6599b99b8fcc67297640aaf1391a0feb97b228baed531e5a3c9dc7af9`

All six restored source files compare byte-for-byte between candidate and fault
tree. Production Json retains its original hash. New proof:
`d79eb9a3400e323e2384fd24d7dd93b292226a41671d75750f30fb863051bc1f`;
current constructive test module:
`54a2eaebf28a99007ccfd5841d504949a7c2038eaef1802e4e7b5432d94352c1`;
unchanged Python baseline fixture:
`bbaabbc7b0b76a09b45d4341bb8227eeb840aa1f2c16ff2e27d4aa8c05609185`.
Historical baseline source hashes always refer to commit `9640523`, not the
current test module's legitimate added witnesses. Ruff check/format, scoped
Pyright and `git diff --check` pass. No Docker builds or oracle changes occur;
the integrator owns full combined Python/schema/oracle gates and old replay
integration. Independent [final review](reviews/table-codec.md) is clear:
the reviewer reran focused/native/five fresh axiom checks, verified all historical
source hashes and protobuf outputs, inspected the real fault diagnostics, and
independently reconstructed/replayed all 56 observations and 56 harness views
against both restored endpoints. No active consumers remain.
