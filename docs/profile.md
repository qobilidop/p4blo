# Current assurance profile

Milestone 1 concerns the current v0 IR, not all P4 or arbitrary hostile input.
Lean's [abstract syntax](../ir/P4bloIR/IR.lean) and executable semantics are
authoritative; [protobuf](../ir/proto/p4blo/v0/p4blo.proto) defines transport
syntax. [Semantics](semantics.md) records closed behavior. The
[evidence matrix](evidence.md) separates proofs, tests and oracle coverage.

## Supported surface

- Types: unsigned fixed-width bits, booleans, named errors/enums, headers,
  structs and fixed-size header stacks. Valid bit widths are positive;
  wire-representable zero widths are not thereby valid programs.
- Expressions: literals, variables, field/stack reads, last index, validity,
  three unary and nineteen binary operators, casts, slices, concatenation,
  lazy Boolean/conditional selection and parser lookahead. Arithmetic wraps
  or saturates as specified; comparisons are unsigned.
- Statements: assignment, conditional, action/block/extern call, table apply
  with optional hit destination, validity changes, stack push/pop, extraction,
  advance, verify and emit. Block kind restricts where each is legal.
- Parsers: named states, direct/select transitions, exact/masked/range/don't-care
  keysets, accept/reject and the no-consumption revisit rule. Calls copy inputs
  and outputs; parser-error copyback is part of the specified behavior.
- Tables: exact/LPM/ternary keys, literal action data, const entries/defaults,
  host-installed entries/default overrides, longest-prefix and largest-priority
  selection. A miss can run an action while `hit` remains false.
- Program declarations: types, errors, extern signatures/instances, blocks,
  exported roles and headers/metadata contract. Host table configuration is
  separate from the program; decoding it does not establish validity.

The executable builtin extern profile is register, counter, checksum16,
CRC16/ARC and CRC32/ISO-HDLC. Family suffixes do not relax signature/width
checking. Registers/counters persist across packets; CRCs are byte-aligned,
stateless and return the full result. Custom externs need their own model and
evidence; the extensible Python registry does not verify arbitrary plugins.

The IR is architecture-free. End-to-end regression uses the supplied switch
and filter adapters and their declared metadata/port rules, not every P4
architecture. The eleven-program corpus includes complete Python/Lean ports
of the forwarder and persistent tutorial Bloom firewall. The latter admits
Bloom false positives; it is not exact connection tracking.

## Inputs and validation

Execution evidence concerns finite programs accepted by the Python validator,
with matching builtin bindings, appropriate architecture exports and valid
host installations. Preparation/indexing on the Lean side is checked by
tests, not proved equivalent to the whole Python validator. Codec tests also
intentionally include invalid-but-representable IR; their successful decoding
is not permission to execute it.

Selected typed Lean expressions/commands have checked lowering and execution
theorems under explicit context/index/frame premises. The complete applications
also assemble raw IR; neither that assembly nor Python's complete eDSL is a
fully verified frontend. A human can still write the wrong intended program
in either language. Independent expected examples check intent separately.

## Cross-language wire contract

The supported interchange profile is the canonical protobuf JSON emitted by
`p4blo.ir.dump_json` (Program) and the corresponding snake-case protobuf
conversion for Entries, and the matching Lean encoders. It uses known fields,
full enum names, numeric uint32 values, booleans, ordered arrays, explicit
decimal-string bit/key values and at most one populated oneof alternative.
Default scalars/empty arrays are omitted; optional message presence matters:
an absent optional is not the same as a present empty message.

The adapters also accept selected noncanonical inputs, tested explicitly, but
there is no unrestricted accepted-input or text-parser equivalence claim:

| Input form | Current boundary |
|---|---|
| Missing/null fields | Lean treats null as absence, then applies field defaults; missing required oneof/enum still fails. Independent codec fixtures test these cases. |
| Decimal bit/key strings | Nonempty ASCII digits; leading zeros may normalize. Empty/missing/null, signs, hex and JSON numbers are not decimal-string values. Python may reject later during validation/installation. |
| uint32 strings | Lean accepts decimal strings as an extension; canonical output uses numbers. Bounds are less than 2^32, independent of semantic width/capacity validity. |
| Numeric enums / camelCase aliases | Not the cross-language contract; Python protobuf accepts forms the handwritten Lean adapter need not accept. |
| Unknown object keys | Python public protobuf parsing rejects them by default; Lean currently ignores them. Do not use unknown keys to carry required semantics or infer safe forward compatibility. |
| Duplicate keys / non-JSON constants | Not supported interchange. The DRT envelope/reply/replay parsers reject these; no theorem about arbitrary production parser inputs is claimed. |

No wire-version negotiation or new v1 schema is introduced. Existing codec
laws are JSON-value left inverses under explicit representability premises,
not proofs of protobuf, text parsing, semantic validation or intended mapping.
Independent literal/constructor answers remain necessary: a paired wrong
encoder/decoder can satisfy a roundtrip law.

## Errors, state and operational limits

Successful drop is an empty output list, not an error. Parser rejection is
distinct from its error name (explicit reject carries `NoError`); architecture
policy decides what follows. Decode, validation, binding and installation
errors are distinct from packet execution faults and harness protocol errors.
The comparison checks error reasons and diagnostic presence; matching errors
do not make a generated-valid-input campaign successful.

A host configuration rejected before packet execution must not execute that
packet or change persistent extern state. This is not transactional rollback
of an accepted program that mutates state and then encounters an execution
error. Stateful tests retain the complete request prefix, not just a final
packet. Detailed diagnostics need not have identical formatting in both
languages.

This is a trusted-input development/simulation profile, not a hardened
untrusted-input service. uint32 wire bounds can still describe impractically
large allocations; JSON nesting, host stack/memory and runtime limits apply.
There is no proved global resource bound or validated-program termination
theorem. The actual Lean runner has no semantic fuel counter. The DRT client
defaults to a ten-second request deadline; a transport deadline is a harness
failure, never semantic `ParserTimeout`. Certificate experiments have their
own explicit bounded-check contract in [certificates.md](certificates.md).

## Exclusions and trust

Signed/variable-width integers, header unions, general loops/return/exit,
value sets, architecture-specific table match kinds/services and complete
P4 elaboration remain outside this profile. The construct-by-construct P4
comparison is [coverage.md](coverage.md); syntax presence alone is not tested
semantic coverage. All-P4 expressiveness and IR minimality remain north stars.

Trust includes the Lean kernel for theorems, compiled Lean runtime/compiler
for executable comparisons, Python/runtime, protobuf/JSON libraries, observers,
test generators, oracle adapters and pinned external tools. Default theorem
audits reject unexpected axioms, but cannot prove that a theorem states the
desired requirement. Independent expected values, external oracles and actual
mutations reduce shared mistakes; none yields a numerical probability of
correctness or a universal Python-correctness proof.
