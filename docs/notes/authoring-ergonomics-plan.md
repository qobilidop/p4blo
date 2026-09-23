# Next Lean authoring increment: names and command lists

2026-09-23. Read-only plan based on the reviewed concrete field-command
modules and `FieldCommandExamples`. No implementation or syntax is implied
by the illustrative API below. Land only after that interface is committed.

## Recommendation

Add two small typed smart-constructor layers: name-based scalar path
resolution and list-based command sequencing. Keep the same source Ref,
Place, ExprWith and CmdWith types and their existing meanings/lowering.
First use ordinary Lean functions; a custom parser/elaborator is not needed
to remove the most conspicuous friction. Do not add a second DSL AST,
monadic interpreter, schema declaration language or implicit packet state.

The current forwarding body is already readable once its references exist.
Its largest hazards are positional `.there`/`.field` chains (same-width
wrong selections can compile) and nested `.seq` parentheses. Address those
directly before committing to a larger `do`-like surface.

## 1. Resolve explicit path segments into existing typed references

Illustrative target:

```lean
def ttl : Place modes (.bits 8) :=
  Place.named ["hdr", "ipv4", "ttl"]
def nextDst : Ref roots (.bits 48) :=
  Ref.named ["route", "dst"]
```

The expected result fixes roots/modes and leaf type, keeping dependent-type
inference simple. Start with segment lists rather than splitting dotted
strings: field names are Strings and punctuation should not silently acquire
new escaping rules. Reuse the existing `Place.read` and `.read ref` surfaces.

Implement a total resolver over the independent source layout that returns
an existing `Ref roots t`, with a small explicit resolution-error type.
Require a nonempty path, exactly one matching name at each selected level,
aggregate intermediates and an exactly matching scalar leaf type. Reject
missing/empty segments, ambiguous duplicate matches, attempts to descend
through a scalar, aggregate endpoints and width/type mismatches. Never pick
the first/last ambiguous match, default to another field, truncate widths or
use an unchecked cast. The traversal may construct existing Slot/Path proofs;
it must not call the IR interpreter or manufacture a new layout.

The public checked constructor extracts a successful resolver result using
a kernel-checked proof, with a default `by decide` for concrete schemas if
feasible. A separate fallible function remains useful for clear diagnostics.
Do not use native evaluation as a proof escape. If `by decide` produces poor
diagnostics, improve that locally before introducing a custom elaborator.
Expected-type inference failing without a result annotation is acceptable
for this first layer; changing the whole representation to avoid every
annotation is not justified.

`Place.named` resolves the same Ref, then checks the selected root mode's
writability. A route input may be read but must not become writable because
its stored aggregate is mutable. Existing `Modes.Agrees` and `RootWellFormed`
premises remain required by correctness theorems. Successful resolution is
not global schema/index/declaration validity: in particular unvisited
duplicate names or cross-root nominal conflicts are not silently certified.

Prove a small naming-soundness result: successful resolution returns the
exact requested root/member spelling and requested scalar type. Define
reference spelling structurally from real Slot names/path components, not
by echoing the request. Relating the result's actual lowered expression or
lvalue to a direct root/member chain is a useful equivalent statement.
For a well-formed layout, successful resolution should be unique; completeness
for every valid existing named reference is a useful follow-up if small.
No new source-to-IR semantic proof should be necessary: the output is an
existing checked reference and existing theorems apply unchanged.

## 2. Sequence a readable list using the existing combinator

Add `Cmd.block` (name tentative) as a fold of `Cmd.seq`, ending in `.done`.
Keep its implementation once on `CmdWith`, with scalar/field adapters as
needed. This is a list combinator, not another command evaluator.

```lean
def rewrite : Cmd modes := Cmd.block [
  Cmd.assign dst (.read routeDst),
  Cmd.assign src (.read routeSrc),
  Cmd.assign ttl (ttl.read + bits[8, 255]),
  Cmd.assign port (.read routePort),
  Cmd.assign drop (.boolean false)
]
```

