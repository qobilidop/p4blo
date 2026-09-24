# Milestone 1: whole-program interchange

2026-09-23. Baseline `7bfdcca`. This finite checkpoint follows
`milestone-1.md`, not the older open-ended proof ladder. Production codecs,
validator, host installation and interpreters remain unchanged unless a
demonstrated defect requires a separately reviewed fix.

## Acceptance plan

Two independent test modules cover Export/Program and TableEntries/Entries.
The test endpoint adds only `export`, `program`, `table_entries`, `entries`;
all existing labels and request inventories remain unchanged. Complete native
descriptors read the actual decoded records, using existing independent member
descriptors, not production encoders or a second decoder. Python builds literal
wire/expected pairs; strict JSON comparison distinguishes Boolean from integer.

Program covers all eleven fields in actual order: name, errors, header_types,
struct_types, enum_types, extern_types, extern_instances, blocks, headers,
metadata, exports. Export observes role and block separately. Host entries
observe every ordered table record's block/table/entries/default_action and
distinguish absent/null from present-empty ActionCall. Three-element asymmetric
lists and unrelated strings constrain loss, order and equal-shaped slot swaps.
Empty/duplicate/unresolved names, non-core error lists and invalid semantic
shapes remain representable wire data; no validator premise enters codec tests.

Canonical successes pass actual public `ir.load_json`/`ir.dump_json` Program
conversion, including the Export wrapper. Entries use the actual protobuf
`Entries` JSON adapter, not a fictional Program field. Canonical protobuf
interchange is separate from arbitrary JSON: unknown annotations/null defaults,
malformed types, enum numbers, noncanonical decimals and error order need not
have identical acceptance across Lean and ProtoJSON. Tests identify this
boundary explicitly rather than normalize a mismatch away.

The finite matrix includes omitted/null/empty repeated/string fields, present
optional empty defaults, wrong-type top-level/field/list elements, later/nested
indices, adjacent competing errors and empty-root paths. Numeric boundaries
are inherited only: uint32 type width/stack size, literal width, Expr slices,
Stmt counts, KeyValue prefix, Entry priority and Table size. Zero/max positives
and overflow negatives reach each member family; arbitrary natural decimal
values remain unbounded wire data. Existing exhaustive member matrices remain
their own evidence, not duplicated wholesale as new independent cases.

Freeze ordered unique requests and independently expected answers, source
hashes and raw stdin/stdout/stderr/status before optional proof work or faults.
Capture refuses overwrites and checks source identities before/after execution.
Historical replay uses the baseline commit's source objects and separately
checks current request/answer identity. No old artifact is altered.

## Pre-execution rejection boundary

Use a small validated stateful program with asymmetric persistent cells and
packet outputs. A valid/rejected/valid sequence must preserve the full state
at rejection and resume with exactly the next expected write. Cover actual
request decoding errors and installation failures (unknown target, wrong key
kind/width/prefix/priority, action/default mismatch, duplicate entries and a
later error after an otherwise acceptable earlier host entry).

Python exercises actual public protobuf decoding, `arch.load`, `Loaded.entries`
and the production run path. Detached snapshots include program/index content,
extern cells and an independently installed configuration; packet-entry spies
must remain unused on rejected load/install attempts. Program validation failure
is a startup boundary, not a packet request or replacement of a running program.
Assert the actual validator/loader failure and no extern binding/packet call.

Lean exercises the actual CLI startup and persistent request server plus native
`Switch.run` installation-before-parser trap controls. A pure Except error
alone cannot reveal discarded intermediate work: state transcript and explicit
first-error/trap controls are finite evidence, not a universal no-execution or
rollback theorem. Do not claim Python and Lean validators accept exactly the
same arbitrary program language. No transactional runtime-error rollback claim.

## Finite sensitivity and gates

After independent baseline review, use just two scoped actual faults: a paired
Program headers/metadata mapping and a Python host-boundary state/early-execution
fault. Independent literal constructor anchors must reject the first, and the
strengthened no-mutation/entry observer must reject the second. Existing reviewed
Block campaigns already exercise the paired-observer/default/error-order fault
patterns; do not repeat that entire ladder for counts. Retain precise source
recipes and distinguish direct state observation from generic packet DRT replay.
Any survivor is investigated before claiming coverage. Noncompiling edits are
setup failures, not detected semantic faults.

