# Proof-visible expression decoding

Date: 2026-09-23. Base: `939e762`. Implementation of the independently reviewed
`codec-recursion-plan.md`; this note records the bounded contract and evidence.

## Contract and decisions

The existing public `Expr.decode` is the sole production decoder. Replace its
`partial` declaration with well-founded recursion on the actual finite JSON
tree, preserving every field default, accepted syntax value, field visitation
order, and error path/string. No fuel, semantic validator, or parallel codec.
LValue and Stmt remain partial and outside this increment.

The selected oneof payload is strictly smaller than the outer object. An
absent/null message synthesizes `{}`, whose size is at most that of the payload;
this nonstrict/strict composition supplies recursive descent without changing
the missing-field diagnostic. Bounds use physical tree structure, not the
TreeMap cached node count or its well-formedness predicate.

Decision (high confidence): preserve the existing nonrecursive `oneof` helper
as the proof-erased reference, and introduce bounded field collection in its
recognized-case order. Prove generic helper erasure including malformed inputs,
then prove the actual Expr definition unfolds to the original body. This is
not a second recursive decoder. `JsonBounds.lean` isolates pinned TreeMap
representation details. The candidate does not need array traversal changes.

Decision (high confidence): extend the already registered test-only
`codec-leaves` endpoint with `kind: "expr"` rather than add a production protocol
mode or executable. Its separate recursive descriptor distinguishes unequal
subexpressions, independently of the production wire encoder. Operator
observations use explicit constructor matches, never the production enum-name
table. Independent fixtures name every operator. This independence was
strengthened after a genuine surviving mutant exposed the initial design.

Decision (high confidence): retain raw request/expectation on subprocess
timeout, launch error, signal exit, empty output and malformed output. A timeout
may contain byte streams even when subprocess text mode is set; normalize with
UTF-8 replacement for artifact serialization. Process failure must still fail,
never be turned into a semantic codec result. Keep exact JSON type comparisons.

## Pre-change baseline

Before altering Expr, the extended endpoint ran 39 hand-specified expression
vectors (every constructor, all 3 unary/19 binary operators, unequal operands,
nested mux/member/index/slice, boundary/default and semantically invalid syntax)
plus 20 exact malformed/error-order vectors. Existing 170 leaf/key tests and
six new process-failure observer controls bring the focused baseline to
**274 passed**. Endpoint and production runner built first, exit 0.

Actual raw transcripts are retained locally, not required as the only source
of expectations: `.artifacts/codec/expr-baseline.json`, 48,463 bytes, SHA256
`acb0802410c35aa7d6f6e4116ab3a17d8c633bf2f8220694c274ba4143e9dd4c`.
The tracked `expressions()` and `malformed()` fixtures reconstruct every request
and independent expected result. Initial setup failed before running tests
because `uv` was outside Nix and then a test import omitted the `tests.` prefix;
both were corrected before the successful baseline, not counted as tests.
Five normalization controls were subsequently run against the still-old
baseline binary, bringing that pre-refactor run to **279 passed**. They cover
null plus a live kind, ignored unknown annotation, null string default, and
noncanonical decimal/uint32 spellings. They do not claim Python accepts all
of those spellings/policies. A seventh process-observer regression for invalid
UTF-8 brings the final focused count to **280**.

## Checked claims

`Expr.decode` is now a total, well-founded definition. Its generated unfolding
equation is kernel-visible. `Expr.decode_unfold` proves equality to the original
body using `oneof`, including its case order and field access order. Generic
`oneofBounded_erasure` and `msgFieldBounded_erasure` hold for arbitrary inputs
and callbacks. They cover success and errors, including synthetic defaults.
This is not an equality theorem against the former opaque `partial` constant;
the old recurrence is pinned by the new equation, and the original executable
transcripts provide additional checked compatibility evidence.

