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

## Integrated baseline replay

Run after both main Lean packages finish building, never concurrently with a
rebuild. The ignored baseline copy is byte-identical to the original; recorded
sources use the baseline commit, while current proof-only helper identities
are checked separately. This reads artifacts and never executes their metadata.

```sh
nix develop -c uv run python - <<'PY'
import hashlib,json,subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_blocks import requests,protobuf_value
from tests.test_codec_leaves import same_json
root=Path('/Users/qobilidop/my/work/p4blo')
data=(root/'.artifacts/codec/block-baseline.json').read_bytes()
assert len(data)==3568250 and hashlib.sha256(data).hexdigest()=='910a517c0832f9ae2413577c18a774de51290c6e775bf4be07f8398796bef49e'
baseline=loads(data.decode())
fixtures=requests()
assert len(fixtures)==len(baseline['rows'])==498 and len(baseline['sources'])==18
for path,digest in baseline['sources'].items():
 source=subprocess.run(['git','-C',str(root),'show','6b9ffd0:'+path],check=True,capture_output=True).stdout
 assert hashlib.sha256(source).hexdigest()==digest,path
successes=0
for (request,expected),row in zip(fixtures,baseline['rows'],strict=True):
 assert same_json(request,row['request']) and same_json(expected,row['expected'])
 assert row['stdin']==json.dumps(request,separators=(',',':'))+'\n'
 result=subprocess.run([str(root/'ir/.lake/build/bin/codec-leaves')],input=row['stdin'],text=True,capture_output=True,timeout=10)
 assert (result.returncode,result.stdout,result.stderr)==(row['returncode'],row['stdout'],row['stderr'])==(0,row['stdout'],'')
 actual=loads(result.stdout)
 assert same_json(actual,expected)
 if 'encoded' in actual:
  _,canonical=protobuf_value(request['kind'],actual['encoded'])
  assert same_json(canonical,actual['encoded'])
  successes+=1
assert successes==114
for path,digest in {'ir/P4bloIR/TableCodecLaws.lean':'323cff1035971abcbf85a40c755857109de2d15765a262a7524821d1604655ab','ir/P4bloIR/CodecObjectLaws.lean':'5f3061a319308e42ada1398b2d54a6c5559e90aeb90231059091526d9d768bea'}.items():
 assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
print('498 exact baseline rows; 114 actual protobuf successes; 18 historical identities; reviewed current helper identities')
PY
```

## Universal Action/Block laws

After baseline `6b9ffd0` and independently reviewed helper `707fb3f`,
BlockCodecLaws composes the actual two total codecs with existing member and
ordered-array laws. ActionRepresentable is exactly its two member lists;
BlockRepresentable is exactly its six member lists. Kind, name, startState,
direction, arity, uniqueness and semantic field combinations add no premise.
All paths are arbitrary. No new interpreter/decoder, successful-codec callback,
resource assumption or increased proof limit is used.

The two advertised laws and the forall-kind mixed Block witness are default
audited for exactly propext/Classical.choice/Quot.sound. The witness includes
all four directions, duplicated/empty/unresolved names, all Block fields, all
three Table default variants, const flags, nested State/Stmt bodies, zero/max
bounds and unbounded decimal values. Twenty kernel exclusions propagate type,
literal, slice, stack/count, LPM prefix, priority and table-size bounds through
every Block member family. They impose no extra semantic validity restriction.
The 28 baseline native anchors and all 498 request/expected pairs are unchanged.

The law module builds in 468ms, and witness/default audits build 0:
`/tmp/p4blo-block-laws-module-final.log`,
`/tmp/p4blo-block-laws-witness.log`. Initial proof development found one
redundant final rfl after a successful rewrite; removing that finished the goal.
This is not fault evidence.

Both full Lean packages/default audits/native suites pass **595** spec checks
before consumers (`/tmp/p4blo-block-laws-lean.log`). All eight codec files pass
**1850** tests in 40.22 seconds (`/tmp/p4blo-block-laws-focused.log`).
The required `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees -q`
gate passes **2304 / 1800 deselected**, exit 0 in 158.32 seconds
(`/tmp/p4blo-block-laws-required.log`). Scoped Ruff and Pyright pass
(`/tmp/p4blo-block-laws-lint.log`, `/tmp/p4blo-block-laws-types.log`).
Root owns the combined full integration gate.

## Actual compiling fault campaign

