# forwarder

The p4lang tutorial's `basic` forwarder, rewritten by hand as a p4blo
program in protobuf text format. It is the first corpus program and the
honest test of claim 1: whether the core is small enough, and
post-elaboration enough, to hold a real program without an escape hatch.

| | |
|---|---|
| Source | [p4lang/tutorials](https://github.com/p4lang/tutorials) `exercises/basic/solution/basic.p4` |
| IR | `forwarder.txtpb` |
| Vectors | `forward.stf`, `miss.stf`, `non_ipv4.stf`, `lpm_precedence.stf`, `too_short.stf` |

It is written by hand for step 1 and regenerated from the eDSL in step 3;
until then it rots with every schema change, which
[design.md](../../docs/design.md#risks) accepts.

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

## Deferred

- **The checksum.** `MyVerifyChecksum` and `MyComputeChecksum` are left out
  entirely: `verify_checksum` and `update_checksum` are v1model externs, and
  externs arrive in step 2. The consequence is visible in the vectors, where
  `hdr.ipv4.hdrChecksum` is carried through unchanged and is therefore wrong
  after the TTL decrement. It is wrong in the expected output too, on
  purpose, so that the day the extern lands the vectors change and say so.
- **`size = 1024`** is carried on the table but is informative; the IR gives
  it no meaning and the interpreter does not bound the entry count.
- **The egress pipeline.** The tutorial program's `MyEgress` is empty, so
  nothing is lost; the step-1 architecture runs one control regardless.
