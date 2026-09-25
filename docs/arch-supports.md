# Architecture support

The IR is architecture-free: a parser, control or deparser is a function
of its inputs, and [ir-semantics.md](ir-semantics.md) never mentions a
port, a packet's fate or its payload. An architecture is ordinary code
that calls those functions, decides what the metadata they leave means,
and supplies the externs a program may declare. This page records what
this repository supplies, the rules those architectures share, and what
is deliberately not supported.

| Architecture | Where | What it is |
|---|---|---|
| filter | `impl/python/p4blo/arch/filter.py` | parser and control; the packet leaves as it came, or not at all |
| switch | `impl/python/p4blo/arch/switch.py`, `spec/arch/P4bloArch/Switch.lean` | parser, control and deparser over a few ports, with drop, unicast and flood; the Lean twin is what the differential tests run |
| v1model | `standard_metadata_binding` in `impl/python/p4blo/arch/v1model.py` | not an implementation: a printing shim that maps the contract onto `standard_metadata` so the P4 oracles can run printed programs |
| PSA, PNA, TNA and other P4 architectures | none | see [Not supported](#not-supported) |

The filter and the switch exist to make [claim 3](design.md#the-four-claims)
measurable: each is about fifty lines with no P4 in it, and every corpus
program runs under both unchanged. They are reference architectures in
the sense that the differential tests, the oracles and the proofs about
authored applications run programs under them, not in the sense of a
standard anyone else implements.

The generic Python loader, `p4blo.arch.load`, requires an explicit extern
registry, metadata contract and mapping of required roles to block kinds.
`p4blo.arch.reference.load` selects the supplied switch/filter environment
as a convenience; it is not a mandatory architecture. Independent P4 blocks
are collected in a core `BlockLibrary`, which may have several blocks of each
kind and no selected pipeline. `reference.assemble` or a custom adapter
selects wire exports and H/M roots in an architectural `BlockAssembly`.
The generic loader can also take a compiled library and explicit
`BlockBindings` directly. Another composition can use the same block
definitions without the supplied pipeline defaults. See
[Python authoring](python-edsl.md) for the public API and a custom extern.

## The metadata contract

The supplied filter and switch communicate their host policy through the
selected metadata struct `M`. Each names the fields it needs, with a type and a
direction: provided fields are written before the blocks run, consumed
fields are read afterwards. At load the program's `M` is checked
structurally against the contract, by field name and type, and nothing
else about `M` concerns anyone. Every field is optional. A field the
program does not declare reads as its zero value and ignores writes, so a
program without `egress_port` unicasts to port 0 and a program without
`flood` runs unchanged under an architecture that offers it.

The vocabulary the supplied architectures share:

| Field | Type | Direction | Meaning |
|---|---|---|---|
| `ingress_port` | `bit<9>` | provided | port the packet arrived on |
| `parser_error` | `error` | provided | the parser's error, `NoError` on accept |
| `egress_port` | `bit<9>` | consumed | unicast destination |
| `drop` | `bool` | consumed | discard the packet; wins over the rest |
| `flood` | `bool` | consumed | send to every port but the ingress one |

Fate is a set of booleans rather than an enum so that a program that
knows nothing of flooding runs unchanged under an architecture that
offers it. A declared contract field of the wrong type is a load error.
Any other field of `M` is plain user metadata.

## Rules every supplied architecture follows

The IR does not decide these, so each architecture here decides them the
same way, and a Lean twin must match its Python original exactly.

- **Loading** happens once per program: validate, bind every extern
  instance to its implementation, check `M` against the contract, and
  resolve the blocks the architecture needs by their exported role. Extern
  state lives with the loaded program and persists for as long as it does,
  which is what makes a register stateful across packets.
- **The metadata starts** as the zero value of `M` with `ingress_port`
  set. An ingress port that is not a port of the architecture, or that
  does not fit `bit<9>`, is the caller's error, raised before anything
  runs.
- **After a parser rejection the control still runs**, over the partial
  headers the parser returned, with `parser_error` set when the program
  declares it. This is v1model's behavior and what the corpus expects.
- **A parse that ends off a byte boundary**, accepted or not, is treated
  as a program bug: the packet is dropped with a diagnostic, since P4
  targets require byte-aligned parsing anyway.
- **The payload** is the bytes after the ones the parser consumed. The
  output packet is the deparser's bytes followed by the payload.
- **The deparser runs before the fate is read**, so its extern calls
  happen on a dropped packet too.
- **Fate:** `drop` wins over everything; then `flood` sends the packet to
  every port but the one it arrived on; otherwise the packet goes to
  `egress_port` alone. An `egress_port` that is not a port of the
  architecture drops the packet with a diagnostic, the same way a
  misaligned parse does.
- **Table entries** are inputs installed by the host: the program's const
  entries and defaults first, then the host's, afresh for every packet in
  a vector replay, while extern state persists.
- **Diagnostics** are the architecture's own record of a packet it
  dropped for a reason the program did not decide. They are compared by
  presence, not by exact text, between Python and Lean.

## The filter

The filter runs the parser and the control and acts on the metadata they
leave: `drop` discards the packet, otherwise the original bytes leave on
`egress_port`. There is no deparser, so whatever the control did to the
headers never reaches the wire; a program that rewrites headers still
runs here unchanged, its rewrites merely go unseen. The filter has no
port count: any `bit<9>` egress port passes through. A vector that
expects a rewritten packet therefore fails under the filter by
construction, and the filter tests rewrite expectations to the input
bytes. The filter is Python only; nothing runs under it in Lean.

## The switch

The switch runs all three blocks over `ports` ports numbered from zero.
Ports are `0` to `ports - 1`; `511`, BMv2's drop port, is just an
out-of-range port here, so a program that writes it without `drop` is
dropped by this architecture for that reason and by BMv2 for its own.
The Lean switch in `spec/arch/P4bloArch/Switch.lean` follows the same rules line
for line and is what `p4blo-lean run` executes, so the differential tests
compare whole packets in and out under one architecture on both sides.

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
| `register` | `register(bit<32> size)`; `read(out T result, in bit<32> index)`, `write(in bit<32> index, in T value)` for any width `T` | `size` cells of width `T`, zero at load, persistent across packets. A read at or beyond `size` yields zero and a write there is ignored. BMv2 ignores the write too but leaves the read's destination untouched; the divergence is documented, not resolved. |
| `counter` | `counter(bit<32> size)`; `count(in bit<32> index)` | `size` counts, zero at load, persistent; out-of-range indices are ignored |
| `checksum16` | `checksum16()`; `get(in T data) -> bit<16>` | the RFC 1071 one's-complement sum over `data` as a bit string, zero-padded to 16-bit words, carries folded; stateless |
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

## The v1model shim

There is no v1model implementation. What exists is the mapping the
printer applies so that the two P4 oracles, P4-SpecTec's simulator and
BMv2, can run printed programs under `v1model`:

| `M` field | v1model |
|---|---|
| `ingress_port` | `M.ingress_port = standard_metadata.ingress_port;` at the top of the parser's start state and of the ingress control |
| `parser_error` | `M.parser_error = standard_metadata.parser_error;` at the top of the ingress control |
| `egress_port` | `standard_metadata.egress_spec = M.egress_port;` at the end of the ingress control |
| `drop` | `if (M.drop) { mark_to_drop(standard_metadata); }` at the end of the ingress control, after the egress port so that drop wins |
| `flood` | no mapping; checked between the two architectures instead |

The shim prints `register`, `counter` and `checksum16` as the v1model
externs of the same name, and each CRC service as `hash` with the
corresponding `HashAlgorithm`, base zero and maximum `2^W`, which needs a
width of `W+1` so that `2^32` is not encoded as zero. The verify-checksum,
egress and compute-checksum stages are printed empty, so an oracle neither
verifies nor recomputes a checksum the program does not compute itself.
This is a shim for evidence, not support for programs written against
v1model: intrinsic metadata beyond the contract, meters, digests, clone,
recirculate and multicast groups have no counterpart.

## Not supported

The supplied architecture and printing adapters have these limits; they
do not restrict how a custom caller composes core blocks.

- **PSA, PNA, TNA and any other named P4 architecture.** No program
  written against them can be loaded, and no `psa.p4` or similar shim
  exists. Supporting one would be a new architecture module on each side
  plus a printing shim, not a change to the IR.
- **An egress pipeline, recirculation, cloning, multicast groups,
  meters, digests and timestamps.** The supplied pipelines run one control
  without a second pass; their packet fate is drop, unicast or flood.
- **Ports outside `bit<9>`**, and any port numbering other than
  `0 .. ports - 1` for the switch.
- **Additional match kinds and supplied services.** The core supports exact,
  LPM and ternary keys. The five extern families above are the supplied
  implementations; custom families can be registered explicitly, without
  automatically gaining Lean semantics or P4 printer support.

The block-oracle package named `P4blo` is an isolated P4-SpecTec testing
adapter. It does not define a required architecture for p4blo programs.

## Adding an architecture

A custom architecture may live outside p4blo. It assembles a block library,
loads with an explicit registry and contract, then calls blocks according to
its own logic. The [custom extern example](../examples/custom_extern.py) runs
a control without a packet pipeline. Neither ports nor packet fate are
mandatory inputs to an architecture composition.

To use the supplied STF driver, provide a `run` method of the shape
`run(loaded, entries, ingress_port, packet)` returning egress ports and
packets. Use `load` for the once-per-program work and the `Metadata` view
for contract fields; a contract may declare its own fields. Supplied
adapters live under `impl/python/p4blo/arch/`. If programs must run under
it in the differential tests, a Lean twin follows the same rules and the
`p4blo-lean` endpoint learns to select it. The shared rules above describe
the supplied filter and switch. A custom architecture defines its own
contract and execution policy; document those choices with its adapter.
