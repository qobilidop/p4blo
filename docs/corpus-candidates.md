# p4c corpus candidates for p4blo

Survey date: 2026-09-22. Source: `p4lang/p4c` `main`, `testdata/p4_16_samples/`
(tree sha `d56afa13b25d8f5908bd78b023c9eadb16397844`, 1573 entries, listing
not truncated). Method: enumerated the directory through the GitHub git-trees
API, downloaded every `.stf` with its sibling `.p4` (253 pairs), and scanned
the 191 pairs that `#include` `v1model.p4` for constructs and STF line
counts with a regex pass, then read the candidates line by line. Nothing in
the repository was modified.

## 0. What the STF format means (from p4c's own runner)

Quoted from `backends/bmv2/bmv2stf.py` and `tools/testutils.py` on `main`,
because two judgments below depend on it.

Grammar (comment block at `bmv2stf.py:380`):

```
# statement : ADD qualified_name priority match_list action [= ID]
#           | ADD qualified_name match_list action [= ID]
#           | REMOVE [ALL | entry]
#           | CHECK_COUNTER ID(id_or_index) [count_type logical_cond number]
#           | EXPECT port expect_data
#           | EXPECT port
#           | NO_PACKET
#           | PACKET port packet_data
#           | SETDEFAULT qualified_name action
#           | WAIT
#           | direct_cmd
...
#           | REGISTER_READ qualified_name number
#           | REGISTER_WRITE qualified_name number number
#           | REGISTER_RESET qualified_name
```

- `add` priority. The optional integer after the table name is inverted
  before it reaches BMv2 (`parse_table_add`):

  ```python
  if prio:
      # Priorities in BMV2 seem to be reversed with respect to the stf file
      # Hopefully 10000 is large enough
      prio = str(10000 - int(prio))
  ```

  BMv2 treats the smaller number as the higher priority, so **in STF the
  larger `add` priority wins**. `ternary2-bmv2.stf` confirms it: with
  `add ex1 100 extra$0.h:0x25** act1(...)` and `add ex1 110 extra$0.h:0x2525
  act2(...)`, the packet with `h = 0x2525` matches both and the expected
  output shows `act2` ran (`extra[0].b1 = 0x27`, then `tbl2` set
  `extra[1].b1 = 0x28`).

- `const entries` priority is the opposite convention. `@priority(n)` with
  the **smaller** `n` wins (`table-entries-priority-bmv2.p4` comment:
  "the matching entry with the _smallest_ numerical priority will win"),
  and entries without an annotation win in list order (first listed wins;
  `table-entries-ternary-bmv2.stf` packet `t=0x1187` matches entries 2, 3
  and 4 and expects entry 2). The IR's `Entry.priority` (uint32) must fix
  one convention and the STF runner must invert `add` priorities into it.

- Ternary key syntax. `*` hex digits are wildcards; `makeMask` turns
  `0x****0101` into `0x00000101&&&0xFFFF0FFF` (the `*` positions get a `0`
  in the mask, all other digits `F`). `&&&` may also be written directly.
  Decimal values are rejected for ternary keys. Lpm keys accept `v/len`
  or the same `*` convention (`makeLpm`).

- Key names. `extra$0.h` is rewritten to `extra[0].h` (`TableKeyInstance.set`:
  `re.compile("(.*)\$([0-9]+)(.*)")`). Names are whatever the BMv2 JSON
  calls the key: `data.f1` (header-struct parameter stripped), `meta.test`,
  or an explicit `@name("e")`. The IR's `Key.name` field can carry these.

- Action names may be qualified (`ingress.setb1`) or bare (`act1`); the
  runner resolves them per table (`actionByName(tableInstance, actionName)`).

- `expect <port> <hex>`: compared digit by digit after whitespace removal;
  `*` matches any digit; the received packet may be **longer** than the
  expectation unless the line ends in `$`:

  ```python
  # If the expected packet string ends with a '$' it means that the packets are only equal,
  # if they are the exact same length.
  ```

  `expect <port>` with no data means "any packets on this port".

- `wait` is a synchronisation point for the asynchronous BMv2 harness; a
  sequential interpreter can treat it as a no-op.

- `register_read/write/reset` and `check_counter` exist but no v1model STF
  uses them (only the PSA files do, e.g. `psa-register-read-write-bmv2.stf`).

## 1. Inventory

Of the 191 v1model programs with an STF, those touching the three
categories (feature scan; `add`/`packet`/`expect` line counts):

| program | add | pkt | exp | features |
|---|---|---|---|---|
| ternary2-bmv2 | 6 | 4 | 4 | ternary, stack `.next`/`.last`/index, masked select, `switch` action_run |
| table-entries-ternary-bmv2 | 0 | 5 | 5 | ternary, const entries, `_` entry |
| table-entries-priority-bmv2 | 0 | 3 | 3 | ternary, const entries, `@priority` |
| table-entries-exact-ternary-bmv2 | 0 | 5 | 5 | exact+ternary, const entries |
| table-entries-ser-enum-bmv2 | 0 | 5 | 5 | ternary on a serializable enum, const entries |
| parser_error-bmv2 | 0 | 2 | 2 | `parser_error == error.PacketTooShort` |
| issue1824-bmv2 | 0 | 1 | 1 | user `error {}`, `verify(false, ...)`, `parser_error != NoError` |
| issue510-bmv2 | 0 | 1 | 1 | `error`-typed metadata field |
| header-stack-ops-bmv2 | 0 | 15 | 15 | push/pop/setValid/setInvalid on stack, verify, sub-control |
| subparser-with-header-stack-bmv2 | 0 | 1 | 1 | sub-parser extracting into `.next`, verify |
| stack_complex-bmv2 | 0 | 1 | 1 | parser loop over stack, `.last`, cast |
| issue1097-2-bmv2 | 0 | 2 | 2 | global `register<bit<8>>`, read/write in ingress and egress |
| issue1814-1-bmv2 | 2 | 1 | 1 | control-local `register<bit<1>>`, read only, bool key |
| issue1566-bmv2 | 0 | 1 | 1 | `counter`, control constructor params |
| key-bmv2 | 2 | 4 | 4 | exact key on an expression, `@name` |
| issue2153-bmv2 | 1 | 2 | 2 | exact key, `switch` action_run |

