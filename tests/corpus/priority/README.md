# priority

p4c's `table-entries-priority-bmv2`, a companion to the ACL: one ternary
table whose `const entries` carry `@priority` annotations, with three
vectors that each match more than one entry. It is the only priority-bearing
`const entries` in p4c's v1model suite, so it is the program that pins the
frontend's mapping from p4c's convention onto the IR's.

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/table-entries-priority-bmv2.p4` |
| IR | `priority.txtpb`, regenerated from the eDSL |
| eDSL | `priority.py` |
| Vectors | `table_entries_priority.stf`, p4c's file with the edit listed in its header |

## Elaborated away

- **`@priority`.** p4c's BMv2 backend (`backends/bmv2/common/control.h`,
  `convertTableEntries`) numbers const entries with a counter that starts
  at 1 and advances after every entry, annotated or not: an annotated
  entry takes its annotation, an unannotated one the counter's value, and
  BMv2 lets the smaller number win. The source's entries are therefore

  | entry | source | p4c priority | IR priority |
  |---|---|---|---|
  | 1 | `0x1111 &&& 0xF ... @priority(3)` | 3 | 1 |
  | 2 | `0x1181` | 2 | 2 |
  | 3 | `0x1181 &&& 0xF00F ... @priority(1)` | 1 | 3 |

  The IR's priority is larger-wins everywhere
  ([decisions.md](../../../docs/decisions.md), "Entry priority"), so the
  mapping is `IR = 4 - p4c`, any order-reversing injection of the three
  numbers being equivalent. Entries keep the source's order in the golden;
  the printer prints them in descending priority without annotations so
  that p4c, numbering by position, sees the same order. Two entries with
  the same p4c priority and overlapping keys would have no faithful IR
  form, since the IR rejects that tie at validation; the source has none.
- **Canonical ternary values.** `0x1111 &&& 0xF` is stored as value `0x1`
  under mask `0xF` and `0x1181 &&& 0xF00F` as `0x1001` under `0xF00F`,
  since an entry value may set no bit outside its mask
  ([semantics.md](../../../docs/semantics.md), "Tables"); the plain `0x1181`
  is a full mask.
- **`standard_meta.egress_spec`.** The source's `Meta_t` is empty; the
  program's has the one contract field the source writes, `egress_port`,
  and `m` and `standard_meta` become one `meta`. `h` keeps its name.
- **Unsized literals.** `a_with_control_params(1)` and the others take the
  parameter's width, `bit<9>`.
- **`packet_in`, `packet_out`, `V1Switch`.** As in every corpus program;
  `vrfy`, `update` and `egress` are empty and left out.

## Deferred

- **The STF's own comment** describes `v` as `bit<1>` where the program
  declares `bit<8>`. It is p4c's comment and the bytes are consistent with
  `bit<8>`; the copy leaves it as written.
- **Sizes.** The source declares none and the table carries none.
