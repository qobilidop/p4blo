# Parser-syntax codec laws

2026-09-23. Implements the first slice of the reviewed
[Program completion plan](program-codec-completion.md). The independently
reviewed baseline was committed as `9d68d7df713c681d89771cb7f15352eee07bb91d`
before any production law/export/audit work. The historical unregistered probe
remains feasibility, not default-audited production coverage. The new module
proves five actual universal representable roundtrips without changing codecs.

## Scope and independent observers

Base: `1c1b08e`. Actual Json stays byte-identical, SHA-256
`0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`.
No runtime, schema, generated code, corpus or user-package source changes.

The test-only endpoint adds five distinct labels: target, key_set, select_case,
transition, state. Existing key still denotes KeyValue, table_key still denotes
Key, and all old inventories remain unchanged. Tests.ParserCodec directly
matches every Target/KeySet/Transition constructor and describes every State
and SelectCase field, reusing prior independent Literal/Expr/Stmt observers.
It never uses production toJson output to describe an abstract value.

The native module contributes **27 independent anchors**: literal state/accept/
reject meanings and separate accept/reject observer checks; Boolean exact,
asymmetric mixed-type masked operands, descending range and wildcard; empty
select versus empty direct; missing/null/empty target and transition; null
oneof absence and a surviving alternative; multiple kinds before malformed
payload; member/field error order; root-path nested later index; unequal
case and arbitrary statement-body order. These run in the default IR tests
and the existing codec endpoint self-test.

Python fixtures independently construct both canonical wire and full abstract
answers. The canonical set includes every Literal family, all prior Expr
families through a select key list, all prior Stmt families and nested branches
through State bodies, all Target/KeySet/Transition constructors, zero/max
bounds and huge decimal values. Empty/unresolved/cyclic names, duplicate keys,
unequal arities, mixed literal types, descending ranges, unknown action/block
names and statements forbidden in a valid parser are deliberately retained.
No Index.build, semantic validator or parser interpreter is invoked.

Successful canonical replies pass the actual public protobuf Program JSON
dump/load functions with minimal State/transition/select-case wrappers.
Explicit SetInParent preserves message/oneof presence. The recovered selected
message and strict canonical wire are checked, not the wrapper's validity.

The fixed ordered inventory has **231 unique requests**: **51 canonical**,
**155 exact errors**, **25 normalizations**; thus **76 successful observations**.
Null is tested separately as omitted list, list element, oneof alternative
and nested message. Missing/null/present-empty required oneofs fail; empty
select succeeds. Error matrices include every top-level nonobject, no/multiple
kind, wrong payload, value/mask and lo/hi precedence, sets/target, keys/cases,
name/body/transition, first/later/nested indices and propagated numeric bounds.
Prior independently authored Expr/Stmt malformed inputs are embedded at a
new later array index without deriving expected diagnostics from Lean.
Normalized successes retain unknown annotations, decimal spellings, null
defaults and member normalizations. Type-sensitive same_json, strict loads
and the existing failure-retention/process checks remain shared and unchanged.

## Checked baseline

Fresh worktree caches. Actual native module build exits 0:
`/tmp/p4blo-parser-baseline-module.log`.
Both complete Lean packages/default audits/native tests exit 0, **567 spec
checks**, before native consumers:

```text
nix develop -c /Users/qobilidop/my/work/p4blo-parser-codecs/scripts/check-lean.sh
```

Log: `/tmp/p4blo-parser-baseline-lean.log`.
The new focused file exits 0, **283 passed** (52 pure Python + 231 real Lean),
in 7.78 seconds; all seven codec files exit 0, **1332 passed**, in 22.06 seconds:

```text
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_codec_leaves.py tests/test_codec_expr.py tests/test_codec_lvalue.py tests/test_codec_stmt.py tests/test_codec_declarations.py tests/test_codec_tables.py tests/test_codec_parser.py -q
```

Logs: `/tmp/p4blo-parser-baseline-focused.log` and
`/tmp/p4blo-parser-baseline-all-codecs.log`.
The endpoint self-test exits 0, **133 checks** (106 prior + 27 new):
`/tmp/p4blo-parser-baseline-native.log`.
Scoped Ruff format/check and Pyright pass. Initial Python type checking found
list invariance; using Sequence at fixture helper inputs fixed that without
suppressing errors. A manually reviewed nested null-oneof expected path was
corrected before the first native fixture run and capture. These development
corrections are not deliberate semantic fault detections.