Names the task suggested that do **not** exist with an STF: `basic_routing-bmv2`
(`.p4` only), `mpls*`, `vlan*` (only `xdp_vlan_push_pop_ebpf-kernel`, an
eBPF program), `register-bmv2`/`register*` (only `register-serenum-bmv2.p4`,
no STF), `counter-bmv2` (only `unused-counter-bmv2.p4`, no STF),
`parser-unroll-*` (none with STF), `acl*`, `lpm*` for v1model (only
`lpm_ebpf`, `lpm_ubpf`). `stack-bmv2.p4`, `stack-bvec-bmv2.p4`,
`inline-stack-bmv2.p4` exist without STF. The `psa-register-*` and
`psa-basic-counter-bmv2` programs have STFs but are PSA, not v1model.

Everything else with an STF is either out of scope by construction
(`union*`, `issue447-*`/`checksum*` with `varbit`, all `gauntlet_exit_*`,
`v1model-special-ops-bmv2` with clone/resubmit) or exercises arithmetic
and header-validity corners that are useful for layer-1 unit vectors but
not for the corpus.

## 2. Category 1: ACL (ternary keys with priorities; parser errors or verify)

### 2.1 `ternary2-bmv2.p4` / `ternary2-bmv2.stf`

Summary. Headers `data_h {f1:32, f2:32, h1:16, b1:8, b2:8}` and a stack
`extra_h[4] {h:16, b1:8, b2:8}`. Parser: `start` extracts `data`, then
state `extra` extracts `hdrs.extra.next` and loops while
`hdrs.extra.last.b2 &&& 0x80 == 0x80`. Ingress: five ternary tables:
`test1` on `data.f1` (actions `setb1(port,val)` sets `egress_spec` and
`data.b1`, `noop`), `ex1` on `extra[0].h` (actions `setbyte(out reg, val)`
bound to `extra[0].b1`, `act1/2/3(val)` writing `extra[0].b1`, `noop`),
and `tbl1/2/3` on `data.f2` each with `setbyte` bound to a different field
(`data.b2`, `extra[1].b1`, `extra[2].b2`). Apply: `test1`, then
`switch (ex1.apply().action_run)` dispatches to `tbl1/2/3`. Egress empty;
deparser emits `data` then the whole `extra` stack.

Out of scope / needs elaboration (exhaustive scan):
- `standard_metadata`: only `egress_spec` (in scope).
- Externs: none. No `exit`, `return`, `int<`, `varbit`, `header_union`,
  `value_set`, `hash`, `clone`, `resubmit`, `truncate`, `random`,
  `log_msg`, `assert`, `assume`, `digest`, `meter`, `direct_counter`,
  `action_selector`, `for`, no annotations.
- `switch (ex1.apply().action_run)` (line 94): elaboration already planned
  (the rewrite records which action ran, e.g. a metadata flag set by
  `act1/2/3`, and dispatches with `if`).