Build both Lean packages before consumers; run new/old codec tests, native tests,
required real-Lean discovery, Ruff/Pyright and source-pinned raw replay. No Docker
builds. Independent review precedes small freshly coauthored commits; root owns
combined full gates, shared status and integration. Optional Export/Program laws
are allowed only as straightforward composition after the test baseline; no
proof research or new framework may delay this milestone.

Confidence is high in the four-codec field boundary and inherited wire domains;
medium in the smallest host observer fixture until the actual rejection/fault
probes pass. Revisit only for a demonstrated observer gap or discrepancy, not
for general validator correctness, resource bounds, all JSON text behavior or
new language features. This checkpoint is tested conformance, not universal
Python correctness or complete execution verification.

## Frozen codec baseline

The completed test-only baseline contains **165 ordered unique requests**:
Export/Program 19 canonical + 56 malformed + 29 normalization (104);
TableEntries/Entries 11 canonical + 36 malformed + 14 normalization (61).
All **73** actual successful encoded replies pass the public protobuf adapters.
The 92 errors pin exact paths and order. This is a finite top-level matrix,
not a repeat of every existing component test. Direct policy controls show
Python accepts camelCase aliases and numeric enums while Lean ignores the
alias field or rejects the numeric enum; Python rejects unknown fields while
Lean ignores them. These are outside canonical interchange, not mismatches
normalized into agreement.

Both complete Lean packages/default audits pass, with **624** spec checks
(`/tmp/p4blo-milestone-baseline-lean.log`). The endpoint self-test passes
**190** anchors (`...-baseline-native.log`), including 29 new independent
native checks. The two focused files pass **203** checks
(`...-baseline-focused-final.log`, 6.27 seconds).
Initial fixture development had ordinary static type/elaboration failures
and fourteen wrong English articles in expected errors ("a object/array");
these were corrected before freezing. They are not production defects,
semantic fault detections or retained fault evidence.

The source-pinned raw capture is
`.artifacts/codec/milestone-interchange-baseline.json`: **813788 bytes**,
SHA-256 `ac4bf8faed73c025be23086bcb20acbf958c20a07c7430e4048da3063aee496e`.
It records 22 exact source identities and production base `7bfdcca`.
The source fixture files and the reconstruction below remain tracked; the
ignored transcript is convenience evidence, not the sole acceptance source.
No production codec changed and no new proof claim is added.

Capture ran from this worktree with `nix develop -c uv run python -`;
log `/tmp/p4blo-milestone-baseline-capture.log`, exit 0. The script refuses
existing output and a changed production codec before launching any child.
To repeat after later tests are appended, run at the committed baseline
revision in an isolated tree, adjusting only that owned root/output path.
Never overwrite the old capture or relabel its historical sources.

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests import test_codec_program as program, test_codec_entries as entries
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-milestone-interchange')
out = root / '.artifacts/codec/milestone-interchange-baseline.json'
assert not out.exists(), 'baseline evidence must not be overwritten'
original = subprocess.run(['git','-C',str(root),'show','7bfdcca:ir/P4bloIR/Json.lean'],check=True,capture_output=True).stdout
assert (root / 'ir/P4bloIR/Json.lean').read_bytes() == original
paths = ['ir/P4bloIR/IR.lean','ir/P4bloIR/Json.lean','ir/Tests/CodecLaws.lean',
    'ir/Tests/DeclarationCodec.lean','ir/Tests/TableCodec.lean','ir/Tests/ParserCodec.lean',
    'ir/Tests/BlockCodec.lean','ir/Tests/ProgramCodec.lean','ir/Tests/EntriesCodec.lean',
    'ir/Tests/CodecLeaves.lean','ir/Tests/Main.lean','tests/test_codec_leaves.py',
    'tests/test_codec_expr.py','tests/test_codec_stmt.py','tests/test_codec_declarations.py',
    'tests/test_codec_tables.py','tests/test_codec_parser.py','tests/test_codec_blocks.py',
    'tests/test_codec_program.py','tests/test_codec_entries.py','python/p4blo/ir.py',
    'ir/proto/p4blo/v0/p4blo.proto']
