# Total LValue decoding and argument wire laws

Date: 2026-09-23. Base: `cdb7a3c`. This bounded increment follows the checked
Expr codec (`expr-codec.md`) and changes no intended wire semantics.

## Contract and decisions

Replace the existing `partial def LValue.decode` with the sole actual decoder
using the already checked oneof/message bounds and `termination_by sizeOf j`.
Its index expression calls the already-total Expr decoder; there is no mutual
recursion. Arg is already nonrecursive and needs no decoder implementation
change. Stmt and array traversal remain outside this increment.

Preserve case ordering, null/default treatment, accepted invalid syntax,
diagnostic paths and first-error behavior. Capture actual native baseline
outputs before changing either decoder. No fuel or semantic validator is
introduced. LValue representability constrains only its nested index Exprs;
Arg representability selects the existing Expr or new LValue predicate.
Empty/unresolved names and semantically invalid stack access remain in scope.

Decisions (high confidence): reuse existing helper erasure rather than create
another recursive codec; extend the registered test-only endpoint with
`lvalue`/`arg` kinds; keep independently constructed descriptors and canonical
wire fixtures with type-sensitive comparisons and public Python protobuf
round trips. Embedded Expr descriptors retain explicit operator-constructor
observations, not the shared production name table that hid an earlier fault.

`LValue.decode_unfold` now reproduces the old ordinary `oneof`/`msgField`
body, including LValue base before Expr index. This is a checked unfolding/
erasure theorem for the actual new decoder, not equality against the old
opaque partial constant. No production encoder, Arg implementation, helper
or Stmt code changes.

`lvalue_roundtrip` covers all four constructors and `arg_roundtrip` both
constructors, universally for every diagnostic path. They use actual encoders/
decoders and the existing Expr law. Only nested Expr wire bounds constrain
representability. The existing default audit checks the actual LValue decoder,
its unfolding, Arg decoder and both new laws against exactly `propext`,
`Classical.choice`, `Quot.sound`.

No complete Program codec, text-parser, semantic validity, general resource
bound or universal Python equivalence claim follows. Revisit the traversal
helper equivalence when addressing Stmt arrays separately.

## Independent fixtures and baseline

The registered test-only `codec-leaves` endpoint adds `lvalue`/`arg` kinds:
`{kind, wire}` input, `{value, encoded}` or `{error}` output. Independent
descriptor functions match constructors directly. Python checks hand-built
descriptors, canonical wires, exact errors and type-sensitive JSON equality.
Actual Lean encoded output also enters Python protobuf and the public Program
JSON adapter, without semantic validation. No production CLI mode is added.

`tests/test_codec_lvalue.py` supplies 39 valid wires, 24 malformed fixtures and
six normalizations: all constructors, empty/unresolved/unicode names, nested
next/member/index, invalid repeated next, huge decimal values, zero/max widths,
reversed slices, asymmetric operands, null/missing messages, overlapping cases,
nested overflow and unknown annotation behavior. All 39 canonical fixtures
also have separate Python protobuf controls. Shared fixture builders describe
expected syntax, not production codec results. Existing raw subprocess failure
retention and type-confusion negative controls are reused unchanged.

Before changing production Json, the extended endpoint and all 388 combined
leaf/Expr/LValue tests passed. Captured 69 actual original responses including
stdout bytes, stderr and status. After refactoring, all 69 matched byte-for-byte
and the same 388 tests passed. Ignored baseline:
`.artifacts/codec/lvalue-baseline.json`, 66,445 bytes, SHA256
`9a93ac7f5ef00731f4ce6e1c07f76587887ebdc70297af7ba4e6e9afa778e0fe`.
Requests/expectations come from `cases()`, `malformed()`, `normalized()` in
that order; original production source is `cdb7a3c`. This finite preservation
evidence does not prove equivalence of all text-parser inputs.

Nine new native checks (68 total) cover independent operands, next/member
shape, Arg tags, invalid-but-representable nested values, missing stack path,
index error order and Arg oneof diagnostic order. Kernel witnesses use the
universal laws on nested `next(next(var ""))`, huge zero-width literals and
reversed slices, reject embedded width overflow, and prove missing-stack error.

## Actual fault campaign

All intentional faults were isolated, restored by inverse anchored edits, and
the final Json file compared exactly with a saved candidate. No fault commits.

| Fault | Build/proof result | Independent runtime result |
|---|---|---|
| Index encoder only swaps base/index payloads | Actual Json build 0; audit 1 at genuine `lvalue_index` definitional goal | Not counted as runtime detection |
| Matching index encoder/decoder swap, including unfolding statement | Audit and endpoint build 0; all universal laws survive unchanged | Four wrong values plus first-error path fail; four Python controls pass; native 66 pass / 2 fail |
| Matching Arg encoder/decoder branch labels swapped | Audit and endpoint build 0; all universal laws survive unchanged | Four wrong Arg tags plus oneof diagnostic fail; four Python controls pass; native 65 pass / 3 fail |

