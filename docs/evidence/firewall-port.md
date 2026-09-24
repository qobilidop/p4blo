# Tutorial firewall: typed Python port

## Contract and decisions (2026-09-23)

This increment ports the unchanged pinned tutorial solution in
`tests/oracle/firewall.p4` to the typed Python eDSL. It introduces no IR
construct or new extern. Source, revision and license are pinned by
`tests/oracle/firewall.py`; adapted source retains Apache-2.0 attribution.

Preserve fixed Ethernet/IPv4/TCP extraction (including the original lack
of IHL/data-offset option handling), IPv4 routing and MAC rewriting,
wrapping TTL decrement, the exact direction-table hit guard, SYN-only
outbound insertion, reverse-ordered inbound five-tuples, two independent
4096-cell one-bit Bloom filters, and final IPv4 checksum recomputation.
IPv4/TCP checksum verification is absent in the original and stays absent.
The two hash results are reduced by masking with 4095; this is exactly
remainder modulo 4096, not a new general hash-range contract.

The empty verify and egress controls are erased and checksum computation
runs last in the one control, as in the existing forwarder. `mark_to_drop`
maps to the architecture's drop metadata; the egress port is also set to
511 to preserve direction-table lookup keys after a routing drop.
Confidence: high for this fixed sequential two-port profile. This does not
claim equivalence for arbitrary v1model architecture metadata or topologies.

Tests must assert independently expected packet bytes and all 8192 register
cells after each request, not just Python/Lean agreement. A Bloom false
positive must remain accepted: this is not exact connection tracking and
does not support aging or FIN deletion. The pinned SpecTec odd-byte CRC32
padding bug stays explicit; no source/model padding workaround is allowed.

No Lean-authored port or application theorem is claimed in this increment.

## Independent expected behavior

The original smoke input/output bytes are reused exactly, with sequence
numbers distinguishing otherwise identical flow packets. The port has
two ordinary corpus vectors: connection establishment and a Bloom false
positive. Tests additionally check both orders of partial collisions,
SYN-only insertion, FIN non-deletion, reverse-flow RST, non-TCP forwarding,
TTL underflow, fixed parser shape despite IHL/data-offset 6, and direction
table misses. The checksum expectation uses a test-only one's-complement
sum and does not call the production checksum extern.

The SYN guard means **the SYN bit is set**, not that the packet is pure
SYN: SYN+ACK also satisfies the source condition. The explicit multi-flag
case here is SYN+FIN. Edge tests additionally cover a 43-byte frame with
complete Ethernet/IPv4 and only nine TCP bytes, non-IPv4 passthrough, a
routing miss, and an invalid incoming IPv4 checksum that is recomputed
without verification. Truncated Ethernet and IPv4, all possible truncation
lengths, general fragment behavior and exhaustive flag combinations are
not yet exercised by this firewall-specific original-program comparison.

The following independently calculated indices use the 104-bit key
`10.0.0.1, 10.0.0.2, internal_port, 80, 6` in network order:

| Internal port | CRC16 index | CRC32 index |
|---|---:|---:|
| 12345 | 1990 | 1987 |
| 12346 | 966 | 2093 |
| 749 | 966 | 747 |
| 13602 | 780 | 2093 |

Ports 749 and 13602 jointly authorize an inbound packet for 12346 without
that flow ever sending SYN. Either partial match alone rejects, in both
orders. Exact expected snapshots include every cell of both registers,
including all zeros, after each request. Python and Lean each run against
these independent expected values, not only against each other.

SpecTec still has the known odd-byte CRC32 disagreement. For these fixed
13-byte keys its low-12-bit results differ by the same XOR value `0xf45`;
collision relationships and packet fates are preserved despite wrong
register indices. Original-source packet passes, including the collision
witness, therefore cannot establish correct hash/state semantics. The
strict primitive divergence cases remain in `tests/test_crc.py` unchanged.

### Independent table-mask discrepancy

