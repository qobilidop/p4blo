# Small v0 codec proof increment

Read-only design check, 2026-09-23. Recommendation: prove leaf round trips
through the **existing** Lean JSON encoder/decoder, with explicit v0 wire
representability. Do not begin with a universal program codec, a new wire
framework, a replacement proof-only decoder, or changes to global parsing
policy. Confidence: high in this scope and decimal feasibility; medium in
the amount of object/oneof proof plumbing needed.

## Concrete implementation boundary

`ir/P4bloIR/Json.lean` implements actual `Ty.decode`, `Literal.decode`,
`KeyValue.decode` and corresponding `toJson` functions. These leaf decoders
are ordinary definitions. `Expr.decode`, `LValue.decode`, and `Stmt.decode`
are `partial`; their executable recursion is opaque for ordinary unfolding
proofs. The prose claim of finite-tree descent is not a kernel termination
proof. Do not conceal that barrier behind a second decoder used only in
the theorem.

`python/p4blo/ir.py` delegates `load_json` to protobuf `json_format.Parse`
and `dump_json` to `MessageToJson(..., preserving_proto_field_name=True)`.
It does not implement the same accepted-input language as Lean. The new DRT
duplicate/envelope hardening is separate and does not prove those languages
equal or change the public `ir.load_json` API.

The useful first theorem concerns **in-memory `Lean.Json`**:

```lean
Literal.WireV0Representable lit →
  Literal.decode path lit.toJson = .ok lit
```

Use the real named functions. It does not establish
`Json.parse (Json.compress j) = ok j`, byte-level protobuf correctness,
Python parser/compiler correctness, or valid-program execution. State this
boundary in the module, default audit, README and assurance note.

## Representability is not semantic validity

Prefer small predicates beside the leaf proof module, not a new package or
generic typeclass hierarchy:

- `Ty`: `.bits width` needs `width < 2^32`; `.stack name size` needs
  `size < 2^32`; other constructors impose no numeric restriction.
- `Literal`: `.bits width value` needs only `width < 2^32` for this wire
  theorem; `value` is encoded as an arbitrary finite decimal string. Other
  constructors need no additional restriction.
- Subsequent `KeyValue`: only LPM `prefixLen < 2^32`; exact values and
  ternary values/masks are decimal strings, not protobuf integer fields.

Do not require positive widths, nonempty names, resolved declarations,
`value < 2^width`, or a legal LPM prefix for a syntax-only round trip. Those
belong to validation. Conversely, do not silently modulo/truncate Nat
fields into uint32 to make an unrestricted theorem true. Encoding a Lean
`.bits (2^32) value` currently produces a JSON number that its decoder
rejects; preserve and test that counterexample. A large numeric width test
must exercise only the codec, never allocate/evaluate `2^width` values.

For future complete-program representability, constrain every protobuf
uint32 occurrence (including nested slice bounds, counts, priorities and
table sizes), not just types. Finite length/resource limits are an additional
execution policy, not a consequence of these mathematical predicates.

## First two independently reviewable increments

1. **Actual primitive and literal laws.** Add one focused proof module
   (for example `P4bloIR.JsonLaws`) with decimal and uint32 helper laws,
   canonical object/default lookup lemmas, a literal representability
   predicate and `Literal.decode_toJson`. Cover all literal constructors,
   especially Boolean false, bits zero and empty string names. Register
   theorem roots in the normal spec audit and ordinary test driver.
2. **Other finite leaves and independent interoperability.** Add
   `Ty.decode_toJson` (including zero-size stack and omitted defaults),
   then KeyValue if small. Exercise actual compiled Lean encoding/decoding
   and pinned protobuf parsing with independent expected leaf values.
   This may be combined with increment 1 if the resulting diff remains
   small; do not expand into recursive expressions just to fill a commit.

Object helpers should prove lookup on unique-key `Json.mkObj` objects,
including omitted defaults and singleton oneof fields. Existing pinned
`Std.Data.TreeMap.Raw.Lemmas` has `ofList_singleton`,
`getElem?_ofList_of_mem` and absent-key lemmas. A short finite oneof
selection lemma is preferable to copying its decoder loop. Keep field-name
uniqueness explicit if generalizing an object helper; `mkObj` is a map and
cannot itself preserve evidence of duplicate textual keys.

### Decimal feasibility checked, not just conjectured

The installed Lean v4.34.0 core already supplies:

- `Nat.toString_eq_repr`, `Nat.toList_repr`, `Nat.repr_ne_empty`;
- `Nat.isDigit_of_mem_toDigits`;
- `Nat.ofDigitChars_ten_toDigits`;
- `String.isEmpty_eq_false_iff`, `String.all_bool_eq`,
  `String.foldl_eq_foldl_toList`.

I compiled this universal probe through pinned Lean `--stdin` against my
review worktree's cached **actual** `Decode.decimal` (its definition is
unchanged on current main). It exits 0; axiom output is the standard
`[propext, Classical.choice, Quot.sound]`. No source or build cache was
modified, and no package was rebuilt/downloaded. An initial probe failed
only to unfold `Except.pure`; the explicit `change` below resolves it.