`CodecLaws.expr_roundtrip` proves, for every path and every representable Expr,
`Expr.decode path value.toJson = .ok value`. The only restrictions are recursive
Literal/Type representability and uint32 slice bounds. Zero-width literals,
huge decimal payloads, unresolved names, invalid operand types, and reversed
slice bounds remain representable. A nested mux/binary/member/index/literal/
slice witness deliberately contains semantically invalid syntax. A kernel
negative example excludes an overflowing lookahead type. Another kernel
example pins the exact missing nested-message diagnostic.

Five added default-audit roots (`msgFieldBounded_erasure`,
`oneofBounded_erasure`, actual `Expr.decode`, `Expr.decode_unfold`, and
`expr_roundtrip`) have exactly the standard axiom set `[propext,
Classical.choice, Quot.sound]`. No `sorry`, alternate recursive decoder,
new axiom or native-evaluation escape is used.

## Adversarial experiments

Only `ir/P4bloIR/Json.lean` was intentionally mutated; the exceptions are the
permanent observer improvement and independent tests described below. Every
fault is restored by inverse anchored edits, and the final file byte-compares
with the saved pre-mutation candidate. Do not commit an intentional fault.

### 1. Encoder-only recursive index reversal

In the **Expr** encoder (not the similar LValue branch), replace:

```diff
-  | .index base idx => case "index" (obj [ofMsg "base" base.toJson, ofMsg "index" idx.toJson])
+  | .index base idx => case "index" (obj [ofMsg "base" idx.toJson, ofMsg "index" base.toJson])
```

Run from the checkout root:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build P4bloIR.Json
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build CodecProofAudit
```

Actual Json compiled, exit **0**. The proof build exited **1** at
`CodecLaws.expr_index`: the intended operand order is no longer definitionally
equal to the decoder/encoder composition. This is a real proof rejection, not
a semantic runtime kill; the failing proof build was not used as a new binary.

### 2. Consistently wrong recursive codec and unfolding statement

Keep the encoder mutation and additionally apply these two precise changes:

```diff
      ("index", fun p v h => do
-       pure (Expr.index (← msgFieldBounded j p v h "base" recur)
-         (← msgFieldBounded j p v h "index" recur))),
+       pure (Expr.index (← msgFieldBounded j p v h "index" recur)
+         (← msgFieldBounded j p v h "base" recur))),
```

```diff
         ("index", fun p v => do
-           pure (Expr.index (← msgField p v "base" Expr.decode) (← msgField p v "index" Expr.decode))),
+           pure (Expr.index (← msgField p v "index" Expr.decode) (← msgField p v "base" Expr.decode))),
```

The latter is the **statement** of `Expr.decode_unfold`. It is explicitly part
of this consistent wrong-model experiment: leaving it unchanged would itself
reject the changed decoder. The proof is not replaced or weakened with an
axiom, and the universal representability/roundtrip theorem remains unchanged.

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build
P4BLO_REQUIRE_LEAN=1 P4BLO_CODEC_FAILURE_DIR=/absolute/checkout/.artifacts/codec/expr-index-paired \
  nix develop -c uv run pytest tests/test_codec_expr.py tests/test_codec_leaves.py -q
/absolute/checkout/ir/.lake/build/bin/codec-leaves --self-test
```

Default build/audit exited **0**. Python tests: **3 failed, 277 passed**, exit
**1**. Native checks: **57 passed, 1 failed**, exit **1**. The canonical index
`left[right]` decodes to internal `right[left]` while re-encoding to exactly
the original wire. The nested fixture preserves that wrong internal index
inside a mux. Both valid encoded-only comparisons survive. The third failure
is precise error order: `{"index":{"base":{},"index":{}}}` reports
`leaf.index.index: no kind set` instead of `leaf.index.base: no kind set`.
All three retained inputs reproduced their exact live mismatch.
These native counts precede the additional unary control below; repeating
the index campaign from final source has that one extra passing native check.

### 3. Genuine observer survivor, then methodology improvement

Restore the index changes. Mutate the shared production unary table only:

