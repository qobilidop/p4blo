# Foundational declaration codec plan review

Final review: clear for the proposed planning boundary; implementation and
its independent evidence remain pending.

2026-09-23. Independently read the complete plan and standalone probe in
`p4blo-program-codec-next` at `dcbf392`, and checked the selected production
decoder dependency graph in `ir/P4bloIR/Json.lean`. No candidate files were
edited and no executable or library was rebuilt.

The nine selected total codecs form a coherent acyclic slice: Field/Var/Param
depend on Ty; HeaderType/StructType on Field; Method on Param and optional Ty;
ExternType on Param/Method; ExternInstance on Literal; EnumType on strings.
There is no reason to alter production decoder behavior or introduce another
codec. Reusing the actual list roundtrip lemma is appropriate. Splitting the
six foundational declarations from the three extern-related declarations is
a sensible fallback if the implementation becomes too large to review.

The proposed predicates correctly exclude semantic validation requirements:
names may be empty, duplicated or unresolved; header fields may be aggregate;
enum lists may be empty; all four directions are representable, including
non-input constructor parameters. Optional return absence is distinct from a
present zero-width type. Embedded Ty/Literal wire bounds remain necessary.
The probe's mixed invalid-but-representable witness makes those distinctions
concrete rather than relying on vacuous premises.

Independently ran the complete standalone probe with pinned Lean 4.34.0,
`-DwarningAsError=true`, and the candidate's frozen existing IR library path.
Exit 0; Param, Method, ExternType and the mixed witness all report exactly
`[propext, Classical.choice, Quot.sound]`. This checks proof feasibility for
the actual decoder/encoder, not nine completed laws or cross-language parity.

The acceptance plan addresses the main assurance risks: baseline capture
before any production changes, no overwrite, exact request/source provenance,
strict JSON observation, all directions observed by independent constructor
matches, unequal ordered arrays, and simultaneous-error precedence. In
particular, the shared Direction.names encoder/decoder table needs its paired
IN/OUT mutation: a roundtrip theorem alone cannot establish intended enum
meaning. Paired ExternInstance labels and optional/error-order faults cover
independent holes in successful roundtrip claims. Runtime mismatches and
proof rejection must remain separately classified.

No blocker found. This review does not approve a universal Program codec,
semantic validator, ProtoJSON acceptance equivalence, binary/text codec, or
Python correctness claim. Each implementation checkpoint still needs its
registered audits, independent fixtures, actual mutation/restoration evidence,
and final read-only review.
