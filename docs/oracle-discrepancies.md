# Oracle discrepancies

p4blo follows the applicable language or architecture contract, with explicit
choices where that contract leaves behavior unspecified. Agreement between two
executables is evidence, not the definition of correctness. A disagreement is
classified only after checking the same source and inputs on both sides.

The observations below target P4-SpecTec
`2730cfd9e74048bb5439da0f8afcef124079a064`, p4c **1.2.5.15** and BMv2
**1.15.4** `simple_switch`. The [build script](../tests/oracles/build.sh) pins
P4-SpecTec and our driver patches; the [Dockerfile](../tests/oracles/bmv2/Dockerfile)
pins p4c and BMv2 by immutable image digests. These are claims about those
inputs, not every release of either project. Broader guarantees and remaining
single-oracle limitations are in [assurance](assurance.md).

## Reproducing the differences

Four reduced, standalone P4 programs live in
[tests/oracles/discrepancies](../tests/oracles/discrepancies). Each has a
`.bmv2.stf` and `.spectec.stf`: source, setup and input packets are identical;
only expected answers differ. Their tests check that invariant and require
the complete recorded answer from each executable. These characterization
tests pass when the recorded discrepancy remains present. A corrected oracle
fails its old expectation and requires an investigated update; this is not an
exception that accepts arbitrary failures.

