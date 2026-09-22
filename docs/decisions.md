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
- **p4c through Docker as an optional local check.** The printer's
  goldens are typechecked with `p4test` from the `p4lang/p4c` image when
  Docker is available and skipped otherwise. p4c is not in nixpkgs and
  building it is out of proportion; the image is pinned by tag for now
  and by digest once the oracle job exists.
- **`Stmt.if`, `If.else`, `Mux.else`, `Arg.in` renamed** to
  `conditional`, `otherwise`, `otherwise`, `expr` (with `Arg.out` to
  `lvalue`). The originals are Python keywords, and generated code would
  have forced `getattr` on every consumer. Found by the corpus agent
  while hand-writing the forwarder.
- **Expressions and lvalues stay separate messages.** Hand-writing
  read-modify-write paths twice is the main bulk of the forwarder text.
  A dotted-path string sugar was considered and rejected: it is a
  second syntax inside strings and cannot express indices. The eDSL is
  the authoring tool; the hand-written file is a step-1 artifact.
- **STF dialect conventions**, recorded in `python/p4blo/stf.py`: a
  `packet` with no `expect` asserts that nothing came out; a priority
  on a non-ternary table is an error; an lpm key without `/n` is a
  full-width prefix; a hex or binary literal's written form fixes its
  width for wildcards; a table name declared in two blocks must be
  qualified with the block name.
- **Metadata contract fields fixed** as the table in the design doc:
  `ingress_port`, `parser_error` provided; `egress_port`, `drop`,
  `flood` consumed; fate as booleans, not an enum, so the forwarder
  runs unchanged under the switch. Byte-aligned parsing required by the
  architectures; the control runs after a parser rejection.
- **Corpus programs picked from p4c's test suite** after the survey in
  `docs/notes/corpus-candidates.md`: ACL is `ternary2-bmv2` (the only
  v1model STF with runtime ternary adds and overlapping priorities),
  header stacks is `header-stack-ops-bmv2` (fifteen BMv2-produced
  vectors over push, pop, holes and `next`), stateful is
  `issue1097-2-bmv2` (a register read and written from two blocks) plus
  vectors of our own for cross-packet state. Micro-programs with
  oracle-grade vectors (`parser_error-bmv2`, `issue1824-bmv2`,
  `table-entries-priority-bmv2`, `issue655-bmv2` for csum16, the lpm
  const-entries files) join as companions. No v1model MPLS or VLAN
  program has an STF, and the tutorial forwarder has none either.
- **Entry priority: larger wins, everywhere in the IR.** p4c's STF
  `add` priority has larger winning (its runner inverts for BMv2), while
  `const entries` have smaller `@priority` winning and list order
  otherwise. The frontend elaborates const entries into IR priorities
  where larger wins; the printer prints const entries in descending
  priority without annotations, so p4c sees the same order.
- **`expect` lines match a prefix unless they end in `$`**, as in p4c's
  runner, because its vectors name only the header bytes. The runner
  stays strict about unclaimed outputs.
- **Slice as an lvalue is elaborated** to a read-modify-write of the
  whole field rather than added to `LValue`; one elaboration named in
  the coverage table, no new node for Lean.
- **Per-table action copies keep the corpus STF adjusted.** p4c
  elaborates `setbyte(out reg, val)` bound per table into `setbyte`,
  `setbyte_1`... and its runner resolves names per table; p4blo's
  corpus copy of the STF names the elaborated actions directly and
  sets `Key.name` to p4c's key names so the vectors read unchanged.
- **Architecture rules the design left open.** A parse that ends off a
  byte boundary drops the packet whether or not it accepted, since the
  payload is undefined either way. A contract field the program does
  not declare reads as its zero value and swallows writes, so a program
  without `egress_port` sends to port 0 and one without `flood` runs
  unchanged under the switch. `parser_error` is written after the
  parser's own `inout` writes and before the control, as v1model does.
  The filter forwards the original bytes, so a vector that expects a
  rewritten packet fails under it by construction; the filter tests
  rewrite expectations to the input bytes.
- **Printed ternary entries are not const.** p4c 1.2.5 refuses
  priorities on `const entries` and rejects `@priority`, so the printer
  emits a ternary table's const entries as ordinary `entries` with
  `largest_priority_wins = true`, sorted by descending priority. The
  oracle therefore sees host-mutable entries where the IR has const
  ones; nothing in the vectors depends on the difference.
- **Independent review after each step.** Step 1's review is kept at
  `docs/notes/reviews/step1.md`; its confirmed findings are fixed on
  main and its rulings are in `docs/semantics.md`.
- **Node in the flake.** The `pyright` wheel downloads its own Node
  when none is on the path, which is a hidden unpinned dependency.
  The flake provides Node so the download never happens.
