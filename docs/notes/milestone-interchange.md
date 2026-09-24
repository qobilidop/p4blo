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
