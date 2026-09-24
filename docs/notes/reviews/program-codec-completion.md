# Remaining Program codec plan review

Final planning review: CLEAR. This approves staged scope and feasibility,
not registered parser or whole-Program codec coverage.

2026-09-23. Read the complete plan and ParserCodecProbe in
`p4blo-program-codec-completion` at `634a21a`, plus every remaining actual
decoder/encoder in Json.lean. Only the two planning files are untracked;
production codecs/default registrations/tests remain unchanged.

## Coherent dependency slices

The five parser-syntax messages form the smallest coherent next DAG: Target,
KeySet, SelectCase, Transition and State compose committed Literal/Expr/Stmt
and array laws. Their definitions are already total; no new recursive decoder
or termination argument is hidden here. Action/Block then Export/Program are
appropriate separate baseline/proof checkpoints. TableEntries/Entries are not
Program members and remain an explicitly separate optional pair.

The dependency table accounts for every actual Program field and inherited
numeric bound. New wire predicates must preserve empty/unresolved/duplicate
names, cyclic targets, unequal select arities, mixed KeySet literal types and
descending ranges, unusual statement placements, all Directions/BlockKinds,
and invalid semantic export/error/declaration combinations. No validator or
index success premise is smuggled into codec roundtrip. Optional host-default
presence and Program's successful empty-object decode are correctly separated
from application validity. JSON text parsing and binary protobuf remain outside
the JSON-value theorem.

## Actual proof and defaults

The standalone probe uses actual existing codecs throughout. Target is
unconditional; KeySet/Transition/State carry only their embedded wire bounds.
List composition preserves order, object-shape exposure is explicit, and no
member-correctness callback, alternate serializer, admitted theorem or raised
limit is introduced. The mixed State witness exercises all target/set families,
unequal types/arity, nested statement branches and boundary numeric members.
Twelve kernel anchors agree with the actual decoder's empty/null/oneof/default
behavior, including empty Program and host entries; they are not promoted to
universal assembly laws.

Independently executed the final absolute probe against its stable own compiled
CodecLaws with pinned Lean v4.34.0 and `-DwarningAsError=true`: exit 0,
0.60 seconds. All six named roots print exactly propext, Classical.choice and
Quot.sound. No candidate library build, source mutation or executable consumer
was required. The initial failed elaboration/sorryAx output is explicitly
excluded by the plan and is not part of this acceptance.

## Independent evidence and later proof plumbing

The baseline-first, source-pinned, immutable ordered inventory procedure is
appropriate. Literal native constructor anchors remain independent of both
production mappings and Python expectations; asymmetric operands/lists and
malformed-input error order address paired roundtrip survivors. Planned
accept/reject and operand-pair mutations correctly distinguish proof rejection,
stronger intermediate lemma failure, compiled wire-intent errors and actual
runtime mismatches. Historical hashes and repeated observations/views are not
counted as new inputs.

The later Block/Program object proofs may reuse the proved lookup/omission
technique, but current Table helpers are private rather than a public API.
A narrowly reviewed helper extraction with old laws rechecked is preferable
to mangled private-name imports, copied decoders or exponential omission splits.
That ownership expansion is deliberately not needed for the parser slice.

Confidence is high in the next five-codec proof boundary, supported by the
complete probe; medium-high in later composition, whose observer breadth and
object factoring still need implementation review. No conceptual blocker or
required plan correction found. Full package/Python/schema/oracle gates are
not claimed for these two planning-only files.