No binary is rebuilt while its consumers run. No Docker operation or prior
artifact modification occurs. Full required/integration and actual compiling
fault gates remain obligations of the post-baseline proof checkpoint.

## Frozen raw provenance

`.artifacts/codec/parser-baseline.json` contains all 231 exact compact-plus-LF
stdin/raw stdout/stderr/exit-status transcripts and their independent expected
answers, with thirteen source hashes. Capture additionally checks all 76
canonical successful outputs through the public protobuf wrapper. It refuses
changed original Json bytes and an existing output before invoking children,
uses strict duplicate-rejecting loads and rechecks every source after capture.

Capture exits 0 (`/tmp/p4blo-parser-baseline-capture.log`):
**411355 bytes**, SHA-256
`454ff7c9b2c68b02ec81eb07d0897355b75721fad2ebe742000ffcb348a5e2bb`.
Exact source identities are inside the artifact and printed in that log.
The baseline is test-only, not a production decoder refactor or a codec-fault
observation. No command metadata from evidence is executed.

### Exact non-overwriting reconstruction

Run in this reviewed baseline checkout with freshly built endpoints and the
task-specific absolute root below. Reconstruct in a separate checkout if the
original artifact still exists; never overwrite retained evidence. Sources and
JSON serialization contain no timestamps or local path metadata.

```bash
P4BLO_PARSER_ROOT=/Users/qobilidop/my/work/p4blo-parser-codecs nix develop -c uv run python - <<'PY'
import hashlib, json, os, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_parser import requests, protobuf_value, test_parser_baseline_contract
from tests.test_codec_leaves import same_json
root = Path(os.environ['P4BLO_PARSER_ROOT']).resolve()
old_json = '0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e'
assert hashlib.sha256((root / 'ir/P4bloIR/Json.lean').read_bytes()).hexdigest() == old_json
base = subprocess.run(['git', '-C', str(root), 'show', '1c1b08e:ir/P4bloIR/Json.lean'], check=True, capture_output=True).stdout
assert hashlib.sha256(base).hexdigest() == old_json
out = root / '.artifacts/codec/parser-baseline.json'
assert not out.exists(), 'never overwrite baseline evidence'
test_parser_baseline_contract()
source_paths = ['ir/P4bloIR/IR.lean', 'ir/P4bloIR/Json.lean', 'ir/P4bloIR/JsonBounds.lean', 'ir/Tests/CodecLaws.lean', 'ir/Tests/DeclarationCodec.lean', 'ir/Tests/TableCodec.lean', 'ir/Tests/ParserCodec.lean', 'ir/Tests/CodecLeaves.lean', 'tests/test_codec_leaves.py', 'tests/test_codec_expr.py', 'tests/test_codec_stmt.py', 'tests/test_codec_parser.py', 'ir/proto/p4blo/v0/p4blo.proto']
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
assert len(rows) == 231
assert sources == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths}
artifact = {'format': 'p4blo.parser-codec.baseline.v0', 'production_base': '1c1b08e', 'sources': sources, 'rows': rows}
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('x') as stream:
    stream.write(json.dumps(artifact, indent=2) + '\n')
print('rows', len(rows), 'successes', sum('encoded' in r['expected'] for r in rows))
print('bytes', out.stat().st_size, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest())
print(json.dumps(sources, indent=2))

PY
```

Pin these source hashes to reviewed baseline commit `9d68d7d` when replaying.
Later kernel witnesses may legitimately change Tests.ParserCodec; compare old
hashes to historical git objects, then separately compare all current request/
expected pairs. Do not demand old test-source hashes equal new witness sources
or silently recapture a changed request set. Additional regressions belong in
a separate inventory.

## Universal wire-only laws

`P4bloIR.ParserCodecLaws` imports only the existing CodecLaws module, composing
its actual Literal/Expr/Stmt and indexed-array roundtrips. All statements hold
at every diagnostic path. Target has no premise; its three constructors and
every string, including the empty state name, are representable. KeySet requires
LiteralRepresentable on each stored operand. SelectCase quantifies over its
ordered sets. A select Transition quantifies over every key expression and case;
a direct Transition has no restriction. State requires each statement and its
transition to be representable. Thus the only exclusions are inherited uint32
bounds, not typing, mask compatibility, range order, arity, name resolution,
permitted parser statements or semantic termination.

