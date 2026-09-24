# Foundational declaration codecs

2026-09-23. Implementation follows the accepted
[nine-codec plan](program-codec-next.md) and its independent review.

## Baseline checkpoint

Production base: `c146126`. Only test files, endpoint/native registration and
the shared test CodecKind union change in this first checkpoint. All production
decoders/encoders, syntax, runtime and user-package sources remain unchanged.
In particular `ir/P4bloIR/Json.lean` retains SHA-256
`0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`.
This is an independent observation baseline, **not** a codec refactor or nine
completed universal roundtrip laws. Independent baseline review is clear;
proof work follows this baseline's separate commit.
See [baseline review](reviews/declaration-codec-baseline.md).

The dedicated `Tests.DeclarationCodec` observes every field of Field,
HeaderType, StructType, EnumType, Var, Param, Method, ExternType and
ExternInstance. It reuses independent Ty/Literal constructor observations;
Direction is a direct four-case constructor match, never a lookup in
Direction.names or protoName. The existing test-only codec executable delegates
these nine kinds here and all earlier kinds to the unchanged old reply function.
Fourteen additional default native checks include separately written literal
direction anchors, asymmetric field/argument order and names, exact nested
diagnostics and null-versus-present-empty return behavior.

`tests/test_codec_declarations.py::requests()` is the complete ordered source:
247 unique requests (102 successes and 145 errors), including every selected kind, all four directions and
all embedded Ty/Literal families. Canonical cases include empty/duplicate names,
invalid aggregate header fields, directionless/non-input constructor parameters,
unresolved externs, zero/max widths/sizes, huge/out-of-width decimal values,
Unicode/escaping, three unequal fields/arguments and multiple unequal methods.
There is no semantic validator or Index.build between the public protobuf
dump/load wrapper and the selected declaration observation.

Malformed/default controls cover nonobjects; absent/null/empty/nonobject type;
absent/null/empty/nonarray repeated fields; null and malformed children at zero,
later and nested indices; missing/numeric/unknown/UNSPECIFIED directions;
optional return absence versus `{}` and overflow; and simultaneous errors
anchoring each actual declaration's evaluation order. Numeric Direction input
is an actual Lean rejection, not a claim about all protobuf accepted inputs.
Unknown keys are ignored as existing Lean behavior. Strict same_json comparisons
avoid Boolean/number equality; duplicate-rejecting loads observes raw responses.

Confidence: high in this finite baseline and the reviewed proof feasibility.
Revisit if a selected codec unexpectedly needs a production change: preserve
this baseline and seek a separate reviewed fix boundary. No whole Program,
text/binary codec, semantic validation or universal Python equivalence follows.

## Gates and provenance

Fresh worktree-owned Lean caches and Python environment were used, with no
Docker build or shared mutable executable. Both packages and all default audits
and native tests pass, including 520 spec checks; command exit 0:

```text
nix develop -c /Users/qobilidop/my/work/p4blo-declaration-codec/scripts/check-lean.sh
```

Log: `/tmp/p4blo-declaration-baseline-lean.log`. Only after this completed did
the endpoint consumers run. Initial development errors were wrong native
checkOk predicate syntax/record indentation and Python list-invariance typing;
those failed builds are not positive assurance evidence or fault campaigns.

Focused command (repository cwd):

```text
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_codec_leaves.py tests/test_codec_expr.py tests/test_codec_lvalue.py tests/test_codec_stmt.py tests/test_codec_declarations.py -q
```

Exit 0: 814 focused tests passed in 13.70s, including 319 new declaration
checks. Log: `/tmp/p4blo-declaration-baseline-focused.log`. Scoped Ruff check/format and
Pyright pass. Required/full integration gates and final proof/mutation review
remain later obligations; do not equate this baseline with those gates.

## Raw baseline capture and reconstruction

The ignored artifact is `.artifacts/codec/declaration-baseline.json`; it retains
all original compact-plus-LF inputs, exact stdout/stderr/status and independent
expected answers. Its source map pins actual IR, Json, JsonBounds, previous leaf
observations, new observations/dispatch, shared strict Python harness, new
fixtures and the protobuf schema. This is raw codec evidence, not packet DRT.
No metadata command is executed during capture or replay.

