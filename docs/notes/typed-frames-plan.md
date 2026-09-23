# Next increment: typed scalar frames and statements

Investigation: 2026-09-23, after verified closed scalar lowering at
`52fbebb`, against specification interface `4b64497`. This is a scoped
implementation proposal, not implemented code or a new proof claim.
The integrator owns the namespace migration; names below use its intended
result: `P4blo` is the user library, `P4bloIR` the specification. At the
inspected commits those namespaces are `P4bloLean` and `P4blo` respectively.

## Recommendation

Checkpoint 2026-09-23: increment 1 is implemented in `cb69a86` and
`faa373f`, integrated at `46893ff`. See `../../lean/ASSURANCE.md` and
`reviews/typed-frames.md` for actual theorem boundaries and evidence.
The investigation below remains the rationale; increment 2 is next.

Make the next useful milestone a **verified scalar block-body fragment**:
typed variable reads, scalar assignment, sequencing and boolean conditionals.
Finish it in two independently reviewed increments:

1. Context-indexed expressions with exact meaning preservation under an
   explicit typed-frame relation, plus context-aware scalar checking in the
   specification.
2. Writable scalar places, assignment/sequence/if, with total source state
   semantics and a finite-trace proof into the existing production executor.

This is enough to author a real dependent update such as `x := x + 1;
y := x + y`, prove its result for arbitrary initial values, and exercise
it through both interpreters. It is not yet enough for the forwarder or
stateful firewall: header/metadata paths, packet operations and extern
contracts follow. Do not call the fragment a verified complete control,
program compiler, or whole-program validator.

Confidence: **high** in this boundary and execution-proof strategy;
**medium** in the precise context representation and API syntax. Revisit
representation when the first field/reference or action-parameter example
exposes needless transports or name-management friction. Do not pause
implementation waiting for that future choice.

## What the existing code actually does

Inspected `ir/P4blo/{ScalarTyping,Env,Eval,Exec,Interp,Index}.lean`,
`ir/Tests/{Execution,Interp,ScalarTyping}.lean`, the user scalar library,
`python/p4blo/interp/env.py`, and the validator's assignment/lvalue checks.

- `Frame.read?` first tries `actionVars`, then `vars`. A missing read raises
  an interpreter fault; it does not return zero. Zero initialization occurs
  in `Frame.forBlock`, separately from reads.
- `Frame.write?` writes an existing action binding first, otherwise an
  existing block binding, and returns `none` if neither exists. It does
  not create arbitrary new variable names.
- `readVar`, `writeVar`, `.var` evaluation and `.var` lvalue writes already
  expose proof-visible definitions. Unlike the derived scalar equality
  issue, no new evaluator implementation is needed for variables.
- Runtime writes do **not** enforce parameter direction or declared type.
  Python's validator rejects writes to `in`/directionless parameters and
  mismatched assignments. A source place must therefore carry permission,
  not merely a name and a scalar type.
- `Index.build` checks names, not complete type validity. `Frame.forBlock`
  looks up a scope and creates zero values from its declarations; claiming
  it establishes arbitrary source contexts without a theorem is unsound.
- Assignment evaluates the RHS before invoking `writeLValue`. `.conditional`
  evaluates its condition and schedules only the selected statement list.
- `execute` is `Execution.run [.statements body]`; it uses the existing
  total `step` and proof-visible `drive`. `Finishes.sound` already connects
  finite traces to the actual executable runner. Do not introduce a second
  recursive reference statement interpreter or semantics-changing fuel.
- Action entry/return and block call/copyback have distinct layering and
  fault behavior. The first writable fragment should run in a block frame
  with both `action = none` and `actionVars = none`; it does not cover calls.
- Existing `ScalarTyping.Typed.sound` proves global computation purity for
  *closed* terms. Variable-dependent expressions cannot satisfy
  `evaluate e = pure v` for one fixed value across all frames. The new
  theorem must quantify an environment and a related initial Run.

Pinned Lean's `Std.Data.HashMap.Lemmas` provides `getElem?_insert`,
`getElem?_insert_self`, `contains_eq_isSome_getElem?`, and associated lookup
lemmas. Use those rather than inspecting hash buckets or redefining maps.
Their existence was inspected; no new proof was compiled in this study.

## Contexts, references and independent values

Use one finite context with distinct, nonempty IR names. Each binding has
a scalar type and read/write capability; every bit width is positive.
Declarations and names are supplied once. Human code subsequently uses
typed reference objects, not repeated string lookup or a cast from strings.

Recommended initial representation: a list of bindings with a well-formedness
proof, typed positional membership for `Ref Γ t`, and a corresponding
heterogeneous list of values for `Env Γ`. A writable `Place Γ t` is a
reference plus evidence that its binding permits writes. Names are a
lowering concern; source evaluation reads the positional environment.
Keep this representation private enough that ergonomic syntax can change.

