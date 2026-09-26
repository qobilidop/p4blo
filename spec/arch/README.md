# Executable v1model and block adapters

Lake package `p4blo-arch`, imported as `P4bloArch`, depends on the core IR
in `../ir`. It supplies the executable adapters needed to run programs:

- `P4bloArch/Assembly.lean`: architecture bindings and their runtime checks.
- `P4bloArch/Externs.lean`: register, counter, checksum16, CRC16 and CRC32
  families, their shapes, registry and call implementations. Core extern
  state is data; this package supplies its concrete interpretation.
- `P4bloArch/V1Model.lean`: the scoped six-stage v1model implementation,
  matching the Python adapter's serial packet and metadata rules.
- `Main.lean`: the `p4blo-lean` conformance endpoint used by differential
  tests. It loads an architecture assembly and runs its blocks.

These are tested executable definitions, with no formal architecture or
concrete-extern guarantee. The core's progress theorem assumes an
`ExternContract`; this package does not prove that its families discharge
that contract. The behavior and evidence boundaries are in
[architecture support](../../docs/arch-supports.md) and
[assurance](../../docs/assurance.md).

Client modules live under `P4bloArch/`; gate-only modules and fixtures live
under `P4bloArchTest/`. `Main.lean` is the one executable root. `lake test`
checks bindings, entry behavior, extern families and v1model, including
forwarder vectors from `../ir/P4bloIRTest/`. From the repository root,
`scripts/check-lean.sh` builds and tests both Lean packages in dependency
order and runs the architecture-free core's proof audits.