sources = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
rows, success = [], 0
for module in [program, entries]:
    for request, expected in module.requests():
        stdin = json.dumps(request,separators=(',',':')) + '\n'
        run = subprocess.run([str(root / 'ir/.lake/build/bin/codec-leaves')],input=stdin,text=True,capture_output=True,timeout=10)
        assert run.returncode == 0 and run.stderr == ''
        actual = loads(run.stdout)
        assert same_json(actual,expected), request
        if 'encoded' in actual:
            _, canonical = module.protobuf_value(request['kind'], actual['encoded'])
            assert same_json(canonical,actual['encoded'])
            success += 1
        rows.append(dict(request=request,expected=expected,stdin=stdin,stdout=run.stdout,stderr=run.stderr,returncode=run.returncode))
assert len(rows) == 165 and success == 73
assert len({json.dumps(row['request'],sort_keys=True) for row in rows}) == len(rows)
assert sources == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x') as stream:
    stream.write(json.dumps(dict(format='p4blo.milestone-interchange.baseline.v0',
        production_base='7bfdcca',sources=sources,rows=rows),indent=2)+'\n')
print('rows',len(rows),'canonical successes',success,'bytes',out.stat().st_size,'SHA256',hashlib.sha256(out.read_bytes()).hexdigest())
for path,digest in sources.items(): print(path,digest)
```

The independent [baseline review](reviews/milestone-interchange.md) is CLEAR:
203 focused checks, the native endpoint, all 22 source pins, 165 exact raw
request/answer identities and 73 actual protobuf conversions were independently
checked. The old eight codec files also pass 1850 checks (50.85 seconds);
scoped Ruff/Pyright pass. No production codec bytes changed. This review does
not cover the pending host rejection tests or two bounded fault challenges.
Optional proof composition is omitted to keep the milestone focused on its
explicit independent test acceptance.

## Host rejection tests

The host fixture is an actually validated scalar program with four tables
(exact, LPM, ternary and const-default), two declared actions and two persistent
counter arrays. Each accepted packet emits literal `2a` plus untouched
`abcd` payload and increments ticks[0] and guard[2]. Independent full-array
answers are [1,0,0]/[0,0,1,0] after the first valid request and
[2,0,0]/[0,0,2,0] after the final valid request.

Fourteen rejected host profiles cover actual public protobuf decoding
(nonarray and uint32 overflow), unresolved table, wrong match kind, overflowing
key value, bad prefix, noncanonical mask, forbidden priority, bad action,
wrong argument width, present-empty default, const-default replacement,
duplicate entry and a later table failure after an earlier accepted entry.
Python invokes the actual ParseDict → run_python → Loaded.entries path; no
replacement installer or interpreter is used. Wrapped actual parser/control/
deparser entry points must have zero calls on rejection. Detached observations
cover the complete Index (including maps/scopes), metadata contract/config,
role map, existing independently installed entries, input protobuf bytes and
strict raw extern objects. The observed existing configuration is not the
temporary partially constructed installation that is discarded on failure.

Lean exercises the actual CLI server with the same valid/rejected/valid
sequences and exact independent state/output/error answers. Three additional
native checks run actual Switch.run: a successful installation reaches a
missing-parser trap, while bad host entries/default reject first. That
intentionally invalid switch is an ordering witness, not a validated-program
claim. A pure Except result cannot expose discarded intermediate work; these
are finite operational controls plus persistent-state observations, not a
universal no-execution theorem.

Three startup inputs (bad JSON field type, duplicate block, empty block name)
exercise actual public program decode/validation/load rejection. Python spies
extern binding and packet entry; Lean supplies an otherwise executable packet
request to the actual CLI and requires startup exit 1, exact stderr and no
stdout. Python semantic validation and Lean Index/load checks are not asserted
to recognize the same arbitrary language. Startup is not a hot replacement
of an already-running program. No accepted-program runtime-error rollback is
claimed.

### Review-driven strictness controls

Root found that logical hex encoding maps both int1 and True to `"0x1"`.
A retained process-local delegating rejection hook now replaces ticks[0] with
True: the logical state answer demonstrably survives, but exact-type raw
extern freezing rejects it. This observes every actual Counter attribute,
including its complete array/capacity, not only cells touched by the program.

Independent review then reproduced a second survivor: after actual
Loaded.entries raises InstallError, replace the shared metadata contract's
first field `provided=True` with integer 1. Ordinary detached dataclass/dict
equality accepted it. All configuration snapshots now use the existing
fail-closed exact-type `tests.test_lean_forwarder.freeze`, and a permanent
one-hit regression rejects specifically `metadata configuration`. Its
finally block restores the shared frozen field, so it cannot contaminate
later tests. No additional semantic campaign is counted for either observer
control. The independent reviewer reran the exact survivor and confirms it
is killed by the strengthened observer.

The first host draft's plain Metadata object equality compared identities
after deepcopy and failed despite unchanged content. That development-only
assertion was replaced; later review strengthened all content comparisons as
above. Native trap syntax/type corrections were ordinary build setup failures,
not semantic fault evidence.

## Exactly two actual sensitivity campaigns

Both ran only in `/Users/qobilidop/my/work/p4blo-milestone-interchange-faults`,
created at baseline `e03cd7a`, with the current owned host tests copied
exactly. No production candidate/main source was mutated. No Docker operation
or optional proof work was performed.

1. **Paired Program field swap.** Exchange headers/metadata reads in
   Program.decode and corresponding writes in Program.toJson. Actual Json and
   both executables compile (`/tmp/p4blo-milestone-fault-field-build.log`,
   exit 0). Ordinary focused pytest fails **5 / 122 pass** (5.62 seconds):
   four complete decoded answers plus one competing first error. The native
   endpoint fails two anchors: complete independent Program constructor and
   adjacent first error. There is no preflight failure or direct-test fallback.
   A minimal tracked `{"headers":"HdrOnly"}` fixture retains exactly the
   original encoded object but decodes into the wrong nominal slot. The
   1366-byte representative raw transcript is live-replayed twice, exit 0
   with empty stderr; it is one representative, not five distinct captured
   transcripts. Mutant Json SHA is
   `7183a035b3566d08adb633a54b9f4d38bcb02c85a0fe78d2db8443e34307447c`.
2. **Actual Python rejection-state write.** Change Loaded.entries so its
   InstallError branch calls ticks.count(1) before rethrowing. This executes
   the actual loaded extern and corrupts an otherwise untouched persistent
   cell. The actual module compiles with py_compile, exit 0; the fourteen
   focused rejection controls give **12 failures / 2 decode controls pass**.
   The error text remains correct, but the full-state observer rejects the
   extra ticks[1]. The final strict-source repetition has the same result
   (98 other tests deselected, 0.25 seconds). It is the same fault/input,
   not another campaign. The captured valid/rejected prefix is run twice
   from fresh actual state and reproduces [1,1,0] instead of [1,0,0].
   This artifact is a direct host-state observation, not a packet DRT bundle.
   Mutant loader SHA is
   `221436406e80d5a3ae39d5203763723acee878b6ad5861418e4470924675cbf1`.

No universal Program theorem was added or claimed; the paired field fault's
unchanged encoded answer is only the explicit finite witness. Existing
component proofs and historical inventories remain intact.

### Small retained observations and reconstruction

Paths relative to the candidate:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `.artifacts/codec/milestone-field/raw.json` | 1366 | `f5b5cf7ce22e6be04f4805a49a57caef85041bf44273429aa659ec3d8deadcef` |
| `.artifacts/codec/milestone-host/raw-strict.json` | 10573 | `ca3cf93868c5936598b286463c0b3a512fce0b31c4e495d72081300e6742e682` |

The earlier host `raw.json` (before the final strict-config refinement) is
left untouched but superseded as final evidence; it is the same request, not
an extra distinct input. No historical source identity is silently updated.
The final artifact pins the final test/observer/builder sources. Ordinary field
test harness views are incidental sensitivity output; the accepted retained
codec witness is the one source-matched raw transcript listed above.

Reproduce the field fault using the two uniquely anchored replacements in
the restoration script below, then from the fault `ir` working directory:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 build codec-leaves p4blo-ir
```

