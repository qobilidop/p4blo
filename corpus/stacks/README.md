# stacks

p4c's `header-stack-ops-bmv2`, rewritten in the eDSL. It is the header
stack program of the corpus: every packet carries three op bytes, and each
op pushes or pops the five-deep `h2` stack, fills a slot, or invalidates
one; the control then records which slots are valid in `h1.h2_valid_bits`,
so that the vectors can read the stack's state off the output packet. The
fifteen vectors were produced by BMv2 and reviewed by the p4c maintainers,
and they exercise exactly the rules under "Header stacks" in
[semantics.md](../../docs/semantics.md): `push_front` and `pop_front` on
full, partial and empty stacks, holes left by `setValid` and what `emit`
does with them, and `next` advancing through the parser and travelling
with the stack through a sub-control's `inout` argument (the STF's "Note
1", p4c issue #1128, is a bug in exactly that copy).

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/header-stack-ops-bmv2.p4` |
| IR | `stacks.txtpb`, generated from the eDSL |
| eDSL | `stacks.py` |
| Vectors | `header-stack-ops-bmv2.stf`, p4c's file verbatim |

The STF file's long header is its own history of three BMv2 versions; the
`#expect` lines for the older two are comments, and every live `expect` is
the P4_16 semantics ("v3").

## Elaborated away

- **`#define MAX_H2_HEADERS 5`.** The preprocessor constant is the number
  5, a Python constant in the source and a stack size in the IR.
- **Slice lvalues.** `hdr.h1.h2_valid_bits[i:i] = 1` has no `LValue` in the
  IR ([decisions.md](../../docs/decisions.md): slice lvalues are
  elaborated, not added). `set_slice` in the source writes the
  read-modify-write of the whole field, `f = (f & ~mask) | (v << lo)`,
  with every literal at the field's width: for `[2:2] = 1` the IR holds
  `f = (f & ~0x04) | (0x01 << 0x02)` on `bit<8>`, the complement and shift
  as nodes, so the golden reads like the formula.
- **Unsized literals.** `op[7:4] == 1`, `hdr.h2[0].f1 = 0xa0`, the select
  cases `2:` and `3:`: each takes its width from the other operand, the
  target or the key, which the eDSL does.
- **`hdr.h2.last`** is `hdr.h2[hdr.h2.lastIndex]`, which is how the
  language defines it; the IR has `lastIndex` and indexing, and no `last`.
- **The sub-control instance.** `cDoOneOp() do_one_op;` and
  `do_one_op.apply(hdr, hdr.h1.op1)` are a block call naming the block:
  an instantiation without constructor arguments adds nothing, and the IR
  has no instances. The block is called three times with `op1`, `op2` and
  `op3`.
- **The `in` argument that overlaps the `inout` one.** `do_one_op.apply(hdr,
  hdr.h1.op1)` passes a field of `hdr` beside `hdr` itself. The validator
  refuses any call in which an `out` argument may alias another argument,
  so that copy-in and copy-out order never matters; the source therefore
  reads the op into a control local first, `op1 = hdr.h1.op1;
  cDoOneOp(hdr, op1)`. This is what `in` means anyway, the argument is
  copied before the callee runs, and it is the hoist p4c's own
  side-effect-ordering pass performs, so the program's meaning is
  unchanged.
- **`standard_metadata`.** The program never reads or writes it, so `M` is
  an empty struct. With no `egress_port` in the metadata contract the
  switch sends every packet to port 0, which is what every vector expects
  ([decisions.md](../../docs/decisions.md), architecture rules).
- **`error { BadHeaderType }`** is declared after core.p4's seven errors,
  as the IR requires, and `verify(..., error.BadHeaderType)` names it.
- **The parser's `packet_in` and the deparser's `packet_out`.** A p4blo
  parser and deparser carry the packet by their kind, not as a parameter.
- **`isValid()`, `setValid()`, `setInvalid()`, `push_front(n)`,
  `pop_front(n)`, `emit`.** Each is the IR's own node; `packet.emit(hdr.h2)`
  is an emit of the stack, which writes its valid elements in index order.

## Deferred

- **The empty blocks.** `cEgress`, the verify-checksum control `vc` and
  the update-checksum control `uc` have empty bodies and are left out; the
  step-1 architecture runs one control regardless.
- **`push_front(6)` and `pop_front(6)`.** The arms are in the IR but no
  vector reaches them; the vectors use counts 1, 4 and 5.
- **The reject path.** Every `hdr_type` byte in the vectors is right, so no
  `verify` fails and `BadHeaderType` is never raised.