- Actions with a directional parameter bound in the table's action list:
  `setbyte(out bit<8> reg, bit<8> val)` used as `setbyte(hdrs.data.b2)`,
  `setbyte(hdrs.extra[0].b1)`, `setbyte(hdrs.extra[1].b1)`,
  `setbyte(hdrs.extra[2].b2)` (lines 72, 82, 86, 90). `Table.actions` in
  the IR is a list of names and `ActionCall.args` are literals, so this
  elaborates to one action per table with the lvalue substituted. p4c's own
  frontend does exactly that: `ternary2-bmv2-frontend.p4` has `setbyte`,
  `setbyte_1`, `setbyte_2`, `setbyte_3`, each `@name("ingress.setbyte")`
  taking only `val`. The STF calls all four `setbyte(val:...)`, so the
  p4blo STF runner must resolve action names per table (as p4c's does) or
  the corpus copy of the STF renames them.
- Unsized literals in `select` (`8w0x80 &&& 8w0x80` is sized; fine).
- `struct Meta {}` empty user metadata.
- `b.emit(hdrs.extra)`: emit of a whole header stack (emits each valid
  element in order). In scope per "emit", but the IR's `Emit.value` must
  accept a stack-typed expression.
- `#include "v1model.p4"` with quotes (cosmetic).
- Not exercised but latent: a fifth `extra` header with `b2 & 0x80` would
  overflow the 4-element stack (`StackOutOfBounds`); `test1` default action
  is not `const`.

STF (verbatim):

```
# SPDX-FileCopyrightText: 2016 VMware, Inc.
#
# SPDX-License-Identifier: Apache-2.0

add test1 0 data.f1:0x****0101 ingress.setb1(val:0x7f, port:2)
add test1 503 data.f1:0x****0202 ingress.setb1(val:7, port:3)

#          f1       f2      h1  b1 b2  h   b1 b2
expect 2 00000101 ******** **** 7f 66
packet 0 00000101 00000202 0303 55 66 7777 88 00
expect 3 00000202 ******** **** 07 66
packet 2 00000202 00000303 0404 55 66 7777 88 00
wait

add ex1 100 extra$0.h:0x25** act1(val:0x25)
add tbl1 100 data.f2:0x0202**** setbyte(val:0x26)
add ex1 110 extra$0.h:0x2525 act2(val:0x27)
add tbl2 100 data.f2:0x0202**** setbyte(val:0x28)

#          f1       f2      h1  b1 b2  h   b1 b2 payload
packet 0 01010101 02020202 0303 55 66 2500 ff 7f 01020304
expect 2 01010101 02020202 0303 7f 26 2500 25 7f 01020304
#          f1       f2      h1  b1 b2  h   b1 b2  h   b1 b2 payload
packet 0 01010101 02020202 0303 55 66 2525 ff ff 3333 ff 7f 01020304
expect 2 01010101 02020202 0303 7f 66 2525 27 ff 3333 28 7f 01020304
```

Verdict: **fits with named elaborations** (action_run switch; per-table
copies of `setbyte`). It is the only v1model STF that installs ternary
entries at runtime with explicit priorities (six `add` lines, two of
which overlap on `ex1` and decide the priority convention), and it doubles
as a second header-stack parser loop. It has no parser error or `verify`.

### 2.2 `table-entries-ternary-bmv2`, `table-entries-priority-bmv2`, `table-entries-exact-ternary-bmv2`

Summary (all three share the skeleton). Header `hdr {e:8, t:16, l:8, r:8,
v:8}`; parser extracts it; one ternary table on `h.h.t` (exact `h.h.e` +
ternary `h.h.t` in the exact-ternary variant) with `const entries` and
actions `a()` (`egress_spec = 0`) and `a_with_control_params(bit<9> x)`
(`egress_spec = x`); `default_action = a`; apply is one `t.apply()`.
Egress empty; deparser emits `h.h`. The port number in `expect` is the
entry that matched (0 = miss).

Out of scope / elaboration:
- `standard_metadata`: `egress_spec` only. No externs, no other flagged
  constructs (scan of every line: none of `exit/return/switch/int</varbit/
  header_union/value_set/hash/clone/...`).
- `const entries` with unsized literals (`0x1111 &&& 0xF`) → width
  elaboration; `_` don't-care entry → ternary mask 0 (or, for lpm, prefix 0).
- `@priority(3)` / `@priority(1)` annotations (priority variant only,
  lines 68, 70): these are the only priority-bearing entries in the whole
  v1model STF corpus; they map to `Entry.priority` with "smaller wins" and
  unannotated entries take list order.
- No `add` lines at all: the vectors exercise `const_entries`, not the
  runtime `add` path.

STFs (verbatim):

`table-entries-ternary-bmv2.stf`
```
# SPDX-FileCopyrightText: 2017 Barefoot Networks, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# header hdr { bit<8>  e; bit<16> t; bit<8>  l; bit<8> r; bit<1>  v; }

# t_ternary tests: if packets come on port 0, we missed!

expect 1 01 **** ** ** ** $
packet 0 01 1111 00 00 b0

# check that the mask works
expect 1 02 **** ** ** ** $
packet 0 02 0001 00 00 b0

expect 2 03 **** ** ** ** $
packet 0 03 1187 00 00 b0

expect 3 04 **** ** ** ** $
packet 0 04 1000 00 00 b0

expect 4 04 **** ** ** ** $
packet 0 04 aaaa 00 00 b0
```

`table-entries-priority-bmv2.stf`
```
# SPDX-FileCopyrightText: 2017 Barefoot Networks, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# header hdr { bit<8>  e; bit<16> t; bit<8>  l; bit<8> r; bit<1>  v; }

# t_ternary tests: if packets come on port 0, we missed!

expect 1 01 0001 ** ** ** $
packet 0 01 0001 00 00 b0

# should hit port 3, even though it matches the first entry
expect 3 02 1001 ** ** ** $
packet 0 02 1001 00 00 b0

# should hit port 3, even though it matches the second entry
expect 3 03 **** ** ** ** $
packet 0 03 1181 00 00 b0
```

`table-entries-exact-ternary-bmv2.stf`
```
# SPDX-FileCopyrightText: 2017 Barefoot Networks, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# header hdr { bit<8>  e; bit<16> t; bit<8>  l; bit<8> r; bit<8>  v; }

# t_ternary tests: if packets come on port 0, we missed!

expect 1 01 **** ** ** ** $
packet 0 01 1111 00 00 b0

expect 2 02 **** ** ** ** $
packet 0 02 1181 00 00 b0

expect 3 03 **** ** ** ** $
packet 0 03 1000 00 00 b0

expect 4 04 **** ** ** ** $
packet 0 04 1111 00 00 b0

# misses
expect  0 02 11F1 ** ** ** $
packet  0 02 11F1 00 00 b0
```

Verdict: **fit as is**, but they are 70-line micro-tests with one table
and no parser beyond one extract; they are better as `const_entries`
priority vectors folded into the ACL program's STF (or as validator/unit
vectors) than as the corpus ACL themselves.

### 2.3 Parser-error add-ons: `parser_error-bmv2`, `issue1824-bmv2`, `issue510-bmv2`

`parser_error-bmv2.p4`: Ethernet header only; ingress does
`if (standard_metadata.parser_error == error.PacketTooShort) { setValid;
zero the fields }` and `egress_spec = 0`; deparser `b.emit(hdr)` (emit of
the whole struct → elaborate to `emit(hdr.eth)`). No other flagged
constructs. The second vector sends a 6-byte packet: extract fails, the
parser rejects, v1model still runs ingress, and the output is 14 zero
bytes followed by **all six original bytes** with a strict `$`, i.e. a
failed extract consumes nothing.