From the fault repository:

```sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_codec_program.py -q
/Users/qobilidop/my/work/p4blo-milestone-interchange-faults/ir/.lake/build/bin/codec-leaves --self-test
```

The exact non-overwriting representative capture runs from the clean
candidate using `nix develop -c uv run python -`:

```python
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_program import requests
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-milestone-interchange')
fault = Path('/Users/qobilidop/my/work/p4blo-milestone-interchange-faults')
out = root / '.artifacts/codec/milestone-field/raw.json'
assert not out.exists()
request, expected = next((r,e) for r,e in requests() if r == {'kind':'program','wire':{'headers':'HdrOnly'}})
stdin = json.dumps(request,separators=(',',':')) + '\n'
source = fault / 'ir/P4bloIR/Json.lean'
digest = hashlib.sha256(source.read_bytes()).hexdigest()
assert digest == '7183a035b3566d08adb633a54b9f4d38bcb02c85a0fe78d2db8443e34307447c'
result = subprocess.run([str(fault / 'ir/.lake/build/bin/codec-leaves')],input=stdin,text=True,capture_output=True,timeout=10)
assert result.returncode == 0 and result.stderr == ''
actual = loads(result.stdout)
assert not same_json(actual,expected)
assert same_json(actual['encoded'],expected['encoded'])
assert actual['value']['headers'] == '' and actual['value']['metadata'] == 'HdrOnly'
assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
artifact = dict(format='p4blo.milestone-field.v0',baseline='e03cd7aae971d5cdfca03665cb5191019d0e4f07',mutant_json_sha256=digest,
    request=request,expected=expected,actual=actual,stdin=stdin,stdout=result.stdout,stderr=result.stderr,returncode=result.returncode)
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x') as stream: stream.write(json.dumps(artifact,indent=2)+'\n')
again = subprocess.run([str(fault / 'ir/.lake/build/bin/codec-leaves')],input=stdin,text=True,capture_output=True,timeout=10)
assert (again.returncode,again.stdout,again.stderr) == (result.returncode,result.stdout,result.stderr)
print(out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest())
```

