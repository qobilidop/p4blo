# Architecture support

p4blo supports one packet architecture: a scoped, single-pass **v1model**
profile. Core **Parser**, **Control** and **Deparser** blocks remain independent
functions with arbitrary typed parameters. The block runner invokes those
blocks for semantic testing; it is not a second packet architecture.

| Surface | Implementation | Independent comparison |
|---|---|---|
| Core blocks | Python and Lean core interpreters; H/M entry helpers for the block runner | P4-SpecTec through our explicit block-runner adapter |
| v1model packet processing | `p4blo.arch.v1model`, `spec/arch/P4bloArch/V1Model.lean` | Python/Lean; supported P4 programs on P4-SpecTec and BMv2 `simple_switch` |

Architecture and concrete extern implementations are tested executable code,
without architecture-specific proof guarantees. Core progress assumes a
generic `ExternContract`; this package does not prove that its families
satisfy that premise. [Assurance](assurance.md) states the evidence boundary;
[oracle discrepancies](oracle-discrepancies.md) records the governing contract,
selected behavior and reduced reproductions when the external tools differ.

## Minimal v1model profile

A `BlockLibrary` contains declarations and independent blocks without pipeline
selection. `v1model.assemble` chooses H/M roots and named exports in an
architectural `BlockAssembly`. The parser, ingress and deparser are required;
omitted verify-checksum, egress and compute-checksum stages are empty. All
four controls use the existing `(inout H, inout M)` core calling convention.

```python
from p4blo.arch import v1model

program = v1model.assemble(
    blocks,
    name="router",
    headers=Headers,
    metadata=Metadata,
    parser=Parse,
    ingress=Ingress,
    deparser=Emit,
    verify_checksum=Verify,
    egress=Egress,
    compute_checksum=Compute,
)
loaded = v1model.load(program)
pipeline = v1model.V1Model(ports=4)
```

Explicit stages must select distinct blocks. A selected stage cannot also be
called as a sub-block: its native P4 interface has architecture parameters
that an ordinary core call does not. Internal blocks remain reusable and may
have arbitrary signatures. These are adapter restrictions, not core validity
rules. See [Python authoring](python-edsl.md) for the generic assembly and
loader interfaces.

## The metadata contract

The adapter reserves four optional fields of the selected `M` struct. A field
of the wrong type is rejected. Adapter reads of an absent field return zero,
and adapter writes to it have no effect; ordinary user fields are unrestricted. The frontend renames
colliding native user-metadata fields to preserve their separate identities.

| Field | Type | Meaning |
|---|---|---|
| `ingress_port` | `bit<9>` | Provided input port |
| `parser_error` | `error` | Parser outcome, `NoError` on acceptance |
| `egress_spec` | `bit<9>` | Requested destination in ingress; drop request in egress |
| `egress_port` | `bit<9>` | Read-only destination selected after ingress |

Only ingress and egress may write `egress_spec`. A value of **511** marks a
stage's packet for dropping; a later assignment in that stage can undo it.
The adapter does not use boolean `drop` or `flood` fields.

| Stage | Standard fields the program may read |
|---|---|
| Parser | `ingress_port` |
| VerifyChecksum | None |
| Ingress | `ingress_port`, `parser_error`, `egress_spec` |
| Egress, ComputeChecksum | All four |
| Deparser | No metadata parameter |

These restrictions follow the available native stage interfaces. In
particular, VerifyChecksum has no standard-metadata argument, and the selected
egress port does not exist during ingress. Profile checking follows accesses
through actions and nested calls, including argument index expressions; whole
metadata replacements that overwrite protected fields are rejected. The core
validator still accepts architecture-independent uses of those same types.

## Packet execution

The serial interpreter executes:

```text
Parser → VerifyChecksum → Ingress → select output port
       → Egress → ComputeChecksum → Deparser → append payload
```

- Loading validates core blocks and bindings, checks the profile and binds
  fresh extern instances. Reuse one `Loaded` object to retain state across
  packets. Host entries are supplied separately for each request.
- Metadata begins at zero with the input port populated. `ports` is between
  1 and 511; configured physical ports are `0 .. ports-1`. An invalid input
  port is a caller error before any block runs.
- Parser rejection preserves partial headers, supplies `parser_error`, and
  continues to the controls. A non-byte-aligned consumed length drops with a
  diagnostic. Payload is the bytes after the parser's consumed prefix.
- If ingress ends with `egress_spec = 511`, no egress, compute-checksum or
  deparser code runs. Otherwise the destination is saved as `egress_port`.
  A destination outside configured ports drops with a diagnostic.
- Before egress, `egress_spec` is reset to **zero**, matching the pinned BMv2
  target profile. Egress may request a drop by writing 511; other writes do
  not change the saved output port. A drop skips compute-checksum and
  deparser, including their extern effects.
- Successful output is deparser bytes followed by the retained payload,
  emitted once on the saved egress port. Diagnostics accumulate on the
  pipeline object and should be checked alongside outputs.

This is a serial per-packet model, not a model of concurrent ingress/egress
threads or queue scheduling. Complete extern-state observations and ordered
stage witnesses check its implementation. The BMv2 backend accepts a narrower
set of operations in checksum/deparser stages than the core interpreter;
interpreter tests of arbitrary stage side effects do not claim BMv2 execution
support. Portable packet witnesses and the original P4 sources are tested on
both external oracles. A target compile rejection is an unsupported program,
not oracle agreement.

