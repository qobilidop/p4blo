# Next bounded bridge: actual frame initialization

2026-09-23. Read-only recommendation after field bodies, named authoring and
the local ForwardPolicy theorem. Inspected actual `Value.zeroWith/zero`,
`Frame.forBlock`, block dispatch/argumentValue/copyBack, Modes and the field
fixture wrapper. No code edits, probe compilation or candidate builds.

## Recommended next checkpoint

Prove independent aggregate zero values correspond to actual `Value.zero`,
then prove the actual `Frame.forBlock` produces their matching action-free
frame under explicit real scope/index conditions. Instantiate that result
for the mixed forwarding declarations. This removes a concrete assumption
currently supplied by hand-built `Modes.frame` witnesses and finite runtime
examples. It is smaller and more reusable than proving a whole call wrapper
at once, while directly enabling that next application bridge.

Do not add a competing runtime initializer. A structural zero *source value*
is appropriate: zero Fin scalars, false Bool leaves, false header validity,
Unit struct validity, recursively zero source records. Prove its conversion
equals the existing production initializer; ordinary execution continues to
call the same `Value.zero` and `Frame.forBlock` functions.

## Explicit obstacles and honest premises

1. **Actual zeroing is fuel-bounded.** `Value.zeroWith` consumes one unit
   even for scalar values, and `Value.zero` supplies
   `index.headerTypes.size + index.structTypes.size + 2`. Define a structural
   maximum source-shape depth and prove `zeroWith` correspondence when the
   fuel is sufficient and the real nominal Index agrees. For the first
   `Value.zero` corollary require the explicit depth bound, then discharge it
   for the concrete forwarding shapes. Do not assume IndexAgrees alone has
   already proved the global acyclic nominal-count bound. Deriving that bound
   generally is a separate theorem, not a reason to change runtime fuel.
2. **Actual initialization visits every scope variable.** `Modes.Agrees`
   only accounts for modeled roots. An extra declaration can fail zeroing,
   even if every modeled root is valid. The fixture's observer and unrelated
   local are such extras. A general frame theorem needs actual zero-definedness
   for all scope declarations, not merely the modeled subset. A corollary for
   an exactly covered Modes scope can discharge this from source-zero laws;
   the concrete wrapper must explicitly discharge its finite extra declarations.
3. **Scope lookup is authoritative.** `Frame.forBlock` looks up
   `index.scopes[block.name]` and uses that scope; it does not itself verify
   `scope.block = block`. Preserve this behavior. State exact lookup/scope
   consistency premises where a block-body conclusion needs them. Do not
   infer general Index.build/global semantic validation from a hand-built map.
4. **Hash-map representation is not the conclusion.** Prove exact lookup
   contents (including no undeclared extra bindings), actual returned scope
   and `action = none`/`actionVars = none`. Avoid equality to an independently
   rebuilt HashMap with an assumed insertion order. Use the actual for-loop
   and finite `scope.vars.toList` lookup/uniqueness facts.

A useful generic IR-layer frame statement is: given actual scope lookup and
successful actual zeroing for each declaration, `Frame.forBlock` succeeds;
each returned variable lookup is exactly that declaration's zero value,
missing names stay absent, its scope is the looked-up scope, and it is a
BlockFrame. Its premises are per-type initialization facts, not an assumed
whole-frame correctness callback. The user-package source-zero theorem
then supplies those facts and derives `FrameMatches (sourceZero roots)`.

For the real forwarding example, discharge scope lookup/declaration agreement
from an actual successful `Index.build` on its concrete declaration program,
with a checked finite witness or narrow computation lemmas. A universal proof
of Index.build and the validator is not necessary for this first useful
instantiation. Preserve the distinction between kernel witnesses and native
tests; do not promote native checks into logical initialization theorems.

## Immediately useful follow-up: call entry and body prefix

After the frame bridge, prove a bounded **sub-control entry plus authored
body prefix**, not a general call theorem. Start with the actual forwarding
wrapper's plain root arguments: hdr/meta inout, route input, observer inout,
scratch and unrelated locals. Keep caller roots disjoint for writable
arguments. Permitted input-snapshot overlap and arbitrary member arguments
can stay separate; action calls have an action layer and are not this theorem.

Use the real `Execution.dispatch (.block ...)`: it checks block lookup and
argument count, initializes a fresh frame, evaluates argument values in the
caller before installing the callee, then queues `runBlock` and `blockReturn`.
Prove exact parameter binding by these actual operations and the source
input conversions. All required argument reads must preserve the entire Run;
an out parameter uses actual zeroing, never caller contents. Fresh callee
initialization supplies the body theorem's no-action premise; retain explicit
caller no-action assumptions for this bounded wrapper rather than quietly
claiming action-layer compatibility.

Compose local scratch initialization and the existing typed body's arbitrary-
continuation prefix. Stop **before observer statements and blockReturn**, with
the pending observer/copyback continuation stated exactly. This establishes
that real call entry reaches the intended policy state, while honestly leaving
observer serialization, caller restoration and copyback outside the theorem.
The existing policy theorem can describe that state without another evaluator.

Only then add normal-success copyback for disjoint writable plain roots,
using actual `copyBack` and preserving read-only arguments/unrelated caller
storage. The established argument-count guard matters because `copyBack`
uses zip. General writable aliases are validator errors, not an interesting
valid execution-order case. Parser-fault unwinding/copyback and action return
must remain separate from the normal sub-control result. Existing runtime
call-copy DRT provides useful tests, not these absent proofs.

## Independent acceptance and faults

- Exact independent expected zero stores for mixed fields, empty headers,
  nested structs, both scalar kinds, widths 8/9/65, and every declaration mode.
  Out/inout/input all start zero in Frame.forBlock; parameter binding changes
  their values later. Include unexpected extra declaration zero failures,
  missing scope and too-small fuel as explicit boundary checks.
- Mutate actual zeroing to valid headers, wrong nominal kind/name, nonzero
  siblings or wrong scalar widths. Distinguish source-zero proof rejection
  from compiled Python/Lean divergence. Full stored values/validities must
  be observed, not only emitted valid headers.
- Mutate actual frame construction to drop a variable, initialize the wrong
  name, or add an action overlay. Exact lookup/no-action statements should
  reject these; independent frame tests must not reuse its construction code.
- For the later entry bridge, swap unequal argument bindings, copy caller
  contents into out, lose packet/emitter/entries/externs/visits, or fail to
  initialize scratch. Test full state after entry/body before observers,
  retain mismatches first, and replay live/restored. Input-header alias faults
  need the existing snapshot-sensitive call tests, not only scalar outputs.

Confidence: high that per-shape zeroing plus exact forBlock lookup facts are
the smallest meaningful premise-discharge step; medium on HashMap fold proof
cost and automatic nominal-depth bounds. Prefer a concrete forwarding-scope
instantiation over building a general block/call framework if those costs
grow. Revisit once the initialized body prefix is established; the priority
is fewer unproved application assumptions, not more authoring surface APIs.
