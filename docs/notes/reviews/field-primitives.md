# Field primitive bridge review

Independent read-only review on 2026-09-23 of the small `FieldLaws` increment
in `p4blo-typed-fields`, before any aggregate source API refactor. No production
evaluator changes. **Clear for the separate foundation commit**, subject to
the implementer's remaining ordinary gates; no correctness blocker found.

## Statement and premise assessment

`Declared` requires the exact nominal declaration, correct header/struct
kind, absence of the opposite kind under the same name, nonempty names and
unique field names. This is stronger than a successful header-first numeric
lookup and correctly excludes ambiguous same-named header/struct entries.
Field order and declared types are part of declaration equality. It does
not pretend to establish that stored values have those types.

The raw read law requires actual indexed cell existence. The raw setter law
intentionally permits out-of-range `List.set`, accurately exposing the
current silent no-op. The stronger declared laws require exact runtime and
declaration list lengths; the selected declaration position then proves the
cell is in range. There is no hidden assumption that a too-short list is a
valid typed container.

`update_declared` gives the exact reconstructed container, successful
readback of the written value, unchanged list length, and every other
position preserved (including absent positions). Exact reconstruction keeps
nominal name and arbitrary header validity, including invalid headers. All
primitive equations preserve the entire Run because these functions return
a container/value; they do **not** persist a nested lvalue into the frame.
That recursive writeback, source path typing, root permission and global
Index/program validity remain future obligations, correctly excluded by
the module documentation.

Concrete kernel examples inhabit both header/struct declaration premises,
apply the update theorem to an invalid header, and reject wrong-kind,
duplicate-name and short-list premises. Runtime tests also use real
`Index.build`, rather than relying only on a manually assembled map. The
premises are therefore neither circular nor merely hypothetical.

## Independently executed evidence

After the implementer confirmed stable binaries, ran the existing spec-test
executable from its required package directory: **exit 0, all tests passed**,
including both validity states, metadata siblings, declaration shadows,
wrong names/order/width, malformed names, short-list behavior and actual
Index construction. No rebuild, source modification or Docker operation.

Queried all six new public audited roots using the pinned Lean compiler and
existing libraries. Each depends only on
`[propext, Classical.choice, Quot.sound]`, matching exact default audit guards.
No sorry/custom axiom or native-decision assumption surfaced. Root library
export, spec test-driver registration and default proof-audit imports were
inspected and include the increment.

The implementer reports both package build/test/audit gates and 242 required
DRT cases passed, with no skips. Subsequently inspected all three isolated
primitive fault logs and the completed ASSURANCE section: forcing validity
true, selecting index `i + 1`, and replacing every sibling with the written
value each fail the actual `setField_pack` proof. The latter renames its
unused binder, so the detector is the false list equality, not a warning.
These are correctly labeled **proof/build rejection**, not executable
semantic detection. The restored module build log succeeds and the isolated
evaluator has zero tracked diff. Exact edits and reconstruction commands are
persisted; no Python field-runtime kill is claimed at this foundation stage.
The next source/aggregate increment requires its own independent review.
