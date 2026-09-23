# Actual codec leaf laws

## Contract before implementation (2026-09-23)

Base `4ce3798`. Prove laws about the existing `P4bloIR.Json` implementation,
not a second proof-only encoder or decoder. First prove
`Decode.decimal path (toString n) = .ok n` for every natural number. Then
prove exact `Literal` and `Ty` JSON-value encode/decode roundtrips under
explicit protobuf representability predicates: widths and stack sizes fit
uint32, while decimal-string values are arbitrary naturals. No positivity,
value-fits-width, declaration resolution or name-validity premise belongs
in these wire predicates. Representable invalid syntax remains representable.

Confidence: high in this boundary; medium in proof ergonomics around the
existing JSON object and imperative oneof helpers. Prefer helper lemmas over
production changes. Revisit if the actual helpers require a behavior-preserving
refactor, with tests before any change. Do not alter intended wire semantics.

Scope is abstract values to JSON values and back, not JSON text parsing or
universal Python/Lean ProtoJSON agreement. Existing `partial` recursive
expression/lvalue/statement decoders remain an explicit barrier to general
recursive codec theorems. Unknown fields, duplicate text keys, aliases,
resource limits and complete program validity remain separate obligations.

Root owns package export/audit/test registration while the field agent owns
those shared seams. This branch adds isolated proof/test/audit modules and
provides exact registration instructions before acceptance. No Docker builds.

## Claims and implementation

`ir/P4bloIR/CodecLaws.lean` proves five advertised roots over the actual
production definitions:

- `decimal_toString`: every natural's decimal rendering decodes exactly;
- `uint32_toJson`: numeric encoding decodes under `n < 2^32`;
- `uint32_toJson_reject`: the complementary domain is rejected with the
  actual diagnostic, so the representability bound is observable;
- `literal_roundtrip`: every `LiteralRepresentable` literal is recovered;
- `type_roundtrip`: every `TypeRepresentable` type is recovered.

The proofs use pinned Lean v4.34.0 decimal lemmas, actual object/oneof
definition reduction, and explicit cases for omitted ordinary defaults.
No alternate codec, axioms, `sorry`, native-decide proof escape or production
helper change is introduced. `ir/CodecProofAudit.lean` guards the transitive
axioms of all five roots: `[propext, Classical.choice, Quot.sound]`.

Representable counterexamples to semantic validity include a zero-width
literal carrying `10^100`, an empty-name/zero-size stack and unresolved
enum/error names. Those round-trip. Width `2^32` does not. The test module
checks these with kernel-checked witnesses as well as native execution;
large width values are never evaluated as runtime bitvector allocations.

## Test-only interoperability endpoint

`ir/Tests/CodecLaws.lean` defines `CodecLawTests.tests` (36 native known
answers); `ir/Tests/CodecLeaves.lean` supplies the separate `codec-leaves`
executable entry point so importing tests cannot clash with another `main`.
Without arguments it reads one
JSON object per line, `{"kind":"literal"|"type", "wire": <leaf JSON>}`.
Success returns `{"value": <semantic descriptor>, "encoded": <actual
production re-encoding>}`; a decoding failure returns `{"error": <actual
diagnostic>}`. Descriptor constructors directly inspect decoded abstract
values; they do not call the encoder. `--self-test` runs the native checks.
This is test infrastructure, not a new production protocol or CLI mode.

The Python test suite independently specifies 39 canonical vectors. Each
is parsed into the generated protobuf leaf, embedded in an intentionally
unvalidated Program, and run through the public `ir.dump_json/load_json`
functions. Actual field values and explicit default/oneof presence must
match the independently specified payload. The same vectors pass through
the native Lean leaf decoder and encoder. Nine additional native probes
pin malformed/default/range rejection and leading-zero normalization;
they deliberately do not claim protobuf accepts exactly the same language.

A mismatch saves the raw request, intended abstract observation and exact
expected re-encoding before the known-answer assertion, under
`.artifacts/codec/leaf-<request SHA256 prefix>.json` (override with
`P4BLO_CODEC_FAILURE_DIR`). This is a leaf failure artifact, not an execution
DRT bundle: invalid raw JSON may not have any abstract program representation.

## Integration registration (root-owned)

The implementation worktree temporarily registers the test executable and
audit in its own Lake configuration for native checks, with root approval.
That temporary configuration is reverted before the implementation commit.
The integrator must apply these changes before accepting the increment:

