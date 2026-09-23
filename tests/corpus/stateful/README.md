# stateful

p4c's `issue1097-2-bmv2`, the stateful pick of
[decisions.md](../../../docs/decisions.md): one program-level
`register<bit<8>>(256)` read and written from both halves of the pipeline.
It is the corpus program for the extern registry, and the only p4c v1model
STF program whose register is both read and written.

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/issue1097-2-bmv2.p4` |
| IR | `stateful.txtpb`, generated from the eDSL |
| eDSL | `stateful.py` |
| Vectors | `fresh_cells.stf` (p4c's two, verbatim), `persist.stf` (ours) |

## Elaborated away

- **`ingress` and `egress`.** The architecture runs one control, so the
  two are one control, `pipeline`, whose body is the ingress body followed
  by the egress body. Nothing happens between them in v1model that this
  program could observe: it has no tables, no egress-side metadata, and
  no clone or recirculate.
- **`register<bit<8>>(256) r`.** The generic `register<T>` is the
  monomorphic extern type `register` with `T = bit<8>`, which
  `p4blo.edsl.externs.Register[bit8]` declares, and `r` is an instance
  with the one constructor argument `256`. Both halves call the same
  instance.
- **`(bit<32>) h.myhdr.reg_idx_to_update`.** An explicit cast in the
  source is a `cast` node in the IR, written once per call as the source
  writes it.
- **`0x2a`.** An unsized literal; the eDSL gives it the width of `write`'s
  `value` parameter, `bit<8>`.
- **`bit<8> x` and `bit<8> tmp`.** Locals of the apply block become locals
  of the control block, which is where the IR keeps them.
- **`standard_metadata`.** Unused, and `Meta` is empty. The program
  declares no contract field, so the switch reads `egress_port` as 0 and
  `drop` as false; every packet leaves on port 0, which is what p4c's
  vectors expect of BMv2 too.
- **The parser's `packet_in` and the deparser's `packet_out`.** Carried by
  the block's kind, as in the forwarder.

## Added

- **The seed guard.** The donor writes `0x2a` to the cell unconditionally
  in ingress, then reads it back in egress, so its output is always
  `0x2a + value_to_add` whatever the cell held before: no vector could
  observe state across packets. The donor also reads the cell into `x` in
  ingress and never uses it. Here the write is `if (x == 0)`: a cell is
  seeded with `0x2a` the first time it reads as zero and accumulates after
  that. p4c's two vectors each touch a fresh cell, so they run the donor's
  path unchanged; `persist.stf` hits a cell twice and sees the sum. The
  cost is that a cell that wraps to exactly zero is re-seeded, which
  `persist.stf` shows on purpose.
- **`counter(256) pkts`.** v1model's `counter(256, CounterType.packets)`,
  counted once per packet at the register's index, first thing in the
  ingress half. STF cannot read a counter, so no vector observes it and it
  changes no output; it is here so that the printer and the oracle exercise
  a counter at all.

## Deferred

- Nothing of the donor's. `vrfy` and `update` are empty in the source.