Each paired campaign selected nine permanent tests, deselected 99, and exited
1 with five failures/four passes. Five raw artifacts were retained and live
replayed: exact saved wrong result, different from expected, status 0 and empty
stderr. In each campaign, all four valid cases still re-encoded to the original
wire. Thus encoded-wire checks and roundtrip laws genuinely survive coordinated
faults; independent constructor observations and diagnostics catch them.

Index cases 6,14,22,30 are asymmetric var/member base/index pairs, both bare and
wrapped as Arg.lvalue. Malformed case 12 has both operands empty: error changes
from `leaf.index.base: no kind set` to `leaf.index.index: no kind set`. Arg cases
16,19,33,36 use common var/member/index syntax that remains accepted with wrong
enclosing tags. Malformed case 19 reverses `[expr, lvalue]` to `[lvalue, expr]`.

### Exact reconstruction

Use a fresh isolated worktree at this increment. Never mutate while another
process builds/tests its executable; restore each fault before the next one.
Only production Json is changed; no theorem proofs or observers are weakened.
One-sided index fault:

```diff
--- a/ir/P4bloIR/Json.lean
+++ b/ir/P4bloIR/Json.lean
@@
 def LValue.toJson : LValue → Json
@@
-  | .index base idx => case "index" (obj [ofMsg "base" base.toJson, ofMsg "index" idx.toJson])
+  | .index base idx => case "index" (obj [ofMsg "base" idx.toJson, ofMsg "index" base.toJson])
```

Run `nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build P4bloIR.Json`
(exit 0), then the same command targeting `CodecProofAudit` (exit 1).
Keep that edit and add the following for the paired index fault:

```diff
--- a/ir/P4bloIR/Json.lean
+++ b/ir/P4bloIR/Json.lean
@@
-       pure (LValue.index (← msgFieldBounded j p v h "base" recur)
-         (← msgField p v "index" Expr.decode))),
+       pure (LValue.index (← msgFieldBounded j p v h "index" recur)
+         (← msgField p v "base" Expr.decode))),
@@
-           pure (LValue.index (← msgField p v "base" LValue.decode)
-             (← msgField p v "index" Expr.decode))),
+           pure (LValue.index (← msgField p v "index" LValue.decode)
+             (← msgField p v "base" Expr.decode))),
```

The changed unfolding statement is explicit: leaving it fixed rejects the fault
before runtime. With this wrong statement checked against the wrong decoder,
all roundtrip proofs still pass. Scoped to the disposable worktree, run:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build CodecProofAudit codec-leaves
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest tests/test_codec_lvalue.py -q -k '(known_answers and (case6 or case14 or case22 or case30)) or (exact_errors and wire12)'
ir/.lake/build/bin/codec-leaves --self-test
```

Expected exits: 0,1,1. `P4BLO_CODEC_FAILURE_DIR` can be an absolute directory
for a separate campaign; default is `.artifacts/codec` under the current tree.
Restore all three index edits. The independent Arg fault is:

```diff
--- a/ir/P4bloIR/Json.lean
+++ b/ir/P4bloIR/Json.lean
@@
 def Arg.decode (path : String) (j : Json) : Dec Arg :=
   oneof path j
-    [("expr", fun p v => Arg.expr <$> Expr.decode p v),
-     ("lvalue", fun p v => Arg.lvalue <$> LValue.decode p v)]
+    [("lvalue", fun p v => Arg.expr <$> Expr.decode p v),
+     ("expr", fun p v => Arg.lvalue <$> LValue.decode p v)]
@@
 def Arg.toJson : Arg → Json
