# KeyValue codec laws

## Contract before implementation (2026-09-23)

Base `d8e2341`. Extend the existing actual-codec proof module to exact, LPM
and ternary `KeyValue` constructors. The wire representability predicate
requires only LPM `prefixLen < 2^32`; values and masks are arbitrary natural
numbers encoded as decimal strings. Do not require a resolved table key,
prefix/key-width agreement, or zero bits outside a mask/prefix. Those are
semantic validity obligations, not representability restrictions.

Confidence: high, reusing the checked decimal/uint32 laws and the production
nonrecursive decoder. No alternate codec, intended wire semantics change,
recursive decoder change or new production mode. Extend the already
registered test-only endpoint and axiom audit. Preserve type-sensitive JSON
comparison and raw failure retention before known-answer assertions.

Independent vectors must distinguish value from mask, preserve decimal zero,
exercise prefix defaults and uint32 boundaries, and document malformed input
without claiming complete protobuf acceptance parity. Challenge actual code
with isolated faults, including a paired remapping that preserves a roundtrip
but violates independent expected wire payloads. Restore every fault before
final gates. No Docker builds.

JSON-value left inverses are the claim. JSON text parsing, binary protobuf,
Python correctness, unknown fields/aliases/versioning, resource limits and
general recursive/whole-program codec laws remain outside this increment.

## Actual proof and independent observations

`CodecLaws.KeyValueRepresentable` constrains only `.lpm`'s prefix length.
`keyValue_roundtrip` proves `KeyValue.decode path key.toJson = .ok key`
for every representable key, using the real `KeyValue.decode/toJson` and
the previously audited decimal/uint32 helpers. Exact and ternary keys need
no extra premise. The new audit root uses only
`[propext, Classical.choice, Quot.sound]`. No production-code change is
needed. Existing package registration automatically includes the extended
proof audit, native test driver and test endpoint.

Kernel-checked witnesses retain `.lpm (10^100) 0` and `.ternary 255 0`,
which are representable despite failing possible semantic key-canonicality
conditions. Another witness checks the actual error for `.lpm 0 (2^32)`.
No table declaration or key width is invented to make these codec tests valid.

The test endpoint adds `kind: "key"` to its existing test-only envelope.
Its descriptor directly inspects the decoded constructor and returns a tag,
decimal-string value/mask, and numeric LPM prefix. It separately returns
the production encoder's output. The Python adapter embeds generated
protobuf KeyValue messages in unvalidated Program table constants and
exercises actual public `ir.dump_json/load_json`; the actual Lean-encoded
payload also passes through that adapter. Semantic validation is not invoked.

There are 23 independently specified canonical-wire keys: six exact, nine LPM,
and eight ternary cases. Values cover decimal zero, digit boundaries,
uint32 and 101-digit values; prefixes cover omitted zero, one, and uint32
maximum. Unequal ternary components are essential, including both operand
orders and values outside masks. Four normalization probes check leading
zeros and null/string prefix inputs; canonical cases cover missing-prefix
zero defaults. Fourteen malformed/default/
range probes and twelve nondecimal-spelling cases pin the actual Lean
acceptance profile. Missing strings may be representable to Python's raw
protobuf parser before validation but are rejected by Lean's Nat adapter;
these negative probes do not claim full accepted-language parity.

All prior strict JSON comparisons and observer regressions are retained.
The increment adds 76 focused checks, including 53 real-Lean probes, and
16 native known answers (52 total in `codec-leaves --self-test`). Malformed
raw input and exact expected semantic/wire observations are retained before
a known-answer failure, in the existing raw-leaf artifact format.

## Adversarial evidence

### LPM prefix perturbation: production builds, proof rejects

In the actual `KeyValue.toJson` branch, temporarily replace
`ofNat "prefix_len" prefixLen` with `ofNat "prefix_len" (prefixLen + 1)`.
Building `P4bloIR.Json` succeeds (exit 0), but building
`P4bloIR.CodecLaws` fails (exit 1) at `keyValue_lpm`. Zero prefixes no longer
round-trip, and a maximum prefix becomes unrepresentable. The failed proof
reduction also causes unused-simp diagnostics; those are not the only
failure. This is a **proof rejection**, not a compiled runtime kill.

### Paired ternary remapping: both roundtrips survive, semantics fail

After restoring the first fault, introduce exactly this pair of edits in
the actual codec:

```diff
-       pure (KeyValue.ternary (← decimalField p v "value") (← decimalField p v "mask")))]
+       pure (KeyValue.ternary (← decimalField p v "mask") (← decimalField p v "value")))]
-  | .ternary value mask => case "ternary" (obj [ofDecimal "value" value, ofDecimal "mask" mask])
+  | .ternary value mask => case "ternary" (obj [ofDecimal "value" mask, ofDecimal "mask" value])
```

`codec-leaves CodecProofAudit` builds with every universal leaf theorem
and audit intact, exit 0. The proof infers actual diagnostic paths: a
successful left inverse should not accidentally depend on the spelling of
those paths. It still proves the real composition exactly; the paired
mutation genuinely preserves that property. No proof is edited for a mutant.

The independent canonical-wire test fails on exactly six unequal ternary
cases: **6 failed, 17 passed, 147 deselected**, exit 1. All exact/LPM
controls and equal-component ternary controls pass. The native direct
`value=3, mask=12` probe also fails; its other 51 checks pass. It receives
`.ternary 12 3` rather than `.ternary 3 12`.

Six raw bundles are saved. Live replay demonstrates **six complete
observation divergences but six encoded-only agreements**, exit 1. Thus
merely checking `encode(decode(wire)) = wire` would also miss this fault.
The independent abstract descriptor, not a larger roundtrip sample count,
detects it. After exact restoration and rebuilding, the same six bundles
have zero divergences (exit 0). Production `Json.lean` has an empty diff.

