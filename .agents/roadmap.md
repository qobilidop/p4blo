# Roadmap

The research backlog beyond the completed finite scopes. Python and Lean
only; full architecture-independent P4 is the north star, not a
completion criterion. Nothing here is active: an item becomes work only
when the user scopes it. Landed results are summarized in
[assurance.md](../docs/assurance.md) and `impl/lean/ASSURANCE.md`; the
step-by-step record is in git.

The mechanized relation to P4-SpecTec is a joint milestone with
`p4-spectec-lean`, the user's project that compiles SpecTec into Lean;
this repository supplies the IR, the elaboration, the block contract
`tests/oracle/p4blo.watsup` and the validation suite, and builds no
rendering of SpecTec itself (`docs/design.md`, "Relation to
p4-spectec-lean"; `decisions.md`, 2026-09-24).

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
- [ ] Codec composition through core BlockLibrary and architecture Export
  and BlockAssembly (C3). Landed: component laws through Action and Block,
  total decoders, independent anchors.
- [ ] Checker completeness per fragment; `ResultOk` and the entry-point
  corollaries are landed, `structVar` on the final frame is not.
- [ ] Typed Lean construction language beyond what landed (closed scalars,
  fields, initialization, calls, the forwarder's selected action, the
  firewall's initialization and Bloom insertion): complete applications
  and their parser, checksum and architecture boundaries; the parked
  readback and ingress drafts.
- [ ] General assignment preservation and further extern contracts.
- [ ] Generated action and sub-block calls with changing host table
  snapshots across sequences: parser-error copyback and table-invoked
  actions. Landed: bounded copy-in/out, aggregate copies, computed
  indices.
- [ ] Generalize the execution-claim checker beyond its fixed fragment.

## Interchange

- [ ] Text parsing, resource limits, semantic-version and unknown-field
  policy for the wire profile.

## Applications (frozen scopes; extend only with a new scope)

- [ ] Tutorial stateful firewall: the two-read prefix (parked draft),
  drop/no-op composition, hash bounds, control composition.
- [ ] xdp-filter: kernel execution, the p4blo port, behavioral
  equivalence, capability and licensing handling. No kernel claim.
- [ ] Conditional flowlet bridge: needs a controlled time/randomness
  oracle first.
- [ ] Bounded Katran: needs a profile audit first; no whole-Katran or
  general eBPF-translator claim.
- [ ] The p4c backend, the experiment that would really test claim 1.
