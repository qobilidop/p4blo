# Decisions

Dated choices with their reasons, newest last. A decision that the
design doc already settles is not repeated here; this file is for
everything decided while building. Overrule an entry by adding a new
one that says so.

## 2026-09-22

- **Nix flake as the development environment; uv for Python packages;
  elan for Lean.** One tool set for contributors and CI. Python
  packages are not packaged through Nix because uv does it with less
  friction and gives non-Nix contributors a working path. Lean comes
  from elan, not nixpkgs, because nixpkgs lags Lean releases.
- **No devcontainer for now.** The uv-only tier already serves people
  who avoid Nix. A devcontainer that did not run the flake would drift;
  one that did would be Nix in a box. Revisit for a Windows contributor
  without WSL2 or for Codespaces.
- **Python 3.13, pure Python.** Kept even with the playground deferred,
  because the constraint is free now and reopening it later is not.
- **Proto package `p4blo.v0`.** Pre-1.0 by design. buf's
  `PACKAGE_VERSION_SUFFIX` lint rule does not accept `v0`, so it is
  excepted in `buf.yaml` rather than renaming to `v1alpha1`, which says
  the same thing in a dialect nobody outside buf uses.
- **Generated protobuf code committed at `python/p4blo/v0/`.** The
  proto package path and the Python import path coincide, so the
  generated module's own imports resolve without a rewrite. CI
  regenerates and fails on drift.
- **STF as the vector format; P4-SpecTec's `sim` as the first oracle;
  BMv2 optional and second.** STF is text, readable, and already
  understood by both oracles, so pcap and its native library go away.
  P4-SpecTec runs natively on macOS, needs no Docker, and is the spec's
  own mechanization.
- **P4-SpecTec built in a separate CI job and a local script, not in
  the dev shell.** Its OCaml toolchain is heavy and only the oracle
  needs it.
- **One `Block` message with a kind tag.** Three messages would triple
  the shared machinery for locals, parameters and sub-block calls.
- **Parser loop bound is the no-consumption revisit rule.** Fuel makes
  meaning depend on an unspecified number; the revisit rule is one
  sentence and matches BMv2.
- **Two testing directories only: `corpus/` and `tests/`.** Vectors sit
  beside the program they test; oracle drivers and the differential
  loop are tests and live with the tests.
- **References by scoped name, not integer id.** The first draft used
  global integer ids. Switched the same day, on Bili's pointer to ONNX
  and on 4ward's stated principle, because the text format is the
  golden format and must read like the program; the hand-written
  forwarder is the first beneficiary. Scopes are P4's and the
  validator resolves every reference once. Lean pays with string-keyed
  maps, which costs nothing the project claims.
- **Typed oneofs, not an ONNX-style generic node.** ONNX's single
  `NodeProto` with a string `op_type` suits an operator set of
  hundreds that evolves separately from the file format. P4's core has
  about twenty fixed operators, and a schema whose messages are the
  grammar is what the Lean decoder and the readers need.
- **No type annotations on expressions.** 4ward, p4c and SpecTec
  annotate every node. p4blo does not: leaves are typed, operators
  determine their result, values carry widths at run time, and the
  validator computes every type once. Annotations would double the
  goldens and add a consistency check for no semantic gain.
- **Dedicated nodes for packet and header operations.** extract, emit,
  lookahead, advance, verify, isValid, setValid, setInvalid, push and
  pop are statements and expressions of the IR, not method calls on
  `packet_in`, `packet_out` and headers as in SpecTec, p4c and 4ward.
  The calling convention has no packet value, and the Lean side is
  simpler without method dispatch. "Externs" means declared externs
  only. The printer reverses this.
- **`int<N>` out by scope for v0.** Present in every prior IR and in
  core P4, but no corpus program needs it and it doubles the arithmetic
  rules. Additive when wanted.
- **Table `size` kept as an informative field.** It has no meaning; the
  printer needs it for a faithful roundtrip.
- **Field numbers 100 and above reserved for annotations**, as 4ward
  reserves 100 for source info, so semantics and metadata never mix.
- **Node in the flake.** The `pyright` wheel downloads its own Node
  when none is on the path, which is a hidden unpinned dependency.
  The flake provides Node so the download never happens.
