# priority

p4c's `table-entries-priority-bmv2`, a companion to the ACL: one ternary
table whose `const entries` carry `@priority` annotations, with three
vectors that each match more than one entry. It is the only priority-bearing
`const entries` in p4c's v1model suite, so it is the program that pins how
the IR numbers const entries. P4-SpecTec follows portable language priority
syntax; p4c's BMv2 backend honors this source's nonstandard `@priority`
extension, so their expected answers differ. This does not establish a BMv2
violation of the language: p4blo chooses the portable interpretation, and
its printer emits explicit language priorities. The
[discrepancy catalog](../../../../docs/oracle-discrepancies.md#const-entry-priority-annotations)
records that policy and a reduced reproducer.

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/table-entries-priority-bmv2.p4`, pinned at `tests/oracles/frontend/p4c/table-entries-priority-bmv2.p4` |
| IR | `priority.txtpb`, regenerated from the eDSL |
| eDSL | `priority.py` |
| Vectors | `table_entries_priority.stf`, p4c's file with the two edits listed in its header |

## Elaborated away

- **Priorities, by the specification's numbering.** P4 1.2.5 section
  14.2.1.4, as P4-SpecTec mechanizes it in
  `$set_priorities_of_tableEntryListIR`
  (`spec/5-typing/5.02.2-typing-table-context.watsup` at the pin), numbers
  the entries of a table with the defaults `largest_priority_wins = true`
  and `priority_delta = 1`: an entry written with `priority = n:` keeps
  `n`, and the larger wins. When no entry has one, the first takes
  `(size - 1) * delta + 1` and each later one the previous minus the
  delta, so list order decides. `@priority(n)` is not that syntax: it is
  p4c's non-standard annotation (the source's own comment says the
  language decided against it), and the specification's typing carries
  it as an annotation without reading it. None of the source's entries
  therefore has a priority in the language's sense, and the three are
  numbered by position under the portable language interpretation:

  | entry | source | rule | IR priority | p4c/BMv2 number (smaller wins) |
  |---|---|---|---|---|
  | 1 | `0x1111 &&& 0xF ... @priority(3)` | first, (3 - 1) * 1 + 1 | 3 | 3, its annotation |
  | 2 | `0x1181` | previous minus delta, 3 - 1 | 2 | 2, the counter |
  | 3 | `0x1181 &&& 0xF00F ... @priority(1)` | previous minus delta, 2 - 1 | 1 | 1, its annotation |

  The numbers happen to coincide; what differs is which one wins. p4c's
  BMv2 backend (`backends/bmv2/common/control.h`, `convertTableEntries`)
  numbers const entries with a running counter, annotated entries taking
  their annotation, and BMv2 lets the smaller number win, so the third
  entry ranks highest there and the first ranks highest here. The
  source's comment ("the 3rd entry in the list below will win") and p4c's
  vectors describe BMv2's reading. That P4-SpecTec ignores the
  annotations was checked at the pin: with `@priority(3)` and
  `@priority(1)` swapped, or both removed, it routes every packet exactly
  as it does the original.

  The packets decide as follows, with the entries each one matches:

  | vector line | packet `t` | matches | specification (IR, P4-SpecTec) | p4c's file (BMv2) |
  |---|---|---|---|---|
  | 24 | `0001` | 1 | port 1 | port 1 |
  | 29 | `1001` | 1, 3 | port 1 (priority 3 over 1) | port 3 |
  | 34 | `1181` | 1, 2, 3 | port 1 (priority 3 over 2, 1) | port 3 |

  The specification's column was established independently of p4blo:
  P4-SpecTec at the pin, run on p4c's unedited program and p4c's unedited
  STF file (`p4spectec sim spec -arch v1model -i p4c/p4include -p
  table-entries-priority-bmv2.p4 -stf table-entries-priority-bmv2.stf`,
  exit 1), passes the first packet and fails the other two, outputting
  `0210010000b0` and `0311810000b0` on port 1 where the file expects port
  3. The vector's second and third expectations are p4c's with the port
  changed to 1, which is exactly those outputs; the printed golden passes
  them on P4-SpecTec (`tests/oracles/test_oracle.py`). BMv2 compiled from the
  source gives p4c's answer, a strict expected failure in
  `tests/oracles/test_oracle_bmv2.py`; the printed golden passes on BMv2 too,
  because the printer writes explicit priorities with
  `largest_priority_wins = true` rather than relying on position.
  Entries keep the source's order in the golden. Two entries with equal
  priority and overlapping keys would have no faithful IR form, since the
  IR rejects that tie at validation; the source has none.
- **Canonical ternary values.** `0x1111 &&& 0xF` is stored as value `0x1`
  under mask `0xF` and `0x1181 &&& 0xF00F` as `0x1001` under `0xF00F`,
  since an entry value may set no bit outside its mask
  ([semantics.md](../../../../docs/ir-semantics.md), "Tables"); the plain `0x1181`
  is a full mask.
- **`standard_meta.egress_spec`.** The source's `Meta_t` is empty; the
  program's has the one contract field the source writes, `egress_spec`,
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