Restore Json before the host fault. Apply only the two loader replacements
specified in the restoration script, then from the fault repository run:

```sh
nix develop -c uv run python -m py_compile /Users/qobilidop/my/work/p4blo-milestone-interchange-faults/python/p4blo/arch/loader.py
nix develop -c uv run pytest tests/test_codec_entries.py -k host_rejection_does_not_execute_or_change_state -q
```

Exact final non-overwriting state capture, same fault working directory and
`nix develop -c uv run python -`:

```python
import hashlib, json
from pathlib import Path
from p4blo import arch, ir
from p4blo.drt._json import loads
from p4blo.drt.case import Case
from p4blo.drt.run import run_python
from p4blo.drt.state import encode, snapshot
from p4blo.interp.tables import InstallError
from tests.test_codec_entries import host_program, host_wire, host_rejections, expected_host_state
from tests.test_codec_leaves import same_json
from google.protobuf import json_format
from p4blo.v0 import p4blo_pb2 as pb
root = Path('/Users/qobilidop/my/work/p4blo-milestone-interchange')
fault = Path('/Users/qobilidop/my/work/p4blo-milestone-interchange-faults')
out = root / '.artifacts/codec/milestone-host/raw-strict.json'
assert not out.exists()
paths = ['python/p4blo/arch/loader.py','tests/test_codec_entries.py','tests/test_lean_forwarder.py','python/p4blo/drt/programs.py']
sources = {p:hashlib.sha256((fault/p).read_bytes()).hexdigest() for p in paths}
assert sources['python/p4blo/arch/loader.py'] == '221436406e80d5a3ae39d5203763723acee878b6ad5861418e4470924675cbf1'
program = host_program()
rejected = next(c for c in host_rejections() if c.name == 'target')
def observe():
    loaded = arch.load(program)
    good = json_format.ParseDict(host_wire(),pb.Entries())
    assert run_python(loaded,Case(good,0,b'\xab\xcd'),4) == [(0,b'\x2a\xab\xcd')]
    before = encode(snapshot(loaded))
    assert same_json(before,expected_host_state(1))
    try:
        run_python(loaded,Case(json_format.ParseDict(rejected.wire,pb.Entries()),0,b'\xab\xcd'),4)
    except InstallError as error:
        message = str(error)
    else:
        raise AssertionError('expected genuine installation rejection')
    after = encode(snapshot(loaded))
    assert message == rejected.python_error
    assert after['ticks']['values'] == ['0x1','0x1','0x0']
    assert not same_json(after,before)
    return dict(error=message,before=before,after=after)
observed = observe()
assert observe() == observed
assert sources == {p:hashlib.sha256((fault/p).read_bytes()).hexdigest() for p in paths}
data = dict(format='p4blo.milestone-host-state.v0',sources=sources,program=loads(ir.dump_json(program)),
            valid=host_wire(),rejected=rejected.wire,port=0,packet='abcd',expected=expected_host_state(1),observed=observed)
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x') as stream: stream.write(json.dumps(data,indent=2)+'\n')
print(out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest())
```

