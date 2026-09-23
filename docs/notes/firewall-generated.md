# Structured firewall flows

## Contract before implementation (2026-09-23)

Base `8b2ebdd`; named profile **tcp-flow-policy-v1**. Keep the committed
tutorial firewall and its two fixed /32 routes unchanged. Generate complete
54-byte Ethernet/IPv4/TCP packets between 10.0.0.1 and 10.0.0.2, server
port 80, client ports 0–65535, both wire directions and all eight TCP flag
bits. Port zero is a valid bit-pattern here, not a claim about TCP socket
validity. No connection tracking semantics beyond the tutorial are added.

Each request supplies a complete host entry snapshot. The two directional
rules independently contain no entry, direction 0, or direction 1. Their
presence/value may change between packets without resetting registers.
Direction 0 hashes wire order and inserts both Bloom bits iff SYN is set;
direction 1 hashes reversed wire order and passes iff both bits were
already set. A missing direction rule bypasses filtering and never writes.
Every packet still receives the fixed route's MAC/TTL/checksum rewrite.

The expected model uses two sets of occupied indices, not a set of allowed
connections: false positives must remain observable. Compute CRC16 by
GF(2) polynomial long division with explicit input/output reflection,
independent of Python's byte table and Lean's bit fold. Compute CRC32 with
stdlib zlib (test-only, not a production dependency). Pin those reference
calculations to known literals and the previously original-BMv2-checked
flow indices. Compare exact packets and all 8192 cells after every request.

Hypothesis shrinks small reusable port pools, rule configurations and
event lists without rejecting valid configurations. Start with forty
deterministic examples and targeted correlation, rule-change and collision
scenarios. More random cases are not the acceptance criterion. Preserve
concrete full-sequence replays before independent answer checks; filenames
must include program and all requests so shrinking cannot overwrite them.

Original BMv2 checks two short reproducible samples with constant rules,
using unchanged pinned P4 and the reviewed fresh-prefix/full-array barrier.
The current driver installs entries only before traffic; it cannot claim
original-oracle coverage of mid-sequence host changes. Keep that limitation
explicit rather than resetting state or weakening packet/state assertions.

Confidence: high on the bounded behavior and oracle independence, medium
on generator diversity. Revisit when mutation survivors expose missing
correlations. This is neither general firewall correctness nor proof of
the Python implementation, and it adds no IR construct or extern contract.

## Implemented generator and independent model

`tests/test_firewall_generated.py` owns the complete profile. `campaigns()`
draws a reusable pool of one to three distinct client ports, then one to
ten events. Each event chooses a pool member, wire direction, flag byte,
and two optional direction rules. Shrinking preserves finite-width values
and installable configurations by construction; no application-level
`assume`/filter removes uncomfortable cases. Both Python and real-Lean
property tests run forty deterministic Hypothesis examples. They are
bounded campaigns, not an
exhaustive enumeration of policies or sequences.

`--hypothesis-show-statistics` confirmed forty passing examples for each
property. The Lean campaign additionally reported two internal invalid
generation attempts; no invalid IR/program execution was filtered out.

Every request has a distinct sequence ID starting at 2000. The ID is not
hashed, but prevents identical aggregate oracle packets from hiding an
early drop or a later admission. The model snapshots two independent sets
of indices into full 4096-cell arrays after each event; it includes the
three stateless checksum/hash instances too. It does not call either
production CRC, interpreter, or application body to calculate an answer.
Packet assembly and expected routing/checksum use the previously reviewed
test-only helpers in `tests/test_firewall.py`.

The CRC16 reference divides the reflected message times x^16 by the
polynomial `0x18005` over GF(2), then reflects the 16-bit remainder. This is
structurally different from the production byte lookup table and Lean's
forward shift fold. CRC32 uses `zlib.crc32` only in tests. Before **every**
model evaluation, both are checked against `123456789` (BB3D/CBF43926),
the zero CRC16 input, and all four previously original-BMv2-confirmed
tuple indices (ports 12345, 12346, 749, 13602).

Three named scenarios force useful correlations beyond random draws:

- `missing-direction-syn`: a SYN with both rules absent must pass without
  touching state; this is also the minimal mutation regression below.
- `host-policy-changes`: absent rules do not insert a SYN, restored rules
  reject its reply, a later SYN inserts, removing/restoring rules preserves
  state, and swapped rules insert/check the reversed tuple independently.
  FIN/RST do not delete entries and SYN+ACK has the SYN bit set.
- `bloom-false-positive`: ports 749 and 13602 jointly admit the never-
  inserted port 12346. The model must not silently become an exact set of
  established flows. Explicit fate/count assertions pin these scenarios
  independently of subsequent engine agreement.

Direction 0 uses wire order and direction 1 uses reversed wire order;
“inbound” in the input description means wire direction, not a fixed
security policy. Deliberately swapped policy entries are valid inputs.
The host entry snapshot is replaced per request through the existing DRT
protocol, while registers persist.

## Original oracle profile

The original-source pin and Apache-2.0 notice remain in
`tests/oracle/firewall.py`; neither printed source nor the expected model
substitutes for that input. Seeds 20260923 and 20260924 choose client ports
45274 and 2001. The first uses normal rules, the second swaps them. Each
five-event sample starts with a denied return packet, inserts via SYN+ACK,
admits a return packet, sends FIN, and still admits RST. Expected occupied
indices are respectively `(3568, 2439)` and reversed-tuple `(698, 494)`.
The one-event `missing-direction-syn` regression is additionally sent to
the original program, for eleven total fresh-prefix snapshots.