All faults ran only in the fresh isolated tree
`/Users/qobilidop/my/work/p4blo-block-codecs-faults`, branch
`work/block-codecs-faults`, based on reviewed helper `707fb3f`.
The unchanged candidate BlockCodecLaws file was added there for explicit proof
checks. During faults the endpoint/public root/audits/native tests retained
their committed baseline layer at that commit: a failed new proof did not
prevent building the actual codec endpoint. No proof was disabled or repaired.
After the faults the candidate witness/export/audit additions were copied
exactly, all sources restored, and the complete restored targets built.

Each mutation below changed the actual production Json source, compiled that
module successfully, then checked the unchanged new law separately. Runtime
campaigns also compiled both codec endpoint and packet driver before tests.
All other runtime sources stayed untouched. Log prefix below is
`/tmp/p4blo-block-fault-`; suffixes name exact retained logs.

| Fault | Unchanged new proof | Runtime evidence |
| --- | --- | --- |
| Action encoder reverses body | Rejects ordered-array goal | Proof-only; no runtime mismatch claimed |
| Shared parser/control enum table swap | Both laws still pass | 70 ordinary focused mismatches, 4 native failures |
| Paired Block name/startState reads and writes | Stronger path-sensitive proof step rejects; closed all-kind roundtrip still holds | Packet preflight blocks; direct unchanged codec bodies give 12 mismatches, native gives 5 |
| Block kind read before name | Both laws still pass | 2 ordinary focused error mismatches, 1 native failure |
| Absent/null kind defaults to parser | Both laws still pass | 2 ordinary focused error mismatches, 2 native failures |

The reverse fault compiles actual Json (`reverse-json.log`, exit 0), then
fails the actual Action law's ordered array goal (`reverse-proof.log`,
exit 1). It is not a parser/build failure and is not runtime evidence.

For kind, `kind-json.log` and `kind-build.log` exit 0 (the latter includes
both unchanged laws and both executables). `kind-pytest.log` exits 1 with
**70 failed / 448 passed**; `kind-native.log` exits 1 with four failed
literal-constructor/all-field anchors. `kind-capture.log` exits 0 after
capturing and exactly replaying the 70 genuine live mismatches.

For names, `names-json.log` exits 0; `names-proof.log` exits 1 at the
path-sensitive `hn` rewrite: the expected `path.name` read is now
`path.start_state`. This is a stronger intermediate-proof sensitivity, not
a demonstration that every successful roundtrip is false. The following
unregistered stdin kernel probe compiles, for all three kinds, with the
mutant actual codec (`names-coherence.log`, exit 0):

```lean
import P4bloIR.Json
open P4bloIR
example (kind : BlockKind) :
    Block.decode "" (Block.mk "left" kind [] [] [] [] [] "right" []).toJson =
      .ok (Block.mk "left" kind [] [] [] [] [] "right" []) := by cases kind <;> rfl
```

Run that probe from the fault tree's `ir` working directory with
`nix develop -c lake +leanprover/lean4:v4.34.0 env lean -DwarningAsError=true --stdin`.
It is a closed asymmetric string/list witness, not a universal mutant law.

After `names-build.log` exits 0, ordinary `names-pytest.log` exits 1:
**20 passed / 498 setup errors**. The real shared packet preflight fails with
`error: empty name in program`; no actual codec test body ran through that
pytest invocation. Only then did `names-direct.log` invoke the unchanged
518 scoped test bodies directly through the existing harness: **12 fail /
506 pass**, exit 1. Failed labels are known-8/9/10/12/13/14/16/17/18 and
error-11/58/64. `names-native.log` has five failed independent anchors.
This direct runner is codec known-answer checking, not normal pytest or
packet DRT. Its exact body is below; run from the fault repository with
`nix develop -c uv run python -` and set
`P4BLO_CODEC_FAILURE_DIR=/Users/qobilidop/my/work/p4blo-block-codecs/.artifacts/codec/block-campaign/names/harness`.