```
# SPDX-FileCopyrightText: 2018 VMware, Inc.
#
# SPDX-License-Identifier: Apache-2.0

packet 0 012345678910 111213141516 0A0B
expect 0 012345678910 111213141516 0A0B

packet 0 012345678910
expect 0 000000000000 000000000000 0000 012345678910$
```

`issue1824-bmv2.p4`: header `{dstAddr:48, srcAddr:48}`; user `error {
IPv4OptionsNotSupported, IPv4ChecksumError, IPv4HeaderTooShort,
IPv4BadPacket }`; parser does `verify(false, error.IPv4BadPacket);
verify(false, error.IPv4HeaderTooShort);` after the extract; ingress sets
`dstAddr = 0xbad` (unsized literal → width elaboration) when
`stdmeta.parser_error != error.NoError`. No other flagged constructs.
Tests that a failing `verify` leaves `parser_error != NoError` (the
vector does not distinguish which of the two errors was recorded; the
spec says the first, since `verify` transitions to `reject` at once) and
that the packet still reaches ingress with the extracted header intact.

```
packet 0 112233445566 778899aabbcc
expect 0 000000000BAD 778899aabbcc
```

`issue510-bmv2.p4`: 1-byte header; user metadata has a field of type
`error` (`error parser_error;`) assigned `error.NoMatch` in the parser;
ingress `setInvalid()`s the header when it equals `error.NoMatch`. Tests
the `error` type as a value.

```
# SPDX-FileCopyrightText: 2017 VMware, Inc.
#
# SPDX-License-Identifier: Apache-2.0

packet 0 1234567890
expect 0 34567890
```

Verdict: all three **fit as is** (only `emit(hdr)` of a struct in
`parser_error-bmv2` needs a per-field expansion), but each is one or two
vectors around a single mechanism.

## 3. Category 2: header stacks

### 3.1 `header-stack-ops-bmv2.p4` / `.stf`

Summary. Headers `h1_t {hdr_type, op1, op2, op3, h2_valid_bits,
next_hdr_type}` (all 8-bit), stack `h2_t[5] {hdr_type, f1, f2,
next_hdr_type}`, `h3_t {hdr_type, data}`; user `error { BadHeaderType }`.
Parser: `start` extracts `h1`, `verify(hdr_type == 1)`, selects on
`next_hdr_type` (2 → `parse_h2`, 3 → `parse_h3`); `parse_h2` extracts
`hdr.h2.next`, verifies `h2.last.hdr_type == 2`, loops on
`h2.last.next_hdr_type`; `parse_h3` extracts `h3` and verifies. Ingress
instantiates sub-control `cDoOneOp(inout headers hdr, in bit<8> op)` once
and applies it for `op1`, `op2`, `op3`; the op byte's high nibble selects
`push_front(n)`, `pop_front(n)`, `h2[i].setValid()` + fill, or
`h2[i].setInvalid()`, and the low nibble gives `n`/`i`. Then it records
`h2[i].isValid()` for i in 0..4 into the bits of `h1.h2_valid_bits`.
No tables. Deparser emits `h1`, the `h2` stack, `h3`.

Out of scope / elaboration (exhaustive scan):
- `standard_metadata`: **none used**; the STF expects every packet on port
  0, so the v1model shim must default `egress_spec` to 0.
- Externs: none. None of `exit/return/switch/int</varbit/header_union/
  value_set/hash/clone/resubmit/truncate/random/log_msg/assert/assume/
  digest/meter/direct_counter/action_selector/for`; no annotations.
- `#define MAX_H2_HEADERS 5` (preprocessor; the eDSL just writes 5).
- Unsized literals compared with slices and fields: `op[7:4] == 1`,
  `op[3:0] == 1`.. (lines 82-155), `select` cases `2:`/`3:`, field
  assignments `hdr.h2[0].hdr_type = 2` etc. → width elaboration.
- **Slice as an lvalue**: `hdr.h1.h2_valid_bits[0:0] = 1;` through
  `[4:4]` (lines 177-189). The IR's `LValue` is `var | member | index |
  next`, so this needs either an `LSlice` kind or an elaboration to a
  read-modify-write on the whole field (`f = (f & ~mask) | (v << lo)`).
- Sub-control with a non-architecture `in bit<8> op` parameter, applied
  three times with different arguments (in scope as sub-control
  instantiation; note the STF's "Note 1": the stack's `next` index must be
  passed with the stack through the `inout` argument, which p4c issue
  #1128 once got wrong).
- `push_front(6)` / `pop_front(6)` on a 5-element stack are legal but
  never exercised (vectors use counts 1, 4, 5).
- `packet.emit(hdr.h2)`: stack emit.
- `verify` never fails in the vectors (every `hdr_type` byte is correct),
  so the reject path is not exercised.

STF (verbatim; the long header is the file's own history of BMv2
behaviour, and only the uncommented `expect` lines are live, all of
which are the P4_16-spec "v3" semantics):

```
# SPDX-FileCopyrightText: 2018 Cisco Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Here are abbreviated names for several versions of behavioral-model
# simple_switch referred to below:

# v1 - The 'original' version.

# v2 - Version 1.10.0 compiled without enabling support for P4_16
# header stacks, i.e. without supplying the command line option
# '--enable-WP4-16-stacks' when running 'configure'.

# v3 - Version 1.10.0 compiled _with_ enabling support for P4_16
# header stacks, i.e.  supplying the command line option
# '--enable-WP4-16-stacks' when running 'configure'.