These scripts are tracked recipes for clean isolated recreation. Adjust only
the owned checkout/output locations when reproducing; old ignored artifacts
and temporary logs are not required inputs to run the known-answer tests or
sensitivity commands. Never execute command metadata from a retained artifact.

## Restoration, gates and final review

Both actual production files are restored. The isolated codec endpoint/driver
rebuild passes (`/tmp/p4blo-milestone-fault-restored-build.log`).
The following read-only check asserts baseline hashes at historical `e03cd7a`,
matches every current request/independent expected answer, checks exact
baseline bytes on both restored endpoints, reconstructs both mutant source
hashes in memory, replays the representative codec/state observations and
compares all six restored source pairs. Run from the clean candidate with
`nix develop -c uv run python -`:

```python
import hashlib, json, subprocess
from pathlib import Path
from google.protobuf import json_format
from p4blo import arch, ir
from p4blo.drt._json import loads
from p4blo.drt.case import Case
from p4blo.drt.run import run_python
from p4blo.drt.state import encode, snapshot
from p4blo.interp.tables import InstallError
from p4blo.v0 import p4blo_pb2 as pb
from tests import test_codec_program as program, test_codec_entries as entries
from tests.test_codec_leaves import same_json
root = Path('/Users/qobilidop/my/work/p4blo-milestone-interchange')
fault = Path('/Users/qobilidop/my/work/p4blo-milestone-interchange-faults')
baseline = loads((root / '.artifacts/codec/milestone-interchange-baseline.json').read_text())
fixtures = program.requests() + entries.requests()
assert len(fixtures) == len(baseline['rows']) == 165
for path,digest in baseline['sources'].items():
    old = subprocess.run(['git','-C',str(root),'show','e03cd7a:'+path],check=True,capture_output=True).stdout
    assert hashlib.sha256(old).hexdigest() == digest
for (request,expected),row in zip(fixtures,baseline['rows'],strict=True):
    assert same_json(request,row['request']) and same_json(expected,row['expected'])
    assert row['stdin'] == json.dumps(request,separators=(',',':'))+'\n'
    assert row['returncode'] == 0 and row['stderr'] == '' and same_json(loads(row['stdout']),expected)
    for tree in [root,fault]:
        run = subprocess.run([str(tree/'ir/.lake/build/bin/codec-leaves')],input=row['stdin'],text=True,capture_output=True,timeout=10)
        assert (run.returncode,run.stdout,run.stderr) == (0,row['stdout'],'')
field = loads((root/'.artifacts/codec/milestone-field/raw.json').read_text())
assert any(same_json(r,field['request']) and same_json(e,field['expected']) for r,e in fixtures)
assert field['stdin'] == json.dumps(field['request'],separators=(',',':'))+'\n'
assert field['returncode'] == 0 and field['stderr'] == ''
assert same_json(loads(field['stdout']),field['actual']) and not same_json(field['actual'],field['expected'])
assert same_json(field['actual']['encoded'],field['expected']['encoded'])
for tree in [root,fault]:
    run = subprocess.run([str(tree/'ir/.lake/build/bin/codec-leaves')],input=field['stdin'],text=True,capture_output=True,timeout=10)
    assert run.returncode == 0 and run.stderr == '' and same_json(loads(run.stdout),field['expected'])
clean = (root/'ir/P4bloIR/Json.lean').read_text()
edits = [
('headers := ← strField path j "headers", metadata := ← strField path j "metadata",',
 'headers := ← strField path j "metadata", metadata := ← strField path j "headers",'),
('ofList "blocks" (p.blocks.map Block.toJson), ofStr "headers" p.headers,\n       ofStr "metadata" p.metadata,',
 'ofList "blocks" (p.blocks.map Block.toJson), ofStr "headers" p.metadata,\n       ofStr "metadata" p.headers,')]
for before,after in edits:
    assert clean.count(before) == 1
    clean = clean.replace(before,after)
assert hashlib.sha256(clean.encode()).hexdigest() == field['mutant_json_sha256']
host = loads((root/'.artifacts/codec/milestone-host/raw-strict.json').read_text())
for path,digest in host['sources'].items():
    text = (root/path).read_text()
    if path == 'python/p4blo/arch/loader.py':
        edits = [
          ('from p4blo.interp.tables import InstalledEntries',
           'from p4blo.interp.tables import InstallError, InstalledEntries\nfrom p4blo.interp.values import Bits'),
          ('        return InstalledEntries.build(self.index, host)',
           '        try:\n            return InstalledEntries.build(self.index, host)\n        except InstallError:\n            self.externs["ticks"].call("count", [Bits(32, 1)])\n            raise')]
        for before,after in edits:
            assert text.count(before) == 1
            text = text.replace(before,after)
    assert hashlib.sha256(text.encode()).hexdigest() == digest, path
assert same_json(host['program'],loads(ir.dump_json(entries.host_program())))
case = next(c for c in entries.host_rejections() if c.name == 'target')
assert same_json(host['rejected'],case.wire) and same_json(host['valid'],entries.host_wire())
assert host['port'] == 0 and host['packet'] == 'abcd'
assert same_json(host['expected'],entries.expected_host_state(1))
assert same_json(host['observed']['before'],host['expected'])
assert not same_json(host['observed']['after'],host['expected'])
loaded = arch.load(ir.load_json(json.dumps(host['program'])))
valid = json_format.ParseDict(host['valid'],pb.Entries())
good = Case(valid,host['port'],bytes.fromhex(host['packet']))
assert run_python(loaded,good,4) == [(0,b'\x2a\xab\xcd')]
before = encode(snapshot(loaded))
assert same_json(before,host['expected'])
try:
    run_python(loaded,Case(json_format.ParseDict(host['rejected'],pb.Entries()),0,b'\xab\xcd'),4)
except InstallError as error:
    assert str(error) == host['observed']['error'] == case.python_error
else:
    raise AssertionError('installation must reject')
assert same_json(encode(snapshot(loaded)),host['expected'])
assert run_python(loaded,good,4) == [(0,b'\x2a\xab\xcd')]
assert same_json(encode(snapshot(loaded)),entries.expected_host_state(2))
for path in ['ir/P4bloIR/Json.lean','python/p4blo/arch/loader.py','ir/Tests/ProgramCodec.lean',
             'ir/Tests/EntriesCodec.lean','tests/test_codec_program.py','tests/test_codec_entries.py']:
    assert (root/path).read_bytes() == (fault/path).read_bytes(), path
    print(path,hashlib.sha256((root/path).read_bytes()).hexdigest())
print('165 historical rows exact on both endpoints; paired field and host state restored; both source patches reconstructed')
```

