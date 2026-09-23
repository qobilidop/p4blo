# Implementation roadmap

Accepted 2026-09-23. The design is [notes/ir-spec-boundary.md](notes/ir-spec-boundary.md).
Python and Lean only. Full architecture-independent P4 is the north star,
not a completion criterion for this finite example-driven roadmap.

Work autonomously in small reviewed increments. Record uncertain decisions
with confidence and a revisit trigger in `decisions.md`; prefer reversible
choices. Keep the existing proof audit, Python/schema, Lean/conformance and
both P4-oracle gates green. A skipped oracle is not passing evidence.

## Foundation

- [x] Move authoritative Lean semantics and wire schema into `ir/`, preserving
  module identities, golden bytes and behavior. Introduce a separate `lean/`
  Lake package depending one-way on `ir/`. Update CI, tools and instructions.
- [x] Consolidate shared corpus/oracle infrastructure under `tests/`; keep
  generated bindings with Python, package-local Lean tests with their package.
  Avoid compatibility directories that indefinitely duplicate ownership.
- [x] Reserve `P4blo` / Lake package `p4blo` for the user library; use
  `P4bloIR` / `p4blo-ir` for the independent specification. Preserve wire
  identities and the existing `p4blo-lean` conformance executable.
- [ ] Provide a typed Lean construction language, independent compositional
  source semantics, lowering-validity and semantic-preservation theorems.
  Start with a small proved fragment and extend it toward actual applications;
  do not present raw IR constructors as a verified complete frontend.
  Closed scalar literals/addition/equality/mux now have these guarantees;
  references, statements and complete applications remain to be implemented.
- [ ] Provide an ergonomic Lean surface and interpreter API using the reference
  execution functions. Test diagnostics and notation, including rejection cases.
- [ ] Define a versioned restricted interchange profile and representability
  predicate. Prove codec properties incrementally; test real Python/Lean
  conversions, missing variants, limits, unknown fields and semantic versioning.
- [ ] Expand the Lean validator beyond closed scalars with soundness and
  completeness for each claimed fragment; document remaining global obligations.
- [ ] Exercise existing forwarder/stateful examples through both authoring
  paths and execution APIs, with named application properties and mutations.

## Application milestones

Each milestone requires a pinned source/configuration, explicit environment
and exclusions, readable Python and Lean programs, original-program oracle
comparisons on sequences and relevant state, scoped checked proofs, intentional
mutation evidence, and an IR-minimality review. See the design for details.

- [ ] Tutorial stateful firewall: source audit and oracle preflight; model CRC
  services explicitly; preserve Bloom collisions; test routing/direction rules,
  before/after initiation and malformed inputs. No exact-conntrack claim.
- [ ] xdp-filter: audit and pin a named configuration; Linux BPF replay with
  controlled maps/CPU; preserve early decisions, counters, pass/drop/abort and
  malformed-input order. Expand only to an explicitly selected full profile.
- [ ] Conditional flowlet bridge: establish controlled time/randomness replay
  before claiming oracle coverage; test timeout/wrap/collision behavior. If the
  oracle remains unavailable, record the limitation and advance other work.
- [ ] Bounded Katran: audit and select a meaningful build profile; compare its
  actual BPF datapath, backend selection and packet transformations. No whole
  Katran, throughput, concurrent Linux, or general eBPF-translator claim.

## Checkpoint protocol

For each increment: state its contract, implement, run relevant/full gates,
obtain an independent read-only review in an isolated worktree, resolve findings,
record exact evidence and next action in `status.md`, commit and push. Larger
semantic steps include mutants of implementation, specification, lowering and
observers; proof failures and runtime mismatch detections are distinct evidence.
Keep dependencies/interfaces committed before delegating implementation.

External infrastructure is investigated early. Missing Linux BPF capabilities
must not silently weaken acceptance; other independent work continues. Do not
call the plan complete while required profiles, proofs or tests remain open.