```python
from functools import partial
from pathlib import Path
from tests import test_codec_blocks as t
binary = Path('/Users/qobilidop/my/work/p4blo-block-codecs-faults/ir/.lake/build/bin/p4blo-lean')
checks = [('contract', t.test_block_baseline_contract)]
for i, case in enumerate(t.cases()):
    checks += [(f'protobuf-{i}', partial(t.test_block_protobuf_known_answers, case)),
               (f'known-{i}', partial(t.test_lean_agrees_block_known_answers, binary, case))]
for i, (kind, wire, error) in enumerate(t.malformed()):
    checks.append((f'error-{i}', partial(t.test_lean_agrees_block_exact_errors, binary, kind, wire, error)))
for i, (kind, wire, case) in enumerate(t.normalized()):
    checks.append((f'normal-{i}', partial(t.test_lean_agrees_block_normalization, binary, kind, wire, case)))
assert len(checks) == 518
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

For order/default, each `*-json.log`, `*-proof.log`, `*-build.log`
exits 0. Ordinary `order-pytest.log` gives **2 failed / 516 passed** in
14.10 seconds; `default-pytest.log` gives **2 failed / 516 passed** in
13.76 seconds. Their native logs exit 1 with one and two failed anchors.
Their capture logs exit 0 after exact live replay. These explicitly show
why a representable-success roundtrip is not an error/default compatibility
theorem.

### Paired observer challenges

While the actual shared kind fault was active, the Python `record` helper's
single `value[key] = child` line was replaced with:

```python
            value[key] = ({"BLOCK_KIND_PARSER": "BLOCK_KIND_CONTROL",
                           "BLOCK_KIND_CONTROL": "BLOCK_KIND_PARSER"}.get(child, child)
                          if key == "kind" else child)
```

The faulty Python file SHA was
`3a5d40f43e2ebccaf13681e0459cdcd68f5c301c636f682d532bd4e975638d3f`.
Ordinary `kind-paired-python.log` then misleadingly passes all **518**
checks (12.56 seconds, exit 0), while `kind-paired-python-native.log`
still fails the four independent literal/all-field anchors. Python was
restored before the next challenge.

Separately, with Python clean and the actual kind fault still active, the
Lean descriptor's direct `kindValue` branches were swapped:

```lean
  | .parser => "BLOCK_KIND_CONTROL"
  | .control => "BLOCK_KIND_PARSER"
```

The faulty baseline-layer native file SHA was
`5b32ef4b5fb4bac363ef44ee877e6d5d7c8bd4d35a5d00d2c656de8b504fbb06`.
The actual endpoint rebuilt (`kind-paired-observer-build.log`, exit 0).
Ordinary `kind-paired-observer.log` misleadingly passes **518** checks
(11.98 seconds), while `kind-paired-observer-native.log` fails **six**
independent literal/all-field/direct-observer anchors. No new raw mismatch
artifact is claimed for these false-assurance runs. Both paired observers
were restored exactly before the names/order/default campaigns.

### Exact patch reconstruction and execution

The following read-only reconstruction starts from the restored actual Json,
asserts every unique source anchor and verifies the four recorded mutant
source hashes. It also prints the proof-only reverse source identity.
It never edits production or existing artifacts. Run from the candidate with
`nix develop -c uv run python -`; result is
`/tmp/p4blo-block-fault-reconstruct.log`, exit 0.

```python
import hashlib, json
from pathlib import Path
from p4blo.drt._json import loads
root = Path('/Users/qobilidop/my/work/p4blo-block-codecs')
clean = (root / 'ir/P4bloIR/Json.lean').read_text()
assert hashlib.sha256(clean.encode()).hexdigest() == '0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e'
patches = {
  "reverse": [
    [
      "def Action.toJson (a : Action) : Json :=\n  obj [ofStr \"name\" a.name, ofList \"params\" (a.params.map Param.toJson),\n       ofList \"body\" (a.body.map Stmt.toJson)]",
      "def Action.toJson (a : Action) : Json :=\n  obj [ofStr \"name\" a.name, ofList \"params\" (a.params.map Param.toJson),\n       ofList \"body\" (a.body.reverse.map Stmt.toJson)]"
    ]
  ],
  "kind": [
    [
      "[(\"BLOCK_KIND_PARSER\", .parser), (\"BLOCK_KIND_CONTROL\", .control),\n   (\"BLOCK_KIND_DEPARSER\", .deparser)]",
      "[(\"BLOCK_KIND_PARSER\", .control), (\"BLOCK_KIND_CONTROL\", .parser),\n   (\"BLOCK_KIND_DEPARSER\", .deparser)]"
    ]
  ],
  "names": [
    [
      "def Block.decode (path : String) (j : Json) : Dec Block := do\n  pure { name := ← strField path j \"name\", kind := ← enumField path j \"kind\" BlockKind.names,",
      "def Block.decode (path : String) (j : Json) : Dec Block := do\n  pure { name := ← strField path j \"start_state\", kind := ← enumField path j \"kind\" BlockKind.names,"
    ],
    [
      "startState := ← strField path j \"start_state\",",
      "startState := ← strField path j \"name\","
    ],
    [
      "def Block.toJson (b : Block) : Json :=\n  obj [ofStr \"name\" b.name, ofEnum \"kind\" b.kind.protoName,",
      "def Block.toJson (b : Block) : Json :=\n  obj [ofStr \"name\" b.startState, ofEnum \"kind\" b.kind.protoName,"
    ],
    [
      "ofList \"states\" (b.states.map State.toJson), ofStr \"start_state\" b.startState,",
      "ofList \"states\" (b.states.map State.toJson), ofStr \"start_state\" b.name,"
    ]
  ],
  "order": [
    [
      "def Block.decode (path : String) (j : Json) : Dec Block := do\n  pure { name := ← strField path j \"name\", kind := ← enumField path j \"kind\" BlockKind.names,",
      "def Block.decode (path : String) (j : Json) : Dec Block := do\n  pure { kind := ← enumField path j \"kind\" BlockKind.names,\n         name := ← strField path j \"name\","
    ]
  ],
  "default": [
    [
      "def Block.decode (path : String) (j : Json) : Dec Block := do\n  pure { name := ← strField path j \"name\", kind := ← enumField path j \"kind\" BlockKind.names,",
      "def Block.decode (path : String) (j : Json) : Dec Block := do\n  pure { name := ← strField path j \"name\",\n         kind := ← (do\n           match ← get? path j \"kind\" with\n           | none => pure .parser\n           | some _ => enumField path j \"kind\" BlockKind.names),"
    ]
  ]
}
for name, replacements in patches.items():
    mutant = clean
    for before, after in replacements:
        assert mutant.count(before) == 1
        mutant = mutant.replace(before, after)
    digest = hashlib.sha256(mutant.encode()).hexdigest()
    if name != 'reverse':
        artifact = loads((root / '.artifacts/codec/block-campaign' / name / 'live-raw.json').read_text())
        assert artifact['sources']['ir/P4bloIR/Json.lean'] == digest
    print(name, digest)