The module opens the actual total decoder/encoder bodies and composes their
ordered arrays; no alternate decoder, codec callback, source validation or
new representation is introduced. Production Json and JsonBounds stay exact.
The public IR root exports the module. Default CodecProofAudit checks all five
laws and `ParserCodecTests.parserState_roundtrip` for exactly the standard
propext/Classical.choice/Quot.sound set, with no sorry or native reduction axiom.

The kernel witness includes all targets/sets, unequal key-set arities, mixed
literal types, zero and maximal widths, a huge decimal value, empty/unresolved
names and a conditional body with push and emit. Fifteen kernel exclusions
exercise each KeySet operand, nested cases, both slice bounds, type/stack bounds,
push/pop counts and nested body/transition bounds. They do not exclude any
additional wire-representable value. Existing 27 native anchors and all 231
request/expected pairs are unchanged; the added witness is not a native test.

Confidence is high in the compositional kernel laws and finite independent
answers. Revisit if a member codec or omission rule changes, or review finds an
unobserved field/default or fixture coupling; preserve the historical answers
and review semantic changes separately. This is not full Program composition,
JSON text/binary protobuf equivalence, semantic validity, parser execution or
termination. Independent
[baseline review](reviews/parser-codec-baseline.md) is clear: 283 focused checks,
133 native anchors, all 231 exact raw rows, 76 actual protobuf outputs and
thirteen source hashes independently verified. Final proof/campaign review is
recorded separately in [parser codec review](reviews/parser-codec.md).

## Checked proof checkpoint

Pinned Lean 4.34.0, fresh candidate caches. The standalone law and kernel
witness/default audit builds exit 0:
`/tmp/p4blo-parser-laws-module.log`,
`/tmp/p4blo-parser-laws-witness.log`.
Both complete Lean packages/default audits/native suites exit 0, **567 spec
checks**, before consumers (`/tmp/p4blo-parser-laws-lean.log`).
All seven codec files pass **1332 tests** in 27.00 seconds
(`/tmp/p4blo-parser-laws-focused.log`). The required discovery gate:

```text
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees -q
```

passes **1699 tests / 1779 deselected**, exit 0 in 143.32 seconds
(`/tmp/p4blo-parser-laws-required.log`). Scoped Ruff check and Pyright exit 0:
`/tmp/p4blo-parser-laws-lint.log`, `/tmp/p4blo-parser-laws-types.log`.
No candidate code changes follow those gates; only this evidence note changes.
The integrator owns the combined full gate. No Docker build or external system
mutation is used.

## Isolated actual-code challenges

Fault tree: `/Users/qobilidop/my/work/p4blo-parser-codecs-faults`, branch
`work/parser-codecs-faults`, created from reviewed baseline `9d68d7d`.
It starts with fresh build directories, the unchanged new ParserCodecLaws file
and baseline public root/audit/Tests.ParserCodec layers. This deliberately
separates explicit proof-target checking from the baseline runtime endpoint:
a rejected new proof is never disabled, repaired, replaced with sorry, or
mistaken for a runtime observation. The actual Json compilation is checked
first, the unchanged law target separately, then the actual codec endpoint
and interpreter driver. Failed proof builds do not certify runtime detection.
All mutations are single-category and confined to the fault tree. Candidate
codecs/fixtures remain unchanged throughout; each prior fault is restored before
the next. No caches from a different worktree are copied.

The ordinary 283-test file always executes through the shared lean_binary
fixture. Its forwarder preflight succeeds for these faults. No direct-body
fallback or setup-error counting is used. Raw capture separately invokes the
actual endpoint on the frozen 231 requests, retains only genuine independent
answer mismatches with status 0 / empty stderr, then replays those exact bytes
while the fault is live. This is codec known-answer conformance, not packet DRT.

