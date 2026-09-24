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
| Lean authoring | [`P4blo/Forwarder.lean`](../../../lean/P4blo/Forwarder.lean), checked field paths plus explicit ordinary IR assembly |
| Vectors | `forward.stf`, `miss.stf`, `non_ipv4.stf`, `lpm_precedence.stf`, `too_short.stf` |

The golden was written by hand for step 1 and is generated from the eDSL
source since the checksum landed: `python tests/corpus/forwarder/forwarder.py`
prints it, after the leading comment.

The independent Lean source builds exactly the same complete IR, and its
in-memory `Program` runs these same vectors through the public Lean switch
API. The [quickstart](../../../docs/quickstart.md) runs both authored versions.
Scoped proofs cover the invalid-IPv4 identity, the actual selected forwarding
action, and bounded installed-table lookup/application families. These are
not a verified whole frontend or pipeline; see the
[port](../../../docs/notes/lean-forwarder.md),
[action](../../../docs/notes/forwarder-action.md) and
[application](../../../docs/notes/forwarder-apply.md) assurance notes.

## Elaborated away

- **typedefs.** `macAddr_t`, `ip4Addr_t` and `egressSpec_t` are their
  widths, 48, 32 and 9.
- **`const bit<16> TYPE_IPV4 = 0x800`.** A literal in the one select case
  that used it, written in decimal as the schema requires: 2048.
- **`standard_metadata`.** The three intrinsic fields the program actually
  uses become fields of the program's own `metadata` struct, which is the
  metadata contract of the step-1 architecture: `ingress_port`, which the
  architecture provides, and `egress_port` and `drop`, which it consumes.
  `standard_metadata.egress_spec = port` is `meta.egress_port = port`, and
  `mark_to_drop(standard_metadata)` is `meta.drop = true`. This is the
  substance of claim 3 on one program: the packet's fate is data the block
  writes, not an effect it performs.
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
  `hdr.ipv4.hdrChecksum`. v1model runs the block after egress, which is
  empty here, so the call sits at the end of the one control under the
  same `hdr.ipv4.isValid()` guard. The printer turns it back into
  v1model's `hash(..., HashAlgorithm.csum16, 16w0, { data }, 32w65536)`,
  the same arithmetic. Every expected IPv4 header in the vectors carries
  the checksum this computes, derived by hand in each file.

## Deferred

- **`MyVerifyChecksum`.** `verify_checksum` is left out. In v1model a
  failed check sets `standard_metadata.checksum_error`, which the tutorial
  program never reads, so nothing observable is lost: the vectors send a
  zero input checksum, which is wrong, and it goes unnoticed on the way in
  and is overwritten on the way out. A verify extern would need a contract
  field to report through, and none is declared yet.
- **`size = 1024`** is carried on the table but is informative; the IR gives
  it no meaning and the interpreter does not bound the entry count.
- **The egress pipeline.** The tutorial program's `MyEgress` is empty, so
  nothing is lost; the step-1 architecture runs one control regardless.
