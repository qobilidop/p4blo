# Example-guided eDSL ergonomics

Authorized 2026-09-25: complete a co-design of the router, firewall and
load-balancer examples and the Python authoring API; make extern registration
explicit and keep architecture choices outside the core. The user authorized
isolated delegated work, autonomous integration, milestone review and a final
engineering reflection. Semantic/proof backlog is not reopened.

## Acceptance

- All three applications read more clearly, remain independently readable,
  and preserve their packet, fate and persistent-state contracts.
- Independent P4 blocks compile without architecture roots or roles. An
  optional BlockLibrary bundles shared declarations without claiming to be
  a complete program; architecture assembly owns wire exports and H/M roots.
- The core supplies generic extern declarations/calls; concrete families
  live in explicit support libraries. Registration, binding, instance state
  and runtime lifetime have a documented public API.
- A third-party custom extern and alternative block composition work without
  editing p4blo. Runtime registration does not imply Lean or printer support.
- Type checking, diagnostics, existing byte-reconstruction tests, Python/Lean
  differential tests and applicable oracle gates retain their guarantees.
- Independent review covers each milestone and final PR revision; full local
  gate precedes push, applicable remote CI precedes merge.

## Milestones

1. Inspect actual examples and agree concrete before/after API sketches.
2. Implement generic exports and explicit extern registration, migrate the
   three examples and existing callers, document public usage, review.
3. Challenge extensibility and behavior, run integration/oracle gates,
   review final revision and merge through a PR.
4. Reflect on workflow improvements, persist verified lessons and compact
   the working state when closing this scope.

## Work allocation

Integrator: `/Users/qobilidop/my/work/p4blo`, branch
`work/edsl-ergonomics`, base `80eba84`. Owns documentation, state, remaining
caller migrations, cross-cutting acceptance tests and integration.

All delegated work starts at committed `80eba84`:

- `work/edsl-externs`, `/Users/qobilidop/my/work/p4blo-edsl-externs`:
  generic extern declaration separation, concrete extern library and public
  registration API, with focused registration tests.
- `work/edsl-program`, `/Users/qobilidop/my/work/p4blo-edsl-program`:
  generic named exports and explicit loader/support convenience, with tests.
- `work/edsl-examples`, `/Users/qobilidop/my/work/p4blo-edsl-examples`:
  the three programs/demos/READMEs, small expression ergonomics if justified,
  with focused tests.

No concurrent rebuilds of shared Docker images or Lean executables. Review
worktrees will be created from each committed integrated milestone.

## Current checkpoint

Implementation and caller migration are complete. Independent review is
checking the local-type dependency fix at `c150d31`; status.md records local
checks and remaining integration gates. Initial named-export Program API,
explicit loader, concrete extern split and readability changes were implemented
in isolated commits. During integration
the user clarified that public `p4.Program` itself mixes core and architecture.
The final design must start from independently authored P4 blocks, with
composition and role assignment in architecture support; the wire Program
container can remain an assembly detail. The named-export Program proposal
is superseded and must not be shipped as the public authoring API.

That correction is implemented in the final API below. Lean and the first
full integration gate passed; current evidence and remaining obligations are
in status.md. No goldens, wire schema or Lean semantics changed.


## Final API contract after user steering

`p4.BlockLibrary(*block_classes, externs=..., errors=...)` is the reusable
source collection. `.compile()` returns a CompiledLibrary fragment without
H/M roots or exports. No public typed `p4.Program` remains. Generic
`arch.assemble(library, name=..., headers=..., metadata=..., exports=...)`
and the optional `arch.reference.assemble` pipeline adapter produce the
existing wire Program through one compiler context. `arch.load` requires
registry/contract/role kinds; `arch.reference.load` is the explicitly named
supplied environment. Concrete extern imports and explicit local registration
remain as agreed. A scalar-only block is a required independence witness.

The three examples retain one program.py each with block definitions, a
BlockLibrary and a small reference assembly `build()` for the existing test
contract. Their demos explicitly select the reference environment and supplied
extern registry. This retains independent readability and exact IR goldens.
