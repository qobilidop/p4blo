# Action and Block codec acceptance boundary

2026-09-23. Worktree `work/block-codecs`, base `ca2f20f`, after the five
parser laws are committed. This is the next bounded slice of the reviewed
[Program completion plan](program-codec-completion.md): **Action and Block
only**, baseline first. No runtime, schema, generated code, user-package,
corpus or production Json change is planned. Root owns integration/status/
decisions. Independent plan/baseline review precedes its small commit; the
two universal laws and their campaigns follow that committed baseline.

## Exact wire-only domain

ActionRepresentable will require every parameter ParamRepresentable and every
body statement StmtRepresentable. BlockRepresentable will require all elements
of params, locals, actions, tables, states and body to satisfy their existing
member predicates (using the new ActionRepresentable only for actions).
Name, startState and all three BlockKind constructors are unrestricted.

Every inherited uint32 position remains explicit: type bit width/stack size,
literal bit width, expression slice bounds, statement push/pop counts, table
key expression bounds, default/entry action literal widths, KeyValue LPM
prefix, entry priority, table size, parser select keys/sets and nested state
body statements. Decimal values/masks stay unbounded naturals. There is no
list-length, typing, arity, uniqueness, nominal resolution, direction, parser
shape/progress or fuel premise. Actions admit all four directions, including
in/out/inout; every kind admits every Block field. Parser body/actions/tables
and control/deparser states/startState are intentional positive witnesses.
Duplicate/empty/unresolved names and mismatched calling conventions remain
representable. No Index.build, validator or interpreter is invoked by a law.

## Actual fields, defaults and diagnostics

The actual total definitions are Json.lean Action.decode/toJson and
Block.decode/toJson; no recursion refactor is needed. Their field order is:

| Codec | Decoding/evaluation order |
| --- | --- |
| Action | name, params, body |
| Block | name, kind, params, locals, actions, tables, states, start_state, body |

All ordinary strings default to empty and empty strings are omitted by the
encoder. Ordinary repeated fields accept absent/null/empty arrays as empty;
the encoder omits empty lists. Nonarray values and null list elements fail at
their precise member/index path. Action `{}` succeeds. Block `{}`, null kind,
and `BLOCK_KIND_UNSPECIFIED` fail at kind: unspecified; there is no abstract
unspecified kind. Any unknown string ending `_UNSPECIFIED` has that same
diagnostic, while other unknown strings report their quoted value. Enum
numbers/Booleans are not accepted as named strings. The encoder always emits
one of the three named kinds, even for otherwise empty blocks. Unknown
annotations are ignored as current behavior, not a compatibility guarantee.

Pin simultaneous-error precedence for each adjacent field pair, nested action
name/params/body and nested table/state/member errors. Cover root path `""`
and nonempty paths, first/later/nested indices, all member overflow families,
and cases where earlier empty/default fields permit a later error. Existing
member defaults remain unchanged (including Entry.action `{}` and optional
some-empty Table default). Do not infer semantic presence requirements from
comments describing valid P4 blocks.

## Independent baseline design

Add only `Tests.BlockCodec`, `tests/test_codec_blocks.py`, the two endpoint
labels `action`/`block`, narrow CodecKind union and native registrations, plus
this note. Preserve every old label/inventory: `action_call` remains the table
ActionCall and is not Action; `key`/`table_key` remain distinct.

Lean observers directly match BlockKind.parser/control/deparser to three
literal names, independent of BlockKind.names/protoName. Observe every stored
field and every ordered element via existing independent Param/Var/Stmt/Table/
State descriptors. Action and Block descriptors must not derive their answers
from production toJson. Native controls include all three literal kind-to-
constructor answers and separate constructor-to-descriptor answers, empty
Action/Block defaults, missing/null/unknown/numeric kind, a full mixed block
for each kind, arbitrary directions, asymmetric list order, startState versus
name, adjacent error precedence and a later nested path.

Python constructs independent wire and full abstract answers. Canonical
fixtures include all member families reused from frozen declaration/table/
parser/statement fixtures, three asymmetric list elements, duplicate/empty
names, zero/max/huge values, and all three kinds with both minimal and fully
populated shapes. Malformed/default matrices cover all fields, all enum
forms, list null/type/index cases and inherited member errors. Normalization
includes unknown annotations, absent/null/empty fields and nested member
normalizations. Keep a complete ordered nonzero unique request inventory with
fixed counts and strict type-sensitive JSON comparisons; add future controls
separately rather than changing frozen answers.

