# Lean tutorial firewall plan review

Final review: clear for the planning boundary. No application implementation,
new theorem, runtime coverage or oracle result is claimed by this review.

2026-09-23. Independently read the complete plan at `78aa246`, the actual
Python corpus source/README, firewall boundary/generated notes and relevant
fixture API definitions. No production edits, builds, execution or external
oracle operations were performed.

The exact existing Program is a meaningful next application: two 4096-bit
registers, two tables, seven actual ingress locals, fixed headers, ordinary
hash/register/checksum calls and direction-dependent control all already exist
in the IR. Full Program identity against both independent authoring and the
unchanged golden is the right first boundary, not a new semantic firewall
primitive or a claim of verified parser/table/action authoring.

Checked policy descriptions against the actual source: routing precedes
classification, drop also sets port 511, check_ports must hit, direction zero
inserts on any SYN-bit-set packet, direction one reverses tuple order and
requires both Bloom bits. False positives and no FIN deletion remain essential
semantics. IPv4 checksum still executes after drops; TTL wraps. Existing
SpecTec CRC32 and mask disagreements must not be hidden or generalized.

The source-only Forwarder Ethernet/IPv4/metadata declarations are compatible
reuse candidates, while TCP and the three-header root are distinct. Importing
the source does not import its old two-header source agreement proof; no such
proof should be reused for the enlarged roots. Avoiding a new protocol package
or second AST is appropriate for this bounded port.

Actual Index.build/Frame.forBlock success for all seven locals is a useful
constructive prerequisite. The invalid-IPv4 body identity is feasible because
both top-level guards are precisely IPv4 validity; TCP and every effect are
nested under a false first guard, and checksum has the same false guard.
Initialization and identity should remain separate: prove actual initial local
zeros, but do not unnecessarily require unused stored TCP contents or arbitrary
incoming shared state to be valid for the identity theorem. State actual read/
scope/index premises and preserve complete Run, not only packets or registers.

Existing fixture reuse is concrete: connection/collision/shapes/bypass/edges
provide Step sequences with independent outputs/full states; truncated and
persistence cover all byte cuts; generated model/targeted/campaigns provide
rule-change, collision and flag profiles with independent CRC expectations.
Both connection.stf and collisions.stf exist and should be required nonempty
inventories. The fixed in-memory runner must retain extern state between
requests and check all 8192 cells, including zeros, after each request.

Two implementation distinctions deserve explicit retention:

- The fixed authored runner can reuse unchanged-program byte-cut/persistence
  sequences. The existing parser_observer() clone adds diagnostic bytes and
  is not that same fixed Program; its parser-error/validity observations remain
  separately labeled evidence, not direct internal cursor observations.
- Generated mid-sequence entry replacement is Python/Lean-only coverage.
  Current original BMv2 samples use constant configurations and fresh-prefix
  full-array observations. Do not claim the oracle performs dynamic host
  updates or asynchronous per-packet register reads.

The proposed independent full-state invalid-body observer and state-only
mutant are necessary: packet-only tests already missed such a fault in the
forwarder. Source mutation, genuine compiling runtime divergence, setup error,
and zero-hit instrumentation must stay distinct. Reusing retained complete
inputs is sound, provided new faults are not counted as new inputs.

No blocker found. Confidence high in the exact-port boundary; proof/authoring
ergonomics and the persistent fixed-runner protocol need implementation review.
Bloom monotonicity/reverse acceptance are correctly deferred, and the false
universal unsolicited-flow-drop claim is explicitly excluded. All gates and
independent final review remain required before implementation clearance.

Final plan update inspected: it now explicitly separates the seven-local
initialization witness from unused-state identity premises, unchanged-program
boundary sequences from the parser observer clone, and dynamic Python/Lean
entries from constant-rule original-oracle profiles. These close the review
clarifications; planning disposition remains clear.
