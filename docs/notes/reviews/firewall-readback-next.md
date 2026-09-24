# Firewall register readback: next checkpoint

Recommendation: implement the exact two-read prefix, leaving the existing
conditional pending. Design review clear; this is a read-only feasibility
assessment, not a compiled proof or implementation claim.

## Actual boundary

`TutorialFirewall.checkBloom` calls register 1's `read(out reg_val_one,
reg_pos_one)`, then register 2's corresponding read, then tests the two returned
bits against one. Prove an actual `Execution.Steps` chain from
`.statements checkBloom :: K` to `.statements [theExistingConditional] :: K`,
for arbitrary continuation `K`. The machine requires four transitions: expand
each list head and execute its call. Keep numeric counts as independent native
checks unless an indexed relation is explicitly introduced. Also expose the
whole-Run checkpoint immediately after the first completed call/copy-back.

Use the actual `Exec.callExtern`, `Externs.call`, `ExternState.call`, and
`writeLValue` path. Do not add another executor or require successful evaluator,
extern-call, or full write callbacks as hypotheses. A literal source identity
must connect these operations and their order to the authored `checkBloom`.

## Premises and expected result

Keep the actual firewall index premise, both actual register states of width
one, and actual frame reads of the two position names as fitting `bit<32>`
values. Arrays may have arbitrary length and natural cells. No 4096 bound,
canonical-cell, metadata, parser, hash-computation, or global validation premise
is needed for this operational prefix.

The independent answer is zero for a missing array element, otherwise its
natural value modulo two. Prove its agreement with actual `Bits.wrap 1`.
In particular, raw cell 2 reads as zero and raw cell 3 reads as one: neither
raw nonzero membership nor raw equality to one describes all natural states.
Restricting stored cells to 0/1 yields the simpler later application corollary.

Require a concrete destination storage case for each distinct result name:

- An actual action-map binding exists: update only that action map, preserving
  the block decoy and every other binding.
- Its action lookup is absent and the block binding exists: update only the
  block map, preserving the complete action layer.

The existing `writeVar_action` and `writeVar_block_unshadowed` laws discharge
these cases. Avoid `BlockFrame` as a substitute for action-layer reasoning.
A small application-local storage-case proposition is reasonable; no generic
command/read abstraction is required. All four pairs of destination cases
must be constructible. Position reads may independently be action-shadowed.
Prove that the first distinct-name update leaves the second position read and
destination classification intact.

An `out` argument is initialized from its declared type, not from its old
destination value. Existence of the destination storage is necessary for
copy-back, but its old stored value need not be a correctly typed bit for this
operational theorem. Keep typed/startup instances separate. Missing destinations
can be bounded failure tests, not silently admitted by the success theorem.

The exact result must include each actual extern-map reinsertion, in order,
followed by the appropriate frame update. A read returns the original register
state, but `Externs.call` still inserts it into the map. Do not assert structural
identity of the whole extern map without a separate proof; prove pointwise
identity of every register/other key and retain the exact map expressions in
the whole-Run equality. Index, scope, entries, packet, emitter, visits, action
name and untouched frame layers remain exact. There is no action entry/return
in these two extern calls.

## Small implementation sequence and feasibility

1. Independent cell-answer function and wrap/OOB equations; literal actual
   source identity. Reuse the insertion proof's actual instance/type lookup
   facts where accessible, or establish the same small literal facts locally.
2. One concrete read/copy-back lemma, with the two explicit destination-storage
   cases. Unfold the actual method's `out bit<1>` zero initialization, actual
   read and copy-back. Reuse the committed storage-write laws.
3. Instantiate the two names, derive preservation needed between them, and
   compose the four actual machine steps with arbitrary `K`. Add pointwise
   storage/extern preservation and a real initialized-frame instance using
   the committed `frame_locals_zero`/`Bloom.initializedRun` witness.

Confidence is high for this bounded slice: the insertion theorem already
discharges the same index/method/extern dispatch; the extra obligation is one
real copy-back and its action-first destination routing. No feasibility build
was performed in this review. Revisit scope if proving the four storage cases
requires a broad frame API: first retain two concrete one-call variants and
compose them, rather than assuming successful writes or weakening action cases.

## Independent acceptance and adversarial checks

Native cases should cover empty/short arrays, in-bounds endpoints and maximum
32-bit positions, asymmetric answers, all destination-layer pairs, shadowed
position reads, arbitrary old destination values, and raw cells 2/3/7. Mark
noncanonical natural cells as Lean-only; do not inject invalid Python `Bits`
values and claim corresponding legal states. Include a genuine initialized
profile, not only manually assembled frames.

For Python, call the actual two authored statements with normal completion.
Wrap `stmt.call_extern` or `execute_one` delegating to the original and freeze
the complete Env after each returned call: observing `Register.call` alone is
too early because it precedes copy-back. Independently supply intended positions
and expected destination layers; never compute expectations via the production
`Env.read` being challenged. Freeze complete expected snapshots before execution.
Compare all arrays, entries, index/scope maps, both storage layers and other
shared state with type-sensitive detached values. Observe both stages, not just
commuting final writes; ensure exact two-call order and counts. Pending faulting
or state-changing continuation work must remain untouched in native prefixes.

Required faults include zeroed/wrong-position return, omitted/wrong-destination
copy-back, action-hit incorrectly updating a block decoy, reordered calls,
wrong wrapping, and a read that returns the correct bit but modifies another
cell or unrelated frame field. Repeat the prior coupling challenge with an
actual position-read alias and prove the independent expectation rejects it.
Distinguish actual Lean runtime compile/proof rejection from executable test
kills. Packet/extern DRT may miss local-copy-back faults; retain direct whole-Env
boundary evidence and only save packet replays when a genuine packet/state
mismatch exists.

## Subsequent decision/drop checkpoint

Only after readback lands, define an independent decision on the two observed
one-bit answers: keep prior drop when both equal one, otherwise invoke the real
drop action. Prove the actual conditional and action entry/return separately,
then compose with readback. The later action theorem needs real scope/action
lookup and destination-root premises; the read prefix alone supplies none of
those. Initially use the actual initialized block-frame profile for that
composition, rather than silently erasing arbitrary action overlays. No claim
yet covers table selection, hash positions, TCP-direction control, parser,
Bloom false-positive rate, full firewall execution, or packet delivery.