Canonical outputs pass actual public `ir.dump_json`/`ir.load_json` through
Program.blocks (Block) or Program.blocks.actions (Action). Use protobuf
SetInParent where required, compare the recovered selected message and strict
canonical JSON, and never validate the transport wrapper. All real conformance
tests use the shared lean_binary fixture and test_lean_agrees discovery.

Freeze raw compact-plus-LF stdin/stdout/stderr/status and expected answers for
every request, with historical source hashes including the direct observers,
member fixtures, endpoint, IR/Json/JsonBounds and proto. Capture must reject an
existing output and changed original Json before children; hash sources again
after capture. Review all actual successful encoded replies via public protobuf.
After the baseline commit, compare its recorded hashes to historical git
objects, then separately compare current fixture identities. Never overwrite
or silently regenerate old evidence after kernel witnesses change test sources.

## Minimum proof-helper seam (after baseline only)

TableCodecLaws currently has private actual TreeMap lookup/omission lemmas.
Block has nine independently omitted/present fields; an exponential case split
would repeat precisely the cost already solved for Table. Proposed narrow
ownership expansion: move only the shared `fieldLookup`, nil/append facts,
`withoutNull`, `get_mkObj`, string/list lookup and string/array omission facts
into `P4bloIR.CodecObjectLaws`, under an explicitly internal helper namespace.
Keep Table-specific optional-action, Boolean/natural facts and all four public
Table laws/predicates in place, with only imports/qualified helper use changed.
Add a small enum-group lookup fact if Block needs it. Do not expose private
mangled names or change production Encode/Decode; no alternate object codec,
callback premise, broad serializer framework or raised limits.

The helper extraction must be independently reviewed and recheck all old
table/default audit roots. If actual proof cost does not require the extraction,
omit it; if a larger helper/API change is necessary, pause and report the
concrete obstruction before expanding scope. Confidence: medium-high in this
placement, revisited by the later eleven-field Program composition.

Root authorizes that narrow post-baseline extraction only if needed. Old table
fault bundles pin TableCodecLaws SHA
`d79eb9a3400e323e2384fd24d7dd93b292226a41671d75750f30fb863051bc1f`.
If extraction changes that proof file, verify the recorded bytes at historical
table-law commit `228b76b`, then separately verify the current reviewed helper/
Table sources and replay all unchanged inputs. Do not demand old proof bytes
equal the refactored current file, weaken source checks, relabel evidence or
edit captured artifacts. Root adapts the main replay recipe. Keep the helper
change a separately reviewed small commit, with all prior table/native/audit
gates rechecked before new Block proof work relies on it.

## Laws, nonvacuity and adversarial acceptance

After reviewed baseline commit, prove the actual two universal roundtrips at
every path, default-audit both and a constructive mixed Block witness with
exact standard-only axioms. Include all three kinds, all member lists and
directions, invalid-but-representable shapes and inherited overflow exclusions.
No native reduction axiom, successful-decoder callback or complete Program
claim. Both packages/default audits/native tests must pass before consumers.

Isolated actual compiling faults, never in the candidate:

1. One-sided Action body or Block action/state list loss/reversal; the actual
   universal law or independent ordered answers must reject it.
2. Swap parser/control entries in actual shared BlockKind.names. Encoder and
   decoder may remain coherent. Literal inputs and direct native constructor
   anchors must reject it; separately corrupt the Python expected kind and
   Lean descriptor to demonstrate false agreement still killed by native
   literal anchors. Deparser remains an explicit unchanged control.
3. Swap Block name/startState on both codec sides. Use asymmetric strings so
   successful roundtrip cannot substitute for correct decoded field meaning.
4. Change actual first-error order (for example kind before name, or body
   before startState) or a nested array index; exact competing-error answers
   must reject it, independent of representable-success roundtrips.
5. Change actual default behavior (for example drop a populated parser body
   because of its kind, or accept unspecified kind); independent permissive
   shape/default anchors must reject the semantic narrowing/extension.

For runtime campaigns compile actual Json and the endpoint/driver first,
record proof failure versus stronger-body-step failure versus native/Python
assertion mismatch separately, capture source-matched raw mismatches and
ordinary harness views, replay live, restore exact sources/rebuild and replay
against both clean endpoints. If actual shared packet preflight blocks, record
that setup failure honestly before using the existing direct-test-body runner;
do not relabel it normal packet DRT. Observations across faults are not distinct
inputs. Retain non-overwriting recipes and source identities in this note.

Required gates: both Lean packages/default audits/native suites; all old/new
codec tests; required real-Lean discovery; historical and live/restored exact
replays; scoped formatting/lint/types; independent read-only final review;
small fresh-helper coauthored commits, no push. Root owns combined full gates.
No Docker build or mutable oracle operation.

