# acl

p4c's `ternary2-bmv2`, the corpus ACL: five ternary tables with runtime
entries and overlapping priorities, a parser loop over a header stack, and
a dispatch on which action a table ran. It is the program that fixes the
priority convention (see [decisions.md](../../../.agents/decisions.md), "Entry
priority") and the first with vectors produced by BMv2 and reviewed by the
p4c maintainers.

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/ternary2-bmv2.p4` |
| IR | `acl.txtpb`, regenerated from the eDSL |
| eDSL | `acl.py` |
| Vectors | `ternary2.stf`, p4c's `ternary2-bmv2.stf` with the edits listed in its header |

## Elaborated away

- **`switch (ex1.apply().action_run)`.** Out by elaboration per
  [design.md](../../../docs/design.md#scope). A control local `ex1_run`
  (`bit<8>`) records which of `ex1`'s actions ran: the body sets it to 0
  before applying `ex1`, `act1`, `act2` and `act3` assign 1, 2 and 3, and
  `setbyte` assigns 4; `noop`, the default action, stays empty and leaves
  the 0. An `if`/`else` chain on `ex1_run` then applies `tbl1`, `tbl2` or
  `tbl3`. The source's `switch` has no default case, so 0 and 4 fall
  through to nothing, as they do here.
- **`setbyte(out bit<8> reg, bit<8> val)` bound per table.** The source
  lists `setbyte(hdrs.extra[0].b1)`, `setbyte(hdrs.data.b2)`,
  `setbyte(hdrs.extra[1].b1)` and `setbyte(hdrs.extra[2].b2)` in the
  action lists of `ex1`, `tbl1`, `tbl2` and `tbl3`. The IR's tables name
  actions and its actions take only directionless data, so there is one
  action per table with the bound lvalue substituted: `setbyte`,
  `setbyte_1`, `setbyte_2`, `setbyte_3`, each taking `val`, named as p4c's
  own frontend names them (`ternary2-bmv2-frontend.p4`). The vectors name
  the copy of the table they add to.
- **`standard_metadata.egress_spec`.** The source's `Meta` is empty; the
  program's `Meta` has the one contract field the source writes,
  `egress_spec`, and the parser's and ingress control's `inout Meta m` and
  `inout standard_metadata_t meta` become one `meta`.
- **`hdrs.extra.last`.** `hdrs.extra[hdrs.extra.lastIndex]`; the eDSL's
  `.last` is that expression in one word, and the IR holds the index. The
  select keyset `8w0x80 &&& 8w0x80` is `masked(ExtraB2.MORE, ExtraB2.MORE)`
  at the key's width.
- **Key names.** `Key.name` is what p4c's STF calls each key, `data.f1`,
  `extra[0].h` and `data.f2`: the header-struct parameter stripped and, for
  the stack element, p4c's `$0` written `[0]`. A key on a stack element has
  no dotted path of its own, so the name is what the vectors resolve by.
- **`packet_in`, `packet_out`, `V1Switch`.** The parser and deparser carry
  the packet by their kind, and the three exports are the instantiation.
  `vrfy`, `update` and `egress` are empty and left out.
- **Unsized literals.** Action data and keyset values take their widths
  from context, as everywhere in the eDSL.

## Deferred

- **A fifth `extra` header.** A packet whose fourth `extra_h` has `b2 &
  0x80` set would extract past the four-element stack and reject with
  `StackOutOfBounds`. No vector exercises it.
- **The egress pipeline** is empty in the source, so nothing is lost.
- **Sizes.** The source declares none and the tables carry none.