-  | .expr e => case "expr" e.toJson
-  | .lvalue l => case "lvalue" l.toJson
+  | .expr e => case "lvalue" e.toJson
+  | .lvalue l => case "expr" l.toJson
```

Same build/native commands, but use this test selector (exits 0,1,1):

```sh
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest tests/test_codec_lvalue.py -q -k '(known_answers and (case16 or case19 or case33 or case36)) or (exact_errors and wire19)'
```

### Artifact manifest

Ignored local root:
`/Users/qobilidop/my/work/p4blo-lvalue-codec/.artifacts/codec/`.
Filenames are `leaf-<digest>.json`.

| Subdirectory | Digest | Bytes | SHA256 |
|---|---|---:|---|
| lvalue-index-paired | 2329f6dd555fc46e0fdfcd3c | 456 | 3c46038b169407ff5205053a24898768b28229b7648309a38db5b309ea65fa52 |
| lvalue-index-paired | 23996b7d787f10748270d693 | 2472 | 5a44f4a61fc89c4c83bee0bff5b79446c70d091578618ab36a0668dbf6a9861f |
| lvalue-index-paired | b1454e630fae480c69d84faf | 1374 | 53f34a617be11d3f4c642cc1c26d6f16a2faf7a47bcef10dc7b1abbac6e472de |
| lvalue-index-paired | c032e673a4c20e149b3c15ec | 2125 | 911378b8ae22f8d3e589865914e327634be91677c63abc806281033e1ce2915d |
| lvalue-index-paired | e0039d872c2851f39b791690 | 1119 | c0eb64e0f07f1f70fe26a13253dab2c9922f82d086927f753a6e6be9141d3b09 |
| arg-branches-paired | 3630bb78122519a99eb3ef2c | 697 | 457cf9def3f6ac3a1bc994713ad9d04f5ee4a9146022c538846c303b71041ce9 |
| arg-branches-paired | 715860cc778b09d399cc3d5a | 691 | 2388760c0cb299d775b82940831f103338e5995e0edd6e346a41ff557cfe4303 |
| arg-branches-paired | 7774791d425aa096b99d3d39 | 456 | 511b8750cb99c9d9e010950524b121fcac3792cac09278ea4808b746e4b94235 |
| arg-branches-paired | a64879fb21d568f71717fd01 | 1175 | b2741d8c2af64380df3f6e80c51801b7e1ba553e0bd80cee0963a059727ee44c |
| arg-branches-paired | c2d2f155cdb917a7b9a6d02c | 1361 | 4c2484fb231f9432e766c34f3fe7db24cf290fa89a41e11c2872cff6b351d41f |

Tracked fixtures and exact patches reconstruct every input/expectation without
temporary logs. Recreated artifact hashes can differ because their `command`
records the worktree path. Never execute a saved absolute command blindly;
replay with the current selected binary after restoration and rebuilding.

```sh
nix develop -c uv run python - <<'PY'
import hashlib, json, subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_leaves import same_json
from tests.test_codec_lvalue import cases, malformed

root = Path('/Users/qobilidop/my/work/p4blo-lvalue-codec')  # adjust for fresh tree
binary = root / 'ir/.lake/build/bin/codec-leaves'
assert binary.is_file()
count = 0
for folder, indices, bad in [
    ('lvalue-index-paired', [6, 14, 22, 30], 12),
    ('arg-branches-paired', [16, 19, 33, 36], 19),
]:
    inputs = []
    for i in indices:
        c = cases()[i]
        inputs.append(({'kind': c.kind, 'wire': c.wire},
                       {'value': c.value, 'encoded': c.wire}))
    kind, wire, message = malformed()[bad]
    inputs.append(({'kind': kind, 'wire': wire}, {'error': message}))
    assert len(inputs) == 5
    for request, expected in inputs:
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:24]
        path = root / '.artifacts/codec' / folder / f'leaf-{digest}.json'
        assert path.is_file(), path  # missing artifacts cannot falsely pass
        data = loads(path.read_text())
        assert same_json(data['request'], request)
        assert same_json(data['expected'], expected)
        result = subprocess.run([str(binary)], input=json.dumps(request) + '\n',
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0 and result.stderr == ''
        actual = loads(result.stdout)
        assert same_json(actual, expected), (path, actual, expected)
        assert not same_json(actual, data['actual'])
        count += 1
assert count == 10
print('10 source-matched restored raw replays agree')
PY
```

For live replay, use only the active campaign tuple, require count 5, and replace
the two final output comparisons with equality to saved `actual` and inequality
to `expected`. Also compare `encoded` in each valid case. Unexpected status,
stderr, timeout or malformed output fails, rather than counting as a semantic
discrepancy. Restore all faults afterward.

## Final gates and handoff

Restored `scripts/check-lean.sh` passed (exit 0): both packages, default audits,
460 spec runtime checks and user-package positive/negative API tests. Required
`P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees -q` passed: 538 tests,
1,423 deselected, exit 0. `scripts/check.sh` passed (exit 0): formatting, lint,
pyright, 1,955 pytest passes, one optional XDP skip and five existing strict
oracle xfails, schema generation drift and workflow lint. No new skips/xfails
were introduced. Restored source-matched replay: all ten agree, exit 0.

Independent review cleared the implementation and reconstruction note after
rerunning 388 focused tests, 68 native checks and five new compiled audit roots,
matching all 69 source-derived original transcript rows, and replaying all ten
source-matched raw artifacts on the restored endpoint. Local reviewer report:
`/Users/qobilidop/my/work/p4blo-naming-review/docs/notes/reviews/lvalue-codec.md`;
the integrator preserves it under the repository's review directory.

No package, export, driver or CI edits required: existing default audit/endpoint/
native driver and
`test_lean_agrees` discovery already include this increment. Root owns shared
status/decisions and integration. Next bounded task: actual Stmt totality needs
checked recursive array traversal preserving sequence/first-error behavior.
That obligation remains open.