After the [development setup](../README.md#development):

```sh
tests/oracles/build.sh
docker build -t p4blo-bmv2 tests/oracles/bmv2
uv run pytest tests/oracles/test_oracle_discrepancies.py -q
```

Use `-k pinned_spectec` or `-k pinned_bmv2` to run one oracle, and append a
case name such as `crc32_odd` to narrow it. An unavailable oracle skips its
cases locally; that does not establish agreement. The P4-SpecTec command used
by the test is `p4spectec sim spec -arch v1model -i p4c/p4include -p SOURCE
-stf VECTOR`, from its checkout. BMv2 receives the unchanged source through
p4c and replays the vector through the pinned Docker driver. The mask probe's
single STF entry is rendered as the equivalent native BMv2 CLI table entry;
no p4blo interpreter or printer decides its result.

## CRC32 of an odd number of bytes

[Source](../tests/oracles/discrepancies/crc32_odd.p4),
[BMv2 vector](../tests/oracles/discrepancies/crc32_odd.bmv2.stf),
[P4-SpecTec vector](../tests/oracles/discrepancies/crc32_odd.spectec.stf).

The probe hashes the one-byte constant `01`, emits the 32-bit result, then
preserves input payload `00`:

| Oracle | Output on port 0 |
|---|---|
| BMv2 | `a505df1b00` |
| P4-SpecTec | `36de226900` |

**Selected behavior: BMv2's CRC32 result.** The supplied service is
CRC-32/ISO-HDLC, with polynomial `0x04c11db7`, reflected input/output, initial
remainder and final XOR `0xffffffff`. Processing exactly `01` gives
`a505df1b`; processing `0001` gives `36de2269`. The
[BMv2 implementation](https://github.com/p4lang/behavioral-model/blob/1.15.4/src/bm_sim/calculations.cpp)
uses those parameters and the input byte count. P4-SpecTec's
[hash packaging](https://github.com/kaist-plrg/p4-spectec/blob/2730cfd9e74048bb5439da0f8afcef124079a064/p4spec/lib/backend-sim/hash.ml)
adds the extra zero byte through `pad_right_to_16` before choosing the
algorithm. That changes the CRC input; it is not CRC32 of the requested byte
string. p4blo therefore preserves the exact input length. Broader CRC16,
even-byte and explicit-leading-zero controls remain in
[test_crc.py](../tests/oracles/test_crc.py).

## Out-of-range register reads

[Source](../tests/oracles/discrepancies/register_bounds.p4),
[BMv2 vector](../tests/oracles/discrepancies/register_bounds.bmv2.stf),
[P4-SpecTec vector](../tests/oracles/discrepancies/register_bounds.spectec.stf).

A one-cell register is read into the packet's second byte. Packet `01ff`
requests index 1, outside `[0, 1)`; `00ff` is the in-range control.

| Input | BMv2, port 0 | P4-SpecTec, port 0 |
|---|---|---|
| `01ff` | `01ff` | `0100` |
| `00ff` | `0000` | `0000` |

**No unique required out-of-range result.** The pinned
[v1model register contract](https://github.com/p4lang/p4c/blob/v1.2.5.15/p4include/v1model.p4#L290-L308)
says the result is unspecified outside the register's range and should be
ignored by its caller. BMv2 preserves the destination; P4-SpecTec returns zero.
**p4blo chooses zero as its deterministic policy**, without claiming BMv2 is
incorrect. Applications requiring portability must check bounds. The
[existing bounds corpus](../tests/programs/corpus/register_bounds/README.md) also checks
ignored out-of-range writes and persistent in-range state.

## Control-plane table masks

[Source](../tests/oracles/discrepancies/table_mask.p4),
[BMv2 vector](../tests/oracles/discrepancies/table_mask.bmv2.stf),
[P4-SpecTec vector](../tests/oracles/discrepancies/table_mask.spectec.stf).

Install one ternary entry with key `0a` and full mask `ff`. Its action selects
port 1; the default selects port 2. `0a` is a hit on both. `0b` is a miss on
BMv2 (port 2), but P4-SpecTec forwards it on port 1. Packet bytes are unchanged.

**Selected behavior: BMv2's full-mask comparison.** A ternary entry matches
when masked lookup value and masked entry value agree; `0b & ff != 0a & ff`.
This is the mask/set meaning in P4 1.2.5 §8.16.3 and table lookup §14.2.1.1
([language specification](https://archive.p4.org/wp-content/uploads/2024/10/P4-16-spec-v1.2.5.html)).
The pinned [P4-SpecTec table interface](https://github.com/kaist-plrg/p4-spectec/blob/2730cfd9e74048bb5439da0f8afcef124079a064/spec/9-arch/9.1-table-interface.watsup)
constructs the mask but casts the base expression instead. It effectively
uses `0a` as the mask, under which both packets match. This defect concerns
control-plane entry construction; an equivalent const entry in the P4 source
does not exhibit it. Existing firewall tests retain the full `/32` LPM
manifestation, where `10.0.0.3` incorrectly matches `10.0.0.2/32`.

## Const-entry priority annotations

[Source](../tests/oracles/discrepancies/const_priority.p4),
[BMv2 vector](../tests/oracles/discrepancies/const_priority.bmv2.stf),
[P4-SpecTec vector](../tests/oracles/discrepancies/const_priority.spectec.stf).

Three overlapping ternary rows are reduced from the
[upstream p4c regression](../tests/oracles/frontend/p4c/table-entries-priority-bmv2.p4).
Inputs `1001` and `1181` both leave unchanged on port 3 under BMv2, or port 1
under P4-SpecTec.

**Selected behavior: the portable language interpretation, port 1.** P4
1.2.5 §14.2.1.4 gives source order precedence when explicit language priorities
are absent. `@priority` is a p4c-specific extension, not that language syntax;
the [upstream test](https://github.com/p4lang/p4c/blob/v1.2.5.15/testdata/p4_16_samples/table-entries-priority-bmv2.p4)
explicitly documents its smaller-number-wins behavior. Thus these annotated
sources are not portable: BMv2 implements that extension, while P4-SpecTec
uses standard entry ordering. The discrepancy alone is not a blanket claim
that BMv2 violates P4. p4blo retains standard ordering and its printer makes
priorities explicit using supported language properties. The
[corpus derivation](../tests/programs/corpus/priority/README.md) records each row.

## Egress destination and egress_spec initialization

The [egress redirection probe](../tests/oracles/frontend/probes/v1model_egress_redirect.p4)
and its [vector](../tests/oracles/frontend/probes/v1model_egress_redirect.stf) select
port 2 in ingress, then set `egress_spec` to 3 in egress. The packet reports
`egress_port = 2` as bytes `0002` on both oracles, but BMv2 emits on port 2
and P4-SpecTec emits on port 3.

**Selected behavior: output on the previously selected egress port.** The
[pinned architecture pseudocode](https://github.com/p4lang/behavioral-model/blob/1.15.4/docs/simple_switch.md)
ends egress by sending on `egress_port`; rewriting `egress_spec` can affect the
drop decision but cannot choose a new output destination. p4blo models that
architecture rule, matching BMv2. The independent source remains unchanged
when testing the P4-SpecTec discrepancy.

The [egress metadata probe](../tests/oracles/frontend/probes/v1model_egress_spec_read.p4)
and [vector](../tests/oracles/frontend/probes/v1model_egress_spec_read.stf) separately
observe initialization: after ingress selects 2, egress sees `egress_spec = 0`
on BMv2 and `2` on P4-SpecTec. Both see `egress_port = 2`; their output bytes
are `0002` and `0202`, respectively, on port 2.

**Selected behavior: reset egress_spec to zero for our pinned BMv2 target
profile.** This is a target-specific initialization choice, not a universal
P4 language rule. The [simple_switch implementation](https://github.com/p4lang/behavioral-model/blob/1.15.4/targets/simple_switch/simple_switch.cpp)
sets it to `drop_port + 1` before egress; with drop port 511 and a 9-bit field
that truncates to zero. p4blo follows this explicit target profile. The
[stage tests](../tests/programs/test_v1model.py) keep this difference separate
from destination selection and from ingress/egress drop gating.

## Other limits and classification discipline

[Assurance](assurance.md#known-disagreements-with-the-oracles) also records
P4-SpecTec's shift-size implementation limit, non-byte deparser/payload
composition, header equality/validity and stack `pop_front` behavior. Their
existing core/generated-program tests and semantic rulings remain the
references. They are not promoted here into new paired BMv2 reproductions;
this catalog's standalone paired cases establish only the observations above.

For a mismatch, first preserve the source, packet sequence, table entries and
full available extern state. Determine the governing language rule,
architecture contract or explicit unspecified behavior. Then change p4blo only
when it is wrong under that selected contract. Record a narrow discrepancy
otherwise: exact pin, request and observed answer, with a passing control
where useful. A crash, timeout, malformed response, unrelated mismatch or
newly corrected answer must fail the old classification. Existing correctness
suites use strict expected-failure exceptions for these boundaries; this
catalog's characterization suite asserts the two complete distinct answers.
Neither mechanism grants a blanket exception to an architecture or program.