Confidence is high in actual codec/domain inspection and baseline boundaries,
medium-high in proof composition cost. Revisit only for a concrete member-law
or helper obstruction; preserve universality rather than replacing it with
a closed fixture callback. Excludes Export/Program/host entries, JSON text or
binary protobuf correctness, normalization completeness, resource limits,
semantic validation and call/parser/table execution or termination.

## Frozen independent baseline

The independent [acceptance-plan review](reviews/block-codec-next.md) is clear.
This stage contains only the six baseline-owned files; no BlockCodecLaws,
shared-helper extraction, public production export or new axiom audit exists
yet. Those follow a separately reviewed baseline commit.

The fixed inventory is **498 ordered unique requests**: **19 canonical cases**,
**384 exact errors**, **95 normalizations**; **114 successful outputs** in all.
Seven Action cases include every type family in all four directions, every
statement family and reverse-order controls. Twelve Block cases cover minimal,
start-only, fully populated and asymmetric reversed shapes for each of the
three kinds. The complete prior table/state canonical families appear inside
populated blocks. Errors are independently authored, including inherited
declaration/statement/table/state errors at a later index and nested Action
errors at actions[1]. No prior fixture inventory or expected answer changes.

The 28 new native anchors compare exact decoded constructors and every stored
field, including full mixed blocks of every kind, all directions in Actions,
Entry's default action and some-empty Table default, all three direct kind
observers, missing/null/unknown/numeric kinds, adjacent field ordering and
actions[1].params[1] at the empty diagnostic root. The codec endpoint self-test
now has **161** anchors; default IR tests have **595**.

Fresh-cache module and both-package/default audit/native builds exit 0:
`/tmp/p4blo-block-baseline-module-final.log`,
`/tmp/p4blo-block-baseline-lean.log`. Both packages were built before binary
consumers. New focused tests pass **518** (20 pure Python + 498 actual Lean)
in 15.09 seconds; all seven old codec files pass **1332** in 25.20 seconds.
Logs: `/tmp/p4blo-block-baseline-focused.log`,
`/tmp/p4blo-block-baseline-old-codecs.log`. Native endpoint self-test exits 0:
`/tmp/p4blo-block-baseline-native.log`. Scoped Ruff format/check, Pyright
(`/tmp/p4blo-block-baseline-types-final2.log`) and diff checks pass.
The full required/integration gate and deliberate faults remain obligations
of the post-baseline checkpoint, not claimed by this test-only stage.

Early development checks found Python invariant inferred-list types and two
mistyped native fixture statement labels plus an unavailable Except BEq
instance. Explicit list annotations/appends, actual apply/push labels and an
error-pattern comparison fixed these before the first successful native gate
and capture. These are development fixes, not deliberate fault detections.

### Immutable raw provenance

`.artifacts/codec/block-baseline.json` retains exact compact-plus-LF stdin,
stdout/stderr/status, independent expected answers and **18 source hashes**.
Capture additionally parses **114 actual successful encoded replies** through
public protobuf Program dump/load. The source-pinned, non-overwriting capture
exits 0 (`/tmp/p4blo-block-baseline-capture.log`): **3568250 bytes**, SHA-256
`910a517c0832f9ae2413577c18a774de51290c6e775bf4be07f8398796bef49e`.
Json is byte-identical to base `ca2f20f`, SHA
`0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`.

This exact recipe rejects changed original Json and an existing output before
children and rechecks all source hashes afterward. Run only in this reviewed
baseline checkout with its built endpoint; use a separate fresh checkout/path
to reconstruct evidence if the original file exists. Do not overwrite it or
run command metadata from artifacts:

