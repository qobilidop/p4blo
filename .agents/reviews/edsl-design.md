# eDSL architecture boundary review

Reviewer: independent examples agent, Codex GPT-6 Astra. Reviewed the initial
named-export API (`c502e0b`, integrated as `67dbba7`) against the user's
block-first clarification on 2026-09-25. Read-only design review; the reviewer
authored example changes but not the Program/loader implementation reviewed.

## Confirmed boundary problem

Changing Program's parser/control/deparser keywords to an arbitrary export
mapping still requires global headers/metadata roots. The wire export
validator applies the conventional per-kind H/M signature. A control whose
only parameter is `value: InOut[bit8]` therefore cannot be independently
authored through that whole-program API without an unrelated envelope.

Evidence inspected: `spec/ir/proto/p4blo/v0/p4blo.proto` Program/Export,
`impl/python/p4blo/validator/types.py` root checks,
`impl/python/p4blo/validator/blocks.py` export signatures, and the initial
typed `Program` constructor. No runtime commands were run for this design
review; its limitation is explicit.

## Resolution required before integration

Author independent block classes. An optional BlockLibrary may bundle blocks
and shared declarations but must not select H/M roots, pipeline roles or
packet fate. Its compilation result is a fragment, not a validity-certified
complete program. Architecture assembly separately consumes that library and
produces the existing wire envelope. Add a scalar-only compilation test and
exercise standalone compilation of the three application libraries.

The user independently requested this boundary during the review. The
integrator accepted it and the named-export public Program proposal was
superseded before any push. Implementation and runtime validation are left
to the subsequent milestone review.