## Extern families

Each supplied extern implementation ships twice, a Python implementation
and a Lean model, pinned to each other by corpus vectors and independent
known answers. Custom Python registrations do not acquire a Lean model
or a P4 printing translation automatically. The IR sees only a shape; these are the families the supplied
registry binds. A family name is the segment before the first dot:
`register.8` and `register` bind the same service, subject to the
declaration's shape, and a suffix neither changes the algorithm nor
relaxes shape checks.

| Family | Shape | Behavior |
|---|---|---|
| `register` | `register(bit<32> size)`; `read(out T result, in bit<32> index)`, `write(in bit<32> index, in T value)` for any width `T` | `size` cells of width `T`, zero at load, persistent across packets. A read at or beyond `size` yields zero and a write there is ignored. BMv2 ignores the write too but leaves the read's destination untouched. Native v1model leaves that read result unspecified; zero is p4blo's deterministic policy, not a claim that BMv2 is incorrect. |
| `counter` | `counter(bit<32> size)`; `count(in bit<32> index)` | `size` counts, zero at load, persistent; out-of-range indices are ignored |
| `checksum16` | `checksum16()`; `compute(in T data) -> bit<16>` | the RFC 1071 one's-complement sum over `data` as a bit string, zero-padded to 16-bit words, carries folded; stateless |
| `crc16` | `crc16()`; `compute(in bit<D> data) -> bit<16>` | CRC-16/ARC: polynomial 0x8005, reflected input and output, initial value and final XOR zero; full 16-bit result |
| `crc32` | `crc32()`; `compute(in bit<D> data) -> bit<32>` | CRC-32/ISO-HDLC: polynomial 0x04c11db7, reflected input and output, initial value and final XOR 0xffffffff; full 32-bit result |

The CRC services are byte-aligned: `D` must be positive and a multiple of
eight, the input is exactly `D/8` bytes most-significant byte first with
leading zeros retained, and the result is returned in full with no range
reduction. Non-byte inputs are rejected, not padded, and calls must match
the bound width. The Python implementation uses a reflected byte table and
the Lean model the forward polynomial with explicit reflection; they
share neither code nor expected values. The known answers, and the pinned
P4-SpecTec padding defect they exposed, are in
[assurance.md](assurance.md#known-disagreements-with-the-oracles).

After every request the differential harness observes the complete
logical state of every extern instance, as hexadecimal strings so that
arbitrary widths survive, so a fault that changes a register cell but not
a packet cannot hide. Custom externs need their own model and evidence on
both sides; the registry does not verify arbitrary plugins.

## P4 printing and import

`v1model.print_program` emits native V1Switch stage interfaces and maps the
four reserved fields onto native metadata. It creates empty controls for
omitted stages. At egress entry the local M field `egress_spec` is initialized
to zero, while `egress_port` copies the native selected destination. At egress
exit the printer writes native `egress_spec` as 511 for a drop request, or the
native `egress_port` otherwise. This preserves M's observable egress request
for ComputeChecksum while keeping output selection stable on both simulators.
The
[original-source probe](../tests/frontend/probes/v1model_egress_spec_read.p4)
separately exposes P4-SpecTec's different initialization. Egress destination
selection is also compared using an unchanged original-source probe, so a
printer mapping cannot hide that discrepancy.

The printer maps register/counter and checksum/CRC families onto their native
v1model forms. The P4 frontend preserves all six stage boundaries instead of
merging controls. `mark_to_drop` becomes an assignment of 511 to `egress_spec`
in the permitted stages; `update_checksum` with csum16 uses the supplied
checksum16 computation. `verify_checksum` is explicitly rejected until its
`checksum_error` behavior is supported. A frontend or printer success does not
assert that every target backend accepts the program.

The P4-SpecTec block printer selects parser/control/deparser independently over
the same library, with ingress as the default selected control of a v1model
assembly. It does not combine the pipeline's controls. Its custom P4 include
uses `P4bloParser`, `P4bloControl` and `P4bloDeparser`; those names describe our
adapter's interfaces, not upstream standard architectures.

## Not supported

- Other packet architectures: Filter, the custom Switch, eBPF, PSA, PNA, TNA
  and XDP are not supplied.
- Multicast/flooding, cloning, recirculation, resubmission, meters, digests,
  timestamps, queue metadata and arbitrary standard-metadata fields.
- The `verify_checksum` intrinsic and `checksum_error` metadata.
- Ports outside the configured range or the 9-bit profile, and modeling the
  BMv2 scheduler's concurrent packet interleavings.
- Automatic Lean semantics or P4 printing for custom Python extern families.

## Adding an architecture

Custom composition can live outside this package. `p4blo.arch.assemble` and
`p4blo.arch.load` take explicit bindings, extern registry, contract and role
kinds without selecting v1model. A caller can invoke independent core blocks
with no packet pipeline; [custom_extern.py](../examples/custom_extern.py) is a
runnable example. To use STF replay, supply
`run(loaded, entries, ingress_port, packet)` returning output port/packet pairs.
The generic interfaces do not promise support or oracle coverage for that
custom architecture.
