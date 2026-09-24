# IR contract

`P4bloIR/IR.lean` defines the abstract syntax; the other `P4bloIR` modules
define execution and scoped validity/properties. Externs are contracts
here: `Externs.lean` carries an instance's logical state and takes the
model that interprets calls from the architecture (`../arch`), which also
owns the switch and the conformance endpoint. `proto/p4blo/v0/p4blo.proto`
defines the versioned wire syntax.
`Json.lean` is the actual handwritten adapter. `CodecLaws.lean` proves its
literal/type/table-key round trips over JSON values under explicit v0 uint32
representability. This does not verify text parsing, Python/protobuf or the
recursive program codec; see the archived note `notes/codec-proof.md`.

This Lake package (`p4blo-ir`) imports nothing from the architecture or
user-facing packages; both depend on it. Nothing architectural lives here:
no ports, no packet fate, no concrete extern family.

After the [development setup](../../README.md#development), including `elan`,
run `scripts/check-lean.sh` from the repository root to build/test all
three packages and run their configured proof audit targets.
Whole-program validation and termination remain open; see
[`docs/assurance.md`](../../docs/assurance.md#what-is-proved).