Baseline formatting required the separately committed one-line correction
`93a1e52`: the final diagnostic-article edit had happened after formatting.
Earlier lint/type success was not a final formatting check. Preserve the
original source hash at `e03cd7a`; current format-only drift and appended
host tests are checked separately, never by recapturing the old baseline.

Current full two-package/default/native gate passes **627** spec checks;
the codec endpoint has **193** independent anchors. Final candidate focused
tests pass **239** (4.30 seconds), including both retained strictness controls.
The initial required gate passed **2882 / 1874 deselected** in 220.94 seconds;
the post-review strict-config required rerun passes **2882 / 1875 deselected**
in 190.33 seconds, exit 0 (
`/tmp/p4blo-milestone-required-final.log`). Final format/lint/Pyright checks
all exit 0 (`...-final-format.log`, `...-final-lint.log`, `...-final-types.log`).
The restored isolated focused suite passes **239** in 5.48 seconds and its
native endpoint passes **193** anchors. Exact dual-endpoint baseline replay,
both bounded fault observations and all six source comparisons pass
(`/tmp/p4blo-milestone-restored-replay.log`). No intentional mutation, active
consumer or build remains. Root owns the combined full integration gate.

Final independent [interchange review](reviews/milestone-interchange.md) is
CLEAR: 239 focused checks and 193 native anchors were rerun; the exact prior
metadata survivor is rejected; all historical pins, dual-endpoint baseline
bytes, both reconstructed source faults, retained observations and restored
source pairs were checked independently. The final commit adds only tests and
this note. No optional proof or production behavior change is included.