Existing `Cmd.ite condition yes no` combines such blocks for branches.
This removes nested sequencing parentheses while staying ordinary typed
Lean. Prove lowering equals concatenated component lowerings and denotation
equals the left-to-right fold of component denotations. Check empty and
singleton lists explicitly, and exercise dependency on earlier writes and
the shared tail after either branch. Refactor the forwarding/dependent
examples with an equality witness against the previous constructed AST or
lowered body; do not update expected answers to accommodate a change.

Avoid a general `Monad Cmd` or custom `do` syntax now. Lean `let` can name
host expressions, while packet-state reads remain explicit AST nodes; a
new binder syntax could easily suggest runtime locals/evaluation semantics
that the current IR fragment does not provide. A thin scoped notation can
follow only if ordinary constructors remain materially awkward and it
expands directly to these same checked operations.

## Acceptance and adversarial checks

- Kernel naming soundness and command-list composition roots belong in
  default audits. Existing scalar and field correctness premises stay intact.
- Explicitly typed negative elaboration cases reject missing/ambiguous
  names, empty paths, wrong width/kind, nonaggregate traversal, aggregate
  endpoints and input/directionless writes. Positive input reads remain.
- Keep independent source full-state answers and Python post-body snapshots
  unchanged. Check actual lowered field names, especially same-width dst/src
  and ttl/protocol, rather than only successful typing.
- Reordering a schema's unrelated fields should not change a named path's
  lowered spelling. Changing a spelling must fail or visibly choose that
  different requested field, never silently preserve an old numeric slot.
- Mutate name resolution to select a same-width sibling: the naming theorem
  should reject it; if a surface alias is deliberately changed consistently,
  independent known answers still must fail even when engines agree.
- Reverse a command list, skip a member or misplace a branch tail: distinguish
  composition-proof rejection from compiled known-answer/runtime detection.
  Retain actual DRT divergence inputs before known-answer assertions and
  replay restored inputs. Do not claim more mutation adequacy than exercised.

## Application intent is a separate proof need

Generic lowering correspondence proves faithful execution of the authored
program, not that its chosen fields or policy are the intended forwarder.
The compiled destination/source Place mutant already demonstrates this gap.
Treat a named `ForwardPolicy` theorem as a separate small checkpoint.

A complete independent Snapshot can expose all source scalar fields, both
header validities, route data and scratch through direct data constructors,
not the authored Ref accessors. Keep bounded scalar fields as Fin values,
or state explicit bounds if using Nat. Prove view/fromView inverse laws so
the observation cannot silently omit a field. Define the policy using
independent Boolean hit and Nat `ttl.val > 1`, direct record updates and Nat
predecessor, with miss/TTL0/TTL1 only setting drop. Full record equality must
preserve all other fields, including checksum, protocol, route, sentinels,
scratch and validity. Quantify over arbitrary source stores, not only the
fixed test initializer. Compose with the existing concrete execution theorem
to lift the policy to final frame values and unrelated runtime preservation.

Do not add a valid-header assumption absent from the current authored body;
its rewrite also acts on stored fields of invalid headers. State that scope
plainly. Parser success, route lookup, checksum recomputation and architecture
forward/drop behavior remain unproved, even with a correct local policy.
Deliberately alias dst to src to ensure this independent policy rejects the
wrong well-typed authored intent.

## Checkpoints and confidence

1. Total typed name resolver, naming theorem and negative/known-name tests.
2. Command-list combinator/proofs and unchanged example refactor; then full
   existing authored gates and selected mutations.
3. Independent named forwarding policy, reviewed separately from ergonomics.

High confidence in retaining the existing representations and proof boundary;
medium confidence in the exact named-constructor API and default proof
diagnostics. Revisit if callers need repeated transports/casts, failed
resolution messages obscure the missing segment, or every declaration
requires repeated roots/type annotations. Only then consider a minimal
elaborator that emits the same checked constructors, with independent
surface known answers. Do not solve an ergonomic problem by weakening
resolution checks or duplicating source semantics.