The route-miss case adds destination `10.0.0.3` to the fixed two-/32-route
profile. Python, Lean and unchanged original BMv2 correctly drop it and
leave both arrays zero. The pinned SpecTec instead forwards to port 2.
This is independent of CRC: its
[table-interface source](https://github.com/kaist-plrg/p4-spectec/blob/2730cfd9e74048bb5439da0f8afcef124079a064/spec/9-arch/9.1-table-interface.watsup)
constructs `typedExpressionIR_mask` but supplies
`typedExpressionIR_base` to the cast producing the mask (including the
hex/binary LPM and ternary branches, and slash LPM). The intended exact
key `0x0a000002` therefore becomes `base &&& base`, which admits
`0x0a000003`. Existing wildcard input translation does not repair this.

Two strict tests isolate this exact route-miss observation on unchanged
original P4 and printed IR. They append an independently expected routed
sentinel and whitelist the complete exact mismatch transcript: the oracle
emits the misrouted request before that sentinel. Only the specific
`KnownSpecTecTableMaskDisagreement` earns xfail; crash, extra diagnostics,
wrong output/exit status or any other mismatch fails. Correction produces
strict XPASS. The other original-source edge controls pass separately;
the auto-discovered ordinary corpus vectors contain no masked route-miss
exception. No adapter or input workaround is introduced.

## Original-program register observations

The BMv2 driver gains a separately reviewable, optional readback profile:

- `post_commands`: only whole-array `register_read <qualified_name>`;
  writes, indexed reads, duplicate names and malformed arguments reject.
- `completion_packet`: an exact port/byte sentinel expected once, checked
  after the existing output-settling interval and before register reads.
- Returned `registers`: complete arrays parsed from the entire pinned CLI
  transcript; sizes and value ranges must match the compiled program.
  Extra diagnostics, missing/truncated/duplicate arrays and invalid cells
  fail. Process failure or missing/duplicate sentinel fails as well.

Each observation replays a full sequence prefix on a fresh original
switch, then sends a distinct non-TCP sentinel whose IPv4 route is known
and which cannot touch Bloom state. The caller rejects sentinel collisions
with prior inputs/expected outputs. All earlier ingress processing must
precede that sentinel in this pinned, sequential single-ingress profile;
its observed egress is the barrier before readback. This is **not** a
general proof of asynchronous quiescence, and the existing settling
heuristic remains relevant to output completeness. Do not reuse the
profile for recirculation, multiple ingress workers or asynchronous
externs without a new completion argument. Confidence: high for this
small original firewall, medium as reusable oracle infrastructure.
The pinned BMv2 1.15.4
[switch implementation](https://github.com/p4lang/behavioral-model/blob/1.15.4/targets/simple_switch/simple_switch.cpp)
starts exactly one ingress thread (`start_and_return_`); normal input
packets use FIFO push-front/pop-back in `InputBuffer`. This supports the
barrier argument for this source, whose registers are touched only by
ingress. It does not erase the caveat about parallel egress completion.

Both 4096-cell arrays are compared after every prefix boundary. No source
instrumentation, fake packet field carrying state, privileged container,
host mount or live interface is involved. The full original P4 source is
compiled unchanged. Old driver requests retain their former behavior.
The isolated development image tag is `p4blo-bmv2-firewall-port`, selected
with `P4BLO_BMV2_IMAGE`; integration must rebuild the ordinary image.

## Adversarial coverage and obligations

Four intentionally wrong but validator-accepted IR ports are exercised by
both engines: allowing one Bloom match, inserting without SYN, ignoring
the direction-table hit, and failing to reverse TCP ports. Each is killed
by packet or complete-state expectations without a build/runtime error.
These are authoring/translation mutations, not new interpreter mutations;
the earlier Python/Lean semantic mutation campaign remains separate.

| Valid mutant | Small witness that detects it |
|---|---|
| Require neither filter instead of requiring both | Third collision request is wrongly accepted with only one cell set |
| Insert without SYN | Initial outbound ACK forwards normally but incorrectly changes state |
| Ignore direction-table hit | Bypassed outbound SYN forwards normally but incorrectly changes state |
| Do not reverse TCP ports | Established reverse ACK is incorrectly rejected |

The middle two demonstrate that packet-only conformance is insufficient.
Synthetic observer mutations omit cells, report touched cells only, shift
CRC32 to SpecTec's wrong index, reset state, and admit a premature ACK;
all must be rejected. Driver tests separately exercise malformed command,
sentinel, process and CLI-transcript behavior.

The oracle CI jobs must select `tests/test_firewall.py -k spectec` and
`tests/test_firewall.py -k bmv2`. Required Lean discovery uses the existing
`test_lean_agrees` prefix. Ordinary corpus discovery adds both new vectors
to Python, SpecTec and BMv2 replay without a hard-coded manifest.

Still open: a Lean-authored ergonomic port, scoped monotonicity and
conditional reverse-flow theorems, broader generated flow sequences,
formal proof of CRC equivalence, and full architecture/topology profiles.
This increment adds bounded source/packet/state evidence, not universal
P4-to-IR or Python-to-Lean correctness.

## IR minimality and authoring review

| Firewall behavior | Existing mechanism |
|---|---|
| Fixed Ethernet/IPv4/TCP parsing | Header declarations, extraction, select, validity |
| Routing and direction classification | LPM/exact tables, action parameters, table hit |
| Direction-dependent tuple order | Ordinary actions and conditional calls |
| 104-bit key and 12-bit index | Concatenation, explicit width assertion, bitwise mask/cast |
| Bloom insertion/lookup | Existing register reads/writes, ordinary booleans and branches |
| MAC/TTL/checksum output | Assignment, wrapping subtraction, checksum extern, deparser |

The prerequisite CRC increment added extern contracts, not core nodes;
the port itself adds neither IR nor extern constructs. No opaque firewall
extern hides application semantics. Empty architecture stages are removed
by explicit composition, not simulated inside an application primitive.
This is positive evidence for IR minimality at this milestone, not a
minimality proof over every P4 program.

The typed Python surface is readable alongside the original, with two
noticeable authoring costs. A table hit requires a declared boolean plus
`apply_table(..., hit=...)`, rather than an expression-valued apply; and an
extern result must be assigned immediately, so CRC16 needs a temporary
before masking/casting. The 104-/144-bit concatenations also need explicit
`as_` witnesses because Python's type system cannot calculate widths.
Confidence: medium that these explicit steps are preferable right now.
Revisit with the Lean-authored port: a typed effect/result builder might
make table hits and extern calls ergonomic while retaining visible order.
Do not add IR nodes solely to hide those surface inconveniences.

## Reviewed checkpoint (2026-09-23)

- Both Lean package gates passed: 336 specification checks, proof audits,
  and the user package's 13 scalar known answers / six negative typing
  checks and API tests. This branch precedes the integrator's namespace
  and decimal-codec changes; integration must rerun their combined gates.
- Required real-Lean conformance: **125 passed**. The ten dedicated
  firewall known-answer/mutation cases each use the shared binary fixture.
- Final full `scripts/check.sh`: **1130 passed, five strict known
  divergences, no skips**. Formatting, lint, typechecking, schema and
  workflow checks passed. The five exceptions are the preexisting BMv2
  out-of-bounds rule, two CRC32 probes, and the two new isolated table-mask
  probes; no firewall corpus vector is broadly exempted.
- Original BMv2 state oracle: all **30 prefix boundaries** across six
  profiles passed exact packets and both complete 4096-cell arrays.
  Original SpecTec: six packet/control profiles passed; two exact
  original/printed route-miss cases produced the documented disagreement.
- The final isolated Docker image was rebuilt after the compatibility
  correction; the default image tag was not touched. Eight standalone
  readback-protocol regressions passed, including preserving legacy wait
  behavior. The new completion deadline applies only to readback profiles.
- Independent read-only review cleared the change, separately exercising
  both collision/edge BMv2 prefix observations, all ten Lean profile/mutant
  cases, the two precise SpecTec table-mask probes, and 24 observer/Python
  checks. It found the legacy timeout compatibility change; that was
  narrowed and regression-tested. No confirmed unresolved finding remains.

The integrator owns oracle CI selectors, shared assurance/status updates,
and the review report. The driver/protocol change and the firewall port
are separate logical commits so neither hides the other's trust boundary.
