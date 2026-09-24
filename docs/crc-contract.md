# Byte-aligned CRC extern contract

Decision, 2026-09-23: add two stateless extern families, `crc16` and
`crc32`, with no constructor arguments and one method
`bit<W> compute(in bit<D> data)`, where W is 16 or 32 respectively.
As with existing extern families, a suffix such as `crc16.104` names a
monomorphic declaration, not a different algorithm. No IR syntax changes.

The supported domain is positive D divisible by eight. Binding rejects
unsupported widths explicitly, as does the printer; no padding or guessed
partial-byte behavior is advertised. Runtime calls defensively reject a
different width from the bound declaration. Input is exactly D/8 bytes,
most-significant byte first, including all leading zero bytes.

- `crc16`: CRC-16/ARC, polynomial 0x8005, reflected input/output, initial
  value zero, final XOR zero; full 16-bit result.
- `crc32`: CRC-32/ISO-HDLC, polynomial 0x04c11db7, reflected input/output,
  initial value 0xffffffff, final XOR 0xffffffff; full 32-bit result.

The Python implementation uses a reflected byte-lookup table; Lean uses
the forward polynomial, explicitly reflecting byte bits and the final
register. They share neither implementation nor computed expectations.
Observers retain the instance and family, with no mutable cells.

The v1model printer uses `hash` with the corresponding HashAlgorithm,
base zero, and a maximum of 2^W. The max has width W+1 (or a wider native
width), so CRC32 must not accidentally encode 2^32 as bit<32> zero.
No claim about general nonzero-base v1model range reduction is needed.
The tutorial firewall's 4096 range is a separate explicit AND with 4095.

Confidence: high on algorithm identities and byte ordering, medium on the
best public API. Revisit when another example needs non-byte inputs,
configurable polynomials or arbitrary hash ranges. Keep these outside the
core IR unless concrete evidence requires a new semantic construct.

Acceptance requires externally checked known answers from a hand-written
P4 probe independent of our printer (including 104-bit five-tuples, zero,
all-ones and ASCII `123456789`), Python/Lean packet-observable agreement,
typed and dynamic authoring, stateless observation, malformed-shape/width
rejection, both Lean package gates and independently reviewed changes.
Passing vectors is not a universal CRC equivalence proof. A documented
oracle divergence must be isolated from ordinary passing controls and
must not excuse arbitrary compiler/runtime failures.

## Pinned SpecTec divergence discovered by the probes

The independently written P4 probe in `tests/test_crc.py` exposes both
full CRC outputs, with literal expected answers rather than expectations
computed through either interpreter. BMv2 (the pinned local image,
p4c 1.2.5.15 / simple_switch 1.15.4) passes both this original-source probe
and our printed IR. P4-SpecTec at
`2730cfd9e74048bb5439da0f8afcef124079a064` disagrees on odd-byte CRC32.

| Exact input bytes | Correct CRC32, confirmed by BMv2 | Pinned SpecTec |
|---|---|---|
| `0a0000010a0000023039005006` | `7dd597c3` | `a31aa886` |
| thirteen zero bytes | `0f744682` | `d1bb79c7` |
| thirteen `ff` bytes | `f2d6f3c1` | `2c19cc84` |
| ASCII `123456789` | `cbf43926` | `ce7745fe` |
| `00` | `d202ef8d` | `41d912ff` |
| `ff` | `ff000000` | `6cdbfd72` |
| `0001` | `36de2269` | `36de2269` |
| `01` | `a505df1b` | `36de2269` |
| `0000` | `41d912ff` | `41d912ff` |

Diagnosis: SpecTec's `package` calls `pad_right_to_16` for every hash
algorithm. That helper rounds the width upward but leaves the value
unchanged, effectively **prepending** a zero byte to odd-byte input.
The CRC32 implementation itself then processes that larger input. CRC16
has initial zero, so this particular leading zero does not change its
result. Tests run CRC16 and even-byte CRC32 as ordinary passing controls;
another independent P4 probe explicitly prepends zero and confirms the
recorded odd-input results. No adapter fixes or changes the oracle input.
[Pinned implementation](https://github.com/kaist-plrg/p4-spectec/blob/2730cfd9e74048bb5439da0f8afcef124079a064/p4spec/lib/backend-sim/hash.ml)

The two discrepancy tests (original P4 and printed IR) use strict xfail
restricted to `KnownSpecTecCRCDisagreement`. That exception is raised
only when the oracle exits 1 with the **exact complete diagnostic**:
the recorded mismatch, its source footer, and optionally the known `sink`
warning block. Any other stderr line or stdout is rejected. Build errors, protocol
errors, crashes, other wrong bytes and timeouts remain failures. If the
oracle is corrected, strict XPASS demands review/removal of the exception.
Independent review found the initial classifier ignored extra non-`error:`
stderr lines; the tightened whitelist and synthetic crash/output/exit-code/
wrong-byte/corrected-oracle regressions close that harness blind spot.

This matters directly to the firewall: its 104-bit tuple's CRC32 register
index is 1987 on BMv2, 2182 on the pinned SpecTec. The earlier original
firewall outbound/reverse-flow smoke test passes both despite this state
disagreement. Consistent wrong hashing can preserve simple packet fates;
primitive known answers and actual state observations are necessary.
No full firewall port, state equivalence, or upstream issue submission is
part of this increment. BMv2 remains the original-source CRC authority
until the upstream padding discrepancy is resolved.

## Separate adjacent fix: monomorphic family dispatch

Before this increment, Python chose the segment before the first dot in
an extern type name, but Lean required the complete name to equal a
builtin. For example, `register.8` bound in Python but failed in Lean.
The isolated fix is two existing dispatch sites in `Externs.lean`:
normalize `decl.name` with `(decl.name.splitOn ".").head!` in `make` and
the `shapeOf` call in `bind`. Keep original names for declaration checks
and error diagnostics. No prefix matching beyond Python's exact first
segment is introduced.

`tests/test_extern_families.py` and `ir/Tests/ExternFamilies.lean` are
separate regressions using the preexisting register/counter/checksum
families. They and their Main import/call can accompany the two dispatch
hunks in a separate logical commit, before the CRC addition. This fix
requires no new extern family or CRC implementation. Confidence: high;
the Python behavior and eDSL naming convention were already explicit.

## Verification checkpoint (2026-09-23)

- Both Lean package gates passed: 335 specification checks, user-package
  API tests, and proof audit.
- Required real-Lean differential gate passed: 101 tests (before the
  independent scalar increment is integrated).
- Final full `scripts/check.sh` passed: 1050 tests, three strict known
  divergences, no skips; lint, formatting, type checking, schema drift,
  and workflow checks passed. The expected divergences are the existing
  BMv2 register out-of-bounds case and the two exact SpecTec CRC32 cases.
- Independent read-only review identified and verified fixes for the
  permissive diagnostic classifier and direct CRC constructor-argument
  handling. Direct registry binding and printing now reject extra
  constructor arguments for both CRC families. Review also compared
  CRC32 with zlib for 512 seeded lengths and checked the pinned SpecTec
  padding diagnosis. No additional confirmed implementation issue remains.

Oracle CI must select `tests/test_crc.py -k spectec` and
`tests/test_crc.py -k bmv2` in their respective jobs; the integrator owns
those workflow changes. These checks establish bounded conformance and
known-answer evidence, not a universal implementation-correctness theorem.