Source values remain `Fin (2^width)` and `Bool`; environment lookup and
update operate on those values, not `P4bloIR.Value` or `Run`. A source
statement's meaning must not be defined by calling the IR executor.

Parameterize the existing source expression datatype by `Γ` and add a
reference constructor. Keep one recursive definition of its arithmetic,
equality and mux semantics. Preserve the closed API as an empty-context
specialization or migrate the small existing examples explicitly; do not
keep two almost-identical closed/open compilers indefinitely. A small
`ClosedExpr` alias is preferable to a second AST plus an opaque escape hatch.

Confidence: **medium** on positional references/heterogeneous environments.
They make source aliasing and update identity independent of string hashing.
Revisit if elementary lookup/update laws become dominated by equality
transport machinery; a finite typed name-map representation is acceptable
provided uniqueness and source semantics remain explicit. Do not adopt SSA
or a generic compiler framework solely to avoid these small proofs.

## Three distinct relations, not one overloaded validity claim

1. **Context well-formedness.** Unique nonempty names, positive bit widths,
   consistent declared capabilities. This concerns source construction and
   the representable scoped fragment, not all program declarations.
2. **Declaration agreement.** Each context binding resolves through the
   actual `BlockScope` to the declared scalar type. A writable binding must
   be a local, `out`, or `inout` parameter. Bindings may be a subset of the
   frame: unrelated headers, metadata and locals are allowed. Block-level
   name collisions with other declarations still need a validated wrapper
   or a future global validity theorem.
3. **Value agreement.** For every reference, the actual frame lookup returns
   `some (toValue (sourceEnv.lookup ref))`. This is stronger than merely
   finding a value with the right type. Exact correspondence is required
   to prove the intended result of `x + y`.

For read-only soundness of the specification checker, a weaker relation
(`Γ(name)=t` implies an existing value with `HasType value t`) is appropriate.
It can use actual `Frame.read?`, including action precedence. The stronger
user-library correspondence specializes that relation to exact source
values. The first statement theorem additionally assumes the inactive
action layer; do not silently flatten active action storage.

Construct related states, do not only assume them: prove an initializer
or finite map installation establishes value agreement for every source
environment, and test its connection to `Frame.forBlock`. Otherwise an
inconsistent frame predicate could make all compiler theorems vacuous.

## Increment 1: scoped expression obligations

In the specification, generalize the existing scalar typing relation to
`TypedIn Γ e t`, and the checker to `checkIn Γ`. Preserve `Typed`, `check`,
and `infer` as empty-context interfaces where practical. Reuse
`unaryType`, `binaryType`, `castType` and the current constructor rules.
Avoid adding a competing scalar type checker with its own operator table.

The new variable rule resolves the name in the well-formed context.
Missing names, zero-width bindings and ambiguous/duplicate contexts must
fail before they can produce typing evidence. A raw function from names
to types alone is not an executable validator of these context conditions.

Required proofs:

- `checkIn_sound`: acceptance gives contextual typing evidence.
- `checkIn_complete` for the declared scalar fragment: every derivation
  is accepted with its type. This is scoped completeness, not acceptance
  of lookahead, aggregate expressions, enums, or all valid P4 programs.
- Contextual typed evaluation: for a type-related frame, evaluation
  succeeds at the inferred type and preserves the entire initial Run.
  Re-establish the old closed checker theorem as a specialization.
- Reference lowering resolves the expected IR name and declared type.
- `lower_typed`: a source term lowers to `TypedIn Γ` at its source type.
- **Exact expression preservation**, schematically:

  ```text
  FrameMatches Γ env initial.frame ->
    (P4bloIR.evaluate (lower e)).run initial =
      (ok (toValue (denote env e)), initial)
  ```

Do not replace the last equality with existence of any correctly typed
result. Test two distinct related environments for the same compiled
expression, not just a hardcoded singleton environment.

The old `PureTyped` helpers are useful for the closed specialization but
cannot be applied unchanged to open subexpressions. Add small lemmas for
evaluation of monadic compositions under a fixed related Run; reuse the
existing operator definitions rather than copying their implementations.

Confidence: **high** on obligations, **medium** on proof refactoring cost.
If threading context through all existing scalar operators proves too
large for one commit, split the generic relation/checker change from the
source reference extension. Do not weaken exact value correspondence.

## Increment 2: assignment, sequence and if

Add a small source `Cmd Γ` with writable scalar assignment, sequencing
(or lists), and same-context boolean conditionals. Its independent total
meaning is `Env Γ -> Env Γ`, recursively evaluating RHS expressions before
updating the selected binding. No loops, declarations inside the body,
aggregate paths, calls, extern operations or packet operations yet.