######################################################################
# v1 - The 'original' version, before any changes were made to the
# behavior of push and pop primitives (those are the names in the BMv2
# JSON file for the push_front and pop_front methods in the P4_16
# language spec).
#
# Corresponds to this commit of repository
# https://github.com/p4lang/behavioral-model
#
# commit 9e4a70edbd7255cd0e00e92acc2c7e131cedeaf7
# Author: Antonin Bas <antonin@barefootnetworks.com>
# Date:   Tue Jan 2 10:33:08 2018 -0800
# 
#     Call export_bytes in Data::two_comp_mod operator
#
######################################################################
#
# v2 and v3 both use this version of the source code of the
# p4lang/behavioral-model Github repo:
#
# commit 6b5d99c54198102d11871a92a71d80e6958a0295
# Author: Antonin Bas <antonin@barefootnetworks.com>
# Date:   Thu Jan 4 10:26:42 2018 -0800
# 
#     changed VERSION number to 1.10.0 for release
#
######################################################################


# packet with 3 no-ops should pass through unchanged, except for
# h1.h2_valid_bits in output packet

packet 0  01 00 00 00 00 02   02 de ad 03   03 be
# v1 v2 v3
expect 0  01 00 00 00 01 02   02 de ad 03   03 be


# This one has an operation to push 1 header into h2 stack, but not
# otherwise change any valid bits, so 1 header should come out, but
# internally it should be h2[1], not h2[0], so h1.h2_valid_bits should
# be slightly different.
#
# Note 1: Due to p4c issue #1128, where it is not copying the 'next'
# state for header stacks when calling sub-controls, and because of
# the way bmv2 v1 depends on the value of 'next' in its 'push'
# primitive behavior, it incorrectly generates h2_valid_bits=1 in the
# output packet.

packet 0  01 11 00 00 00 02   02 de ad 03   03 be
# v1 v2
#expect 0  01 11 00 00 01 02   02 de ad 03   03 be
# v3
expect 0  01 11 00 00 02 02   02 de ad 03   03 be


# push_front(1) then fill in new h2[0].  2 h2 headers should come out.
#
# Incorrect output packet for v1 and v2 because same reason as at Note
# 1.
#
# v3 gives correct output packet according to P4_16 language spec.

packet 0  01 11 30 00 00 02   02 de ad 03   03 be
# v1
#expect 0  01 11 30 00 01 02   02 a0 0a 09   03 be
# v3
expect 0  01 11 30 00 03 02   02 a0 0a 09   02 de ad 03   03 be


# Only operation is to make hdr[2] valid and fill it in.  This
# intentionally creates a 'hole', but emit should include it in
# output.

packet 0  01 32 00 00 00 02   02 de ad 03   03 be
# v1 v2 v3
expect 0  01 32 00 00 05 02   02 de ad 03   02 a2 2a 09   03 be


# Like previous case, but also do a push_front(1) after
# hdr.h2[2].setValid().
#
# Incorrect output packet for v1 and v2 because same reason as at Note
# 1.
#
# v3 gives correct output packet according to P4_16 language spec.

packet 0  01 32 11 00 00 02   02 de ad 03   03 be
# v1 v2
#expect 0  01 32 11 00 05 02   02 de ad 03   02 a2 2a 09   03 be
# v3
expect 0  01 32 11 00 0a 02   02 de ad 03   02 a2 2a 09   03 be


# receive no h2 headers in input packet.  Make h2[0] valid and fill it
# in.  pop_front(1) should remove it before it goes out.
#
# Incorrect output packet for v1 and v2 because same reason as at Note
# 1.  Because 'next' is 0 instead of 1, pop_front(1) is a no-op.

packet 0  01 30 21 00 00 03   03 be
# v1 v2
#expect 0  01 30 21 00 01 03   02 a0 0a 09    03 be
# v3
expect 0  01 30 21 00 00 03   03 be



# Receive 5 valid h2 headers, send through without changing
packet 0  01 00 00 00 00 02   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe
expect 0  01 00 00 00 1f 02   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe


# Receive 5 valid h2 headers, push_front(1), fill in new h2[0], 5 valid h2 out
packet 0  01 11 30 00 00 02   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe
expect 0  01 11 30 00 1f 02   02 a0 0a 09   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   03 fe


# Receive 5 valid h2 headers, push_front(4), make none valid, 1 valid h2 out
packet 0  01 14 00 00 00 02   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe
expect 0  01 14 00 00 10 02   02 12 34 02   03 fe


# Receive 5 valid h2 headers, push_front(5), make none valid, 0 valid h2 out
packet 0  01 15 00 00 00 02   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe
expect 0  01 15 00 00 00 02   03 fe


# Receive 5 valid h2 headers, pop_front(1), 4 valid h2 headers out
packet 0  01 21 00 00 00 02   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe
expect 0  01 21 00 00 0f 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe


# Receive 5 valid h2 headers, pop_front(4), 1 valid h2 header out
packet 0  01 24 00 00 00 02   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe
expect 0  01 24 00 00 01 02   02 23 45 03   03 fe


# Receive 5 valid h2 headers, pop_front(5), 0 valid h2 headers out
packet 0  01 25 00 00 00 02   02 12 34 02   02 56 78 02   02 9a bc 02   02 de f1 02   02 23 45 03   03 fe
expect 0  01 25 00 00 00 02   03 fe


# Receive 3 valid h2 headers, make h2[3] valid and fill in, push_front(1), 4 out
packet 0  01 33 11 00 00 02   02 12 34 02   02 56 78 02   02 23 45 03   03 fe
expect 0  01 33 11 00 1e 02   02 12 34 02   02 56 78 02   02 23 45 03   02 a3 3a 09   03 fe