```diff
 def UnaryOp.names : List (String × UnaryOp) :=
-  [("UNARY_OP_NOT", .not), ("UNARY_OP_COMPLEMENT", .complement), ("UNARY_OP_NEGATE", .negate)]
+  [("UNARY_OP_NOT", .negate), ("UNARY_OP_COMPLEMENT", .complement), ("UNARY_OP_NEGATE", .not)]
```

Both production encode and decode use this table. The initial test descriptor
also used `op.protoName`; independent review identified that correlated trust
boundary. With that old descriptor, the actual mutant passed the full default
proof build, **all 280 focused tests**, and **all 58 native tests**. This was
not a hypothetical concern or a mocked response.

The permanent correction observes UnaryOp/BinaryOp by explicit constructor
matches, separate from the wire table, and adds a direct native `.not`
known answer. The same actual table mutant still passes the default build and
all proofs, but now yields **2 failed, 278 passed** in Python and **1 failed,
58 passed** natively, both exit **1**. `UNARY_OP_NOT` wire decodes to internal
`.negate`, and vice versa. Both encoded-only outputs still agree; the new
semantic descriptors expose the error. Both raw inputs reproduced the exact
live mismatch. This experiment is why roundtrip proofs are complemented by
independent constructor observations, not merely more generated roundtrips.

To repeat the historical weak-observer control from final source, temporarily
replace just `.str (unaryOpValue op)` in `exprValue` with `.str op.protoName`,
and omit the added native unary known-answer check; do not alter independent
expected fixtures. The table fault then survives the focused tests. Restore
the explicit observer before rebuilding the fixed campaign:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build
P4BLO_REQUIRE_LEAN=1 P4BLO_CODEC_FAILURE_DIR=/absolute/checkout/.artifacts/codec/expr-enum-paired \
  nix develop -c uv run pytest tests/test_codec_expr.py tests/test_codec_leaves.py -q
/absolute/checkout/ir/.lake/build/bin/codec-leaves --self-test
```

The tracked selected counterexamples are Expr fixtures 5/38 and malformed
fixture 12 for index; Expr fixtures 12/14 for unary names. Full-file commands
above recreate the exact five inputs without any temporary source generator.
Use fresh artifact subdirectories when reconstructing an experiment.

## Retained replay evidence

Files are ignored local artifacts, not additional fixtures duplicating
tracked inputs. Group paths are under `.artifacts/codec/`:

| Group/file | Bytes | SHA256 |
|---|---:|---|
| `expr-index-paired/leaf-5210c6361fb4f8de97620702.json` | 1115 | `1353e3004dcb5864d05d6efe087675ef9d248c03dcee42e095fd8279854b9a09` |
| `expr-index-paired/leaf-b143ee239047b7921b520182.json` | 4417 | `64f518a375247d1aac96e0309a9dac4a3fe6651892bd37d73402c628ef15cda7` |
| `expr-index-paired/leaf-b7c50281137719ba82176bd5.json` | 457 | `34bbea956f16cc40352b06fffff575ab87b2759b7e21b841bc4314dd83aa624c` |
| `expr-enum-paired/leaf-23e370b27db86771c6194bc8.json` | 979 | `e0e6d1b45562244ca3cff124bd578f1b03648231c82694c4beee89a9d3f133e2` |
| `expr-enum-paired/leaf-9ef2080f4f438e938ac3e825.json` | 970 | `bcb7a7994f6fe6986f2dad957cbc64738ed3f179d11538f940e2a798d6d85835` |

The five bundles total 7,938 bytes. Each records raw request, expectation,
actual value, child status/stderr, command and timeout. Their command metadata
is diagnostic, not executable input: replay chooses the current built binary.
Paths embedded in metadata vary when reconstructed in a different checkout;
request/expectation matching, not a location-dependent file hash, is the
source-only identity criterion.

Fail-closed restored replay, after building both packages and restoring faults:

```python
import json
import subprocess
from pathlib import Path
from p4blo.drt._json import loads
from tests.test_codec_expr import expressions, malformed
from tests.test_codec_leaves import same_json

