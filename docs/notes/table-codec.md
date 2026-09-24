# Table declaration codecs

2026-09-23. Implementation follows the accepted [table plan](table-codec-next.md)
and its independent review. This checkpoint adds independent observations only;
four universal Key/ActionCall/Entry/Table laws remain the next stage after
baseline review and its separate commit.

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

## Boundaries and next stage

Confidence is high in the finite baseline and first three proof compositions;
Table's seven-field proof still needs implementation. Preserve every existing
wire default, enum meaning and error order. If a decoder defect or required
production change is discovered, stop and seek a separately reviewed boundary;
do not fix it inside proof work. No text/binary protobuf theorem, universal
Python parity, semantic validity, table-selection/execution or full Program
codec theorem follows here.

After independent baseline review/commit, add four wire-only predicates/laws,
constructive Table witnesses and overflow negatives/default audits, then the
five real compiling fault categories plus paired expectation challenge specified
by the plan. Preserve exact source-matched live raw mismatches, restore and
replay, and obtain final independent review before proof/evidence commits.