```

To reproduce in a new isolated tree based on `707fb3f`, add the reviewed
BlockCodecLaws file, apply exactly one reconstructed patch with an anchored
edit, and run these commands with working directory `<fault-tree>/ir`
(restore/rebuild between faults):

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.Json
nix develop -c lake +leanprover/lean4:v4.34.0 build P4bloIR.BlockCodecLaws
nix develop -c lake +leanprover/lean4:v4.34.0 build codec-leaves p4blo-ir
```

The first two commands must be checked separately; for names/reverse the
second is deliberately nonzero. No runtime claim attaches to reverse.
With the repository as working directory, run the scoped ordinary gate:

```sh
P4BLO_REQUIRE_LEAN=1 P4BLO_CODEC_FAILURE_DIR=<new-output-folder>/harness nix develop -c uv run pytest tests/test_codec_blocks.py -q
<fault-tree>/ir/.lake/build/bin/codec-leaves --self-test
```

Only if actual packet preflight blocks use the explicitly distinguished
direct runner above. Capture from the candidate working directory using
`P4BLO_BLOCK_CAMPAIGN=<kind|names|order|default> nix develop -c uv run python -`
and the following script. Its output path must not already exist; use a new
isolated output root for repetition, never overwrite retained evidence.
The original paths below document the actual run.

