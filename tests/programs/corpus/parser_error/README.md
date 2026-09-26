# parser_error

p4c's `parser_error-bmv2`, a companion to the ACL: one Ethernet header and
a control that reads `parser_error`. Its second vector is the reason it is
here. A 6-byte packet fails the extract; the control still runs, makes the
header valid and zeroes it; and the output is 14 zero bytes followed by all
six original bytes, with `$` demanding that exact length. That checks two
things at once: a failed extract consumes nothing
([semantics.md](../../../../docs/ir-semantics.md), "Extraction past the packet
end"), and the control runs after a parser rejection with `parser_error`
set ([design.md](../../../../docs/design.md#architectures)).

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/parser_error-bmv2.p4` |
| IR | `parser_error.txtpb`, regenerated from the eDSL |
| eDSL | `parser_error.py` |
| Vectors | `parser_error.stf`, p4c's file unchanged |

## Elaborated away

- **`standard_metadata`.** The source's `local_metadata_t` is empty; the
  program's has the two contract fields the source touches:
  `parser_error`, which the architecture provides, and `egress_spec`,
  which it consumes. `standard_metadata.parser_error ==
  error.PacketTooShort` is `meta.parser_error == PacketTooShort`, the
  literal of the core error, and `standard_metadata.egress_spec = 0` is
  `meta.egress_spec = 0`.
- **`b.emit(hdr)` of the whole struct** is kept as it is: the IR's `emit`
  takes a header, a stack, or a struct of those, and emits the struct's
  fields in order.
- **Unsized literals.** `hdr.eth.type = 0` and the two others take the
  field's width.
- **`packet_in`, `packet_out`, `V1Switch`.** As in every corpus program;
  `verify_checks`, `compute_checksum` and `egress` are empty and left out.
- **A field named `type`.** The header keeps the source's field name. A
  header view has one real attribute per field and no `__getattr__`, so
  `hdr.eth.type` is the field and nothing else. The IR is unaffected.

## Deferred

Nothing. The program uses no extern, no table and no size.