```bash
P4BLO_BLOCK_ROOT=/Users/qobilidop/my/work/p4blo-block-codecs nix develop -c uv run python - <<'PY'
import hashlib, json, os, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_blocks import requests, protobuf_value, test_block_baseline_contract
from tests.test_codec_leaves import same_json
root = Path(os.environ['P4BLO_BLOCK_ROOT']).resolve()
old_json = '0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e'
assert hashlib.sha256((root / 'ir/P4bloIR/Json.lean').read_bytes()).hexdigest() == old_json
base = subprocess.run(['git', '-C', str(root), 'show', 'ca2f20f:ir/P4bloIR/Json.lean'], check=True, capture_output=True).stdout
assert hashlib.sha256(base).hexdigest() == old_json
out = root / '.artifacts/codec/block-baseline.json'
assert not out.exists(), 'never overwrite baseline evidence'
test_block_baseline_contract()
source_paths = ["ir/P4bloIR/IR.lean","ir/P4bloIR/Json.lean","ir/P4bloIR/JsonBounds.lean","ir/Tests/CodecLaws.lean","ir/Tests/DeclarationCodec.lean","ir/Tests/TableCodec.lean","ir/Tests/ParserCodec.lean","ir/Tests/BlockCodec.lean","ir/Tests/CodecLeaves.lean","ir/Tests/Main.lean","tests/test_codec_leaves.py","tests/test_codec_expr.py","tests/test_codec_stmt.py","tests/test_codec_declarations.py","tests/test_codec_tables.py","tests/test_codec_parser.py","tests/test_codec_blocks.py","ir/proto/p4blo/v0/p4blo.proto"]
sources = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths}
rows = []
for request, expected in requests():
    stdin = (json.dumps(request, separators=(',', ':')) + '\n').encode()
    run = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')], input=stdin, capture_output=True, timeout=10)
    assert run.returncode == 0 and run.stderr == b''
    actual = loads(run.stdout.decode())
    assert same_json(actual, expected), (request, run.stdout, expected)
    if 'encoded' in actual:
        _, canonical = protobuf_value(request['kind'], actual['encoded'])
        assert same_json(canonical, actual['encoded'])
    rows.append({'request': request, 'expected': expected, 'stdin': stdin.decode(), 'stdout': run.stdout.decode(), 'stderr': run.stderr.decode(), 'returncode': run.returncode})
assert len(rows) == 498
assert sources == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths}
artifact = {'format': 'p4blo.block-codec.baseline.v0', 'production_base': 'ca2f20f', 'sources': sources, 'rows': rows}
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('x') as stream:
    stream.write(json.dumps(artifact, indent=2) + '\n')
print('rows', len(rows), 'successes', sum('encoded' in r['expected'] for r in rows))
print('bytes', out.stat().st_size, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest())
print(json.dumps(sources, indent=2))
PY
```

Pin recorded source identities to the eventual reviewed baseline commit.
Later kernel witness additions may legitimately change Tests.BlockCodec;
compare old hashes to historical git objects and current request/expected
pairs separately. Existing prior frozen inventories and artifacts stay intact.

Independent [baseline review](reviews/block-codec-baseline.md) is clear:
518 focused checks, 161 native anchors, all 498 ordered exact transcripts,
114 actual protobuf outputs and all eighteen source identities checked. No
candidate consumers remain; this baseline is committed before proof/helper work.

## Separately checked object-helper extraction

The baseline was committed as `6b9ffd0fde484cf995bfb18862c7fbbc62bbf38f` before
this proof-only change. The shared nine definitions move into the internal
`P4bloIR.CodecObject` namespace in CodecObjectLaws, importing actual Json and
standard TreeMap/list facts. Table keeps its specialized optional-action,
Boolean and natural helpers. All four public theorem statements/predicates
stay unchanged. There is no Json/runtime/schema/observer/fixture edit.

Moving the first Option matcher to another module splits Lean's generated
matcher sharing. The initial Table rewrite therefore failed in its private
body proof (`/tmp/p4blo-block-helper-core.log`); unfolding the remaining local
`optional_action.match_1` alongside the moved matcher restores the same proof.
This is elaboration plumbing, not a codec behavior change or a deliberate
semantic fault. Final old Table laws and CodecProofAudit build 0
(`/tmp/p4blo-block-helper-core-final.log`).

A pinned standalone stdin probe demonstrates the actual nine-field reuse,
without importing private mangled names, splitting all field-presence choices
or raising limits. It kernel-checks actual Block.toJson name lookup and prints
exact standard-only axioms, exit 0 (`/tmp/p4blo-block-helper-probe.log`).
This is not yet the promised Action/Block roundtrip:

```lean
import P4bloIR.CodecObjectLaws
open Lean P4bloIR P4bloIR.CodecObject
private theorem lookup_enum (key name value : String) :
    fieldLookup key (Encode.ofEnum name value) =
      if compare name key = .eq then some (.str value) else none := by
  simp [fieldLookup, Encode.ofEnum]
theorem block_name (path : String) (b : Block) :
    Decode.get? path b.toJson "name" =
      .ok (if b.name.isEmpty then none else some (.str b.name)) := by
  cases b with | mk name kind params locals actions tables states start body =>
    simp only [Block.toJson, Encode.obj, get_mkObj, List.flatten_cons, List.flatten_nil,
      fieldLookup_append, fieldLookup_nil, lookup_str, lookup_list, lookup_enum]
    simp
    by_cases empty : name = ""
    · simp [empty, withoutNull]
    · simp [empty, withoutNull]
#print axioms block_name
```