Each original phase has constant rules. The existing sequential ingress
completion sentinel and full-array parser are reused without modification;
state is read at the end of each fresh prefix, not asynchronously after
each packet. Mid-sequence rule replacement remains **Python/Lean-only**
coverage: the current oracle protocol cannot perform that host event while
preserving one switch's state. No state reset masquerades as a rule update.
No new SpecTec state-equivalence claim is made: the pinned 13-byte CRC32
discrepancy remains documented and strictly tested in `crc-contract.md`.
All **three original BMv2 samples passed**, exact packets and all 8192 cells
at all **eleven prefix snapshots**, exit **0**, 26.57 seconds. This includes
the exact minimal absent-rule SYN mutant witness with unchanged zero state.
The shared Docker disk-pressure incident was cleared by the integrator
before these runs; no image build or global cleanup was performed here.

## Actual table-hit mutant and shrinking

Both Lean packages built, tested and passed their audits before runtime
comparison. In this isolated worktree, an actual Python semantic fault
temporarily changed `python/p4blo/interp/stmt.py`:

```diff
--- a/python/p4blo/interp/stmt.py
+++ b/python/p4blo/interp/stmt.py
@@ -252,2 +252,2 @@
     if ap.HasField("hit"):
-        write_lvalue(ap.hit, match.hit, env)
+        write_lvalue(ap.hit, True, env)
```

This lies about table misses, including the absent direction rule. It
does not alter the generated IR, oracle model, expected answers or Lean.
Run in a fresh isolated worktree with that patch active:

```sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_firewall_generated.py::test_lean_agrees_on_shrinking_flow_policies -q
```

The command exited **1**, with a runtime divergence, and Hypothesis shrank
the failure to `[Event(0, False, 2, Policy(None, None))]`. The exact
deterministic source-only reconstruction, independent of the example cache
or future shrink order, is:

```sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest 'tests/test_firewall_generated.py::test_lean_agrees_on_targeted_flow_policies[missing-direction-syn]' -q
nix develop -c uv run python -m p4blo.drt.replay .artifacts/drt/firewall-generated-03ed36a5b3105147c8cd9b56.json
```

Comparison runs **before** the independent expected-answer assertions.
Failures and retained protocol errors save the complete program and request
sequence. The filename hashes the program and every request, including
the host entries, so shrinking cannot overwrite a different experiment.
`P4BLO_DRT_FAILURE_DIR` overrides the default `.artifacts/drt` location.

The minimal bundle is **65,928 bytes**, SHA-256
`4996340ee0b17b703d9455627de46fb2d6a88db9478bf08e437793cecc97557c`.
It contains one complete valid SYN packet, client port zero, sequence ID
2000, the two routes, and no direction entries. Live replay exited **1**:
**0 agreed, 1 diverged, 0 errored**. Packets are identical, but Python
wrongly sets filter 1 cell **3978** and filter 2 cell **2158**, while Lean's
8192 cells remain zero. A packet-only comparator survives this mutant;
complete state detects it. All other shrinking bundles are retained too
(about 1 MiB total), not committed as redundant fixtures.

The fault was removed immediately after live replay. `git diff --exit-code
-- python/p4blo/interp/stmt.py` exited **0**; the same minimal replay then
exited **0**, **1 agreed, 0 diverged, 0 errored**. No fault is committed.
Local evidence: `/tmp/p4blo-generated-mutant.log`,
`/tmp/p4blo-generated-live-replay.log`,
`/tmp/p4blo-generated-live-witness.log`, and
`/tmp/p4blo-generated-restored-replay.log`. The actual bundle lives under
this worktree's `.artifacts/drt`; the tracked deterministic regression
above reconstructs its inputs without those temporary files.
An identical hash-verified handoff copy is preserved at
`/Users/qobilidop/my/work/p4blo/.artifacts/drt/firewall-generated-03ed36a5b3105147c8cd9b56.json`.

## Gates and limits

```sh
nix develop -c scripts/check-lean.sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_firewall_generated.py -k lean_agrees -q
nix develop -c uv run pytest tests/test_firewall_generated.py -k 'not lean_agrees and not bmv2' -q
nix develop -c uv run pytest tests/test_firewall_generated.py -k bmv2 -q
nix develop -c scripts/check.sh
```

Both Lean packages built/tested/audited successfully (357 spec checks,
21 authored known answers and nine negative typing checks). After restoring
the fault, all eleven non-Docker tests passed, including both forty-example
campaigns, named profiles and replay identity/round-trip checks. Full
required Lean DRT: **237 passed**, exit **0**, 37.78 seconds. Repository
formatting, ruff and pyright passed. The three original BMv2 samples passed
all eleven prefix snapshots. Final `scripts/check.sh` exited **0**:
**1437 passed, five existing strict oracle expected failures, no skips**,
336.34 seconds. Schema lint/generation drift and workflow checks passed
as well. Logs: `/tmp/p4blo-generated-full.log`,
`/tmp/p4blo-generated-all-drt.log`, `/tmp/p4blo-generated-bmv2.log`, and
`/tmp/p4blo-generated-hypothesis.log`. Root must add
`tests/test_firewall_generated.py -k bmv2` to the external oracle CI job;
the Lean suite uses the automatically discovered `test_lean_agrees` prefix.

No new IR construct, extern contract, application-specific runtime escape,
or production dependency is introduced. This profile deliberately excludes
route changes/misses, explicit `NoAction` host entries, arbitrary server
ports/IP addresses, malformed packets (covered separately),
fragmentation/options, payload variation,
concurrency, rule changes in original BMv2, and a Lean-authored firewall or
application proof. A future survivor should drive a specific new profile,
not an unbounded increase in random case count.

Independent read-only review cleared the candidate. The reviewer reran all
eleven non-Docker tests, including both forty-example campaigns, verified
the exact minimal bundle/hash/input against the tracked named scenario,
and replayed it successfully after restoration. Review record:
`docs/notes/reviews/firewall-generated.md`.
