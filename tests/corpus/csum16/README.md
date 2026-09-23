# csum16

p4c's `issue655-bmv2`: a 16-bit field incremented in ingress and the
Internet checksum over it recomputed into the field beside it. It is the
unit program for the `checksum16` extern; its six BMv2-produced vectors
walk the 0xFFFF/0x0000 edge of one's-complement arithmetic, which pins the
implementation the forwarder's IPv4 checksum uses.

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/issue655-bmv2.p4` |
| IR | `csum16.txtpb`, generated from the eDSL |
| eDSL | `csum16.py` |
| Vectors | `edge_cases.stf` (p4c's six, verbatim) |

## Elaborated away

- **`update_checksum(true, { hdr.h.d }, hdr.h.c, HashAlgorithm.csum16)`.**
  A v1model function call in the `uc` control becomes a `checksum16`
  extern instance, `csum`, whose `compute(in bit<16> data)` takes the field
  list concatenated in order, one 16-bit field here, so there is nothing to
  concatenate, and whose result is assigned to `hdr.h.c`. The condition is
  the literal `true`, so there is no guard. The printer reverses this into
  v1model's `hash(hdr.h.c, HashAlgorithm.csum16, 16w0, { hdr.h.d },
  32w65536)`, which is the same arithmetic.
- **`cIngress`, `cEgress` and `uc`.** One control, `cIngress`, whose body
  is the ingress body followed by the checksum update, at the end where
  v1model runs `uc`. `cEgress` is empty and contributes nothing.
- **`1`.** An unsized literal; the eDSL gives it the width of `hdr.h.d`.
- **`standard_metadata`.** Unused, and `Metadata` is empty: no contract
  field, so every packet leaves on port 0 undropped, as the vectors expect.
- **The parser's `packet_in` and the deparser's `packet_out`.** Carried by
  the block's kind, as in the forwarder.

## Deferred

- **`verify_checksum`.** The `vc` control is dropped. In v1model a failed
  verification sets `standard_metadata.checksum_error`, which this program
  never reads, so the six vectors cannot tell the difference: several send
  a wrong input `c` and are rewritten all the same. A verify extern would
  need a contract field to report through, and none is declared yet.
