# register_bounds

Our own program: a `register<bit<8>>(4)` indexed by an 8-bit header
field, so that most packets name a cell beyond the end. It exists for
one closed behavior, "a read at or beyond `size` yields zero and a
write there is ignored" ([semantics.md](../../../docs/ir-semantics.md),
"Externs"; `impl/python/p4blo/arch/externs/register.py`;
`ir/P4bloIR/Externs.lean`), which the [stateful](../stateful/README.md)
program cannot reach: its register has 256 cells and its index is an
8-bit field cast to `bit<32>`, so neither its vectors nor the
differential random sweep, which draws indices from the same field,
ever crosses the bound (review of steps 2-5, finding 4).

| | |
|---|---|
| Source | ours |
| IR | `register_bounds.txtpb`, generated from the eDSL |
| eDSL | `register_bounds.py` |
| Vectors | `bounds.stf` (ours) |

## The program

The packet is one header, `idx`, `val`, `got` (`out` being a P4
keyword). The control reads cell `(bit<32>) idx`, writes back the sum
with `val`, then reads the cell again into `got`. In range the output
reports the cell's new value and
the cell keeps it for the next packet; beyond the end the first read
gives zero, the write goes nowhere, and the second read gives zero
again, so the output is `00` however often the same index is sent. A
cell that wraps to zero in `bit<8>` is told apart from an out-of-range
zero by the packet after it, which finds the stored zero and adds to
it. The program declares no contract field, so every packet leaves on
port 0, as in the stateful program.

Under the random sweep (`impl/python/p4blo/drt`), `idx` is a random byte, so
about 252 of every 256 cases index past the end and the remaining few
land on the cells; both interpreters run every case.

## What the oracle sees

The printed program declares `register<bit<8>>(32w4) r` and reads and
writes it through `r.read` and `r.write`. Which value a simulator gives
an out-of-range read, and whether it accepts the write, is its own
choice; the vectors here assert p4blo's.

**They are not BMv2's.** The second oracle (`tests/oracle/bmv2/`) showed that
BMv2 agrees about the write, which it ignores, and not about the read:
`register_read` on an index at or beyond the array's size leaves the
destination untouched rather than zeroing it, so a field keeps whatever
the parser put there. Two of these vectors therefore diverge on BMv2 and
are carried as a known divergence in `tests/test_oracle_bmv2.py`. P4
leaves an out-of-range register access implementation-defined, p4blo's
choice is written in `docs/ir-semantics.md` and implemented twice, and the
divergence is documented rather than resolved; see `.agents/decisions.md`.
