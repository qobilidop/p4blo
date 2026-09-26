# forwarder

The p4lang tutorial's `basic` forwarder as a p4blo program. It is the
first corpus program and the honest test of claim 1: whether the core is
small enough, and post-elaboration enough, to hold a real program without
an escape hatch.

| | |
|---|---|
| Source | [p4lang/tutorials](https://github.com/p4lang/tutorials) `exercises/basic/solution/basic.p4` |
| IR | `forwarder.txtpb`, generated from the eDSL |
| eDSL | `forwarder.py` |
| Vectors | `forward.stf`, `miss.stf`, `non_ipv4.stf`, `lpm_precedence.stf`, `too_short.stf` |

The golden was written by hand for step 1 and is generated from the eDSL
source since the checksum landed: `python tests/corpus/forwarder/forwarder.py`
prints it, after the leading comment.

The [quickstart](../../../docs/quickstart.md) builds this Python source and
runs its IR on both the Python and Lean interpreters. Independent packet,
action and installed-table expectations live in
`tests/programs/test_forwarder*_semantics.py`; the BMv2 profile independently
checks five installed-table configurations. These are regression and oracle
tests, not a formal forwarding or whole-pipeline guarantee.

## Elaborated away

- **typedefs.** `macAddr_t`, `ip4Addr_t` and `egressSpec_t` are their
  widths, 48, 32 and 9.
- **`const bit<16> TYPE_IPV4 = 0x800`.** A literal in the one select case
  that used it, written in decimal as the schema requires: 2048.
- **`standard_metadata`.** The authored metadata carries provided
  `ingress_port` and requested `egress_spec`. A drop writes 511 to
  `meta.egress_spec`; another assignment can overwrite that request. The
  packet's fate is data interpreted by v1model, not a core effect.
- **The parser's `packet_in` and the deparser's `packet_out`.** A p4blo
  parser and deparser carry the packet by their kind, not as a parameter.
- **`NoAction`.** core.p4 declares it; the IR has no implicit declarations,
  so the program declares it with an empty body.
- **`isValid()` and the action call syntax.** `hdr.ipv4.isValid()` is the
  `is_valid` expression and `ipv4_lpm.apply()` is the `apply` statement.
- **`MyComputeChecksum`.** Its one statement,
  `update_checksum(hdr.ipv4.isValid(), { the eleven non-checksum fields },
  hdr.ipv4.hdrChecksum, HashAlgorithm.csum16)`, is a `checksum16` extern
  instance `csum` whose `compute(in bit<144> data)` takes those fields
  concatenated in header order and whose result is assigned to
  `hdr.ipv4.hdrChecksum`. The authored program places the stateless
  computation at the end of ingress under `hdr.ipv4.isValid()`, whereas
  the original source computes after egress. The printer turns it back into
  v1model's `hash(..., HashAlgorithm.csum16, 16w0, { data }, 32w65536)`,
  the same arithmetic. Every expected IPv4 header in the vectors carries
  the checksum this computes, derived by hand in each file.

## Deferred

- **`MyVerifyChecksum`.** The authored program omits checksum verification.
  The original sets `standard_metadata.checksum_error`, which its ingress
  does not read. Packet vectors exercise this scoped behavior; they do not
  establish equality of all native metadata. The frontend explicitly rejects
  the unsupported `verify_checksum` intrinsic rather than deleting it.
- **`size = 1024`** is carried on the table but is informative; the IR gives
  it no meaning and the interpreter does not bound the entry count.
- **The egress pipeline.** The authored program omits the empty optional
  egress and checksum stage bindings. Its stateless checksum calculation
  remains in ingress; this is not a source-identical six-stage translation or
  a claim of complete pipeline-state equivalence.
