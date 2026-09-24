# Parser-syntax codec baseline

2026-09-23. Implements the first slice of the reviewed
[Program completion plan](program-codec-completion.md). This checkpoint is
independent test evidence only. Production ParserCodecLaws, public exports
and new proof audits have not been created; they follow a separately reviewed
and committed baseline. The historical unregistered probe is feasibility,
not integrated parser-codec coverage.

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

Pin these source hashes to the eventual reviewed baseline commit when replaying.
Later kernel witnesses may legitimately change Tests.ParserCodec; compare old
hashes to historical git objects, then separately compare all current request/
expected pairs. Do not demand old test-source hashes equal new witness sources
or silently recapture a changed request set. Additional regressions belong in
a separate inventory.

## Next bounded stage and limits

After independent baseline review/commit, implement the five actual universal
wire-only laws, a mixed kernel State witness and propagated-bound exclusions,
and default-audit all six roots. Preserve actual codec bytes and every permissive
wire domain/default/error order. Then perform all five accepted compiling
fault categories and paired expected-model/descriptor challenges in a separate
fault worktree, retaining source-matched live mismatches and restored replays.
A proof rejection, stronger intermediate-lemma failure, setup error and executed
known-answer mismatch must remain distinct.

Confidence is high in the finite frozen answers and direct observations.
Revisit if review finds an unobserved field/default or fixture coupling; never
adjust production codecs merely to satisfy the fixtures. This baseline is not
a universal parser/Program codec theorem, JSON text/binary protobuf theorem,
semantic validity or execution/termination guarantee. Independent
[baseline review](reviews/parser-codec-baseline.md) is clear: 283 focused checks,
133 native anchors, all 231 exact raw rows, 76 actual protobuf outputs and
thirteen source hashes independently verified. Proof work has not started.
