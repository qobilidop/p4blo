# Next forwarder proof: actual selected-action execution

2026-09-23. Read-only follow-up to lean-forwarder-next.md at main7dbb4f0.
Inspected actual Execution.dispatch, Frame.read?/write?, field and generic
command proofs, and the Python corpus action. The authoring owner reports
`P4blo.Forwarder` with real layouts, named refs, `forwardAction`, `ingress`
and `program`; this plan did not access its worktree or binaries. Proposed
names below are provisional until that interface is committed and reviewed.

## Choose the actual table-action boundary

Start with **selected table action**, not table lookup and not direct action
calling. The corpus executes `Execution.Work.tableAction` / `runActionCall`:
the two directionless parameters are populated from literal action data.
This is different from Work.action/callAction, which evaluates expression or
lvalue arguments and queues optional success-only argument copyback.

The desired theorem begins with:

```text
tableAction { action := "ipv4_forward",
              args := [bits48 newDst, bits9 port] } :: K
```

It ends with exactly K, no fault, the independent rewritten headers/metadata
in the original block store, original action layers restored, and the entire
remaining Run unchanged. First prove Steps with arbitrary K, then derive
actual `runActionCall` completion for K=[] using existing Finishes.sound.
No table-selection correctness callback or alternate action executor belongs
in its premises.

## Small first prerequisite, not a new frontend

The current field write and generic command operational theorems require
BlockFrame. That premise is false **inside** an action; its removal is not
just a typing annotation change. FieldTyping also deliberately excludes
action declarations. Do not claim its block-scoped body-typing proof for
`dstAddr`/`port`.

Add a small authoritative `writeVar_block_unshadowed` law over actual
Frame.write?: if the name is absent from the active action map and present
in block vars, actual writeVar changes exactly that block-map entry while
preserving action, actionVars, scope and all other Run fields. It should not
require the action map to be absent. Separately check the action-hit branch
of read/write lookup, so block-first bugs cannot be hidden by name choices.

For this body, fresh actionVars contains exactly dstAddr and port; hdr/meta
are unshadowed. Existing aggregate Path.writeLValue laws can lift the new
root law, and existing Ref.evaluate already uses actual action-first
FrameMatches without BlockFrame. If a reusable FrameMatches update lemma is
needed, generalize only its written root's nonshadowing premise; other roots
may legitimately live in the action layer. Preserve existing block APIs as
corollaries rather than silently broadening their statements.

Then prove this fixed four-statement body's prefix directly from the actual
statement equations and these leaf laws. It is small enough that a general
action construction API is not a prerequisite. This is a proof over existing
IR, not a competing source interpreter. Do **not** duplicate CmdWith or remove
its BlockFrame requirement by assertion. A later typed-action client can
generalize the one generic induction to a preserved frame invariant and add
actual action-aware declaration/permission rules in a separate checkpoint.

## Independent policy and actual trace

Define `ipv4ForwardPolicy` on the real forwarder header/metadata shapes plus
`newDst : Fin (2^48)` and `port : Fin 512`, independently of authored Ref
accessors, lowered syntax and IR execution:

```text
egress_port := port
ethernet.srcAddr := old ethernet.dstAddr
ethernet.dstAddr := newDst
ipv4.ttl := (old ttl + 255) modulo 256
```

Preserve every other stored field, both header-validity bits, ingress_port,
drop, and the checksum's old stored value. An action alone does not recompute
checksum, clear drop, or test validity/TTL. Cover arbitrary validity and TTL0
in the theorem; table/control guards are separate. Use direct source-record
constructors/independent named projections, with asymmetric kernel anchors
for old source, old destination and new destination.

The actual action body must remain exactly egress write, source-from-old-dst,
destination write, then **IR subtraction** by bits8 1. A modular add255 policy
is mathematically independent of that lowering, not permission to change the
golden opcode. Prove its correspondence to actual bits subtraction.

The finite trace is small and concrete:

1. Real tableAction lookup/arity check, literal binding and frame installation
   queues `.statements forwardAction.body :: .actionReturn outer none :: K`.
2. Four assignments take eight real list/statement transitions.
3. Empty-list pop takes one transition; normal actionReturn takes one.

Thus a successful selected action takes **11** transitions to K. The return
keeps the **inner updated block vars** and restores only outer.action and
outer.actionVars. Restoring the entire old outer frame would erase the work;
using blockReturn/copyBack here would prove the wrong semantics.

## Premises and constructive witness

Use the real committed Forwarder program's Index.build result and actual
MyIngress scope/action declaration lookup. State exact declaration/body/param
identity and two-argument lengths, rather than assuming a fake scope accepts
the action. Arbitrary Run shared components remain quantified.

For the first public application theorem, require an action-free **outer
control frame**, exact actual MyIngress scope, hdr/meta values matching the
independent real shapes, and their nominal Index agreement. Initial block
storage may contain unrelated bindings. The actual forwarder has no control
locals: the checksum extern writes hdr.ipv4.hdrChecksum directly, not through
a checksum temporary. Do not introduce a synthetic local as a real declaration. No
BlockFrame premise is applied to the installed action frame. A lower-level
normal action-return equation may allow arbitrary outer layers, but do not
turn that into a claim that nested action calls are valid programs.

Provide a nonvacuity witness obtained through actual Index.build and
Frame.forBlock, then installing real hdr/meta input values. The exact original
golden/action syntax equality and Python whole-program validation are separate
checks. Scope/index premises are not a proof of global program validation or
of the parser producing those inputs.

## Acceptance and adversarial checks

- Native actual tableAction/11-step and runActionCall checks with nonempty K,
  a pending caller write/fault, TTL0/1/255, both validities, prior-drop both
  ways and asymmetric MACs/ports. One step short retains actionReturn; after
  return the temporary action-parameter layer is absent and caller block
  writes survive (operational block-map decoys, when present, become visible
  again rather than disappearing).
- Actual Python `run_action_call` path, not a fake direct call: freeze full
  index/scope/action maps, block fields and shared sentinels. Inspect inside
  the active action before normal completion, and final whole Run afterward.
  Include operational block-map decoys named dstAddr/port at the lower-level
  lookup boundary to demonstrate action precedence; label those decoys as
  runtime evidence, not a validator-accepted program declaration.
- An explicit bad binding/arity control and full exact body identity prevent
  vacuous witnesses. Use strict serialized types and detached snapshots.
- Faults: old-destination read moved after destination write; wrong action
  parameter binding; write placed in action map instead of hdr/meta block
  store; full outer-frame restoration; missing action-layer restoration;
  saturating TTL0 instead of wrapping. Separate proof-killed actual edits
  from compiled runtime mismatches and false-intent source mutations.
- At least one compiling Python field/return fault must be killed by the
  normal action observer and the existing forwarder packet vector, with
  exact-input live/restored replay retained. For observationally invisible
  layer changes, rely on the internal full-frame observer, not packet output.

## Scope and confidence

High confidence in the tiny unshadowed-root bridge and this fixed action
boundary; medium confidence that direct four-statement proof remains the
best reusable surface. Revisit generalization when a second positive action
needs parameter writes, out/inout copying or the typed frontend must certify
action bodies. No new semantics, IR escape hatch, parser/table/checksum/fate
theorem, fault-unwind promise, action-global validator or complete forwarding
claim is part of this increment. The integrator reviewed and accepted this
plan before its documentation-only commit. No implementation or builds were
performed; implementation waits for the reviewed Forwarder interface to land.
