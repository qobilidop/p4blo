# Foundational declaration codecs

2026-09-23. Implementation follows the accepted
[nine-codec plan](program-codec-next.md) and its independent review.

## Baseline checkpoint

Production base: `c146126`; reviewed baseline commit:
`21b0fec353c1776cfb2d33c0c857a0aeb797ab1b`. Only test files, endpoint/native registration and
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

## Universal proof checkpoint

`P4bloIR.DeclarationCodecLaws` extends the existing CodecLaws namespace and is
exported by the public IR root. Nine actual roundtrip laws cover arbitrary paths,
names and finite lists. The only premises are embedded TypeRepresentable and
LiteralRepresentable facts; EnumType is unconditional (its named predicate is
True). Method covers each parameter and each present return; ExternType covers
every member in **both** arrays; ExternInstance covers every argument. No arity,
direction, name-resolution or header-field semantic premise was added.

Proofs expose the concrete actual record decoder body, then apply existing
type/literal laws and array_encoded_roundtrip at each actual member path. The
private type-object lemma merely exposes the shape of the actual encoder; no
new serializer, binder, default policy or interpreter was introduced. The
historical unregistered DeclarationCodecProbe remains a planning artifact,
not a production theorem or default audit.

The default audit registers all nine laws plus the kernel-checked
`DeclarationCodecTests.declarations_roundtrip` conjunction. Every root reports
exactly `[propext, Classical.choice, Quot.sound]`. Its constructive witnesses
include all Ty/Literal families, every direction, duplicate/empty/unresolved
names, aggregate header fields, optional absent/present-zero/max returns,
zero-width huge literal values, and max sizes. Nine kernel negative examples
reject overflowing embedded types/literals, including each ExternType array.
Native descriptor and Python request/expected baseline definitions are unchanged.

Initial EnumType proof elaboration needed explicit encoder/decoder arguments
to the existing array lemma; the generic placeholder was inferred incorrectly.
That failed development attempt is not positive proof or mutation evidence.
The final core/default-audit build succeeds.

Proof-stage both-package/default/native gate exit 0 (520 spec checks), log
`/tmp/p4blo-declaration-proof-lean.log`; focused all-codec gate exit 0 (814 tests),
log `/tmp/p4blo-declaration-proof-focused.log`. Final restoration, required gate
and independent proof/fault review are recorded below.

No action/runtime/schema/user-package files are in scope. Full Program and the
remaining table/parser/executable declaration families remain open.

## Isolated adversarial campaigns

All mutations occur only in
`/Users/qobilidop/my/work/p4blo-declaration-codec-faults`, branch
`work/declaration-codec-faults`, based on baseline `21b0fec` with the reviewed
candidate declaration-law/root/audit/kernel-witness additions applied. Fresh
caches; no copied executable, no concurrent build and consumer in that tree.
The candidate worktree and its original 247-row artifact remain clean of faults.
No mutation is a proposed implementation change.

Reproduce each production patch below separately; restore the exact clean
source before the next unless the paired-challenge paragraph explicitly retains
Direction.names. Use the pinned package cwd and build command:

```text
nix develop -c lake +leanprover/lean4:v4.34.0 build codec-leaves CodecProofAudit
```

For the one-sided array fault, first build `P4bloIR.Json` alone, check its
bare exit status, then build `P4bloIR.DeclarationCodecLaws` unchanged. The
ordinary driver is not needed for the raw codec endpoint. A native command is:

```text
/Users/qobilidop/my/work/p4blo-declaration-codec-faults/ir/.lake/build/bin/codec-leaves --self-test
```

### Exact mutation recipes

1. **One-sided field order.** Only in `HeaderType.toJson`, replace
   `t.fields.map Field.toJson` by `t.fields.reverse.map Field.toJson`.
   Actual Json build exits 0; unchanged declaration-law build exits 1 at the
   exact nonempty-array equality for both empty and nonempty names. This is
   semantic proof rejection, not a compile failure of the mutated codec,
   lint failure, or executable comparison. Logs:
   `/tmp/p4blo-declaration-fault-reverse-{json,proof}.log`.
2. **Paired Direction table.** In actual `Direction.names`, change
   `("DIRECTION_IN", .«in»), ("DIRECTION_OUT", .out)` to
   `("DIRECTION_IN", .out), ("DIRECTION_OUT", .«in»)`, keeping all other
   entries unchanged. Both actual encoder and decoder use this table.
   The endpoint plus every unchanged default codec audit build exits 0;
   five direct known-answer observations and two separate literal native
   anchors reject it. Logs:
   `/tmp/p4blo-declaration-fault-direction-{build,direct,native,raw}.log`.