```python
import hashlib, json, os, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_blocks import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-block-codecs')
fault = Path('/Users/qobilidop/my/work/p4blo-block-codecs-faults')
name = os.environ['P4BLO_BLOCK_CAMPAIGN']
baseline = loads((root / '.artifacts/codec/block-baseline.json').read_text())
fixtures = requests()
assert len(fixtures) == len(baseline['rows']) == 498
for (request, expected), old in zip(fixtures, baseline['rows'], strict=True):
    assert same_json(request, old['request']) and same_json(expected, old['expected'])
out = root / '.artifacts/codec/block-campaign' / name / 'live-raw.json'
assert not out.exists(), 'never overwrite live evidence'
source_paths = ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/BlockCodecLaws.lean', 'ir/P4bloIR/TableCodecLaws.lean', 'ir/P4bloIR/CodecObjectLaws.lean', 'ir/Tests/BlockCodec.lean', 'tests/test_codec_blocks.py', 'ir/P4bloIR.lean', 'ir/CodecProofAudit.lean']
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
out = root / '.artifacts/codec/block-campaign' / name / 'live-raw.json'
out.parent.mkdir(parents=True, exist_ok=True)
artifact = {'format': 'p4blo.block-codec.campaign.v0', 'campaign': name, 'baseline_commit': '6b9ffd0fde484cf995bfb18862c7fbbc62bbf38f', 'proof_base': '707fb3fc897a7ef96483b0a3eec36c4ebfdcc9eb', 'sources': sources, 'rows': rows}
with out.open('x') as stream:
    stream.write(json.dumps(artifact, indent=2) + '\n')
for row in rows:
    replay = subprocess.run([str(fault / 'ir/.lake/build/bin/codec-leaves')], input=row['stdin'], text=True, capture_output=True, timeout=10)
    assert (replay.returncode, replay.stdout, replay.stderr) == (row['returncode'], row['stdout'], row['stderr'])
print(name, 'live raw mismatches', len(rows), 'bytes', out.stat().st_size, 'sha256', hashlib.sha256(out.read_bytes()).hexdigest())
```

### Immutable live artifact inventory

All paths are relative to the candidate. Baseline remains the original
498-row file/hash above. Four bundles retain **86 live observations**;
overlap between campaigns is not counted as new input coverage.

| Bundle under `.artifacts/codec/block-campaign/` | Rows | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `kind/live-raw.json` | 70 | 3002960 | `78d05d6625b519bc4f7062b0c1b852a931824a729ee86ce9476ae0ce7b7cba6b` |
| `names/live-raw.json` | 12 | 4325111 | `40f0d5d283e4a4a10ff4e69224e42da0ed2fbb3bd3a9cd88a75a2f34dbc77981` |
| `order/live-raw.json` | 2 | 1970 | `9be73ebf8690bca5a5f7561476f9fd10bf6260b29cb6fc7fd820995781b655f9` |
| `default/live-raw.json` | 2 | 2761 | `1efa5687a7a802bb8656642d41de03b9e038a527f9836cb7f88d36a53b9f3ed2` |

Every row has one ordinary harness view under its campaign's `harness/`,
including the names direct-body views. The deterministic name is
`leaf-` + SHA-256(`json.dumps(request, sort_keys=True)`)[:24] + `.json`.
The replay below verifies all 86 names and five view fields and prints each
complete relative path/hash: that is the reconstructible inventory, not a
claim that temporary files alone are handoff documentation.

### Restoration and replay

Both actual Json and all observer changes are restored. After copying the
candidate's exact witness/export/audit additions, the fault tree builds
`P4bloIR.BlockCodecLaws CodecProofAudit codec-leaves p4blo-ir`, exit 0
(`/tmp/p4blo-block-fault-restored-build.log`). Restored focused/native
checks pass (518/161; `...-restored-focused.log`, `...-restored-native.log`).
The replay below verifies all historical sources at baseline `6b9ffd0`,
all current request/expected identities, all successful actual encoded
answers through the public protobuf adapter, both endpoints' exact baseline
bytes and both endpoints' clean answers to every live mismatch.

Campaign source layers are explicit: actual mutant Json is reconstructed;
new BlockCodecLaws is the unchanged reviewed candidate; other campaign
sources are pinned to helper/baseline `707fb3f`. The current native witness
and public/audit registrations legitimately differ from their old layers.
Neither old source identity nor frozen fixture answers are relabeled.
The helper-only historical Table drift remains handled as documented above.

