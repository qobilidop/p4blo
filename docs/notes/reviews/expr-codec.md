# Actual recursive Expr codec review

**Final review: clear; chronological investigation follows below.**

Initial structural review in `p4blo-codec-recursion`: **no blocker found in
the helper/actual-decoder/proof seam**. Final restored tests and mutation
evidence are pending. Candidate binaries were not executed while the
implementer prepared deliberate codec faults.

`JsonBounds` isolates the pinned tree representation. Its structural child
bound does not assume map ordering, balancing or accurate cached counts.
The actual null-aware lookup lemma lifts that bound; synthesized empty
message defaults use a non-strict payload bound composed with a strict
enclosing oneof bound. This preserves missing/null decoder calls rather
than inventing a terminating fallback.

Bounded oneof selection scans the existing case list, in the same order,
collecting all recognized present fields before dispatch. Universal erasure
is proved against the actual previous helper loop, including nonobjects,
null absence, zero/multiple cases and exact diagnostics. Bounded message
erasure likewise includes errors. The actual existing `Expr.decode` is
replaced by well-founded recursion over finite JSON size with no fuel limit;
there is no competing proof-only decoder. `decode_unfold` gives its complete
proof-erased original body for arbitrary inputs/paths, keeping constructor
argument order. LValue/Stmt partial recursion is untouched and explicitly
remains future work.

`ExprRepresentable` covers embedded Literal/Type representability and both
uint32 slice indices recursively. It imposes no name resolution, positive
width, operand typing, slice ordering or packet semantic validity. The
universal roundtrip proof uses actual decoder unfolding and all constructors,
with explicit default omission cases where needed. Its claim is an actual
JSON-value left inverse, not raw-text/protobuf acceptance parity, binary
serialization or execution correctness.

The leaf observer extension retains complete requests and expected outcomes
on timeout, launch error, signal/nonzero exit, malformed/empty output and
invalid UTF-8, before failing. Byte timeout output is normalized safely;
previous JSON type-sensitive comparison remains. Fault classifier tests
inspect retained failure fields. Final review must inspect independent Expr
descriptors/known answers, pre-change exact transcript comparison and paired
wire-remapping mutations, since roundtrip correctness alone cannot establish
the intended wire mapping.

## Finding: operator descriptor shares the production wire mapping

The initial `exprValue` descriptor renders unary/binary operators with
`op.protoName`, which is also the production encoder's enum-name mapping.
A coordinated wrong enum-name table can therefore decode a wire name to the
wrong internal operator while both descriptor and re-encoded wire display
the original name. Roundtrip proofs and these purportedly independent
operator known answers could all survive. This is a concrete independence
gap in the observation, not a flaw in the limited left-inverse theorem.

Requested an independent exhaustive constructor-based operator observation,
without the production `names`/`protoName` mapping, and a selected shared-map
mutation to check that the corrected known answers distinguish actual
operators. Implementer and integrator informed; resolution pending.

## Finding resolved with a demonstrated survivor and kill

The actual shared unary table mutation swaps NOT and NEGATE. Inspected logs
confirm the original observer let it pass the full default proof build,
all **280 focused tests** and all **58 then-existing native tests**. This
was a real semantic survivor, not only a proposed thought experiment.

The descriptor now uses independent exhaustive constructor matches for all
three unary and nineteen binary operators, with no production table or
`protoName` call. A native explicit `.not` expected constructor was added.
The same live table fault still passes the default build/proofs but now
fails **two semantic Python cases**, with 278 controls passing, and one
native case with 58 controls passing. Both encoded-only comparisons still
agree, so the new independent constructor observation is the detecting layer.
The operator observer finding is closed.

## Final independent execution and compatibility evidence

After confirmed restoration, independently ran both focused codec files
with required Lean: **280 passed**, exit 0. Independently ran the actual
native endpoint self-test: **59 checks pass**, exit 0. Queried all five added
compiled audit roots; each has exactly
`[propext, Classical.choice, Quot.sound]`. The actual definition, arbitrary-
input proof-erased unfolding, helper erasures and universal representable
Expr theorem are all included in default audit coverage. No reviewer build
or intentional mutation was performed.

Independently matched all **59 pre-change transcript cases** against unique
tracked constructor/error fixtures and reran each on the restored endpoint:
stdout bytes, stderr bytes and exit status match exactly, and parsed results
match independent expectations. The saved baseline is 48,463 bytes, SHA256
`acb0802410c35aa7d6f6e4116ab3a17d8c633bf2f8220694c274ba4143e9dd4c`.
These finite checks are compatibility evidence, not an equality theorem to
the former opaque partial function; the final note makes that distinction.

Inspected the encoder-only index fault: actual codec builds but the actual
roundtrip proof rejects operand order. The paired index fault additionally
changes the decoder and, explicitly, the unfolding theorem's statement;
all proofs then build, but two independent semantic descriptors and one
exact first-error-order case fail (277 passing controls). The note honestly
records that wrong-model statement edit instead of implying the original
unfolding contract survived unchanged.

Independently checked all five saved mismatch artifacts against unique
tracked request/expected pairs, with successful child status and empty stderr
yet a genuine recorded mismatch. Replayed each with the current restored
binary: all five agree. Exact sizes and hashes match the final note:

| Group/file | Bytes | SHA256 |
|---|---:|---|
| `expr-index-paired/leaf-5210c6361fb4f8de97620702.json` | 1115 | `1353e3004dcb5864d05d6efe087675ef9d248c03dcee42e095fd8279854b9a09` |
| `expr-index-paired/leaf-b143ee239047b7921b520182.json` | 4417 | `64f518a375247d1aac96e0309a9dac4a3fe6651892bd37d73402c628ef15cda7` |
| `expr-index-paired/leaf-b7c50281137719ba82176bd5.json` | 457 | `34bbea956f16cc40352b06fffff575ab87b2759b7e21b841bc4314dd83aa624c` |
| `expr-enum-paired/leaf-23e370b27db86771c6194bc8.json` | 979 | `e0e6d1b45562244ca3cff124bd578f1b03648231c82694c4beee89a9d3f133e2` |
| `expr-enum-paired/leaf-9ef2080f4f438e938ac3e825.json` | 970 | `bcb7a7994f6fe6986f2dad957cbc64738ed3f179d11538f940e2a798d6d85835` |

The final replay recipe names all five inputs, checks their existence and
unique source identity, uses strict JSON parsing and bounded subprocesses,
and checks status/stderr/full observations. Command metadata is explicitly
diagnostic, never executed from artifact content. Mutation recipes survive
loss of local artifacts/logs; process-retention regressions also passed in
the independent focused run.

Inspected the completed full-gate log: **1834 passed, 1 skipped, 5 xfailed**,
`all checks passed`; implementer reports exit 0. The skip is the optional
unavailable XDP image and strict divergences are pre-existing. Both package
gates (451 spec checks) and required DRT (457 passes) are attributed to the
implementer, distinct from the independent checks above. Diff check is clean.

**Final disposition: clear.** No remaining review finding. This establishes
the stated finite-JSON totality, helper/unfolding laws and representable Expr
roundtrip, with improved independent wire observations; it does not prove
raw-text parsing, unlimited runtime resources, ProtoJSON policy parity,
recursive LValue/Stmt codecs or general Python/program correctness.
