# IR contract

`P4bloIR/IR.lean` defines the abstract syntax; the other `P4bloIR` modules
define execution, scoped validity/properties, and reference architecture and
extern models. `proto/p4blo/v0/p4blo.proto` defines the versioned wire syntax.
`Json.lean` is the actual handwritten adapter. `CodecLaws.lean` proves its
literal/type/table-key round trips over JSON values under explicit v0 uint32
representability. This does not verify text parsing, Python/protobuf or the
recursive program codec; see the archived note `notes/codec-proof.md`.

This Lake package (`p4blo-ir`) does not import the user-facing Lean package.
`Main.lean` provides the stable `p4blo-lean` conformance executable. The
reference switch/extern models are explicit environment profiles, not claims
that those services are part of architecture-independent P4.

After the [development setup](../README.md#development), including `elan`,
run `scripts/check-lean.sh` from the repository root to build/test both
packages and run their configured proof audit targets.
Whole-program validation and termination remain open; see
[`docs/assurance.md`](../docs/assurance.md#what-is-proved).