3. **Paired instance labels.** In actual `ExternInstance.decode`, read
   `name` from `"extern_type"` and `externType` from `"name"`.
   In actual `ExternInstance.toJson`, emit `i.name` at
   `"extern_type"` and `i.externType` at `"name"`; leave argument
   order and all other declarations unchanged. No theorem statement or premise
   is changed to accommodate this fault.
4. **Actual first-error order.** Replace only the body of `Param.decode` by:

   ```lean
   def Param.decode (path : String) (j : Json) : Dec Param := do
     let name ← strField path j "name"
     let direction ← enumField path j "direction" Direction.names
     let type ← msgField path j "type" Ty.decode
     pure { name, type, direction }
   ```

   This still reads name first but now direction precedes type; successful
   representable roundtrip does not specify malformed-input error order.

### Paired fixture and observer challenges

With only the real Direction.names fault installed, insert these two lines
immediately after `value[key] = child` in the **else** branch of the Python
test-only `decl` fixture builder:

```python
if key == "direction":
    value[key] = {"DIRECTION_IN": "DIRECTION_OUT", "DIRECTION_OUT": "DIRECTION_IN"}.get(child, child)
```

All 319 direct Python check bodies then pass, while the two independently
written native literal-direction anchors still fail (exit 1). This deliberately
demonstrates how a paired wrong expected model can hide the real fault; it is
not evidence of correctness. Logs:
`/tmp/p4blo-declaration-fault-paired-fixture-{direct,native}.log`.
Restore Python exactly to baseline before the next challenge.

Still keeping the real Direction.names fault, independently swap **only**
the IN/OUT result strings in the Lean test `directionValue` constructor
observer. Rebuild endpoint/default audits (exit 0); all 319 unmodified Python
check bodies again pass, but native checks fail at both literal-direction
anchors and both direct-observer anchors (four failures, exit 1). Logs:
`/tmp/p4blo-declaration-fault-paired-observer-{build,direct,native}.log`.
Restore the observer and Direction table before other production campaigns.
These demonstrate why native literal semantic anchors must not be generated
from the producer table, test observer or Python expected fixture.

### Direct test-body runner versus ordinary DRT discovery

The real Direction table fault prevents the ordinary LeanRunner forwarder
preflight from opening checksum16: `checksum16.compute param 0: direction
mismatch`. The first attempted pytest run lacked the ordinary driver, and a
second run after building it encountered that signature failure. Neither is
counted as five known-answer detections or normal packet DRT. Logs:
`/tmp/p4blo-declaration-fault-direction-tests.log`,
`/tmp/p4blo-declaration-fault-direction-driver.log`,
`/tmp/p4blo-declaration-fault-direction-tests-ready.log`.

For the bounded codec campaign, invoke the existing 319 Python check bodies
directly with the actual endpoint's sibling path; assert_leaf itself still
launches the real codec executable, uses strict observations, retains mismatch
artifacts and enforces exit/status/stderr. This deliberately bypasses only the
unrelated packet-driver preflight and must not be described as a required DRT
run. Run in the fault worktree, with
`P4BLO_CODEC_FAILURE_DIR` set to an absolute campaign-specific artifact path:

```python
from functools import partial
from pathlib import Path
from tests import test_codec_declarations as t
binary = Path('/Users/qobilidop/my/work/p4blo-declaration-codec-faults/ir/.lake/build/bin/p4blo-lean')
checks = [('contract', t.test_declaration_baseline_contract)]
for i, case in enumerate(t.cases()):
    checks += [(f'protobuf-{i}', partial(t.test_declaration_protobuf_known_answers, case)),
               (f'known-{i}', partial(t.test_lean_agrees_declaration_known_answers, binary, case))]
for i, (kind, wire, error) in enumerate(t.malformed()):
    checks.append((f'error-{i}', partial(t.test_lean_agrees_declaration_exact_errors, binary, kind, wire, error)))
for i, (kind, wire, case) in enumerate(t.normalized()):
    checks.append((f'normal-{i}', partial(t.test_lean_agrees_declaration_normalization, binary, kind, wire, case)))
assert len(checks) == 319
failures = []
for name, check in checks:
    try:
        check()
    except AssertionError as error:
        failures.append(name)
        print('FAIL', name, repr(error))
print('direct scoped checks', len(checks), 'failures', failures)
raise SystemExit(bool(failures))

```

### Source-matched live raw capture

Run the following through `nix develop -c uv run python -` in the fault
worktree with `P4BLO_DECLARATION_CAMPAIGN` set to `direction`, `names`
or `order`. Do this **before** any paired fixture/observer challenge.
The output is ignored evidence under the clean candidate tree, not a source
edit; open mode x refuses overwrite. Every mismatch must match the frozen
independent request/answer source, and each retained raw transcript is immediately
replayed against the still-live compiled fault before restoration.