# Receive 3 valid h2 headers, make h2[3] valid and fill in, pop_front(1), 3 out
packet 0  01 33 21 00 00 02   02 12 34 02   02 56 78 02   02 23 45 03   03 fe
expect 0  01 33 21 00 07 02   02 56 78 02   02 23 45 03   02 a3 3a 09   03 fe
```

Verdict: **fits with named elaborations** (slice lvalue, unsized literal
widths). Fifteen vectors cover push/pop by 1, 4 and 5, push onto a full
stack, pop from an empty stack, holes in the stack (`setValid` on `h2[2]`
with `h2[1]` invalid, expected valid bits `05`), push after a hole, and
the interaction of `next` with `push_front` (one header in, `push_front(1)`
→ valid bits `02`, not `01`). It has no tables and no `add` lines.

### 3.2 `subparser-with-header-stack-bmv2.p4` / `.stf`

Summary. Same three header types and error as 3.1. A sub-parser
`subParserImpl(packet_in pkt, inout headers hdr, out bit<8>
ret_next_hdr_type)` extracts `hdr.h2.next`, verifies, and returns
`h2.last.next_hdr_type`. The top parser declares a parser-scoped local
`bit<8> my_next_hdr_type;`, extracts `h1`, and in `parse_first_h2` calls
`subp.apply(pkt, hdr, my_next_hdr_type)`, then continues extracting
further `h2` headers itself in `parse_other_h2`, then `h3`. Ingress only
records the valid bits into `h1.h2_valid_bits` (same five slice
assignments). No tables. Deparser emits `h1`, `h2` stack, `h3`.

Out of scope / elaboration: identical list to 3.1 minus push/pop/setValid
(no `standard_metadata`, no externs, no flagged constructs; `#define`;
unsized `select` cases; five slice lvalues; stack emit) plus:
- Sub-parser instantiation and `apply` from a state, with `packet_in`,
  `inout` stack-bearing struct and an `out` scalar (in scope).
- A parser-level local variable (`bit<8> my_next_hdr_type;` at line 64)
  living across states (`Block.locals`).

STF (verbatim):

```
# SPDX-FileCopyrightText: 2018 VMware, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# For any of these input packets, the only change from input packet to
# output packet should be the value of field h1.h2_valid_bits.  It
# should have a 1 in bit position i if h2[i] was valid after parsing.

# packet with 2 h2 headers should have h2_valid_bits=3 in output.

#           h1_t                h2_t          h2_t         h3_t
#        /---------------\    /-------\     /--------\    /---\
#        hdr_type  op3
#         | op1 op2 | h2_valid_bits
#         |  |  |   | |  next_hdr_type
#         |  |  |   | |  |    hdr_type
#         |  |  |   | |  |    |  f1 f2 next_hdr_type
#         |  |  |   | |  |    |  |  |  |
packet 0  01 00 00 00 ff 02   02 de ad 02   02 be ef 03   03 be

# This is what output packet _should_ be.  Both h2 headers in the
# input packet should be extracted, the first in the sub-parser, the
# second in the top level parser.  The first should go into h2[0], the
# second into h2[1].

expect 0  01 00 00 00 03 02   02 de ad 02   02 be ef 03   03 be
```

Verdict: **fits with the same elaborations**; one vector, whose whole
point is that the sub-parser's extract into `.next` advances the index the
parent then uses (expected valid bits `03`). Good companion vector for the
sub-parser path, not a corpus program on its own.

### 3.3 `stack_complex-bmv2.p4` / `.stf`

Summary. `hdr {f1:32, f2:32}`, stack `hdr[3] hs`, metadata `{v:32}`.
Parser `start` extracts `h.hs.next`, does `m.v = h.hs.last.f2; m.v = m.v +
h.hs.last.f2;` and `select(h.hs.last.f1) { 0: start; _: accept; }` (a
loop back to `start`). Ingress: keyless table `t` with `const
default_action = set_port()`, where `set_port` does `sm.egress_spec =
(bit<9>)m.v`. Deparser emits the stack.

Out of scope / elaboration: `egress_spec` only; no externs; no flagged
constructs; unsized `0` in select; `_` default; explicit narrowing cast
32→9; a table with no `key` and a `const default_action`; stack emit.
Latent: three headers with `f1 == 0` would overflow the stack.

STF (verbatim):

```
# SPDX-FileCopyrightText: 2017 Barefoot Networks, Inc.
#
# SPDX-License-Identifier: Apache-2.0

packet 0 00000001 00000002
expect 4 00000001 00000002
```

Verdict: **fits as is** but is one vector (`v = 2 + 2 = 4` → port 4) and
exercises assignment inside a parser state more than stacks.

## 4. Category 3: stateful (register, optionally counter)

### 4.1 `issue1097-2-bmv2.p4` / `.stf`

Summary. Header `myhdr_t {reg_idx_to_update:8, value_to_add:8,
debug_last_reg_value_written:8}`. Top-level `register<bit<8>>(256) r;`.
Ingress: `r.read(x, (bit<32>) idx); r.write((bit<32>) idx, 0x2a);` (the
read result is unused). Egress: `r.read(tmp, idx); tmp = tmp +
value_to_add; r.write(idx, tmp); h.myhdr.debug_last_reg_value_written =
tmp;`. No tables; deparser emits the header.

Out of scope / elaboration (exhaustive scan):
- `standard_metadata`: none used (port 0 by default, as the STF expects).
- Externs: `register<bit<8>>` (in scope) with `read(out T, bit<32>)` and
  `write(bit<32>, T)`; one program-level instance used from two blocks.