root = Path("/absolute/checkout")
groups = {
    "expr-index-paired": ["leaf-5210c6361fb4f8de97620702.json",
                          "leaf-b143ee239047b7921b520182.json",
                          "leaf-b7c50281137719ba82176bd5.json"],
    "expr-enum-paired": ["leaf-23e370b27db86771c6194bc8.json",
                         "leaf-9ef2080f4f438e938ac3e825.json"],
}
paths = [root / ".artifacts/codec" / group / name
         for group, names in groups.items() for name in names]
assert len(paths) == 5 and all(path.is_file() for path in paths)
fixtures = [({"kind": "expr", "wire": e.wire}, {"value": e.value, "encoded": e.wire})
            for e in expressions()]
fixtures += [({"kind": "expr", "wire": w}, {"error": m}) for w, m in malformed()]
for path in paths:
    saved = loads(path.read_text())
    assert isinstance(saved, dict)
    assert sum(same_json(saved["request"], r) and same_json(saved["expected"], e)
               for r, e in fixtures) == 1
    result = subprocess.run(
        [str(root / "ir/.lake/build/bin/codec-leaves")],
        input=json.dumps(saved["request"]) + "\n", text=True,
        capture_output=True, check=True, timeout=10,
    )
    assert result.stderr == ""
    assert same_json(loads(result.stdout), saved["expected"]), path
print("5 source-matched codec artifacts agree")
```

Observed restored result: **5/5 agree**. The 59 original baseline transcripts
also agree byte-for-byte (stdout, stderr, exit status), including after fixing
the operator observer. Full source fixtures plus the exact mutation recipes
above remain usable when all local logs/artifacts are absent.

Supplementary local logs: `/tmp/p4blo-expr-baseline-{tests,normalized}.log`,
`/tmp/p4blo-expr-mutant-encoder-{json,audit}.log`,
`/tmp/p4blo-expr-mutant-paired-{build,tests,native,replay}.log`,
`/tmp/p4blo-expr-mutant-enum-{shared-build,survivor,old-native,fixed-build,fixed-tests,fixed-native,replay}.log`,
and `/tmp/p4blo-expr-final-{lean,focused,drt,full,replay}.log`.

## Gates and remaining obligations

Restored both-package Lean gate: exit **0**, **451** spec checks, all user
package checks. Focused codec/protobuf/observer gate: **280 passed**. Native
codec checks: **59**. Required real-Lean gate: **457 passed, 1383 deselected**,
exit **0** (54.88 seconds). Generic helper/actual definition/roundtrip audits
all pass. Ordinary full gate: **1834 passed, 1 skipped, 5 xfailed**, exit **0**
(347.89 seconds). Formatting, lint, type checks, schema/no-drift and workflow
lint all pass. The skip is the unavailable optional XDP image; the five strict
expected failures are existing external-oracle discrepancies, not new waivers.
Independent review is clear (`notes/reviews/expr-codec.md`): the reviewer
independently repeats all 280 focused checks, 59 native checks and five new
axiom audits, checks all 59 original transcripts and source identities, and
hash-checks/source-matches/replays all five restored mutation inputs.
The first full-gate attempt stopped at a missing invariant-dict type annotation
in a new observer test; it was fixed without changing the runtime test.

No package/CI registration change is required: the endpoint, native test
module and codec audit are already default targets, and every new real-Lean
case uses the shared fixture and `test_lean_agrees` prefix. This work does not
claim a general Program codec theorem, text parser verification, unlimited
physical resources, or full ProtoJSON acceptance parity. Next bounded steps:
LValue totality/roundtrip using these same helpers, then Stmt's array traversal
erasure; recursive structured generation can supplement (not replace) the
universal representable Expr law and independent canonical-wire vectors.