```python
import hashlib, json, os, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_declarations import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-declaration-codec')
fault = Path('/Users/qobilidop/my/work/p4blo-declaration-codec-faults')
name = os.environ['P4BLO_DECLARATION_CAMPAIGN']
baseline = loads((root / '.artifacts/codec/declaration-baseline.json').read_text())
assert len(baseline['rows']) == 247
fixtures = requests()
assert len(fixtures) == 247
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
sources = {p: hashlib.sha256((fault / p).read_bytes()).hexdigest() for p in ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/DeclarationCodecLaws.lean', 'ir/Tests/DeclarationCodec.lean', 'tests/test_codec_declarations.py']}
out = root / '.artifacts/codec/declaration-campaign' / name / 'live-raw.json'
out.parent.mkdir(parents=True, exist_ok=True)
artifact = {'format': 'p4blo.declaration-codec.campaign.v0', 'campaign': name, 'baseline_commit': '21b0fec353c1776cfb2d33c0c857a0aeb797ab1b', 'sources': sources, 'rows': rows}
with out.open('x') as stream:
    stream.write(json.dumps(artifact, indent=2) + '\n')
# Replay the retained exact raw transcript against the still-live fault.
for row in rows:
    replay = subprocess.run([str(fault / 'ir/.lake/build/bin/codec-leaves')], input=row['stdin'], text=True, capture_output=True, timeout=10)
    assert (replay.stdout, replay.stderr, replay.returncode) == (row['stdout'], row['stderr'], row['returncode'])
print(name, 'live mismatches/replays', len(rows), 'bytes', out.stat().st_size, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest())

```

## Final restoration and checked results

All mutation consumers ended before restoration/rebuilding. Four separate cmp
checks (Json, declaration laws, declaration tests, Python fixtures) exit 0
against the clean candidate. Restored endpoint/driver/default audits build exits
0: `/tmp/p4blo-declaration-fault-restored-build.log`. The final ordinary fault-tree
pytest run now uses the shared preflight and passes all 319 tests; native
self-test passes all 86 checks. Logs:
`/tmp/p4blo-declaration-fault-restored-{tests,native}.log`. This restored pytest
success is distinct from the deliberately direct live-mutant comparisons.

| Campaign | Actual codec/audits | Direct check bodies (319) | Native failures | Raw rows |
|---|---|---|---:|---:|
| Header encoder reversal | Json 0; unchanged law 1 | not claimed | not run | 0 |
| Paired Direction table | build/audits 0 | 5 known-answer failures | 2 | 5 |
| Paired Direction + Python fixture | unchanged live codec | all pass | 2 | no new claim |
| Paired Direction + Lean observer | build/audits 0 | all pass | 4 | no new claim |
| Paired instance labels | build/audits 0 | 1 value + 1 precedence failure | 1 | 2 |
| Param direction-before-type | build/audits 0 | 17 exact-error failures | 2 | 17 |

Instance/order logs:
`/tmp/p4blo-declaration-fault-{names,order}-{build,direct,native,raw}.log`.
Successful universal proofs survived all three paired/order production faults
unchanged. They establish actual encode/decode correspondence, not independent
wire agreement or malformed-input error order; finite independent anchors test
those distinct obligations.

The primary raw bundles below are relative to
`.artifacts/codec/declaration-campaign/`. Together: **24 observations of 24
distinct requests**, not 48 inputs. Each also has a harness
`leaf-<digest>.json` view: digest is the first 24 hex digits of SHA-256 of
`json.dumps(request, sort_keys=True).encode()`. This filename rule, the tracked
247-request source and the direct runner reconstruct all 24 harness files.
Their command metadata is never executed.

| Primary raw bundle | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `direction/live-raw.json` | 5 | 33706 | `fe10de274ff7e5c9f6a3dd121f6cf978e754b519b735ba4bfbccc1bec1d2c880` |
| `names/live-raw.json` | 2 | 16233 | `a18f896fa322110a5aba9457015c1af9524b3d8790c157699f778f32c15bfe11` |
| `order/live-raw.json` | 17 | 10915 | `6bbfe29af92580ec1420b26d255630c631241531fc2204588405c3dc19db8a74` |

