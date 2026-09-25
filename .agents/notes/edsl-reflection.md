# eDSL engineering reflection

Scope: example-guided authoring and architecture separation, 2026-09-25.
The final review and remote integration evidence will be recorded in status.

## What improved the result

- Three real applications supplied concrete readability problems. Ordinary
  type aliases, symbolic predicate names and build-time helpers solved them
  without new syntax, and all text/binary goldens remained unchanged.
- The user's architectural correction exposed a weak proxy: arbitrary export
  names did not remove global H/M roots or the wire export convention. A
  scalar-only compilation witness now tests the actual independence claim.
- A complete custom extern example made declaration, registration, binding
  and runtime state ownership reviewable together. Tests reuse one registry
  across loads and two instances to challenge state isolation.
- The existing full gate caught a moved static-diagnostic line anchor. Its
  expected type errors were still present; only the exact source line changed.
  Keeping the negative test precise avoided weakening the static contract.

## What to change in the workflow

- Agree caller examples, boundary counterexamples and shared API signatures
  before implementation delegation. The initial named-export Program and
  then standalone block draft required rework when the actual abstraction
  boundary became clear. User steering remains authoritative; stabilize the
  revised contract before asking every agent to edit again.
- Write down dependency order. The two API agents briefly waited for each
  other's commit before testing. Committed slices with explicit pending
  integration checks break that cycle; a full integrated gate follows.
- Do not amend handed-off commits, even for message wrapping. One agent's
  cosmetic amend raced an already integrated cherry-pick. The trees agreed,
  but it created needless commit identities. Use a follow-up when needed.
- Resolve AST source anchors against an immutable snapshot before replacing
  text. A local migration script reused old AST locations against changing
  text, damaging its second replacement in one file. The file was restored
  from git and migrated with snapshot-derived unique anchors; syntax checks,
  full tests and unchanged goldens verified the repair. This is a concrete
  recurrence of AGENTS.md's existing prohibition on computed-offset edits.

- Freeze the tracked tree for a provenance-checked assurance run. Its digest
  includes documentation, so writing this reflection and workflow notes while
  the mutation experiment ran invalidated the first run's evidence despite
  all semantic stages completing. Rerun against the final frozen tree; never
  count the invalidated run as a pass.
- Independent review must construct inputs outside the representative
  applications. It found that an annotated local struct in a scalar block
  was missing from standalone compilation's dependency closure, a case the
  applications' H/M roots masked. Add that regression at the compiler boundary.

The durable changes are in AGENTS.md's agent workflow, the application/API
procedure in docs/workflows.md, and the executable import-boundary,
standalone-library and extern-isolation tests. The transient scripts remain
ignored local artifacts, not repository tools or handoff dependencies.
