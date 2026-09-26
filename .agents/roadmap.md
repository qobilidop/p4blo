# Roadmap

The research backlog beyond the completed finite scopes. Python and Lean
only; full architecture-independent P4 is the north star, not a
completion criterion. Nothing here is active: an item becomes work only
when the user scopes it. Landed results are summarized in
[assurance.md](../docs/assurance.md); the step-by-step record is in git.
Formal assurance targets only core IR. The Lean authoring/application proof
stack and execution-certificate experiment are retired, recoverable from
`5ee52d90f19d5d5a81bf972a115298ae167e691b`. Their unfinished extensions are
not an active roadmap. Python examples, importer and tested adapters remain.

The mechanized relation to P4-SpecTec is a joint milestone with
`p4-spectec-lean`, the user's project that compiles SpecTec into Lean;
this repository supplies the IR, the elaboration, the block contract
`tests/oracles/p4blo.watsup` and the validation suite, and builds no
rendering of SpecTec itself (`docs/design.md`, "Relation to
p4-spectec-lean"; `decisions.md`, 2026-09-24). The recorded Nano-P4 pin `8c8e0c6f`
differs from this repository’s `2730cfd9`; reconcile them before claiming the
joint comparison. Flood/multicast remains outside the architecture profile.

## Joint milestone with p4-spectec-lean

- [ ] Its executable rendering answers every conformance fixture and
  block-level request as the OCaml simulator does. Prerequisites on this
  side: bump the P4-SpecTec pin to that project's once fixed; read its
  program export in `p4blo.frontend.il` and retire patch `0002`.
- [ ] The simulation theorem between the rendered `p4blo.watsup`
  relations and `P4bloIR.Exec` under the bridge's elaboration, with each
  ledger deviation an explicit exception. Needs an elaboration relation
  in Lean and, for its premises, validity (landed) and termination (open).

## Proofs

- [ ] Termination (C2): the acyclic call graph and the no-consumption
  revisit rule imply `Execution.drive` terminates; with progress, a valid
  program has a defined result. Landed: progress, the revisit check, the
  cursor never moving back.
- [ ] Codec composition through core BlockLibrary (C3). Landed: component
  laws through Action and Block, total decoders, independent anchors.
  Architecture Export/BlockAssembly codecs remain tested adapters.
- [ ] Core checker completeness per fragment. Progress retains its explicit
  extern and machine assumptions; architecture entry proofs are retired.
- [ ] General core assignment preservation.
- [ ] Generated action and sub-block calls with changing host table
  snapshots across sequences: parser-error copyback and table-invoked
  actions. Landed: bounded copy-in/out, aggregate copies, computed
  indices.

## Retained observations

These are follow-ups, not confirmed defects or newly authorized work.

- Printer declaration order: actions calling later declarations fail P4-SpecTec
  typing; order by dependency or require that order during validation.
- Two reachable P4-SpecTec rules remain unhit: `Expr_eval/non-default-abort`
  and `Copy_in_arg/abort`; retain the coverage exclusions and their inputs.
- Some Lean/Python module headers still name former semantics sections.
- Unconfirmed: checksum16 padding for non-multiples of 16, `<block>_inst`
  collisions, and error ordering when both entry and port are invalid. No oracle
  ruling yet; preserve that uncertainty.
- Reassignable public eDSL library settings can bypass constructor checks;
  no runtime bug demonstrated.
- Cache eviction makes builds cold; the stdlib guard uses Python 3.13 while
  Docker uses distro Python, with compatible imports at the recorded checkpoint.
- Retired proof drafts and local snapshots remain in [recovery](notes/recovery.md);
  they predate current layout/externs and are not landed evidence.

## Interchange

- [ ] Text parsing, resource limits, semantic-version and unknown-field
  policy for the wire profile.

## Applications (frozen scopes; extend only with a new scope)

- [ ] Revisit XDP only for a concrete p4blo application with an independent
  execution oracle; compilation alone does not justify support.
- [ ] Conditional flowlet bridge: needs a controlled time/randomness
  oracle first.
- [ ] The p4c backend, the experiment that would really test claim 1.