Add a syntax-directed specification predicate for this **statement
fragment**, reusing `TypedIn` for its expressions. Writes require a
writable context binding of exactly the RHS type. If this relation lives
in a new module, it still belongs to `ir/`; the user library must not
quietly become authoritative for raw IR validity.

Required proof dependencies and results:

1. A successful existing-binding write updates exactly that scalar slot.
   Prove lookup-after-update for the same reference and every other one;
   distinct IR names are essential. Preserve declaration agreement.
2. Expression reads do not change the Run; assignment preserves value
   agreement with the updated independent source environment.
3. The statement fragment preserves its typed frame and cannot raise a
   parser or interpreter fault under the stated premises.
4. Construct a finite prefix trace of the actual `Execution.step` for
   each source command, leaving an arbitrary continuation untouched.
   A small generic `Steps` relation plus composition lemma is acceptable
   in the specification; it is evidence about existing steps, not a new
   evaluator. This avoids assuming that unrelated continuations terminate.
5. Instantiate the prefix result with an empty continuation and apply
   `Finishes.sound` to prove the actual `execute` returns successfully.
   The source environment after execution equals `denoteCmd cmd env`.
6. State noninterference explicitly: `index`, `entries`, `externs`, packet,
   emitter, parser visits, scope and action-layer fields are unchanged;
   all unassigned runtime bindings retain their values. Do not demand
   structural equality of independently rebuilt hash maps when pointwise
   equality of values plus exact unchanged Run fields is the real contract.

This yields termination **for this finite statement fragment**, not for
all validated programs. Reusing the existing machine makes the conclusion
about the same production interpreter the differential tests execute.

## Acceptance experiments and adversarial checks

First authored example: increment an 8-bit `x`, add the new `x` to `y`, and
set a boolean flag when the new `x` is zero. Independent answers include
`(255,7) -> (0,7,true)` and `(3,7) -> (4,11,false)`. The second case catches
accidentally using the old `x`; the first catches missing modular wrap.

- Keep every existing closed-scalar test and audit. Add rejected unknown
  references, mismatched widths/types, read-only assignment, duplicate or
  empty names, invalid context widths, and mismatched conditional branches.
- Test missing runtime bindings and wrong-width values as **rejected frame
  correspondence/initialization**, not silently normalized good states.
  Include unrelated variables and nonempty packet/emitter/extern/visit state
  to exercise noninterference; the universal theorem remains the primary
  guarantee, not equality on one empty frame.
- Export compiled bodies into small independently validated packet wrappers.
  Initialize locals from controlled input, execute the source body, and
  expose all output locals in headers for Python/Lean comparison. The raw
  test wrapper is outside the lowering proof until a later program theorem;
  say so explicitly. Reuse the existing DRT protocol and replay bundles.
- Mutate variable-name lowering to another same-width variable; reverse
  statement order; write the wrong target; skip a write; invert an if.
  Update typing derivations where necessary to ensure exact semantics,
  rather than merely old syntax, are what reject a bad compiler.
- Mutate the source reference/place elaborator while leaving the typed
  core compiler intact. Independent known answers must catch the resulting
  valid-but-wrong source program even when both interpreters agree.
- Mutate Python reads/writes separately after the fragment exists; require
  an executable differential mismatch and a replay. A proof rejection or
  build failure does not count as a Python/Lean semantic test kill.
- Audit every advertised theorem's transitive axioms; run both package
  gates, required discovered DRT, full Python/schema/oracle checks and an
  independent read-only review before integration.

## Deliberately next, not hidden in this increment

Typed paths into headers/metadata are the first extension after scalar
locals: field declarations, validity preservation, and rebuilding parents
need their own relation. Header-stack indexing adds bounds/no-op writes and
evaluation-order obligations. Extern calls require contracts over persistent
state and returned values. Action/block calls add layered frames, parameter
directions, alias restrictions, copyback and fault unwinding. The inspected
runtime already defines these behaviors; extend proofs to it instead of
replacing it with a simpler incompatible machine.

The highest-priority revisit trigger is the first readable Lean forwarder
or firewall body: if scalar locals lead to cumbersome manual field wrappers,
move typed scalar **field paths** ahead of further arithmetic operators.
Confidence: **medium** on that sequencing, **high** that proving every
scalar operator before any packet field would delay practical authoring.

## Investigation evidence

Read-only inspection only, plus this planning document. No implementation
changes, experimental proof compilation, tests, semantic mutations or
commits were performed for this investigation. Existing gate results in
`lean/ASSURANCE.md` belong to the earlier scalar increment and do not
validate this proposed design. Resume by reviewing this plan alongside
the completed namespace migration, then implementing increment 1.
