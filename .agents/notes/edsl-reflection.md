# eDSL engineering reflection

Scope: example-guided authoring and architecture separation, 2026-09-25.
The final implementation merged through PR #2 as `f6c3a6e`, after all seven
remote checks passed on `26d3f38`. The closure evidence is recorded in status.

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

## What the deeper boundary review changed

Stopping at the Python facade preserved a misleading core wire abstraction.
The user's protobuf question exposed H/M assumptions in core validity, entry
helpers and printer defaults. Following one scalar/no-root witness through
all representations produced the actual separation; a second witness with
two blocks of every kind guards against silently rebuilding a fixed pipeline.
Existing entry proofs moved with their definitions, and binding soundness was
preserved explicitly instead of treating successful compilation as evidence.

Mechanical migrations need token-aware, idempotent replacements and collision
checks. The local scripts stopped on missing/ambiguous anchors, but rerunning
a broad `pb.Export` substitution also matched its new `apb.Export` spelling;
a new `wire` module alias collided with existing codec parameters. Syntax,
types, targeted tests and the full gate exposed these, and the final fixes use
unambiguous aliases and preserve independent fixtures. Assemble and validate
all edits from an immutable snapshot before writing a migration batch.

Run the final documentation sweep before the first CI push, including prose
that states universal contracts, not only old symbol names and paths. The
closure audit found older paragraphs still presenting the supplied H/M and
STF conventions as mandatory after the code and newer guide had separated
them. Correcting those late required additional final-head CI runs. Review
caller workflows and conceptual claims together with the implementation.

## Closure and recovery

The interrupted Codex run ended in a responses-endpoint authentication error,
not a repository failure. A later session preserved and reviewed the remaining
prose edits, repaired the bare-interpreter coverage build, passed the full
local gate and all seven final-head remote checks, and merged PR #2. Exact
local evidence is 5,199 passed, one optional XDP-image skip and four expected
failures; the skip is not a local XDP pass. The final remote XDP job passed.

The coverage-build failure exposed a boundary outside the ordinary local
Python environment: CI invokes some scripts with bare Python. The structural
import test now guards all four such scripts, including XDP's container
entrypoint. Checking the command's real execution environment is a durable
lesson; adding imports that pass inside uv is insufficient evidence.

Recovery also found that status still said PR #2 was open after it merged.
Keep the integration result and next action in the repository checkpoint,
not only in a final chat message. The closure commit and subsequent compaction
retain final-head evidence, archived reviews and the parked-work inventory.
The README and design sweep removes older overstatements: Lean is
independently checked against P4-SpecTec, and the frontend supports a
documented subset.

No semantic scope was reopened. The outstanding termination, codec composition
and application proofs remain backlog with their existing limits.
