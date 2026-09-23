# IR contract

`P4bloIR/IR.lean` defines the abstract syntax; the other `P4bloIR` modules
define execution, scoped validity/properties, and reference architecture and
extern models. `proto/p4blo/v0/p4blo.proto` defines the versioned wire syntax.
`Json.lean` is the actual handwritten adapter. `CodecLaws.lean` proves its
literal/type round trips over JSON values under explicit v0 uint32
representability. This does not verify text parsing, Python/protobuf or the
recursive program codec; see [`../docs/notes/codec-proof.md`](../docs/notes/codec-proof.md).

This Lake package (`p4blo-ir`) does not import the user-facing Lean package.
`Main.lean` provides the stable `p4blo-lean` conformance executable. The
reference switch/extern models are explicit environment profiles, not claims
that those services are part of architecture-independent P4.

Run `scripts/check-lean.sh` from the repository root inside the Nix environment
to build/test both packages and run their configured proof audit targets.
Whole-program validation and termination remain open; see
[`../docs/verification.md`](../docs/verification.md).