| Actual compiling fault | Unchanged proof target | Independent executed detection |
| --- | --- | --- |
| Transition encoder reverses select cases only | exit 1 at actual ordered-array body equality | proof-only campaign; no runtime mismatch claim |
| Both Target mappings exchange accept/reject | all five laws build 0 | 24 Python failures, 4 native failures |
| Both masked KeySet mappings exchange value/mask | all five laws build 0 | 10 Python failures, 2 native failures |
| Decode masked mask before value, retain stored operand order | exit 1 at definitional evaluation-order step | 2 exact-error Python failures, 1 native failure |
| Reject present empty select in actual Transition decoder | exit 1, including false empty-select equality | 4 Python failures, 2 native failures |

The order-only proof rejection is **not** evidence that successful roundtrip
behavior is false. The proof fixes an evaluation sequence before applying
successful member laws. A closed asymmetric masked roundtrip still kernel
checks under this mutation (and under the paired operand mutation), using:

```lean
import P4bloIR.Json
open P4bloIR
example : KeySet.decode "" (KeySet.masked (.boolean false) (.error "mask")).toJson =
    .ok (.masked (.boolean false) (.error "mask")) := by rfl
```

Logs: `/tmp/p4blo-parser-fault-{operands,order}-coherence.log`, both exit 0.
This concrete control is not promoted to a universal mutant law.

The paired Target campaign also challenges the observers. With the actual
paired production fault still live, changing only the Python target helper's
expected tag to the opposite tag makes **283 tests pass**; unchanged native
anchors still fail **4** checks. Restore Python, then exchange the two direct
Lean target descriptor tags: again **283 tests pass**, while unchanged native
constructor/descriptor anchors fail **6** checks. This demonstrates the possible
false assurance rather than merely hypothesizing it. Neither paired observer
edit is retained. The frozen baseline request/answer inventory is never
recaptured from these deliberately wrong fixtures.

Logs use `/tmp/p4blo-parser-fault-` plus:

- `reverse-json.log`, `reverse-proof.log`;
- each of `target`, `operands`, `order`, `empty` followed by
  `-json.log`, `-build.log`, `-pytest.log`, `-native.log`;
- `target-build.log` also includes the passing proof target; other categories
  have a separate `-proof.log`;
- `target-paired-python.log`, `target-paired-python-native.log`,
  `target-paired-observer-build.log`, `target-paired-observer.log`,
  `target-paired-observer-native.log`;
- `{operands,order,empty}-capture.log`. Target capture's exact counts/hash are
  in the artifact inventory below and were printed by the same live recipe.

All Json and endpoint build logs listed above exit 0; proof failures are Lean
goal/definitional failures, not warning/lint or tool setup failures. Each pytest
failure above is an executed assertion mismatch.

### Exact mutant reconstruction

The following read-only recipe reconstructs every actual Json delta in memory
from the clean candidate and checks the four saved source identities. Each
replacement was applied once, alone, to the fault tree with apply_patch.
No source or evidence is overwritten by this recipe. Run with
`nix develop -c uv run python -` in the candidate root:

