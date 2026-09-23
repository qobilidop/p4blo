# Concrete field command review

**Final review: clear; chronological investigation follows below.**

Initial structural review in `p4blo-field-commands`: **no blocker found in
the concrete theorem and permission modules**. Runtime fixtures, final audit
registration and adversarial evidence are still being authored; final
clearance is intentionally pending. No candidate builds or binary tests
were run during this initial inspection.

`FieldPlaces.Modes` assigns permission to a root slot, not a path or mutable
runtime value. `Modes.Agrees` independently requires actual declaration
lookup with exact root name, full scalar/nominal IR type and direction.
`Place` carries the selected root mode's writability proof. Its authoritative
typing theorem combines actual declaration permission, root well-formedness
and exact nominal index agreement through the existing member rules.
The small `Mode.declarationIR` helper generalizes declaration construction;
the existing scalar declaration API remains a specialization with the same
meaning.

Constructive `Modes.scope_agrees` and `Modes.frame_matches` witnesses are
provided for well-formed roots and arbitrary independent stores. They are
accurately documented as direct witnesses, not proofs that arbitrary whole
programs initialize successfully. The planned fixtures should also include
an actual `Index.build`/`Frame.forBlock` run to connect this API to ordinary
initialization, plus rejection of forged declaration permissions.

`Fields.Cmd` specializes the single generic command AST. It reads/writes
the existing independent aggregate source store and lowers typed scalar
paths; it does not add a second recursive evaluator. Its concrete `steps`
proof supplies actual `Ref.evaluate`/`Ref.write_matches` laws, carrying
nominal index agreement through exact non-variable state preservation.
No arbitrary correctness callback remains in public `steps` or
`execute_correct`. Both require real declarations, root/index well-formed
agreement, full frame-value matching and explicit action-free `BlockFrame`.

`steps` establishes authoritative body typing and a finite prefix of the
actual machine with an arbitrary continuation left untouched.
`execute_correct` uses that actual prefix to establish successful reference
execution, exact complete converted source-store values, preserved actual
declarations, all source header validities, all non-variable Run state and
every runtime name outside the possible target-root set. Nested sibling
preservation follows from exact independent path-set/root-value agreement;
it is not inferred only from a scalar result or root-name target list.

The claimed slice remains initialized, action-free scalar-leaf assignment
and conditionals. It does not prove parser/table/packet effects, aggregate
copying, whole-program validity or general initialization. Final review will
check constructive mixed-root examples, actual permission negatives,
faulting-continuation witnesses, post-command full-state observers and the
recorded mutation/replay experiments against these limits.

## Stable fixtures and independently executed checks

The completed mixed-root fixture uses Ethernet and IPv4 headers nested in a
header struct, metadata, a read-only route struct and local scratch. Its
forwarding body is expressly already parsed/route-selected and does not
claim checksum maintenance, table lookup or architecture packet fate.
Dependent-write cases read newly updated values, cover modular wrapping,
both branches and a shared tail. Ten independent full-store answers include
both header validities, siblings and read-only data.

Constructive kernel witnesses discharge the exact public theorem premises.
Separate kernel negatives reject input/directionless places, scalar type and
condition mismatch, forged direction/type, missing nominal declarations and
an action-storage overlay. A frame can match the source values while its
scope has the wrong direction; the test explicitly demonstrates why the
declaration premise cannot be omitted. A prefix witness leaves a verify-false
continuation untouched, and runtime evaluation confirms that continuation
really faults if executed. Actual `Index.build`/`Frame.forBlock` initialization
and nested writes are tested for aggregate local/out/inout declarations.

The Python wrapper uses actual corresponding subcontrol directions and
local scratch, runs the authored body exactly once, then snapshots every
source field/validity plus unrelated local storage and a nonempty packet
tail. It observes invalid-header stored fields instead of relying on header
emission. Initializers, caller/observer code and call copying are accurately
outside the body proof. Two permanent scoped faults alter the actual statement
writer only during the authored TTL assignment: force validity or overwrite
the checksum sibling. Each saves complete input before expected-answer
assertion, diverges on the exact independently predicted byte positions,
and replays successfully after restoration.

Independently ran the focused field-command file with required Lean enabled:
**13 passed**, exit 0, including those two live/restored faults. Independently
ran the compiled user tests: all previous suites and the ten new full-state
cases pass, exit 0. Queried all seven new compiled audit roots; six have
`[propext, Classical.choice, Quot.sound]`, while `Cmd.validities` has
`[propext, Quot.sound]`. No reviewer rebuild was performed.

Fixture/observer implementation review is clear. Final closure awaits the
additional isolated production/source mutation campaign, restoration evidence,
and completed documentation/gate checkpoint being prepared by the implementer.

## Final campaign and disposition

**Final review: clear** for the concrete modules, examples, exporter and
bounded campaign. Inspected the final README/ASSURANCE contract, exact
mutation recipes, source-only reconstruction commands and restoration logs.
The integrator retains responsibility for merged full gates; this review
does not turn the bounded forwarding rewrite into a verified application.

Three generic semantic faults reject the actual correspondence proofs:
skipping a lowered assignment fails the machine transition; stale source
reads after writes fail sequencing equality and final source correspondence;
swapping lowered branches fails the actual conditional transition. These
are documented as proof rejection, not runtime kills. A same-width
destination-MAC Place aliased to source-MAC compiles with default audits,
then independent `forward-hit` expected bytes reject the wrong intent even
though the two interpreters agree. Inspection of its failure confirms the
destination remains `111213141516` instead of `aabbccddeeff`.

Two isolated actual Python source faults change only authored TTL-write
validity or checksum sibling state. Inspected saved-before-answer failures
and live/restored replay logs: each live bundle has one genuine output
divergence and no shared error; each restored replay has one agreement.
Independently loaded both original bundles, reconstructed their exact
tracked exported-body programs, and checked the complete request, payload,
ports and seed. Independently replayed both against restored candidate
Python/Lean: one agreement each. Exact identities:

- `lean-field-commands-dependent-wrap-invalid.json`: 39782 bytes,
  `3e81440659ea423da41171af641a3f893b01d4f30516da322ca2c0e014a62685`.
- `lean-field-commands-dependent-next.json`: 40053 bytes,
  `689d227dbe6e84f1398a6fd5bbb8a0db3185123733fbe04231f94919677ed130`.

Independently confirmed the mutant worktree's actual Python source and
generic command module have empty diffs after restoration, and the restored
example file is byte-identical to the candidate. Restored default-build and
user-test logs succeed; the implementer reports their exits as 0. Its final
restored focused log has **13 passed**, and required all-suite DRT has
**314 passed**, with no skips. These additional gate results are attributed,
separate from the independent checks above. No remaining review finding.