Every raw input replayed first against its live compiled fault, with identical
faulty stdout/stderr/status, then restored against **both** clean candidate and
fault-tree endpoints with independent expected agreement. Restored replay exits
0: `/tmp/p4blo-declaration-fault-restored-replay.log`. Exact recipe (candidate
cwd, `nix develop -c uv run python -`):

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_declarations import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-declaration-codec')
fault = Path('/Users/qobilidop/my/work/p4blo-declaration-codec-faults')
fixtures = {json.dumps(r, sort_keys=True): e for r, e in requests()}
assert len(fixtures) == 247
seen = []
for name, count in [('direction', 5), ('names', 2), ('order', 17)]:
    folder = root / '.artifacts/codec/declaration-campaign' / name
    artifact = loads((folder / 'live-raw.json').read_text())
    assert len(artifact['rows']) == count
    leaves = list(folder.glob('leaf-*.json'))
    assert len(leaves) == count
    for row in artifact['rows']:
        key = json.dumps(row['request'], sort_keys=True)
        expected = fixtures[key]
        assert same_json(row['expected'], expected)
        assert row['stdin'] == json.dumps(row['request'], separators=(',', ':'))+'\n'
        assert same_json(loads(row['stdout']), row['actual'])
        assert not same_json(row['actual'], expected)
        assert row['returncode'] == 0 and row['stderr'] == ''
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        leaf = loads((folder / f'leaf-{digest}.json').read_text())
        for field in ['request', 'expected', 'actual', 'returncode', 'stderr']:
            assert same_json(leaf[field], row[field])
        for checkout in [root, fault]:
            result = subprocess.run([str(checkout / 'ir/.lake/build/bin/codec-leaves')], input=row['stdin'], text=True, capture_output=True, timeout=10)
            assert result.returncode == 0 and result.stderr == ''
            assert same_json(loads(result.stdout), expected)
        seen.append(key)
    print(name, count, 'source-matched raw and harness artifacts; restored both endpoints')
assert len(seen) == len(set(seen)) == 24
print('24 distinct requests,24 raw observations,24 harness views; all restored')

```

Clean/restored SHA-256:

- Json: `0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`
- laws: `dcf733faacd636b9f1ba84b26876a8e8e52c9493aca09351c359589ffe86f9e4`
- final declaration tests: `74af67f8b4301995f9d3fe56dea05ed08a0a99c9fcb15b763fee71f9c4d3730b`
- unchanged Python fixture: `2045d18beddf94169e4df42d5aaa45715650f82aba8a44547ad169d26b11c75e`

Candidate both-package/default/native gate, focused 814 and scoped Ruff
format/check/Pyright pass. Required real-Lean gate exits 0: **1069 passed /
1637 deselected**, no skips, in 102.71 seconds, log
`/tmp/p4blo-declaration-proof-required.log`. These gates ran after final Lean
source changes; later candidate edits only record evidence. Root owns the
combined full integration gate; no new full/schema/oracle run or Docker build
is claimed here. No production codec/runtime behavior changes or intentional
faults are proposed.

All 247 original baseline transcripts replay byte-for-byte after the laws.
Every old source hash is checked at baseline commit 21b0fec; every current
request/expected answer is source-matched; all 102 successful outputs pass the
public protobuf wrapper. Exit 0:
`/tmp/p4blo-declaration-proof-baseline-replay.log`. Exact recipe:

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_declarations import requests, protobuf_value
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-declaration-codec')
a = loads((root / '.artifacts/codec/declaration-baseline.json').read_text())
for path, digest in a['sources'].items():
    old = subprocess.run(['git', '-C', str(root), 'show', '21b0fec:'+path], check=True, capture_output=True).stdout
    assert hashlib.sha256(old).hexdigest() == digest, path
assert len(a['rows']) == len(requests()) == 247
for row, (request, expected) in zip(a['rows'], requests(), strict=True):
    assert same_json(request, row['request']) and same_json(expected, row['expected'])
    assert row['stdin'] == json.dumps(request, separators=(',', ':'))+'\n'
    run = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')], input=row['stdin'], text=True, capture_output=True, timeout=10)
    assert (run.stdout, run.stderr, run.returncode) == (row['stdout'], row['stderr'], row['returncode'])
    actual = loads(run.stdout)
    assert same_json(actual, expected)
    if 'encoded' in actual:
        _, encoded = protobuf_value(request['kind'], actual['encoded'])
        assert same_json(encoded, expected['encoded'])
print('247 source-matched original transcripts byte-identical;102 public protobuf outputs;9 old source hashes at21b0fec')
```

Final independent proof/evidence review is **clear**, separately from baseline
review: [declaration codec review](reviews/declaration-codec.md). The reviewer
checked the ten standard-only audit roots, 319 focused tests, 247 historical
transcripts/source hashes, all 24 live/restored observations and matching harness
views, exact fault-source hash reconstruction, and restoration bytes/logs.
Confidence is high in the narrow wire-bound theorem and observed
mapping/error controls. Revisit when enum tables, field names, defaults or
member bounds change: replay the frozen baseline and retain independent native
anchors instead of updating both sides together.