```python
import hashlib, json
from pathlib import Path
from p4blo.drt._json import loads
root = Path('/Users/qobilidop/my/work/p4blo-parser-codecs')
clean = (root / 'ir/P4bloIR/Json.lean').read_text()
assert hashlib.sha256(clean.encode()).hexdigest() == '0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e'
mutations = json.loads(r'''{
  "reverse": [
    [
      "ofList \"cases\" (cases.map SelectCase.toJson)",
      "ofList \"cases\" (cases.reverse.map SelectCase.toJson)"
    ]
  ],
  "target": [
    [
      "(\"accept\", fun p v => emptyMsg p v *> pure Target.accept),\n     (\"reject\", fun p v => emptyMsg p v *> pure Target.reject)",
      "(\"accept\", fun p v => emptyMsg p v *> pure Target.reject),\n     (\"reject\", fun p v => emptyMsg p v *> pure Target.accept)"
    ],
    [
      "| .accept => case \"accept\" empty\n  | .reject => case \"reject\" empty",
      "| .accept => case \"reject\" empty\n  | .reject => case \"accept\" empty"
    ]
  ],
  "operands": [
    [
      "KeySet.masked (← msgField p v \"value\" Literal.decode)\n         (← msgField p v \"mask\" Literal.decode)",
      "KeySet.masked (← msgField p v \"mask\" Literal.decode)\n         (← msgField p v \"value\" Literal.decode)"
    ],
    [
      "| .masked value mask => case \"masked\" (obj [ofMsg \"value\" value.toJson, ofMsg \"mask\" mask.toJson])",
      "| .masked value mask => case \"masked\" (obj [ofMsg \"value\" mask.toJson, ofMsg \"mask\" value.toJson])"
    ]
  ],
  "order": [
    [
      "pure (KeySet.masked (← msgField p v \"value\" Literal.decode)\n         (← msgField p v \"mask\" Literal.decode))",
      "let mask ← msgField p v \"mask\" Literal.decode\n       let value ← msgField p v \"value\" Literal.decode\n       pure (KeySet.masked value mask)"
    ]
  ],
  "empty": [
    [
      "(\"select\", fun p v => do\n       pure (Transition.select (← listField p v \"keys\" Expr.decode)\n         (← listField p v \"cases\" SelectCase.decode)))",
      "(\"select\", fun p v => do\n       if v == Json.mkObj [] then fail p \"empty select rejected\"\n       else pure (Transition.select (← listField p v \"keys\" Expr.decode)\n         (← listField p v \"cases\" SelectCase.decode)))"
    ]
  ]
}''')
for name, replacements in mutations.items():
    changed = clean
    for old, new in replacements:
        assert changed.count(old) == 1, (name, old)
        changed = changed.replace(old, new)
    digest = hashlib.sha256(changed.encode()).hexdigest()
    if name != 'reverse':
        artifact = loads((root / '.artifacts/codec/parser-campaign' / name / 'live-raw.json').read_text())
        assert artifact['sources']['ir/P4bloIR/Json.lean'] == digest
    print(name, digest)
```

The paired Python change, applied only while Target was faulty, is exactly:

```python
# Original target() return:
return ParserCase({tag: {}}, {"tag": tag}, "target")
# Deliberately wrong expected-model replacement:
return ParserCase({tag: {}}, {"tag": {"accept": "reject", "reject": "accept"}[tag]}, "target")
```

Its temporary test source SHA is
`b69d5b5763a2303fc0f2ca07e6a01cb44843e99a5c47af95365614ba1cde68c3`.
The separate paired observer exchanges only the accept/reject string literals
in Tests.ParserCodec.targetValue; its baseline-layer source SHA is
`f0ed3e8136d40af1d26a1f91db826fe336f7c58815b10061590609d5b3bea163`.
Literal native expected constructors and native observer checks stay unchanged.
Python is restored before the observer edit, and the observer before operands.

For each mutation, in the isolated tree's ir directory:

```text
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.Json
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.ParserCodecLaws
nix develop -c lake +leanprover/lean4:v4.34.0 build codec-leaves p4blo-ir
```

Check each exit status separately; expected proof failures must not abort the
separate endpoint build or be counted as runtime failures. The target combined
build log includes all three targets. Reverse stops after the proof failure.
Then run from the fault root (substitute the fixed campaign name):

```text
P4BLO_REQUIRE_LEAN=1 P4BLO_CODEC_FAILURE_DIR=/Users/qobilidop/my/work/p4blo-parser-codecs/.artifacts/codec/parser-campaign/target/harness nix develop -c uv run pytest tests/test_codec_parser.py -q
/Users/qobilidop/my/work/p4blo-parser-codecs-faults/ir/.lake/build/bin/codec-leaves --self-test
```

Use a new campaign output directory in a fresh reproduction checkout; do not
overwrite retained harness evidence. Native anchors run the actual compiled
baseline endpoint; they do not depend on the failed new proof target.

### Raw capture recipe and inventory

Retained base directory:
`/Users/qobilidop/my/work/p4blo-parser-codecs/.artifacts/codec/parser-campaign`.
Each bundle is `<campaign>/live-raw.json`, with a matching
`<campaign>/harness/leaf-<request-sha-prefix>.json` per row. There are four raw
bundles and forty process-harness views; overlap across campaigns is not counted
as additional independent inputs. No raw observations are claimed for reverse
or the intentionally false-assurance paired-fixture runs.