Initial capture exited 0: 247 rows, all 102 successful canonical outputs also
checked through the public protobuf wrapper. Artifact size 189142 bytes,
SHA-256 `a38bc43a8feb08db437ff371925ba1d23d446182aa5906e1cadd462f15d4e2b1`.
The complete capture recipe below reproduces this artifact byte for byte when
run against these frozen sources; it includes no timestamps or local paths.

Run the following from the reviewed baseline checkout (freshly build both
packages first). Set the task-specific absolute root for that checkout. Never
overwrite an existing artifact; reconstruct into a separate baseline checkout
if the original still exists. The production hash guard is checked **before**
running any child or creating the output, and all source hashes are rechecked
after capture. The helper functions are tracked test sources, not generated
expected answers from the decoder.

```bash
P4BLO_DECLARATION_ROOT=/Users/qobilidop/my/work/p4blo-declaration-codec nix develop -c uv run python - <<'PY'
import hashlib, json, os, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_declarations import requests, protobuf_value, test_declaration_baseline_contract
from tests.test_codec_leaves import same_json
root = Path(os.environ['P4BLO_DECLARATION_ROOT']).resolve()
old_json = '0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e'
assert hashlib.sha256((root / 'ir/P4bloIR/Json.lean').read_bytes()).hexdigest() == old_json
base = subprocess.run(['git', '-C', str(root), 'show', 'c146126:ir/P4bloIR/Json.lean'], check=True, capture_output=True).stdout
assert hashlib.sha256(base).hexdigest() == old_json
out = root / '.artifacts/codec/declaration-baseline.json'
assert not out.exists(), 'never overwrite baseline evidence'
test_declaration_baseline_contract()
source_paths = ['ir/P4bloIR/IR.lean', 'ir/P4bloIR/Json.lean', 'ir/P4bloIR/JsonBounds.lean', 'ir/Tests/CodecLaws.lean', 'ir/Tests/DeclarationCodec.lean', 'ir/Tests/CodecLeaves.lean', 'tests/test_codec_leaves.py', 'tests/test_codec_declarations.py', 'ir/proto/p4blo/v0/p4blo.proto']
sources = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths}
rows = []
for request, expected in requests():
    raw_input = (json.dumps(request, separators=(',', ':')) + '\n').encode()
    run = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')], input=raw_input, capture_output=True, timeout=10)
    assert run.returncode == 0 and run.stderr == b''
    assert same_json(loads(run.stdout.decode()), expected), (request, run.stdout, expected)
    if 'encoded' in expected:
        _, canonical = protobuf_value(request['kind'], expected['encoded'])
        assert same_json(canonical, expected['encoded'])
    rows.append({'request': request, 'expected': expected, 'stdin': raw_input.decode(), 'stdout': run.stdout.decode(), 'stderr': run.stderr.decode(), 'returncode': run.returncode})
assert len(rows) == 247
assert sources == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths}
artifact = {'format': 'p4blo.declaration-codec.baseline.v0', 'production_base': 'c146126', 'sources': sources, 'rows': rows}
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('x') as stream:
    stream.write(json.dumps(artifact, indent=2) + '\n')
print('rows', len(rows), 'successes', sum('encoded' in r['expected'] for r in rows))
print('bytes', out.stat().st_size, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest())
print(json.dumps(sources, indent=2))
PY
```

Final replay must validate recorded source hashes against the committed old
baseline revision, then match all 247 ordered current requests/expected answers
independently. Later proof witnesses may change test-module bytes without
invalidating old source provenance; do not compare such changed current files
to the old source hash or silently recapture this original evidence.

## Remaining implementation

After baseline independent review and its small commit: add the nine wire-only
predicates/universal laws in DeclarationCodecLaws, audited constructive witnesses
and negative embedded bounds. Run the four real compiling fault categories in
the accepted plan (including paired Direction/name mappings and independent
observer challenge), preserve live raw artifacts, restore/replay, run final
gates and obtain independent final review. Production Json remains expected to
be byte-identical. No action/runtime/schema/user-package files are in scope.
