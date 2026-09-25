# Example-guided eDSL ergonomics

Authorized 2026-09-25: complete a co-design of the router, firewall and
load-balancer examples and the Python authoring API; make extern registration
explicit and keep architecture choices outside the core. The user authorized
isolated delegated work, autonomous integration, milestone review and a final
engineering reflection. Semantic/proof backlog is not reopened.

## Acceptance

- All three applications read more clearly, remain independently readable,
  and preserve their packet, fate and persistent-state contracts.
- Generic authoring supports named block exports without requiring the
  supplied parser/control/deparser pipeline or metadata vocabulary.
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

Design inspection in progress. Current friction: concrete externs exported
from the core eDSL, implicit default runtime registry/contract/roles, typed
Program requiring three pipeline roles, repeated wide type expressions and
checksum construction, and deeply nested application policy. No API choice
has yet been accepted. Next: compare agent proposals, settle the API, then
implement and migrate.
