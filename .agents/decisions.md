# Decisions

Current cross-cutting choices and reasons. Rules belong in [AGENTS](../AGENTS.md),
contracts in the public documents, and detailed rationale in the linked topic
notes. Dates below are the original decisions; supersede them in place with the
new reason/date. The pre-reorganization register is recoverable at
`de6aa7d9437ffc65c413b0adda7d3f8c558f84f6`; [recovery](notes/recovery.md) owns archive navigation.

## Scope and assurance

Formal assurance targets architecture-free core IR only. Keep existing core
validity, progress, semantic and codec proofs and independent conformance tests;
Python authoring, the importer, concrete externs and architecture adapters remain
tested tools. The user prioritized limited resources over Lean authoring,
application/architecture proofs and their exclusive machinery. Keep Python
examples, independent state/packet answers, useful fault tests and oracle coverage.
Retired proof drafts are recoverable history, not a continuation queue. Confidence
high for this phase; revisit only for a concrete user need justifying the proof
cost. No new proof family, architecture or importer expansion follows from this
simplification. (2026-09-25)

Minimal architecture support is independent Parser, Control and Deparser blocks
plus scoped v1model. Retire Filter/custom Switch/flood; six independent roles
preserve drop/state boundaries and unsupported native services reject explicitly.
Reason: useful behavior with independent oracles merits the limited resources.
[Architecture support](../docs/arch-supports.md) owns the profile;
[assurance](../docs/assurance.md) owns exact premises and exclusions. (2026-09-25)

Full architecture-independent P4 is a north star, not a deliverable (2026-09-23).
The finite milestones remain frozen; keep architectures, applications and claim 3
green without expansion because the value is IR and meaning. Playground stays
out; p4c backend remains deferred behind verification, the community version's
first job (2026-09-22 to 2026-09-25). [Roadmap](roadmap.md) owns deferred work;
[validation rationale](notes/validation-rationale.md) preserves retirement reasons
and revisit triggers, not a new implementation scope.

## Representations and authoring

Lean owns abstract syntax, validity and meaning; Protobuf owns wire syntax, with
separate conversion proof obligations (2026-09-23). Retain Protobuf and its specified
JSON profile at the Lean boundary: generated bindings serve Python and intended
other-language frontends without separate message models. JSON encodes the same
wire schema, not another IR. Native Lean Protobuf tooling has not met the user's
maturity threshold; a custom JSON schema would trade existing tooling for new
binding work. Keep text goldens/codecs; no migration or speculative frontend is
authorized. Confidence high for this scope; revisit only for demonstrated
interoperability/performance needs and mature tooling. (2026-09-26)

Blocks are the authoring unit; an optional BlockLibrary is not a complete program.
`p4.Program` conflated authoring with architecture composition, and arbitrary export
names alone left the H/M wire convention intact. Core validity/progress remains
separate from tested architecture binding/entry behavior. (2026-09-25)
[Design](../docs/design.md) and [authoring](../docs/python-edsl.md) own these contracts;
[IR design rationale](notes/ir-design-rationale.md) retains schema, assembly, extern
and eDSL tradeoffs, including the four pyright deviations.

Public APIs may change for demonstrated usability gains: preserve semantic
contracts/readability, separate authoring from meaning changes, and migrate callers
with diagnostic/golden tests (2026-09-23). Use codec for encoder/decoder pairs and
encode/decode for the operations; serialization describes a process/representation,
not another component or suite name. Reason: the user's established terminology
should remain consistent. (2026-09-26)

## Evidence and dependency boundaries

Judge discrepancies by their governing language or target contract, not an oracle
vote: independent implementations may share defects or implement different extensions.
Label deterministic policy where the language is unspecified. The
[discrepancy catalog](../docs/oracle-discrepancies.md) owns minimal pairs, pins and
rulings. (2026-09-25) The [semantic ledger](../docs/ir-semantics.md) makes deviations
checkable; unlisted differences are bugs, not rulings invented during fixes. Lean is
executable and proved, checked against P4-SpecTec, never normative: that would claim
unsupported authority. (2026-09-24)

P4-SpecTec's Lean rendering belongs to `p4-spectec-lean`; duplicating it wastes effort
and splits trust. p4blo owns IR, meaning, elaboration and validation, with frozen
oracle machinery as its test bed and a small bridge for the eventual theorem.
No duplicate rendering/interpreter, trace-localized N+1 testing, new simulator
patches beyond the two or bridge census beyond corpus. [Design](../docs/design.md)
owns the interfaces; [validation rationale](notes/validation-rationale.md) retains
the oracle/coverage constraints and patch handoff intent. (2026-09-24)

Tests follow responsibility and declare native dependencies. Package tests stay
beside Python but outside the installed module; root suites cover cross-implementation,
oracle, program and repository behavior. Shared answers/builders/catalogs belong in
support modules, never collected-test imports. Explicit dependency markers replace
filename inference so moving a suite cannot silently remove CI coverage. Preserve
independent answers and every existing case; this simplifies ownership, not evidence.
[Tests](../tests/README.md) owns locations/selection. (2026-09-25; explicit real-Lean
selection wording aligned 2026-09-26)

## Engineering and knowledge ownership

Ordinary documented commands and optional pinned tools keep entry costs low;
[engineering rationale](notes/engineering-rationale.md) preserves environment,
CI, package-layout and gate tradeoffs with their dates/revisit triggers.
[Workflows](../docs/workflows.md) owns pins and executable gates.

PRs remain optional in this personal-project phase to reduce overhead; review,
validation and protections still apply through AGENTS. Confidence high for this
phase; revisit when collaboration/release needs justify PRs. (2026-09-25)

Keep public artifact contracts in docs, policy in AGENTS, current state in status,
deferred work in roadmap, and detailed working rationale with its topic. This
avoids competing claims and stale diaries while git retains history (2026-09-24).
The user-approved topic organization now keeps plans, experiments and reviews
together, replacing the separate reviews directory; start with one useful note,
not a hierarchy of empty topic folders. This register carries cross-cutting choices
and links detailed reasons to their owners. (ownership refinement 2026-09-26)

For existing source comments that cite this register by topic: schema/v0, the
four eDSL deviations and Entry priority are in
[IR design rationale](notes/ir-design-rationale.md); printed ternary entries,
STF and oracle choices in [validation rationale](notes/validation-rationale.md);
p4c/BMv2 images and printer hooks in
[engineering rationale](notes/engineering-rationale.md). These links preserve
navigation while the public documents own the contracts.
