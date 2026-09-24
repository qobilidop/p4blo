# Bounded real forwarder installation and lookup review

Final review: clear for installation and lookup checkpoint 1. Chronological
structural investigation below is followed by final executable/evidence review.

2026-09-23. Read the full logically stable ForwarderTables.lean in
`p4blo-forwarder-tables` at `95a784c`, against the accepted plan and actual
Installed implementation inspected during plan review. No source edits,
candidate builds or executable consumers were performed.

## Universal contract and independent policy

Config covers five exact installation shapes and drop/NoAction/forward defaults;
every route/default payload ranges over fitting 48-bit MAC and nine-bit port
values. Query ranges over all 32-bit values. Selection is independently defined
by host equality and network numeric interval, preferring the host, not by
Installed.lookup/keys/beat comparisons. Decision.result separately states
selected call and hit; a forwarding default is explicitly a miss.

The source input distinguishes absent host default (the unchanged real drop)
from explicit NoAction and forwarding. No impossible valid-host optional-none
claim is introduced. This module stops at selected Match; it neither executes
an action nor proves applyTable, ingress prefix or final packet fate.

## Actual installation and nonvacuity

The private seed is justified by actual Installed.build of the real Forwarder
index. Table/key-width/action lookups resolve the actual declarations. Both
concrete route installs discharge actual key canonicality/width, literal arity/
width/range, nonternary priority and duplicate checks. The duplicate-loop helper
proves the real forIn traversal succeeds for fresh keys; the bounded family
proves its own freshness in both orders rather than requiring it from callers.

Actual host-build and setDefault equations compose those facts for arbitrary
fitting payloads and every shape. The public installed getD wrapper has a
proved successful result for all Configs, so its fallback cannot hide failure.
Public facts identify the real index, ordered relevant entries, effective
default and absence at every other table reference. Operational map inserts
are retained instead of asserting unjustified fresh-map structure equality.

## Actual lookup factoring

Private consider/finish abbreviate the actual loop body solely inside the proof.
Zero/one/two-entry equations are proved against Installed.lookup itself. The
single-entry equation needs no nonternary premise because no prior best entry
can be compared; the two-entry equation explicitly uses the actual nonternary
declaration. Every exact map view used by the public lookup theorem is discharged
from its real installed witness, not a lookup-correctness callback.

Factoring quotient-range arithmetic from small loop equations avoids the giant
unfolded kernel terms that blocked the planning probe. Fin query range and
explicit Bits construction are preserved. The final theorem covers all five
shapes, both overlap orders, all query addresses and all fitting payloads; it
has not silently weakened the accepted universal boundary to fixed fixtures.
Owner reports default-limit compilation; independent checking awaits frozen
registered binaries. Literal independent route/data/default anchors and full
installed-state observations still need adversarial review before clearance.

## Final independent checks

After the candidate was frozen, independently ran all 50 focused Python tests
(exit 0, 0.47 seconds), a fresh pinned-Lean query of all nine default audit roots
(each exactly `propext`, `Classical.choice`, `Quot.sound`), and the complete
native table test entrypoint. The latter passed 270 route/default answers plus
its rejection/extremal controls. No candidate build or edit was performed.

The exporter carries actual inputs/maps/results, not policy-computed answers.
The Python validator strictly checks all 30 unique configurations, nine ordered
addresses each, complete Program/Index/maps, widths/data and Boolean/numeric
types. Python actual lookup observations detach the entire installed object,
index and query before execution, and assert preservation as well as the
independent result. Source/data defaults are independently literal fixtures.

Review identified that native map checks initially covered only cardinality,
not their complete contents. The final native checks now compare independently
constructed ordered entries and default calls at the sole key in addition to
map cardinality and complete index comparison. The retained state-only Python
fault now explicitly passes a return-only observer with one hook hit while
changing installed state, before the complete observer rejects it. These final
refinements passed the independent checks above.

## Campaign and restoration

Inspected actual recorded logs for both Lean runtime compilations followed by
genuine proof rejection: shortest-prefix selection leaves a false network/host
call equality; clearing the absent override leaves `none` rather than the real
drop default. Neither is labeled a differential-runtime kill. The fitting
fixture-port mutation compiles, as the universal theorem should allow, but
fails independent native answers and Python input identity. The actual Python
shortest-prefix source edit is rejected internally and produces a clean saved
packet mismatch, with the host versus network MAC/port differences explicitly
checked; restored source replays agree.

Independently loaded the retained bundle, checked its entire Program against
the unchanged forwarder golden, exact `packet_case()` entries/packet/ingress,
four ports and seed zero, and replayed it against the restored actual engines:
one agreement, no errors. Its candidate/campaign copies are byte-identical:
28459 bytes, SHA-256
`18dba3145586f62b4e2559fd461342b7ca58c69f7f15b82339b231620f2ecfc4`.
The two unequal overlapping routes make this a distinct input from the prior
single-route TTL-only witness.

Independently compared the restored IR/Python table runtimes, core proof,
native tests and exporter source between both trees; all five pairs agree and
both runtime diffs are empty. Both actual exporters pass the strict independent
validator and match byte-for-byte: 82350 bytes, SHA-256
`cd34627a55f885e67ff76272fec924446837eaae2e26cdc018d2ece7237ebc42`.
The isolated Python fixture deliberately retains the earlier campaign revision
without the final six-line weak-observer control. This was detected and checked
as the sole test-file delta, is now explicitly documented, and is not claimed
to be a source-restoration mismatch or an identical final test revision.

Owner-attributed gates are both final Lean packages/default/native checks,
final 50 focused/static checks, 1517 required comparisons, and the broad gate
with 3239 passed, five existing strict divergences and one unavailable optional
local XDP-image skip. The broad gate loaded before the two final test-only
refinements; it is not evidence for their later revision. Final focused/native
checks do cover them; main integration owns the combined full gate.

No remaining blocker. Actual table application, selected-action composition,
ingress/checksum continuation and whole-packet theorems remain separate work.

