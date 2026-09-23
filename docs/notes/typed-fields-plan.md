# Next proof slice: typed scalar fields

Independent design review, 2026-09-23, after the scalar-command increment.
This is a proposal, not implemented or verified functionality. Confidence
is high in the proof obligations below, medium in the public API factoring.

## Smallest useful milestone

Prove reads and writes to scalar leaves of metadata structs and nested
packet headers, initially in the existing no-action block-frame fragment.
Use an independent source store that contains aggregate shape, every stored
field value, and each header validity bit. Do not flatten a header to a map
of independent scalar names: that loses validity and sibling preservation.

First executable example: an already-parsed Ethernet/IPv4 value and metadata
record; copy destination MAC to source MAC, install a chosen destination MAC,
assign a nine-bit egress port, and update an eight-bit field. Include both
valid and invalid headers and preserve all unrelated fields and metadata.
An update using addition can reuse existing arithmetic initially; the actual
forwarder's TTL subtraction is a separate small operator/proof increment.
Do not call this a proved complete forwarder: parser, tables/actions,
checksum extern and deparser remain separate obligations.

## Inspecting the actual semantic traps

- `fieldOf` obtains positions through `run.index.fieldIndex?`; field spelling
  and runtime list order are both relevant. A typed source path alone cannot
  justify a read without an actual Index declaration-agreement premise.
- `Index.fields?` tries header types before struct types. Require matching
  nominal declaration kind and unambiguous names, not only agreement on a
  successful numeric field index. Duplicate field names must be excluded.
- `setField` uses `List.set`: a short runtime field list can make an update
  silently do nothing. Exact source/runtime shape correspondence must prove
  field-list lengths and selected-position existence before the write law.
- Invalid-header reads return stored fields. Writing a scalar field preserves
  header validity; it must not zero siblings or make the header valid. The
  independent source semantics must represent that exact p4blo contract,
  without claiming P4 portability for invalid stored-field observations.
- Nested `writeLValue` reads a container, rebuilds it, then recursively writes
  it back. Prove sibling and ancestor preservation at every level; preserving
  only the selected scalar answer misses lost siblings and validity bits.
- Permission belongs to the root variable's actual declaration. A field of
  an `in` or directionless root is not writable because its leaf is scalar.
  Keep `Modes.Agrees`-style evidence separate from exact runtime storage and
  retain the no-action-layer premise until layering/copyback is proved.

## Reuse one expression and command implementation

Do not copy `ExprIn`, its operators, `denoteIn`, or the command sequencing
machine into an unrelated packet-language AST. Two reasonable approaches:

1. Generalize the current finite source context to include scalar and
   aggregate shapes, and let typed read/write references include paths.
   Existing scalar contexts are a specialization. This is direct but touches
   the currently scalar-only type/context checker and many compatibility
   lemmas at once.
2. Factor the existing scalar-expression implementation over its typed read
   reference family, with scalar references and aggregate scalar paths as
   specializations. Likewise factor command writes over typed places and
   an independent store get/set interface. Keep the operator constructors,
   denotation and lowering as one implementation, with the old API exposed
   as aliases/smart constructors. This limits aggregate expansion to scalar
   leaves, but adds abstraction and explicit interface laws.

Tentative preference: **(2), only after field primitive lemmas are proved**.
The reusable source store/read/write algebra must be independently defined
and have concrete constructive instances; do not define denotation by IR
execution or hide the desired theorem in a callback premise. Factor only
the current read/update seam, not a general compiler framework. Record this
medium-confidence ergonomics decision before implementation; revisit if
Lean inference forces pervasive annotations in a realistic forwarding body.

## Suggested small commit sequence

1. Specification bridge lemmas for `fieldOf` / `setField` with explicit
   declaration position and exact container-shape premises. Prove successful
   scalar lookup, selected-value update, unchanged validity/type/name, and
   unchanged other list positions. No production semantic change needed.
2. Independent typed aggregate schemas/values and scalar paths. Prove total
   source get/set laws and source-to-runtime conversion. Add `IndexAgrees`
   for reachable named shapes, shape well-formedness, and constructive index
   plus value/frame witnesses. Distinguish these from general validated-
   program construction and `Frame.forBlock` initialization theorems.
3. Refactor the existing expression/command read/update seam once, retaining
   old scalar examples and proofs as compatibility tests. Instantiate path
   reads and writable path assignments. Extend the scoped typing boundary
   explicitly rather than pretending old scalar-variable typing covers a
   member expression. Preserve the same arbitrary-continuation proof style.
4. Independent known-answer forwarding-body fixtures and Python/Lean DRT,
   including every source field and validity bit in observations. Only then
   add ergonomic field notation; notation correctness still needs its own
   expected answers even when generic lowering proofs pass.

For path reads, prove exact converted source value and unchanged **entire
Run**. For assignments/commands, prove exact updated aggregate source store,
all header validity bits and siblings preserved unless explicitly targeted,
all unrelated runtime roots preserved, and every non-frame-value Run field
unchanged. Keep the actual Index fixed throughout. Existing continuation
prefix and successful-execute theorems should specialize from that bridge,
not be replaced by an alternative executor.

## Nonvacuity and adversarial acceptance

Include metadata-only and struct/header/nested-scalar cases; unequal sibling
values and unequal field widths; both validity states; absent/wrong-kind
Index types; duplicate names; reordered declarations; a short runtime field
list; readonly roots; and an unrelated aggregate outside the source context.
Malformed cases should fail construction/agreement or the scoped checker,
not be counted as successful executions under an impossible theorem premise.

Proof mutants: wrong lowered field, wrong numeric position, lost siblings,
or validity forced true. Runtime/surface mutants: same-width field accessor
alias that still compiles, Python setter clobbering a sibling, and Python
invalid-header field write marking valid. Distinguish proof rejections from
executable semantic detections. Observe full aggregate state, not only
emitted packets: an invalid header is not emitted, so packet-only comparison
can miss corrupted stored values. Save exact full programs/input sequences
before known-answer assertions and replay both live and restored cases.

No new stacks/indexed paths, aggregate assignment, validity-changing command,
parser extraction, tables, action parameters, call/copyback, architecture or
whole-program certificate is needed for this first increment.
