# Complete the block-library boundary

User steering 2026-09-25: the protobuf core bundle must also be called
BlockLibrary, with any number of parsers, controls and deparsers. A library
is not a complete program. PR #2 at 97cc1d8 is held for this follow-up;
its CI is evidence for that revision only, not the final result.

## Contract

- Core protobuf and Lean BlockLibrary contain name, errors, header/struct/
  enum/extern declarations, extern instances and blocks. No H/M roots or
  exports; multiple blocks of each kind are allowed. Python BlockLibrary
  compiles to this same core protobuf value and core validation accepts it.
- H/M choices, exports and their fixed calling-convention checks move to
  architecture bindings. They are optional support, not core requirements.
- Preserve the existing flat transport profile as an explicitly architectural
  BlockAssembly message in an architecture schema/package. Its declaration
  fields project to a core BlockLibrary; its H/M and exports project to
  BlockBindings. This compatibility adapter preserves corpus/JSON/binary
  payloads, without keeping a mixed Program in the core. The descriptor name
  changes intentionally. New core libraries need no assembly envelope.
- Generic core validity/progress remains proved over libraries. Binding
  checks retain H/M resolution, duplicate roles, referenced blocks and exact
  export signatures; architecture loaders additionally require role kinds.
  Preserve and relocate concrete entry helpers/theorems as appropriate;
  no dropped proof guarantee and no new universal guarantee.
- Rename the low-level mutable builder to AssemblyBuilder; public typed
  BlockLibrary remains the ordinary authoring API. Retain lowercase legacy
  protocol keys/fixture filenames unless their change is required.
- Architecture assembly recompiles source definitions in one context as
  before. No linker and no fixed count of parser/control/deparser blocks.

## Work and acceptance

The integrator owns schema/generated Python, core Python compiler/validator/
IR, remaining caller migrations, durable state and integration. A Lean agent
owns spec/ir and spec/arch Lean and impl/lean, including moved tests/audits.
An architecture agent owns Python architecture loading/binding/assembly,
low-level AssemblyBuilder and architecture-focused tests. An examples agent
owns public docs/examples plus a multiple-block library/architecture witness.
Exact files and committed bases are supplied in each delegation brief.

Run independent review, full Python/schema and Lean gates, required Lean
comparison, frozen assurance and applicable oracle/remote CI. Compare original
transport goldens and outputs; test a library with multiple blocks of every
kind and no H/M roots, and reject incorrect architecture bindings before run.
No merge while this boundary remains incomplete.