1. Add `import P4bloIR.CodecLaws` to `ir/P4bloIR.lean`.
2. In `ir/lakefile.toml`, add `"CodecProofAudit"` and `"codec-leaves"` to
   `defaultTargets`, a `[[lean_lib]]` named `CodecProofAudit`, and a
   `[[lean_exe]]` named `codec-leaves` with `root = "Tests.CodecLeaves"`.
3. Import `Tests.CodecLaws` in `ir/Tests/Main.lean` and run
   `CodecLawTests.tests` in its ordinary test sequence.

`tests/test_codec_leaves.py` uses the shared `lean_binary` fixture and
`test_lean_agrees` prefix, so the existing required real-Lean gate discovers
all 48 native interoperability probes without a CI selector change. A built
production executable with a missing test endpoint fails, rather than skips.

## Remaining obligations

These are left-inverse laws over JSON values. They do not prove JSON text
parse/render identity, binary protobuf transport correctness, Python code
correctness, accepted-input language equivalence or complete program validity.
The canonical image omits ordinary defaults but preserves false/zero/empty
oneof payloads and explicit decimal zero. Noncanonical `"0007"` normalizes
to `"7"`; an unrestricted right inverse would be false. General recursive
laws require making the actual `partial` expression/lvalue/statement decoders
proof-visible with a checked termination argument. KeyValue leaves can be a
small later increment; they are not silently included in these predicates.

## Adversarial checks and independent review findings

Four actual `Json.lean` mutations were made one at a time in the isolated
implementation tree, then restored. The first three compile the actual
production codec module successfully (exit 0) but fail the codec law build
(exit 1). These are **proof rejections**, not claimed compiled runtime kills:

| Actual change | Why the intended property is false | Rejected obligation |
| --- | --- | --- |
| Decimal fold `n * 10` to `n * 11` | `"10"` becomes 11 | `decimal_toString` |
| `ofDecimal` omits its field at zero | a literal zero becomes an absent/invalid decimal string | `literal_bits` |
| `uint32` bound `<` to `≤` | first overflow `4294967296` becomes accepted | `uint32_toJson_reject` (the exact acceptance reduction also rejects this edit) |

The fourth intentionally changes both ends consistently:

```diff
-     ("error", fun p v => Literal.error <$> str p v)]
+     ("fault", fun p v => Literal.error <$> str p v)]
-  | .error name => case "error" (.str name)
+  | .error name => case "fault" (.str name)
```

All universal round-trip proofs and the transitive axiom audit still pass.
The actual native endpoint builds (exit 0). The independent wire vectors
then fail on exactly the three literal error names (`""`, `"NoError"` and
the escaped/Unicode name), with **3 failed, 36 passed, 48 deselected**, exit
1. Each receives `{"error":"leaf: no kind set"}` instead of the expected
abstract error constructor and `{"error": <name>}` wire leaf. Replaying the
three retained raw inputs against the live mutant gives three divergences
(exit 1); after restoring `Json.lean` and rebuilding, all three agree
(exit 0). A correct self-roundtrip law alone cannot establish that both
directions implement the intended protobuf mapping.

Independent review then found a real weakness in the new *test observer*:
Python dictionaries equate `false` with `0`, `true` with `1`, and `8` with
`8.0`. The final comparator uses sorted JSON rendering, preserving scalar
types while ignoring object ordering. Four fake-response tests verify that
wrongly typed Boolean replies fail and retain their raw failure bundles;
three nested controls explicitly distinguish bool/int/float equality. The
actual Lean-produced `encoded` object now passes through the Python
protobuf/public IR adapters too, not merely comparison against a separate
preselected input. Review found no defect in the universal leaf proofs.

### Exact source-only reproduction

Run these commands from a worktree containing the final root registration:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build codec-leaves CodecProofAudit
ir/.lake/build/bin/codec-leaves --self-test
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_codec_leaves.py -q
```

For each of the first three faults, use the exact replacement in the table
(`ofDecimal` becomes `if n == 0 then [] else [(key, .str (toString n))]`),
and run these separately, checking both exit codes:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build P4bloIR.Json
nix develop -c lake +leanprover/lean4:v4.34.0 -d ir build P4bloIR.CodecLaws
```

Restore that exact edit before introducing another. For the paired mutation,
apply only the two-line diff above, rebuild `codec-leaves CodecProofAudit`,
then run the retained-source constructor cases:

```sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_codec_leaves.py -k lean_agrees_leaf_known_answers -q
```

