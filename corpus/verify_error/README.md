# verify_error

p4c's `issue1824-bmv2`, a companion to the ACL: user-declared errors, two
`verify(false, ...)` calls in a row, and a control that tests
`parser_error != error.NoError`. Its one vector checks that a failing
`verify` rejects with the error recorded, that the header extracted before
it survives into the control, and that the control's rewrite reaches the
wire.

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/issue1824-bmv2.p4` |
| IR | `verify_error.txtpb`, regenerated from the eDSL |
| eDSL | `verify_error.py` |
| Vectors | `issue1824.stf`, p4c's file unchanged |

## Elaborated away

- **`error { ... }`.** The four errors are declared after core.p4's seven,
  in the source's order, as [semantics.md](../../docs/semantics.md)
  ("Errors") fixes the list.
- **Two `verify(false, ...)`.** Written as two `verify` statements. The
  first raises `IPv4BadPacket` and the parser stops there, so the second
  never runs and the error recorded is the first; the vector cannot tell
  the two apart, and the spec says the same.
- **`standard_metadata`.** The source's `metadata` keeps its `mystruct1`
  field, unused, and gains `parser_error` under the contract's name. The
  program never writes `egress_spec`, so no `egress_port` is declared: an
  undeclared contract field reads as zero
  ([decisions.md](../../docs/decisions.md), "Architecture rules"), which is
  BMv2's default egress port too, and the vector expects port 0.
- **`0xbad`** takes the width of `dstAddr`, `bit<48>`.
- **`packet_in`, `packet_out`, `V1Switch`.** As in every corpus program;
  `MyVerifyChecksum`, `MyComputeChecksum` and `MyEgress` are empty and
  left out.

## Deferred

- **What the issue was about.** p4c issue 1824 concerned how BMv2's JSON
  spells error values once a program declares more than nine of them. That
  is a backend concern with no counterpart in the IR, where errors are
  names; the vector is kept for what it says about `verify`.
