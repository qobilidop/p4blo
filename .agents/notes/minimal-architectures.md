# Minimal architecture scope

User-authorized 2026-09-25; base `14e6f44513556260f8afd7f4545a0844fde5bea2`.
Integrator branch `work/minimal-arch`. Keep core blocks and one scoped v1model
packet architecture. Retire Filter, custom Switch/flood and exclusive plumbing.
No core syntax/proof changes, no other architectures, no architecture proofs.

## Shared contract before implementation

Core API concepts remain Parser, Control and Deparser; one Block kind tag.
Oracle P4 declarations remain P4bloParser/P4bloControl/P4bloDeparser.
The block runner is test infrastructure, not a second packet architecture.

Python packet API: `from p4blo.arch import v1model`;
`v1model.assemble(library, name=..., headers=H, metadata=M, parser=P,
ingress=I, deparser=D, verify_checksum=V, egress=E, compute_checksum=C)`;
`v1model.load(assembly)` and `v1model.V1Model(ports=4).run(...)`.
Parser/ingress/deparser required; omitted checksum/egress stages mean empty
stages, not a merged control. Wire uses existing BlockAssembly with roles
parser, verify_checksum, ingress, egress, compute_checksum, deparser.
All controls use the existing H/M calling convention; no schema change.
Independent core libraries remain arbitrary typed blocks.

The v1model adapter flattens supported standard metadata into reserved M
fields: ingress_port bit9, parser_error error, egress_spec bit9, egress_port
bit9. Missing fields read zero; ingress_port and parser_error are provided;
egress_port is the selected destination snapshot before egress. Only
Egress/Ingress may write egress_spec; other standard fields are read-only
program inputs. Enforce supported-profile restrictions in architecture
validation, not core validity. Retired drop/flood fields are not architecture
facilities; migrate callers to egress_spec511. Unsupported native metadata,
extern functions and services must fail explicitly; verify_checksum is
rejected until its intrinsic checksum_error behavior is supported. Ordinary
core code and existing checksum16 extern calls may run in checksum stages.

Runtime order: parser, verify_checksum, ingress, select egress port, egress,
compute_checksum, deparser, append unconsumed payload. Parser rejection sets
parser_error and still runs controls. Egress_spec511 at end of ingress skips
all later stages and their effects; at end of egress skips compute/deparser.
A later assignment can undo mark-to-drop. Changing egress_spec during egress
does not redirect the selected output port. Configured physical ports remain
explicit; invalid caller ingress and unsupported egress ports are diagnosed.

Independent witnesses cover ordered mutations in all stages, payload,
parser_error, ingress/egress drop with persistent state readback, overwritten
mark-to-drop and egress_port snapshot. Pinned P4-SpecTec may incorrectly use
post-egress egress_spec as output port: confirm with an unchanged P4 witness
on both external oracles and classify precisely, never alter inputs to agree.

Block oracle projects parser/control/deparser roles independently over the
same library (ingress is the default selected control for packet fixtures).
Do not merge v1model stages to make block comparisons pass. Preserve original
P4/STF inputs, useful runtime tests and core proofs. Refresh affected generated
IR/conformance snapshots only after recording intended architecture changes.

## Ownership and acceptance

- Python author: /private/tmp/p4blo-minimal-arch-python, branch
  work/minimal-arch-python; Python arch runtime/printer/load APIs and frontend
  v1model lowering; focused new unit tests. Shared files agreed by messages.
- Lean author: /private/tmp/p4blo-minimal-arch-lean, branch
  work/minimal-arch-lean; spec/arch Lean runtime, endpoint, coverage and tests.
- Independent reviewer: /private/tmp/p4blo-minimal-arch-review, detached base;
  read-only design and final implementation review, reported in .agents/reviews.
- Integrator: callers/examples/goldens, block-oracle projection, shared tests,
  assurance/conformance migration, docs/website/state, integrated checks.

No source changes in shared trees by child agents; committed handoffs, explicit
pending integrated checks. At most two heavy jobs locally; no shared oracle
image rebuild while tests use it. Core gate + both Lean packages + complete
required-Lean Python gate, both applicable oracle suites, staged acceptance,
and frozen assurance/mutation checks before final exact-main CI. Final notes
must record removed/migrated test inventory and any changed discrepancies.

Current iteration: shared contract established after three independent design
audits; implementation begins. No validation has yet run for this scope.