```lean
import P4bloIR.Json
import Init.Data.Nat.ToString
import Init.Data.String.Lemmas
open P4bloIR

theorem decimal_plan_probe (path : String) (n : Nat) :
    Decode.decimal path (toString n) = .ok n := by
  have nonempty : (toString n).isEmpty = false := by
    simp [String.isEmpty_eq_false_iff]
  have digits : (toString n).all Char.isDigit = true := by
    rw [String.all_bool_eq, Nat.toString_eq_repr,
      Nat.toList_repr, List.all_eq_true]
    intro c hc
    exact Nat.isDigit_of_mem_toDigits (by decide) (by decide) hc
  simp only [Decode.decimal, nonempty, Bool.false_eq_true, ↓reduceIte, digits]
  rw [String.foldl_eq_foldl_toList, Nat.toString_eq_repr, Nat.toList_repr]
  change Except.ok ((Nat.toDigits 10 n).foldl
    (fun n c => n * 10 + (c.toNat - '0'.toNat)) 0) = Except.ok n
  congr 1
  simpa [Nat.ofDigitChars, Nat.mul_comm] using
    (Nat.ofDigitChars_ten_toDigits (n := n))
```

This is a planning probe, not a committed proof deliverable. Recheck against
the implementation branch's current module and register the final theorem.
The uint32 numeric branch uses actual `Lean.Json.getNat?` with exact Nat
mantissa/exponent-zero encoding; it should not need decimal-string parsing
or a proof of arbitrary JSON number normalization.

## Restricted canonical output, not all ProtoJSON input

The chosen producer profile is snake_case fields, named enums, JSON numbers
for uint32, decimal strings for arbitrary values, omitted ordinary defaults,
and explicit set-oneof values even when false/zero/empty. Prove this output
round-trips; do not call it unique canonical bytes. Object order, escaping,
whitespace and protobuf binary serialization are separate concerns.

Accepted noncanonical inputs may normalize: e.g. decimal `"0007"` becomes
Nat 7 and re-encodes as `"7"`. Therefore no unrestricted
`encode(decode(json)) = json` theorem is appropriate. A later right-inverse
could be restricted to a defined canonical image, but is not needed now.

The official [ProtoJSON specification](https://protobuf.dev/programming-guides/json/)
accepts original and lowerCamelCase field names, numeric enum values and
numeric exponent forms, while default handling depends on presence. Lean's
handwritten reader implements a narrower/different language. Keep alias,
integer spelling, missing/null decimal strings and conflicting oneof cases
as acceptance-matrix tests; a canonical roundtrip proof does not settle them.

## Unknown fields and versioning remain explicit obligations

Lean `get?`/`emptyMsg` currently ignore unrelated keys; protobuf `Parse` in
`ir.py` does not enable unknown-field ignoring. The schema's reservation of
binary field numbers 100+ for nonsemantic annotations is not a license to
ignore arbitrary JSON names: JSON carries names, not those field numbers.
An unrecognized behavior-changing field must not become a silently accepted
old program. Neither namespace `p4blo.v0` nor replay envelope version 1 is
runtime semantic-version negotiation for a raw Program JSON document.

For this increment, name the proof profile v0 and freeze its mapping; add
no new envelope, annotation erasure, unknown-key relaxation or compatibility
promise. Separately choose an explicit annotation namespace/allowlist and
fail-closed semantic-version policy before claiming cross-version safety.
Changing that policy should include both loaders, diagnostics, replay
compatibility and independent negative cases in its own reviewed change.

## Acceptance and adversarial checks

Require audited universal leaf theorems plus independently specified vectors
through actual compiled Lean and Python protobuf paths. Include 0, 1, 9,
10, 99, 100, uint32 max and one beyond, a many-digit value above uint32,
false oneof, empty enum/error strings, zero stack size, and missing/null
decimal values. Keep malformed-but-representable leaf messages testable;
do not insert whole-program validation merely to drive the codec.

Cross-language checks must assert explicit payload/default presence and
expected decoded values, not only that the two sides agree. Consider a
small **test executable** importing the production Json module to decode
and re-encode tagged leaves; no new production CLI mode or alternate codec
is necessary. Its schema is test infrastructure, not another wire version.

Mutation targets: omit decimal zero; perturb the decimal accumulator;
change uint32 `<` to `≤`; erase false oneof; and paired encoder/decoder
remapping that preserves Lean round trips but violates independent protobuf
known answers. Record proof rejection separately from runtime kills. Save
the exact offending leaf JSON and intended abstract value when a codec
comparison fails; do not pretend an execution DRT bundle captures an
unrepresentable or invalid raw leaf it cannot express.

Before recursive codec proofs, refactor the **actual** recursive decoder to
well-founded recursion over JSON subtree size (preferred) or a genuinely
used bounded decoder with explicit fuel adequacy. Prove array/object lookup
descent and preserve diagnostics with regression tests. This is a later
implementation step, not a prerequisite for valuable leaf guarantees.
