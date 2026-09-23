# Lean user library

The independent `p4blo-lean` Lake package imports `p4blo-ir` from `../ir`.
Import `P4bloLean` for the user API. Reference definitions remain under
`P4blo`; frontend/library definitions use `P4bloLean` to avoid collisions.

`prepareSwitch` performs indexing, extern binding and architecture contract
checks, not complete validation. `runSwitch` and the block entry points reuse
the reference functions. Pass returned extern state to the next call. There
is no independent optimized engine or new correctness claim in these aliases.

The typed eDSL and verified lowering are the next increment; this package
boundary alone does not supply them. `scripts/check-lean.sh` from the repo root
builds/tests both packages; testing just this package does not run the spec's
own proof audit or tests.