Run from the candidate with `nix develop -c uv run python -`:

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_blocks import requests, protobuf_value
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-block-codecs')
fault = Path('/Users/qobilidop/my/work/p4blo-block-codecs-faults')
baseline_commit = '6b9ffd0fde484cf995bfb18862c7fbbc62bbf38f'
baseline = loads((root / '.artifacts/codec/block-baseline.json').read_text())
fixtures = requests()
assert len(fixtures) == len(baseline['rows']) == 498
key = lambda value: json.dumps(value, sort_keys=True)
expected = {key(request): answer for request, answer in fixtures}
old_rows = {key(row['request']): row for row in baseline['rows']}
assert len(expected) == len(old_rows) == 498
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
print('historical source hashes and both endpoints: 498 exact baseline rows, 114 public protobuf successes')
seen, count = set(), 0
for name in ['kind', 'names', 'order', 'default']:
    folder = root / '.artifacts/codec/block-campaign' / name
    data = (folder / 'live-raw.json').read_bytes()
    artifact = loads(data.decode())
    assert artifact['baseline_commit'] == baseline_commit and artifact['campaign'] == name
    assert artifact['proof_base'] == '707fb3fc897a7ef96483b0a3eec36c4ebfdcc9eb'
    assert artifact['sources']['ir/P4bloIR/BlockCodecLaws.lean'] == hashlib.sha256((root / 'ir/P4bloIR/BlockCodecLaws.lean').read_bytes()).hexdigest()
    for path, digest in artifact['sources'].items():
        if path not in ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/BlockCodecLaws.lean']:
            old = subprocess.run(['git', '-C', str(root), 'show', '707fb3fc897a7ef96483b0a3eec36c4ebfdcc9eb:' + path], check=True, capture_output=True).stdout
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
for path in ['ir/P4bloIR/Json.lean', 'ir/P4bloIR/BlockCodecLaws.lean', 'ir/P4bloIR/TableCodecLaws.lean', 'ir/P4bloIR/CodecObjectLaws.lean', 'ir/Tests/BlockCodec.lean', 'tests/test_codec_blocks.py', 'ir/P4bloIR.lean', 'ir/CodecProofAudit.lean']:
    assert (root / path).read_bytes() == (fault / path).read_bytes(), path
    print('restored', path, hashlib.sha256((root / path).read_bytes()).hexdigest())
print('live observations', count, 'distinct requests', len(seen), 'both restored endpoints agree')
```

The replay exits 0 (`/tmp/p4blo-block-fault-restored-replay.log`):
**498 exact baseline rows, 114 actual protobuf successes, 86 live observations
over 78 distinct requests, 86 matching views**, both restored endpoints.
All eight restored source pairs match byte-for-byte; production Json remains
`0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`,
and reviewed BlockCodecLaws is
`cdcdfe822bc1885032cea89eef862d1298546d471c6e3c8acf59597014a12736`.
No intentional fault remains. An initial order-native invocation omitted
`--self-test` and merely consumed EOF; it is not counted. The retained
order-native result is the subsequent actual self-test failure.

Confidence is high for these two wire-only laws and this finite independent
compatibility matrix. Revisit if Json object/default/enum/array behavior or
member representability changes; rerun proofs and independent anchors, not
only a roundtrip. This does not establish semantic validation, resource
bounds, arbitrary-input total correctness of the encoders' inverse direction,
full Program roundtrip, or host-entry codec laws. Export/Program composition
remains the next separate baseline-first slice. Root owns integrated full
gates and any shared status/decision changes.

The independent [Action/Block review](reviews/block-codec.md) is CLEAR.
Independent candidate checks passed 518 focused, 161 native, three exact
standard-only audits and all 498 historical rows. The reviewer separately
reconstructed all five actual Json edits and both paired observer hashes,
verified all 86 views and historical source layers, replayed baseline/live
rows against both restored endpoints, and checked all eight restored source
pairs. No active consumers or rebuilds remain before the scoped commits.

## Main integration

Integrated the three reviewed commits at `7bfdcca`, preserving the separate
main baseline replay recipe above. Both Lean package gates/default audits
pass with 595 spec checks. Required real-Lean conformance passes 2700 tests
without skips. The combined full Python/schema gate also exits 0: 4512 passed,
five strict expected discrepancies and the one explicit missing-local-XDP
skip; formatting, lint, types, generated-code drift and workflow checks pass.
Main copies of the four live bundles are byte-identical to
the inventory above; all 498 baseline rows, 114 public protobuf successes
and 86 source-matched observations (78 distinct requests) replay against main
and the restored fault endpoint. Use the restoration recipe with `root` set
to the main checkout for this check. Actual source pairs remain identical.

The older Table/Parser replays retain their historical source layers while
checking the new public/audit registrations separately at `b0c31425`; those
reviewed additions do not rewrite historical evidence. Their full replays
also pass. The finite milestone does not require replaying all historical
experiments from their old worktrees; its selected clean-checkout command is
a separate closeout deliverable. No Export/Program or host-entry proof follows
from these Action/Block laws.