## Source-only reproduction and retained inputs

All commands run from a checkout containing this increment, using the pinned
toolchain. First establish the normal baseline:

```sh
nix develop -c scripts/check-lean.sh
ir/.lake/build/bin/codec-leaves --self-test
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_codec_leaves.py -q
```

For the prefix fault above, run these separately and check each exit code:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build P4bloIR.Json
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build P4bloIR.CodecLaws
```

Restore that single edit. Apply only the paired ternary diff, then:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build codec-leaves CodecProofAudit
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_codec_leaves.py -k lean_agrees_key_known_answers -q
```

The tracked cases reconstruct every raw artifact without temporary scripts.
The minimal named witness is
`tests/test_codec_leaves.py::test_lean_agrees_key_known_answers[ternary-1-0]`:
wire `{"ternary":{"value":"1","mask":"0"}}`, expected abstract
`{"tag":"ternary","value":"1","mask":"0"}`. Under the paired fault
the abstract components are swapped while encoded wire remains unchanged.

Preserved ignored artifacts in this worktree's `.artifacts/codec/`:

| Filename | Bytes | SHA-256 |
| --- | ---: | --- |
| `leaf-18e56d8b862a0266286f3853.json` | 593 | `ccf1fa56f7b19967918a8ffa6043c8a3de8a2a7715aa5320ab423d9f04d43fe1` |
| `leaf-68e095237e66c8a3f79f63a8.json` | 598 | `783a884433c09717243ca66c378debde0f131f543d3c136cb33bffacb8dabfa6` |
| `leaf-9c68fde7eae4a356c82cc1d6.json` | 1138 | `72940325b31784ecda94f8c288e1f79890b62fd73841b8e5fc1b88678ec89bbf` |
| `leaf-aa3823db33ca1f6c44357f8b.json` | 1138 | `4bda9ecd2e4ab5f4b82e7a0fa9a762be0ec6a4568b7d080fe98bab41c069bfa0` |
| `leaf-cd5e8a42776019052515b79f.json` | 593 | `eaa304e55005490e391fb38fdb3d5ff8efde0c2e3f5d6190209642b47a9ccf22` |
| `leaf-d7df72214cf72db4e3310ffc.json` | 598 | `1342a1e4664f412c8fbfc612f71d90187aee3f08c3cfa3e331a3d1e200da7c50` |

Replay only these experiment inputs (not an unconstrained artifact-directory
glob). Missing inputs fail before execution; other experiments may coexist:

```python
import json
import subprocess
from pathlib import Path

root = Path("/absolute/path/to/p4blo")
names = [
    "leaf-18e56d8b862a0266286f3853.json", "leaf-68e095237e66c8a3f79f63a8.json",
    "leaf-9c68fde7eae4a356c82cc1d6.json", "leaf-aa3823db33ca1f6c44357f8b.json",
    "leaf-cd5e8a42776019052515b79f.json", "leaf-d7df72214cf72db4e3310ffc.json",
]
paths = [root / ".artifacts/codec" / name for name in names]
assert len(paths) == 6 and all(path.is_file() for path in paths)
same = lambda x, y: json.dumps(x, sort_keys=True) == json.dumps(y, sort_keys=True)
divergences = encoded_agreements = 0
for path in paths:
    saved = json.loads(path.read_text())
    result = subprocess.run(
        [str(root / "ir/.lake/build/bin/codec-leaves")],
        input=json.dumps(saved["request"]) + "\n",
        text=True, capture_output=True, check=True, timeout=10,
    )
    assert result.stderr == "", result.stderr
    actual = json.loads(result.stdout)
    divergences += not same(actual, saved["expected"])
    encoded_agreements += same(actual.get("encoded"), saved["expected"]["encoded"])
print("full divergences:", divergences, "encoded-only agreements:", encoded_agreements)
raise SystemExit(1 if divergences else 0)
```

Diagnostics are in `/tmp/p4blo-keyvalue-mutant-prefix-{build,proof}.log`,
`/tmp/p4blo-keyvalue-mutant-paired-{build,tests}.log`,
`/tmp/p4blo-keyvalue-mutant-native-tests.log`,
`/tmp/p4blo-keyvalue-mutant-replay.log`, and
`/tmp/p4blo-keyvalue-restored-replay.log`. These logs are supplementary;
the source recipes and independent fixtures are the durable evidence.

## Gates and remaining work

Restored `scripts/check-lean.sh` passes both packages/default audits and
444 spec checks. Native leaf checks: 52 passed. Focused Python/Lean/protobuf
and observer checks: 170 passed. Required real-Lean gate: 355 passed,
1337 deselected, exit 0, 47.27 seconds. Independent read-only review repeats
all 170 focused checks, 52 native checks, the new axiom audit and six
restored artifact replays successfully. Independent review is clear:
`notes/reviews/keyvalue-codec.md`.

Full ordinary gate: **1686 passed, 1 skipped, 5 xfailed**, exit 0,
342.55 seconds (`/tmp/p4blo-keyvalue-full.log`). The only skip is the
unavailable optional XDP compile image, not a passing native XDP check;
the five xfails are existing strict external-oracle discrepancies.
Formatting, lint, types, schema/no-drift and workflow checks pass.
No default-target
or CI-selector change is needed; existing registration discovers these tests.

No mutation is committed. Next bounded proof candidates are finite wrappers
such as KeySet/Field, while broader recursive laws require making the actual
partial decoders proof-visible with checked termination. Semantic table-key
validity and matching behavior remain separate from the wire laws proved here.
