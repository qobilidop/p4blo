# Action and Block codec plan review

Final planning review: clear to proceed baseline-first. This is not approval
of an unimplemented helper extraction, universal law or fault campaign.

2026-09-23. Read the complete `docs/notes/block-codec.md` in
`p4blo-block-codecs` at `ca2f20f`, the actual Action/Block encoders and decoders,
enum handling, and the proposed source helper section in TableCodecLaws.
No candidate file edits, builds or executable checks were needed.

## Domain and baseline

The proposed two-codec slice is coherent now that all member laws are present.
Action only needs parameter/body representability. Block composes its six
member lists and unrestricted strings/kind; its three kinds do not impose
extra field-presence, calling-convention or parser-validity restrictions at
the codec layer. The plan correctly retains semantically invalid combinations
as positive wire witnesses rather than silently narrowing the theorem domain.

The listed actual decode order is accurate, including kind before parameters
and start_state before body. Action's empty object succeeds; Block's missing,
null or unspecified kind fails. The current enum decoder indeed classifies
any unknown string ending `_UNSPECIFIED` as unspecified, distinct from other
unknown names. Arrays/string omissions, null handling and always-emitted kind
are accurately described. These are recorded existing behaviors, not a newly
promised normalization or compatibility policy.

Direct independent BlockKind matching must remain separate from the production
shared name table. Full ordered nested descriptors, asymmetric name/startState
and all three kinds, literal native constructor answers, competing-field errors
and public protobuf wrapper checks make an appropriate baseline. Distinct new
`action` and existing `action_call` labels avoid changing earlier evidence.
Historical hash checks, non-overwrite capture, before/after source identities
and unchanged ordered request inventories preserve the baseline across later
proof/test additions.

## Narrow helper extraction

The proposed object lookup helpers already prove actual TreeMap/get behavior
and omission semantics; extracting only the shared subset after the baseline
is reasonable. Keep predicates and public Table theorems unchanged, retain
Table-specific optional/Boolean/natural facts in that module, and rerun all
existing Table/default audits and codec checks after the movement. Generated
matcher references in current proofs are implementation plumbing, not an API
to expose or emulate. An explicit internal helper namespace is preferable to
depending on private mangled names. Any changed helper statement needs separate
review rather than being hidden as a mechanical move.

No general serializer framework, alternate decoder, changed omission behavior,
raised proof limits or broader source ownership is necessary on the evidence
currently available. The plan appropriately makes extraction conditional on
actual proof cost and requires reporting a larger obstruction before expanding.

## Adversarial acceptance

The proposed one-sided order/loss, shared kind permutation, paired string-field
swap, error precedence and permissive-default faults exercise distinct risks.
In particular, paired mappings may preserve every roundtrip law; direct native
meaning anchors and independent fields are still required. The planned paired
observer challenge can demonstrate whether that independence is real.
Proof-step rejection must continue to be distinguished from a false theorem,
and interpreter-preflight failure from actual endpoint assertions. The plan
states these distinctions and preserves separate live/restored evidence.

No remaining planning blocker. Export/Program/host entries and semantic
execution remain separate checkpoints. Confidence is high in the boundary and
medium-high in the helper placement, with a concrete revisit trigger at actual
proof obstruction or later Program reuse.
