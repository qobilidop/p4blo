# KeyValue leaf codec review

Initial structural review of `p4blo-keyvalue-codec` against `d8e2341`:
**no structural blocker found; final clearance pending restored gates and
mutation/replay evidence**. This review has not executed candidate binaries
while the implementer's intentional paired codec mutation is active.

`KeyValueRepresentable` bounds only the LPM numeric prefix to uint32.
Exact values and ternary values/masks remain arbitrary naturals, and no
table resolution, prefix-width or mask-canonicality premise is smuggled into
the encoding domain. Constructor laws unfold the actual production
`KeyValue.decode`/`toJson`, reuse decimal and uint32 results, and combine into
an actual JSON-value left inverse. The zero-prefix omission case is explicit.
The aggregate theorem has an exact standard-axiom audit in the already
default-built `CodecProofAudit`; no alternate proof-only codec is introduced.

Kernel witnesses include representable semantically noncanonical keys and
an exact first-overflow diagnostic. The test-only leaf endpoint observes
decoded constructors through an independently named descriptor. Twenty-three
canonical wire fixtures include unequal ternary components in both orders,
zero components, large decimal values and LPM uint32 boundaries. Actual Lean
encoded objects pass through generated protobuf and the public Python IR
load/dump adapter, preserving previous type-sensitive JSON comparisons and
raw failure retention. Additional default, malformed and spelling probes
are accurately scoped as a decoder profile, not complete ProtoJSON parity.

The planned paired value/mask remapping is an appropriate challenge: a
left inverse alone can survive a coordinated wrong mapping. Independent
unequal component fixtures, including a direct native known answer, are
necessary to detect it. Actual outcomes and final restored checks will be
appended once available. JSON parsing, binary protobuf, recursive program
codecs and semantic key validity remain explicitly outside this theorem.

## Independently executed restored checks

After stable-binary confirmation, independently ran the complete leaf file:
**170 passed**, exit 0, with required Lean enabled. The native endpoint's
self-test passes **52 checks**, exit 0. Queried the compiled aggregate
theorem: exact intended representability premise and exactly
`[propext, Classical.choice, Quot.sound]`. Confirmed production `Json.lean`
has an empty diff after restoration.

Inspected the LPM-prefix mutation log: the actual codec compiles, while the
proof rejects changed definitional meanings in both zero and nonzero cases;
additional unused-simp lint failures are not the only reason for rejection.
This is proof rejection, not a runtime detection. The paired ternary field
swap builds the actual codec and proof audit, but six unequal canonical
fixtures fail independently and the direct native fixture returns reversed
components. Seventeen canonical controls still pass. The six live raw
replays retain wrong decoded descriptors even though every encoded-only
comparison agrees, demonstrating the necessity of the semantic observation.

Independently checked the exact six retained raw leaf artifacts against
unique tracked `key_leaves()` inputs and expected descriptors, requiring
successful exit/empty stderr and a genuine retained disagreement. Replayed
each through the restored actual endpoint with a bounded subprocess; all
six agree with their expected observation. Sizes/SHA256:

| Filename | Bytes | SHA256 |
|---|---:|---|
| `leaf-18e56d8b862a0266286f3853.json` | 593 | `ccf1fa56f7b19967918a8ffa6043c8a3de8a2a7715aa5320ab423d9f04d43fe1` |
| `leaf-68e095237e66c8a3f79f63a8.json` | 598 | `783a884433c09717243ca66c378debde0f131f543d3c136cb33bffacb8dabfa6` |
| `leaf-9c68fde7eae4a356c82cc1d6.json` | 1138 | `72940325b31784ecda94f8c288e1f79890b62fd73841b8e5fc1b88678ec89bbf` |
| `leaf-aa3823db33ca1f6c44357f8b.json` | 1138 | `4bda9ecd2e4ab5f4b82e7a0fa9a762be0ec6a4568b7d080fe98bab41c069bfa0` |
| `leaf-cd5e8a42776019052515b79f.json` | 593 | `eaa304e55005490e391fb38fdb3d5ff8efde0c2e3f5d6190209642b47a9ccf22` |
| `leaf-d7df72214cf72db4e3310ffc.json` | 598 | `1342a1e4664f412c8fbfc612f71d90187aee3f08c3cfa3e331a3d1e200da7c50` |

No intentional fault or candidate build was repeated by this reviewer.
Implementation/test review is clear. Subsequently inspected the completed
reproducibility note: exact isolated edits, independent named witness,
six artifact identities and a fail-closed explicit-name replay script are
present. The script checks missing inputs, subprocess status, timeout and
stderr and preserves JSON type distinctions. Hash rows match the independent
checks above. The distinction between proof rejection, paired roundtrip
survival and actual decoded-meaning failure is accurately recorded.

**Final review: clear**, subject only to the ordinary full-gate checkpoint.
The implementer reports 355 required DRT passes and both packages/audits
with 444 spec checks. These larger gate results are attributed; the focused
170/52 checks and six restored artifact replays above were independent.

Integration recipe follow-up: independently reviewed the main
`docs/notes/codec-proof.md` change from an exclusive directory glob to three
explicit original artifact names. The names are fixed and distinct, sorted
for deterministic replay, with all three required to be regular files before
execution. Additional KeyValue artifacts can coexist without a spurious
failure; an empty directory or any missing required artifact still fails.
**Clear**: no empty-glob acceptance or runtime/proof change is introduced.

Final candidate full-gate qualification is closed: inspected the completed
log ending in **1686 passed, 1 skipped, 5 xfailed** and `all checks passed`;
implementer reports exit 0. The skip is the unavailable optional XDP image,
and the five strict divergences predate this change. This is attributed
full-gate evidence, distinct from the independent focused checks above.
