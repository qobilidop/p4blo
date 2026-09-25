# IR contract

`P4bloIR/IR.lean` defines the abstract syntax; the other `P4bloIR` modules
define execution and scoped validity/properties. Externs are contracts
here: `Externs.lean` carries an instance's logical state and takes the
model that interprets calls from the architecture (`../arch`), which also
owns the switch and the conformance endpoint. `proto/p4blo/v0/p4blo.proto`
defines the versioned wire syntax.
`Validity/` defines whole-program validity (`Rules.lean`), the executable
checker `Validity.check` (`Check.lean`) with its soundness proof
(`Sound.lean`), and the machine invariants that `Progress.lean` carries
through every step: a valid program never reaches an interpreter error,
and `drive` returns success or a declared parser error. The `p4blo-lean
check` command in `../arch` runs the checker and is compared with the
Python validator by `tests/lean/test_lean_agrees_validity.py`.
`Json.lean` is the actual handwritten adapter. `CodecLaws.lean` proves its
literal/type/table-key round trips over JSON values under explicit v0 uint32
representability. This does not verify text parsing, Python/protobuf or the
recursive program codec; see the archived note `notes/codec-proof.md`.

Everything a client may import lives under `P4bloIR/`. Everything only
the gate runs lives under `P4bloIRTest/`, the modules of the
`P4bloIRTest` library: the tests `lake test` runs, the proof audits
`ProofAudit.lean` and `CodecProofAudit.lean`, whose `#guard_msgs` pins
every default `lake build` checks, the `codec-leaves` endpoint and the
forwarder fixtures.

This Lake package (`p4blo-ir`) imports nothing from the architecture or
user-facing packages; both depend on it. Nothing architectural lives here:
no ports, no packet fate, no concrete extern family.

After the [development setup](../../README.md#development), including `elan`,
run `scripts/check-lean.sh` from the repository root to build/test all
three packages and run their configured proof audit targets.
Whole-program validation and termination remain open; see
[`docs/assurance.md`](../../docs/assurance.md#what-is-proved).