| Campaign | Rows | Bundle bytes | SHA-256 |
| --- | ---: | ---: | --- |
| target | 24 | 373427 | `3b59dd6158144d7bc832ca3339f60d2ceb3fec5b08d5ab035b83bcad634164f0` |
| operands | 10 | 378560 | `2a94b3223054a28329ea3865371aebd27d0fe4fea8f45c7842ae05dcca79f3a4` |
| order | 2 | 1842 | `9e1179d2ae82256a98fb77054b0dd71ff1bb98792dc225c87cf5ad4ce869543a` |
| empty | 4 | 3795 | `9cf16f2e77b83864c629aebf318e808602553eb7d4ff339d420ae580af3625ec` |

The following exact live-capture recipe runs from the clean candidate while
only the isolated endpoint is faulty. Set P4BLO_PARSER_CAMPAIGN to one of those
four labels; invoke `nix develop -c uv run python -`. It rejects an existing
bundle before children, matches every request and answer to the immutable
baseline, checks all source hashes before/after, retains raw bytes and replays
each mismatch live. Existing evidence is never overwritten.

```python
import hashlib, json, os, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_parser import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-parser-codecs')
fault = Path('/Users/qobilidop/my/work/p4blo-parser-codecs-faults')
name = os.environ['P4BLO_PARSER_CAMPAIGN']
baseline = loads((root / '.artifacts/codec/parser-baseline.json').read_text())
fixtures = requests()
assert len(fixtures) == len(baseline['rows']) == 231
for (request, expected), old in zip(fixtures, baseline['rows'], strict=True):
    assert same_json(request, old['request']) and same_json(expected, old['expected'])
out = root / '.artifacts/codec/parser-campaign' / name / 'live-raw.json'
assert not out.exists(), 'never overwrite live evidence'
source_paths = ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/ParserCodecLaws.lean', 'ir/Tests/ParserCodec.lean', 'tests/test_codec_parser.py', 'ir/P4bloIR.lean', 'ir/CodecProofAudit.lean']
sources = {p: hashlib.sha256((fault / p).read_bytes()).hexdigest() for p in source_paths}
rows = []
for request, expected in fixtures:
    stdin = json.dumps(request, separators=(',', ':')) + '\n'
    run = subprocess.run([str(fault / 'ir/.lake/build/bin/codec-leaves')], input=stdin, text=True, capture_output=True, timeout=10)
    assert run.returncode == 0 and run.stderr == ''
    actual = loads(run.stdout)
    if not same_json(actual, expected):
        rows.append({'request': request, 'expected': expected, 'actual': actual, 'stdin': stdin, 'stdout': run.stdout, 'stderr': run.stderr, 'returncode': run.returncode})
assert rows
assert sources == {p: hashlib.sha256((fault / p).read_bytes()).hexdigest() for p in source_paths}
out = root / '.artifacts/codec/parser-campaign' / name / 'live-raw.json'
out.parent.mkdir(parents=True, exist_ok=True)
artifact = {'format': 'p4blo.parser-codec.campaign.v0', 'campaign': name, 'baseline_commit': '9d68d7df713c681d89771cb7f15352eee07bb91d', 'sources': sources, 'rows': rows}
with out.open('x') as stream:
    stream.write(json.dumps(artifact, indent=2) + '\n')
for row in rows:
    replay = subprocess.run([str(fault / 'ir/.lake/build/bin/codec-leaves')], input=row['stdin'], text=True, capture_output=True, timeout=10)
    assert (replay.returncode, replay.stdout, replay.stderr) == (row['returncode'], row['stdout'], row['stderr'])
print(name, 'live raw mismatches', len(rows), 'bytes', out.stat().st_size, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest())
```

### Restored source matching and replay