This recreates the three raw bundles from tracked fixtures. To isolate the
smallest empty-error witness, select
`'tests/test_codec_leaves.py::test_lean_agrees_leaf_known_answers[leaf14]'`.
The expected observation is `{"tag":"error","name":""}`, and the wire
leaf is `{"error":""}`. The independent observer improvements do not
change the paired mutation's failure; all three fields are strings here.

The retained artifacts under this worktree's `.artifacts/codec/` are:

| Filename | Bytes | SHA-256 |
| --- | ---: | --- |
| `leaf-aaacaa5bb2d071c2a03340df.json` | 329 | `7dcfb245f49e52263fc909416ac0ca1059c075339cf4a4bf06b450989126d7a1` |
| `leaf-20ed59fac41b5ec549d280dc.json` | 350 | `5aaad7b02a93bb14f816a7d312e5b60d902da3c61e72d23bc2a529fe9b05f4b7` |
| `leaf-4258345fb66680b79d8b2c8c.json` | 401 | `d14b92774c9ad1249290d37fcde38b971f34b3fc2449d9261e3f9b03e6e662be` |

These ignored files are supplementary, not required to reconstruct any
input. The integrator preserved byte-identical copies under main's
`.artifacts/codec/` for local handoff. To replay them against the current
endpoint, run this from the repository root (use that checkout's absolute
path for `root`):

```python
import json
import subprocess
from pathlib import Path

root = Path("/absolute/path/to/p4blo")
divergences = 0
paths = sorted((root / ".artifacts/codec").glob("leaf-*.json"))
assert {path.name for path in paths} == {
    "leaf-aaacaa5bb2d071c2a03340df.json",
    "leaf-20ed59fac41b5ec549d280dc.json",
    "leaf-4258345fb66680b79d8b2c8c.json",
}, "expected exactly the three retained paired-mutation inputs"
for path in paths:
    saved = json.loads(path.read_text())
    result = subprocess.run(
        [str(root / "ir/.lake/build/bin/codec-leaves")],
        input=json.dumps(saved["request"]) + "\n",
        text=True, capture_output=True, check=True, timeout=10,
    )
    assert result.stderr == "", result.stderr
    actual = json.loads(result.stdout)
    agrees = json.dumps(actual, sort_keys=True) == json.dumps(saved["expected"], sort_keys=True)
    print(path.name, "agrees" if agrees else "diverges")
    divergences += not agrees
raise SystemExit(1 if divergences else 0)
```

Diagnostic logs: `/tmp/p4blo-codec-mutant-{decimal,zero,uint32}-{build,proof}.log`,
`/tmp/p4blo-codec-mutant-paired-{build,tests,replay}.log` and
`/tmp/p4blo-codec-restored-replay.log`. All production source mutations are
restored; `git diff -- ir/P4bloIR/Json.lean` is empty. No deliberate fault
belongs in the final commit.

## Gate evidence

Both Lean packages build/test/audit successfully after restoration, including
the temporarily registered native endpoint and codec audit. The existing
spec driver runs 392 checks; root registration adds the new codec checks to
that driver rather than treating the standalone run as already integrated.
Native codec
self-tests: **36 passed**. Focused Python/Lean/protobuf/observer gate:
**94 passed**, exit 0. Required real-Lean gate: **294 passed**, exit 0,
46.02 seconds. These include 48 new leaf probes. Independent read-only review
repeated all 94 focused tests, 36 native checks, five axiom audits and three
restored raw artifact replays successfully. Review is clear, recorded in
`notes/reviews/codec-leaves.md`, with mandatory root registrations remaining
an integration obligation.

Full ordinary gate: **1594 passed, 1 skipped, 5 xfailed**, exit 0, 342.15
seconds (`/tmp/p4blo-codec-full.log`). The skip is exactly the unavailable
optional XDP compile image (`tests/test_xdp_build.py:54`), confirmed separately
with `pytest tests/test_xdp_build.py -q -rs` (9 passed, 1 skipped). This task
does not build that image or claim the skipped gate succeeded. All five
xfails are existing strict external-oracle discrepancies. Formatting, lint,
types, schema/no-drift and workflow checks pass.

After those gates, the temporary Lake configuration was reversed by exact
patch and both it and production `Json.lean` have empty diffs. The proof/test
commit contains only the six owned new files; it does not claim fresh-checkout
default registration is complete until the integrator applies the steps above.
