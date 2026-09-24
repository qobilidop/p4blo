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
  Closed scalar literals/addition/equality/mux and typed variable reads now
  have these guarantees under explicit context/frame premises. Writable
  scalar assignment/sequence/if now have exact source-state preservation and
  finite execution proofs, with declaration and permission witnesses.
  Typed aggregate paths and shared scalar/field read expressions now have
  exact nominal/frame correspondence. Writable scalar-leaf field commands
  now preserve full source state, declarations, validity and unrelated runtime
  state under concrete premises. A named forwarding-body policy now relates
  arbitrary complete source states to actual execution; complete applications
  and their initialization/parser/table/checksum boundaries remain open.
- [ ] Provide an ergonomic Lean surface and interpreter API using the reference
  execution functions. Test diagnostics and notation, including rejection cases.
  Typed named scalar paths now resolve with spelling/permission soundness and
  independent diagnostics. List sequencing now preserves the previous ASTs
  and exports, with independent order/branch answers and default-audited laws.
  Read-only header-validity primitives now have concrete typing/evaluation
  laws and independent answers. A unified read adapter preserves scalar writes
  and legacy exports; full post-read observations catch actual Python return
  and state-only faults. A separately specified guarded policy now has arbitrary
  source/execution proofs, an exact invalid-drop-only contract and independent
  full-state answers, without changing the old invalid-header contract.
- [ ] Define a versioned restricted interchange profile and representability
  predicate. Prove codec properties incrementally; test real Python/Lean
  conversions, missing variants, limits, unknown fields and semantic versioning.
  Actual decimal/uint32 and representable Literal/Ty/KeyValue/Expr/LValue/Arg/Stmt
  JSON-value round trips are proved and default-audited. The actual Expr,
  LValue and Stmt decoders use terminating recursion; helper erasure and malformed answers
  preserve its previous behavior. Independent constructor observations catch
  paired wrong-wire mappings, including a shared operator-name fault that
  originally survived the tests. Paired LValue operand and Arg tag mappings
  are likewise caught independently. The statement implementation preserves
  all 79 old raw transcripts; independent answers catch paired tag/branch
  mappings, path-index changes and null-default faults that retain roundtrip
  proofs. Scope and review: `notes/stmt-codec.md` and its matching review.
  The next accepted slice is nine foundational declaration codecs, following
  `notes/program-codec-next.md`: reuse existing type/literal/list laws without
  changing already-total decoders. An independent constructor/raw-error
  baseline is integrated: 247 exact transcripts, independent constructor/error
  answers and public protobuf wrappers. The nine laws/fault campaigns are
  independently reviewed and queued for integration. Full Program codecs, text parsing, resource limits
  and version policy remain open.
- [ ] Expand the Lean validator beyond closed scalars with soundness and
  completeness for each claimed fragment; document remaining global obligations.
  Contextual scalar checking now has both proofs and rejects malformed
  contexts. A scoped scalar statement typing relation is implemented;
  a complete statement checker and whole-program validity remain open.
- [ ] Exercise existing forwarder/stateful examples through both authoring
  paths and execution APIs, with named application properties and mutations.
  Independent aggregate source zero now corresponds to the actual initializer
  under exact nominal agreement and explicit sufficient fuel. The forwarding
  roots supply a constructive instance. Actual complete-scope frame creation
  now has exact lookup/scope/no-action laws under all-entry zero success.
  The source-frame adapter now discharges modeled values and explicitly handles
  extras; kernel-checked actual built-index/frame witnesses anchor the concrete
  forwarding declarations. Actual four-root call entry now preserves the
  whole Run outside the installed callee and captures the exact original
  caller/continuation. Its user theorem discharges actual initialization for
  the selected empty-body declaration program; this is not yet the full
  body-bearing wrapper. Independently frozen/type-sensitive state observers
  and permanent adversarial controls accompany the proof.
  The flat-body command-prefix prerequisite is now proved over the actual
  queue, retaining pending observer/return work and existing whole-body APIs.
  Actual-built body-parametric entry now preserves that API and supplies
  exact real block/scope identity; complete selected-block syntax is checked
  against the tracked Python guarded wrapper. Real local assignments now have
  exact finite-prefix/source-state and separate permission proofs, with
  independent literal answers and retained actual Python fault replays.
  Actual entry, locals and guarded forwarding are now composed up to the
  exact unexecuted observer suffix and captured caller return, following
  `notes/call-body-prefix-plan.md`. Native complete-state and strict Python
  prefix observers retain the independently discovered comparison faults.
  Actual fixed-profile normal return now has
  an exact operational proof: restore the captured caller, copy three writable
  roots and preserve the current callee-after non-frame state. Independent
  complete-state, ordered-write and branch-complete isolation tests accompany
  it. Those boundaries now compose into a separately named observer-free whole
  control call with actual semantic completion, full source/shared state and
  original caller preservation, under `notes/guarded-call-plan.md`. The
  existing observer statements and complete applications remain separate
  obligations. The exact-golden complete Lean forwarder is now integrated,
  including direct public in-memory execution, existing vectors, independent
  TTL/MAC/checksum answers and a bounded invalid-IPv4 whole-Run property.
  Review's packet-invisible metadata fault is retained and rejected by strict
  full-state checks. Scope: `notes/lean-forwarder.md`; raw assembly seams
  remain explicitly unverified, as do the positive pipeline properties.
  Its positive-path prerequisite now has actual unshadowed block-write and
  action-hit read/write laws, with constructive active-frame witnesses and
  four compiled model faults rejected. Source permissions and the existing
  no-action command API are unchanged. The target-only unshadowed field
  adapter is now integrated with mixed-layer witnesses and four default-audited
  roots; it preserves other action-shadowed roots without broadening source
  permissions. The next selected-action trace follows
  `notes/forwarder-action-next.md`; that application proof remains pending.

## Application milestones

Each milestone requires a pinned source/configuration, explicit environment
and exclusions, readable Python and Lean programs, original-program oracle
comparisons on sequences and relevant state, scoped checked proofs, intentional
mutation evidence, and an IR-minimality review. See the design for details.

- [ ] Tutorial stateful firewall: source audit and oracle preflight; model CRC
  services explicitly; preserve Bloom collisions; test routing/direction rules,
  before/after initiation and malformed inputs. No exact-conntrack claim.
  The typed Python port now has independent packet/full-state expectations,
  original BMv2 prefix observations, strict SpecTec discrepancy probes and
  deliberate wrong-port detection. Exhaustive byte cuts of a fixed frame,
  valid-malformed-valid persistence, structured generated flow/policy changes
  and runtime state-only mutants extend the bounded evidence. Lean authoring/
  application proofs and broader profiles remain open.
- [ ] xdp-filter: audit and pin a named configuration; Linux BPF replay with
  controlled maps/CPU; preserve early decisions, counters, pass/drop/abort and
  malformed-input order. Expand only to an explicitly selected full profile.
  The Ethernet-allow original now has a pinned compile-only build, offline
  map/BTF checks and required CI with negative fixtures. Kernel execution,
  the p4blo port and behavioral equivalence remain separate open obligations.
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
