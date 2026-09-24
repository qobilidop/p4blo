# Roadmap

The research backlog beyond the completed finite scopes. Accepted
2026-09-23 with the design in [ir-spec-boundary.md](../docs/ir-spec-boundary.md);
Python and Lean only. Full architecture-independent P4 is the north star,
not a completion criterion. Nothing here is active: assurance
[milestone 1](../docs/assurance.md) and the [application collection](../docs/examples.md)
are complete, and an item below becomes work only when the user scopes it.
Landed results are summarized in [assurance.md](../docs/assurance.md) and
`lean/ASSURANCE.md`; the step-by-step record is in git.

Work autonomously in small reviewed increments. Record uncertain decisions
with confidence and a revisit trigger in `decisions.md`; prefer reversible
choices. Keep every gate green; a skipped oracle is not passing evidence.

## Foundation

- [x] Lean semantics and wire schema in `ir/`; separate user package in
  `lean/`; shared corpus and oracles under `tests/`; `P4blo` reserved for
  the user library.
- [ ] Typed Lean construction language with independent source semantics,
  lowering-validity and semantic-preservation theorems. Landed: closed
  scalars, typed variable reads, scalar and field commands, named paths,
  list sequencing, header-validity reads, initialization, call entry and
  normal return, a guarded control call, the forwarder's selected action,
  bounded table installation and application, the firewall's
  initialization and Bloom insertion. Open: complete applications and their
  parser, checksum and architecture boundaries; the parked readback and
  ingress drafts.
- [ ] Ergonomic Lean surface and interpreter API. Landed: checked
  constructors and diagnostics, unified read adapter. Open: notation, if a
  real application still needs it.
- [ ] Versioned interchange profile and representability predicate with
  codec proofs. Landed: component codec laws through Action/Block, total
  decoders, independent wire anchors, complete Program/Export and host
  Entries fixtures. Open: Program/Export composition, text parsing,
  resource limits, semantic-version and unknown-field policy.
- [ ] Validator beyond closed scalars with soundness and completeness per
  fragment. Landed: contextual scalar checking, a scoped scalar statement
  typing relation. Open: a complete statement checker, whole-program
  validity, the assumptions needed for machine progress and termination
  (acyclic calls, well-formed stores and externs, finite input, the
  no-consumption revisit rule).
- [ ] Generated action and sub-block calls with changing host table
  snapshots across sequences; challenge copy-in/copyback ordering,
  aliasing and fault paths. Landed: bounded copy-in/out and aggregate-copy
  profiles. Open: parser-error copyback and table-invoked actions.
- [ ] Generalize the execution-claim checker beyond its fixed fragment,
  following explicit validity and observation contracts.

## Application milestones

Each requires a pinned source, explicit environment and exclusions,
readable Python and Lean programs, original-program oracle comparison on
sequences and state, scoped proofs, mutation evidence and an IR-minimality
review.

- [ ] Tutorial stateful firewall. Landed: typed Python port with full-state
  BMv2 comparison, exhaustive byte cuts, generated flow and policy changes,
  the Lean port with initialization and Bloom-insertion proofs. Open: the
  two-read prefix (parked draft), drop/no-op composition, hash bounds,
  control composition. No exact connection-tracking claim.
- [ ] xdp-filter. Landed: pinned compile-only build with offline map/BTF
  checks and required CI. Open: kernel execution, the p4blo port,
  behavioral equivalence, capability and licensing handling.
- [ ] Conditional flowlet bridge: needs a controlled time/randomness oracle
  first.
- [ ] Bounded Katran: needs a profile audit first; no whole-Katran or
  general eBPF-translator claim.

## Checkpoint protocol

For each increment: state its contract, implement, run the relevant and
full gates, obtain an independent read-only review in an isolated
worktree, resolve findings, record exact evidence and the next action in
`status.md`, commit and push. Larger semantic steps include mutants of the
implementation, specification, lowering and observers; proof failures and
runtime mismatch detections are distinct evidence. Keep interfaces
committed before delegating implementation. Missing external capabilities
must not silently weaken acceptance.