- Explicit casts `(bit<32>)` on the index (in scope); unsized `0x2a`
  (width elaboration); wrapping 8-bit add; an unused local `x`.
- None of `exit/return/switch/int</varbit/header_union/value_set/hash/
  clone/resubmit/truncate/random/log_msg/assert/assume/digest/meter/
  direct_counter/action_selector/for`; no annotations.

STF (verbatim):

```
# SPDX-FileCopyrightText: 2017 VMware, Inc.
#
# SPDX-License-Identifier: Apache-2.0

packet 0 00 17 00
expect 0 00 17 41

packet 0 01 FF 00
expect 0 01 FF 29
```

Check: vector 1 writes `0x2a` in ingress, egress adds `0x17` → `0x41`;
vector 2 adds `0xFF` → `0x129` wraps to `0x29`. Both hold.

Verdict: **fits as is**, but note the limitation: because ingress
unconditionally writes `0x2a` before egress reads, the vectors only prove
ingress→egress persistence within one packet and 8-bit wraparound; a
register that were reset per packet would pass them too. Cross-packet
persistence needs vectors of our own (e.g. a variant that drops the
ingress write, so two packets at index 0 adding `0x17` yield `0x17` then
`0x2e`), to be confirmed by the oracle later.

### 4.2 `issue1814-1-bmv2.p4` / `.stf`

Summary. Empty `headers` struct; metadata `{ bool test }`. Control-local
`register<bit<1>>(1) testRegister;` read once (never written), cast
`(bool) registerData` into `meta.test`, then `debug_table` keyed on
`meta.test: exact` with actions `drop()` (`mark_to_drop`) and `forward()`
(`egress_spec = 1`). Parser extracts nothing; deparser emits nothing.

Out of scope / elaboration: `egress_spec` and `mark_to_drop` (in scope);
register instance declared inside a control (elaborates to a program-level
instance with a scoped name); **explicit cast `bit<1>` → `bool`** (the IR
`Cast.to` can name `BoolType`, but the semantics need a rule for it);
exact match on a `bool` key (`meta.test:0x0` in the STF); table with no
`default_action` (implicit `NoAction`); no other flagged constructs.

STF (verbatim):

```
# SPDX-FileCopyrightText: 2019 VMware, Inc.
#
# SPDX-License-Identifier: Apache-2.0

add IngressImpl.debug_table meta.test:0x0 IngressImpl.forward()
add IngressImpl.debug_table meta.test:0x1 IngressImpl.drop()

packet 1 01010101 01010101
expect 1 01010101 01010101
```

Verdict: **fits with the bool cast rule**, but the register is never
written and the single vector only checks its initial zero (packet
forwarded to port 1, unchanged). Not a stateful test in any useful sense.

### 4.3 `issue1566-bmv2.p4` / `.stf`

Summary. Ethernet header only. `control C1(inout bit<16> x)` owns
`counter((bit<32>) 65536, CounterType.packets) stats;` and does `x = x +
1; stats.count((bit<32>) x);`. `C2` and `C3` take a control instance as a
**constructor parameter** (`control C2(inout bit<16> x)(my_control_type
c)`), shift `x` left by 1 or 3, and apply `c`. `E` instantiates `C1() c1;
C2(c1) c2; C3(c1) c3;` (the same `c1` instance shared by two parents) and
applies both. Ingress does `E.apply(hdr.ethernet.etherType)`, applying a
control **type** without an explicit instance.

Out of scope / elaboration: abstract control type declaration
(`control my_control_type(inout bit<16> x);`), control constructor
parameters and instance sharing, implicit instantiation of `E` — none of
these is "sub-control instantiation" as scoped, and flattening them
changes the program's shape; `counter` is in scope but its state is
unobservable (no `check_counter` line); `typedef`; unsized shift amounts.
No `standard_metadata` use; no other flagged constructs.

STF (verbatim):

```
# SPDX-FileCopyrightText: 2018 Cisco Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Here is a created-by-hand walkthrough of what the P4 program
# issue1566-bmv2.p4 _should_ do when it receives a packet with an
# etherType field of 0xcafe:

# cIngress call E.apply(0xcafe)
# E calls c2.apply(0xcafe)
# c2 does x = x << 1    (bit<16>) (0xcafe << 1) = 0x95fc = 38396
# c2 does c.apply(0x95fc)
# c does x = x + 1      x becomes 0x95fd = 38397
# c does stats.count(38397)
# c returns back to c2
# c2 returns back to E
# E calls c3.apply(0x95fd)
# c3 does x = x << 3    (bit<16>) (0x95fd << 3) = 0xafe8 = 45032
# c3 does c.apply(0xafe8)
# c does x= x + 1       x becomes 0xafe9 = 45033
# c does stats.count(45033)
# c returns back to c3
# c3 returns back to E
# E returns back to cIngress
# packet goes to cEgress, then deparser, with etherType modified to 0xafe9

packet 0  0000 0000 0000  0000 0000 0000  cafe
expect 0  0000 0000 0000  0000 0000 0000  afe9
```

Verdict: **does not fit** (constructor-parameter plumbing, and the vector
only checks `((0xcafe << 1) + 1) << 3) + 1 = 0xafe9`, which any program
without a counter would also pass).

### 4.4 Others looked at

- `psa-register-read-write-bmv2`, `psa-register-read-write-2-bmv2`,
  `psa-register-complex-bmv2`, `psa-example-register2-bmv2`,
  `psa-basic-counter-bmv2`: PSA architecture (`Register<T,I>` with a
  returning `read`, `send_to_port`, `ingress_drop`), so not v1model; their
  STFs are the only ones using `register_read/register_write/
  register_reset` control-plane lines, which p4c's runner accepts (grammar
  above) if p4blo ever wants control-plane register checks.