Run with `nix develop -c lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true --stdin`
from the worktree's ir directory. No probe source is left in proposed commits.

Both Lean packages/default audits/native tests pass, **595 spec checks**,
before consumers (`/tmp/p4blo-block-helper-lean.log`). Scoped Table+Block tests
pass **753** in 15.95 seconds (`/tmp/p4blo-block-helper-focused.log`), and all
**161** codec native anchors pass (`/tmp/p4blo-block-helper-native.log`).
The historical replay below exits 0 (`/tmp/p4blo-block-helper-replay.log`):
all **181** old table baseline rows and **56** retained fault observations
agree byte-for-byte with the new clean endpoint. It explicitly checks the old
fault proof hash at `228b76b`, not against changed current proof bytes, and
compares all four public statements before replay. The old artifacts are read
only; old mutant Json identities remain those in their independently reviewed
table evidence.

Current proof-only source identities:

- TableCodecLaws: `323cff1035971abcbf85a40c755857109de2d15765a262a7524821d1604655ab`
- CodecObjectLaws: `5f3061a319308e42ada1398b2d54a6c5559e90aeb90231059091526d9d768bea`

For integrator replay, replace the old/current TableCodecLaws equality check
with the explicit historical `228b76b` assertion, retain the other historical
layers, and separately attest these reviewed current helper/proof identities.
Do not alter the old artifact or conflate proof-only relocation with a different
codec execution. Exact read-only recipe, run from the Block candidate using
`nix develop -c uv run python -` (adjust only the old artifact location if
the integrator's ignored copy is used):

```python
import hashlib, json, re, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_tables import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-block-codecs')
old_tree = Path('/Users/qobilidop/my/work/p4blo-table-codec')
proof_path = 'ir/P4bloIR/TableCodecLaws.lean'
historical = subprocess.run(['git','-C',str(root),'show','228b76b:' + proof_path],check=True,capture_output=True).stdout
assert hashlib.sha256(historical).hexdigest() == 'd79eb9a3400e323e2384fd24d7dd93b292226a41671d75750f30fb863051bc1f'
current = (root / proof_path).read_text()
for name in ['key_roundtrip','actionCall_roundtrip','entry_roundtrip','table_roundtrip']:
    pattern = r'theorem ' + name + r'\b[\s\S]*?:= by'
    assert re.search(pattern,historical.decode()).group() == re.search(pattern,current).group()
base = loads((old_tree / '.artifacts/codec/table-baseline.json').read_text())
fixtures = requests()
assert len(fixtures) == len(base['rows']) == 181
answers = {json.dumps(r,sort_keys=True): e for r,e in fixtures}
old_rows = {json.dumps(r['request'],sort_keys=True): r for r in base['rows']}
for path, digest in base['sources'].items():
    old = subprocess.run(['git','-C',str(root),'show','9640523:' + path],check=True,capture_output=True).stdout
    assert hashlib.sha256(old).hexdigest() == digest
for (request, expected), row in zip(fixtures,base['rows'],strict=True):
    assert same_json(request,row['request']) and same_json(expected,row['expected'])
    result = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')],input=row['stdin'],text=True,capture_output=True,timeout=10)
    assert (result.returncode,result.stdout,result.stderr) == (0,row['stdout'],'')
count = 0
for name in ['kind','flag','order','default']:
    artifact = loads((old_tree / '.artifacts/codec/table-campaign' / name / 'live-raw.json').read_text())
    assert artifact['sources'][proof_path] == hashlib.sha256(historical).hexdigest()
    for row in artifact['rows']:
        key = json.dumps(row['request'],sort_keys=True)
        assert same_json(row['expected'],answers[key])
        assert row['returncode'] == 0 and row['stderr'] == ''
        assert same_json(loads(row['stdout']),row['actual'])
        assert not same_json(row['actual'],row['expected'])
        result = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')],input=row['stdin'],text=True,capture_output=True,timeout=10)
        assert (result.returncode,result.stdout,result.stderr) == (0,old_rows[key]['stdout'],'')
        count += 1
assert count == 56
print('four public table statements unchanged; 181 historical rows and 56 fault observations replay clean')
for path in [proof_path,'ir/P4bloIR/CodecObjectLaws.lean']:
    print(path,hashlib.sha256((root / path).read_bytes()).hexdigest())
```

Independent [helper review](reviews/codec-object-helpers.md) is clear: exact
comparison of all nine moved definitions/proofs and four public statements,
753 focused checks, 161 native anchors, four fresh standard-only Table audit
queries, actual Block lookup probe and 181/56 historical replays all pass.
No binary consumers remain before the separate helper commit.