After all consumers finish, restore exact Json/observer/Python source and then
apply the final candidate public-root, test-witness and audit additions to the
fault tree. Build the final proof/audit/endpoint/driver target set there; do not
copy stale compiled caches. The read-only replay below verifies thirteen source
hashes against **historical baseline git objects**, then separately checks all
current fixtures. It verifies forty raw/harness pairs, deterministic filenames
and hashes, and replays each input against **both** clean endpoints to the
historical exact stdout/status/stderr. It never executes command metadata from
an artifact. It also prints the complete per-view SHA inventory and verifies
all six restored source pairs. Run from the candidate using
`nix develop -c uv run python -`:

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_parser import requests, protobuf_value
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-parser-codecs')
fault = Path('/Users/qobilidop/my/work/p4blo-parser-codecs-faults')
baseline_commit = '9d68d7df713c681d89771cb7f15352eee07bb91d'
baseline = loads((root / '.artifacts/codec/parser-baseline.json').read_text())
fixtures = requests()
assert len(fixtures) == len(baseline['rows']) == 231
key = lambda value: json.dumps(value, sort_keys=True)
expected = {key(request): answer for request, answer in fixtures}
old_rows = {key(row['request']): row for row in baseline['rows']}
assert len(expected) == len(old_rows) == 231
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
print('historical source hashes and both endpoints: 231 exact baseline rows, 76 public protobuf successes')
seen, count = set(), 0
for name in ['target', 'operands', 'order', 'empty']:
    folder = root / '.artifacts/codec/parser-campaign' / name
    data = (folder / 'live-raw.json').read_bytes()
    artifact = loads(data.decode())
    assert artifact['baseline_commit'] == baseline_commit and artifact['campaign'] == name
    assert artifact['sources']['ir/P4bloIR/ParserCodecLaws.lean'] == hashlib.sha256((root / 'ir/P4bloIR/ParserCodecLaws.lean').read_bytes()).hexdigest()
    for path, digest in artifact['sources'].items():
        if path not in ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/ParserCodecLaws.lean']:
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
for path in ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/ParserCodecLaws.lean', 'ir/Tests/ParserCodec.lean', 'tests/test_codec_parser.py', 'ir/P4bloIR.lean', 'ir/CodecProofAudit.lean']:
    assert (root / path).read_bytes() == (fault / path).read_bytes(), path
    print('restored', path, hashlib.sha256((root / path).read_bytes()).hexdigest())
print('live observations', count, 'distinct requests', len(seen), 'both restored endpoints agree')
```

The restored proof/audit/endpoint/driver build exits 0
(`/tmp/p4blo-parser-fault-restored-build.log`), restored ordinary focused
tests pass **283** in 7.30 seconds
(`/tmp/p4blo-parser-fault-restored-pytest.log`), and restored native self-test
passes **133** (`/tmp/p4blo-parser-fault-restored-native.log`).
The exact replay exits 0 (`/tmp/p4blo-parser-restored-replay.log`):
**231 historical rows, 76 public protobuf outputs, 40 live observations /
34 distinct requests, 40 matching harness views, both clean endpoints**.
All six restored source pairs are byte-identical. The in-memory mutant identity
check exits 0 (`/tmp/p4blo-parser-mutation-identities.log`).
The original 411355-byte baseline SHA remains
`454ff7c9b2c68b02ec81eb07d0897355b75721fad2ebe742000ffcb348a5e2bb`.

Frozen candidate identities:

- Json: `0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`
- ParserCodecLaws: `b23ba21db002ad23501ae0b77fa770b5b4ff19763555b80b823af5a1340e27b1`
- Tests.ParserCodec: `432092df70df8674162fa4e0cd873f532c8ae363a7b72b76dd330b7231351c7b`
- Python fixture: `9e9f2a732764f247d3f4f42e7ce1d8c632fd5a8149c35d4ab7628831c34ac1ca`
- IR public root: `7d2c64e26712bc6e176df85b91fbaa334afdfd6e3f92f8f60fa3d2a74d1d8af6`
- CodecProofAudit: `b04db2c5a38336889db580ed383911f636b9fb231ceecc3adfa4e66fecd7f76f`

Baseline Tests.ParserCodec differs only by the later witness/import additions;
it must be checked at baseline commit, not compared to this new source hash.
No intentional mutant is present in candidate or restored fault-tree sources.
The next bounded composition is Action/Block, subject to a new baseline-first
implementation contract; this checkpoint does not start it.

Final independent review is **clear**. The reviewer reran 283 focused checks,
133 native anchors and six exact standard-only axiom queries, replayed all 231
historical rows against both endpoints with thirteen old source hashes and 76
protobuf outputs, and checked all forty live raw/view pairs (34 unique inputs),
all five reconstructed mutations and six restored source pairs. The report
distinguishes the proof-order caveat and paired-observer false assurances.
No binary consumers remain at handoff.