- `register-serenum-bmv2.p4`: v1model `register<EthTypes>` over a
  serializable enum, but no STF and a `reject` default.
- No v1model STF uses `check_counter`, so no p4c vector observes a
  counter's state.

## 5. Recommendations

1. **ACL: `ternary2-bmv2`.** The only v1model STF with runtime ternary
   `add` lines and overlapping entries that pin the priority convention;
   it also brings a masked `select`, a stack parser loop and constant stack
   indexing. Elaborations: `switch` on `action_run` (planned) and the four
   per-table `setbyte` copies (what p4c's frontend does). For the "parser
   errors or verify" half of the category, fold in the three vectors of
   `parser_error-bmv2` and `issue1824-bmv2` (either as a second small
   corpus file or by adding a `verify` on `data.f1` to the ACL rewrite
   with hand-written vectors), and borrow `table-entries-priority-bmv2`'s
   three vectors to pin `@priority` on `const_entries`.

2. **Header stacks: `header-stack-ops-bmv2`.** Fifteen BMv2-produced
   vectors over push/pop/holes/`next`, a `verify` in every parser state, a
   sub-control with a scalar `in` parameter, and a stack parser loop; it is
   the closest thing p4c has to an MPLS/VLAN stack test with an STF (there
   is no v1model MPLS or VLAN program with an STF at all). Elaborations:
   slice lvalues (five sites) and literal widths. Add
   `subparser-with-header-stack-bmv2` as one extra vector once
   sub-parsers are implemented; it reuses the same header types.

3. **Stateful: `issue1097-2-bmv2`.** The only v1model STF program with a
   register that is both read and written; fits as is (two program-level
   register operations from two blocks, explicit casts, wraparound). Its
   weakness is that the vectors never observe state across packets, so
   the corpus should add its own vectors (a variant without the ingress
   write, or a third vector after a control-plane `register_write` if the
   runner grows that command) and mark them "confirmed by oracle later",
   as the design already does for the forwarder. If a counter is wanted,
   `issue1566-bmv2` is not the way in; better to add a `counter` to the
   register program and check it through the runner, since no p4c v1model
   STF observes a counter.

## 6. Tutorial forwarder: is there an STF-backed equivalent in p4c?

No. `testdata/p4_16_samples/basic_routing-bmv2.p4` exists (VRF/BD/nexthop
tables with `exact` and `lpm` keys, `ttl - 8w1`, `verify_checksum`/
`update_checksum` with `HashAlgorithm.csum16`, `switch` on `action_run`,
`standard_metadata.ingress_port` as a key, named arguments `extract(hdr =
...)`) but has **no `.stf`**, and it is a different program from the
tutorial's `basic.p4`. `flag_lost-bmv2.p4` is a mutated copy of the
tutorial program (same `typedef`s and headers, `ipv4_lpm` table) whose
STF only checks that four packets are dropped (`# no packets should be
generated`), so it donates nothing.

The `p4lang/tutorials` repository's `exercises/basic/` has no STF either;
it ships `ptf/basic_fwd.py` (scapy `simple_tcp_packet` in, `ip_ttl=64` →
`63`, MAC rewrite, `verify_packets` on the egress port; tests `DropTest`,
`FwdTest`, `MultiEntryTest` with /32 and /24 entries) and
`pod-topo/s*-runtime.json` table entries. Those can be transcribed into
hand-written STF vectors (scapy's defaults are deterministic) but they are
not maintainer-reviewed hex.

Partial donors from p4c, all v1model with STF:
- `issue655-bmv2` (6 vectors): a 16-bit field incremented in ingress with
  `verify_checksum`/`update_checksum(true, {d}, c, HashAlgorithm.csum16)`
  over it; exercises the csum16 extern including the `0xFFFF`/`0x0000`
  edge cases. Useful as a unit vector for the checksum extern the
  forwarder needs.
- `v1model-const-entries-bmv2` (3 vectors) and `table-entries-lpm-bmv2`
  (4 vectors): lpm `const entries` with /48, /8, /0 and /4, /8, /0 prefixes
  respectively; useful to pin longest-prefix semantics.
- `checksum1/2/3-bmv2` and `checksum-l4-bmv2` compute real IPv4/TCP
  checksums but use `varbit` options (out of scope) and `lookahead`.

So the plan in `docs/design.md` (hand-written vectors for the forwarder,
confirmed by the oracle later) stands; the checksum and lpm micro-vectors
above are the parts that can be cross-checked against BMv2-produced output
before the oracle runs.

## Appendix: files consulted

Local copies of every `.p4`/`.stf` pair, `bmv2stf.py` and `testutils.py`
are in
`/private/tmp/claude-501/-Users-qobilidop-my-work-p4blo/07cfdaea-e2c5-4c99-819f-19a428efb35b/scratchpad/samples/`
and `.../scratchpad/`. Upstream paths:
`https://raw.githubusercontent.com/p4lang/p4c/main/testdata/p4_16_samples/<name>.{p4,stf}`,
`https://raw.githubusercontent.com/p4lang/p4c/main/backends/bmv2/bmv2stf.py`,
`https://raw.githubusercontent.com/p4lang/p4c/main/tools/testutils.py`,
`https://raw.githubusercontent.com/p4lang/p4c/main/testdata/p4_16_samples_outputs/ternary2-bmv2-frontend.p4`,
`https://github.com/p4lang/tutorials/tree/master/exercises/basic`.
