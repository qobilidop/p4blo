# Header-validity read plan review

**Approved for the staged read-only validity capability**, after rebasing
onto the committed command-list interface. Reviewed the plan and isolated
probe in `p4blo-validity-reads`; no production changes are part of this
feasibility checkpoint.

The proposed HeaderPath/HeaderRef is a reasonable small constrained addition.
It duplicates only aggregate navigation, not expression operators or command
semantics. Its endpoint is a header by construction, its source observation
reads the independent stored Bool, and it has no write/lvalue or conversion
to scalar Place. This preserves the essential existing theorem that scalar
field writes do not change any validity bits. A generic all-endpoint path
refactor can wait until another aggregate operation justifies its larger
proof/API impact.

The authoritative typing rule appropriately separates an actual declared
header path from exact endpoint nominal declaration agreement. Intermediate
containers retain existing FieldsOf premises. Runtime correspondence should
continue to use exact source data/index/frame agreement, without pretending
runtime evaluation performs semantic declaration validation. Directly rooted,
nested and empty headers are legitimate tests; scalar/struct endpoints and
forged kind/declaration cases must reject independently of API inference.

The proposed `Read` sum is the existing generic read-family seam's intended
use. It preserves one ExprWith/CmdWith implementation, with concrete scalar
and header leaf-law discharge, while keeping scalar Ref/Place unchanged.
One-way coercion from scalar Ref is appropriately modest; avoid promising
definitional identity with the old read parameter. Existing scalar exports
and behavior should remain identical, and concrete theorem assumptions must
not be replaced by arbitrary callbacks. Named header references should share
the certified unique-slot lookup, not create a subtly different ambiguity
policy or overload scalar Ref.named to accept aggregate endpoints.

Independently ran the isolated probe against the pinned, already-built
named-path interfaces using explicit LEAN_PATH: **exit 0**. The arbitrary-Run
header observation theorem uses exactly
`[propext, Classical.choice, Quot.sound]`; struct/scalar endpoint rejections
and expected-type scalar Ref-to-Read coercion examples also compile. This
checks primitive/coercion feasibility, not the unimplemented public adapters,
authoritative typing extension or whole-program initialization.

The new validity-guarded application must remain separately named from the
existing forwarding body/policy. Prove the invalid-input branches instead
of assuming valid headers away. Full-state independent answers and policy
should preserve all non-drop state when either validity is false, and use
the existing independent hit/TTL policy otherwise. Continue excluding parsing,
checksum maintenance, route lookup and architecture fate.

Planned full post-read observers are important: a validity read can return
the correct Bool while corrupting a sibling's validity or stored field.
Run the read once before snapshots, retain full DRT input before assertions,
and check live/restored replay. Opposite validity siblings distinguish wrong
well-typed header aliases; constant/inverted source observations and skipped
application guards must be challenged at their respective proof boundaries.

No requested design correction. Confidence is high in the existing read
seam and scope, medium in the constrained-path/coercion ergonomics. Revisit
if navigation/lookup code materially duplicates or real call sites require
pervasive dependent casts; do not weaken endpoint/permission constraints to
avoid those costs. Review each proposed checkpoint independently before
claiming the full capability.
