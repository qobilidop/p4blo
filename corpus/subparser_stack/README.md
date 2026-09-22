# subparser_stack

p4c's `subparser-with-header-stack-bmv2`, rewritten in the eDSL. It is the
companion of [stacks](../stacks/README.md) for the sub-parser path: the
same three header types, but the first `h2` header is extracted by a
sub-parser into `hdr.h2.next`, and the top-level parser continues from
where the sub-parser left the stack. The one vector's whole point is that
the sub-parser's extract advances `nextIndex` through the `inout`
argument, so the second header lands in `h2[1]` and the control reports
valid bits `03`.

| | |
|---|---|
| Source | [p4lang/p4c](https://github.com/p4lang/p4c) `testdata/p4_16_samples/subparser-with-header-stack-bmv2.p4` |
| IR | `subparser_stack.txtpb`, generated from the eDSL |
| eDSL | `subparser_stack.py` |
| Vectors | `subparser-with-header-stack-bmv2.stf`, p4c's file verbatim |

## Elaborated away

- **The sub-parser.** `subParserImpl(packet_in pkt, inout headers hdr, out
  bit<8> ret_next_hdr_type)` is a parser block with the two parameters
  `hdr` (inout) and `ret_next_hdr_type` (out); the packet travels by the
  block's kind. `subParserImpl() subp;` and `subp.apply(pkt, hdr,
  my_next_hdr_type)` are a block call from the state, naming the block: an
  instantiation without constructor arguments adds nothing, and the IR has
  no instances. The top-level parser's `out headers hdr` is passed as the
  `inout` argument, as in the source.
- **The parser-scoped local.** `bit<8> my_next_hdr_type;` declared in the
  parser body, outside any state, is a block local; it is written by the
  sub-parser call in `parse_first_h2` and read by that state's `select`.
- **`#define MAX_H2_HEADERS 5`.** The preprocessor constant is the number
  5.
- **Slice lvalues.** `hdr.h1.h2_valid_bits[i:i] = 1` becomes the
  read-modify-write `f = (f & ~mask) | (v << lo)` on the whole `bit<8>`
  field, written by `set_slice` in the source, exactly as in
  [stacks](../stacks/README.md#elaborated-away).
- **Unsized literals.** The select cases `2:` and `3:` and the comparisons
  `== 1`, `== 2`, `== 3` take their widths from the key or the other
  operand, which the eDSL does.
- **`hdr.h2.last`** is `hdr.h2[hdr.h2.lastIndex]`.
- **`standard_metadata`.** Unused, so `M` is an empty struct; with no
  `egress_port` the switch sends the packet to port 0, as the vector
  expects.
- **`error { BadHeaderType }`** is declared after core.p4's seven errors.
- **`isValid()` and `emit`.** The IR's own nodes; `packet.emit(hdr.h2)`
  emits the stack's valid elements in index order.

## Deferred

- **The empty blocks.** `cEgress`, `vc` and `uc` have empty bodies and are
  left out.
- **The reject path.** No `verify` fails in the vector, so `BadHeaderType`
  is never raised, and neither is `StackOutOfBounds`: the vector carries
  two `h2` headers into a stack of five.
