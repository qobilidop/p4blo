# Firewall truncation boundaries

## Contract before execution (2026-09-23)

Base: `50322dd`. Extend the reviewed pinned tutorial firewall without any
IR, extern or interpreter change. Test every byte length 0 through 54 of
a fixed Ethernet/IPv4/TCP SYN frame. This is byte truncation, not a claim
to exhaust malformed P4 or network inputs.

The parser extracts atomic fixed-size headers: Ethernet 14 bytes, IPv4
20 bytes and TCP 20 bytes. Below 14 bytes it consumes zero; from 14 to 33
it consumes 14; from 34 to 53 it consumes 34. Every incomplete extraction
rejects with `PacketTooShort`, leaving the failing header invalid. Length
54 accepts with `NoError` and consumes all 54 bytes. These expectations
come from header widths and the atomic-extraction contract, not execution.

The unchanged firewall must not update Bloom state for any truncated
frame, including length 48, where the SYN flag byte is already present.
Before a complete IPv4 header, controls leave the default egress port 0
and the output is the unchanged input. With complete IPv4 but incomplete
TCP, routing/MAC/TTL/checksum logic still runs; the failed TCP header is
not emitted, and all its supplied bytes remain payload. A complete SYN
updates the known five-tuple cells. No checksum or input-length check is
invented beyond the original source.

Python's direct parser API additionally exposes accepted/error/cursor and
header validity. The Lean line protocol exposes packets and extern state,
not raw parser results. A separate, labeled test-only observer clone keeps
the parser structurally identical, adds `parser_error` metadata and emits
five diagnostic bytes (short-error, no-error, three validity indicators).
It is not the original-program oracle input. The unchanged firewall's
packet/state comparisons remain separate. Do not claim a direct internal
Lean cursor observation from this instrumented switch output.

Original BMv2 will be checked against the unchanged pinned P4 source for
selected boundaries and valid-malformed-valid persistence. Empty/runt
transport behavior and invalid-header/architecture differences must be
classified from actual results, without blanket expected failures or
normalizing source/input bytes. Invalid stored header fields are not used
as original P4 observations; the firewall guards their reads by validity.
Confidence: high on the IR expectations, provisional on BMv2 empty/runt
input transport pending the experiment.

## Coverage and independence

`tests/test_firewall_boundaries.py` exhausts **byte cuts of one 54-byte
frame**, not arbitrary inputs. The frame is an outbound SYN for
`10.0.0.1:12346 -> 10.0.0.2:80`, with distinct sequence number 1001. Known
CRC cells are `(966, 2093)`; established flow 12345 uses `(1990, 1987)`.
Those constants and the independent checksum/packet transformations are
reused from the previously reviewed firewall tests, not obtained from
either interpreter. Every state assertion compares complete arrays,
including all zero cells and all three stateless hash/checksum observations.

| Input length | Consumed bytes | Valid headers | Error | Packet output |
| --- | --- | --- | --- | --- |
| 0–13 | 0 | none | PacketTooShort | unchanged on port 0 |
| 14–33 | 14 | Ethernet | PacketTooShort | unchanged on port 0 |
| 34–53 | 34 | Ethernet, IPv4 | PacketTooShort | routed on port 2, incomplete TCP retained as payload |
| 54 | 54 | Ethernet, IPv4, TCP | NoError | routed on port 2; insert flow 12346 |

For every incomplete length, a second scenario executes valid outbound
SYN 12345, malformed SYN 12346, valid inbound ACK 12345, and unrelated
inbound ACK 12346. The established reply must still pass; the unrelated
reply must still drop; state must remain exactly the two cells for 12345
after **every** request. This distinguishes missed writes, resets,
premature SYN processing, and unexpected writes outside the known cells.

The parser probe runs all 55 inputs in Python and Lean, with freshly zeroed
packet-local metadata each time. It explicitly compares the parser block
before and after instrumentation and validates the resulting program.
Its five diagnostic bytes are independently expected from the table
above. The retained payload is also checked, but that is not a claim of
direct access to Lean's internal cursor. No Lean-authored firewall, proof
of compilation, or proof of parser correctness is added by these tests.

## Original-program oracle evidence

The original source/revision/license and unchanged configuration are
those pinned by `tests/oracle/firewall.py` and
`docs/notes/firewall-port.md`. Tests compile that original source, not the
observer clone or a printer-generated replacement. The existing reviewed
single-ingress completion sentinel and fresh-switch prefix replay protocol
are reused without change. State is read only at the final boundary of
each fresh prefix, not asynchronously after each packet in one run.

All 13 selected cuts passed on BMv2: **0, 1, 13, 14, 15, 33, 34, 35, 47,
48, 49, 53, 54**. This includes empty and one-byte pcap records: both
produced their exact expected output packet on port 0, with unchanged
complete register arrays. No minimum-frame padding, byte normalization,
skip or expected-failure exception was introduced. The 47/48 boundary
places the final SYN flag byte into an otherwise incomplete TCP header;
it did not cause state writes. BMv2's parser error and cursor are not
directly read by this original-program test.

Seven selected persistence cases use cuts **0, 13, 14, 33, 34, 48, 53**;
their four fresh prefixes per case check packet order and complete state
at every request boundary. All seven passed, for **41 total original
BMv2 prefix snapshots** across the cut and persistence tests.

Confidence is high for this bounded byte-cut profile, including the
observed BMv2 empty/runt behavior. It is not a portability claim for all
hardware/v1model implementations. Failed headers' stored field values are
not inspected: P4 invalid-field values can be undefined, while p4blo has
its own deterministic stored-value semantics. No parity is asserted for
those values. This increment found no implementation mismatch or new
test survivor requiring a production fix.

## Reproduction and remaining work

From the repository root, build before executing Lean comparisons:

```sh
nix develop -c scripts/check-lean.sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests/test_firewall_boundaries.py -k lean_agrees -q
nix develop -c uv run pytest tests/test_firewall_boundaries.py -k 'not lean_agrees and not bmv2' -q
nix develop -c uv run pytest tests/test_firewall_boundaries.py -k bmv2 -q
nix develop -c scripts/check.sh
```

BMv2 requires the pinned image built as documented in `docs/workflows.md`;
this campaign used the already-built image read-only and did not rebuild
the shared Docker tag. The external tests skip only when that oracle is
unavailable, following the existing fixture convention. The BMv2 CI job
must select this file with `-k bmv2`; the 56 new Lean test cases use the
required `test_lean_agrees` prefix and shared binary fixture.

Initial gates: both Lean packages built/tested/audited successfully
(348 spec checks, 13 eDSL known answers and six negative typing checks);
165 focused Python checks passed; 56 Lean comparisons passed;
13 original BMv2 cut checks and seven persistence checks passed. Ruff and
focused pyright passed. The initial full gate passed with 1413 tests and
five previously documented strict oracle expected failures, no skips;
the required Lean gate passed all 223 cases. After the replay-retention
addition and mutation restoration, the full gate again exited **0**:
**1413 passed, five existing strict expected failures, no skips** in
309.38 seconds. It included formatting, lint, pyright, schema generation
drift and workflow checks, plus both available external oracles. The
required Lean gate again exited **0**, **223 passed** in 35.71 seconds.
Final logs: `/tmp/p4blo-boundaries-restored-full.log` and
`/tmp/p4blo-boundaries-restored-drt.log`.

## Replay retention and actual semantic mutation

Both Lean test profiles first run ordinary `compare_program` on their
complete sequence from fresh state. On any divergence, matching runtime
error, or retained peer-protocol failure they save a self-contained bundle
under `P4BLO_DRT_FAILURE_DIR` (default `.artifacts/drt`) and fail. Names are
`firewall-boundary-observer-all-cuts.json` and
`firewall-boundary-cut-N.json`. Only then do the separate independent
known-answer assertions run. Agreement therefore cannot hide a shared
wrong answer, and a first failing narrow assertion cannot lose the full
stateful replay. The observer bundle intentionally contains its instrumented
program; cut bundles contain the unmodified firewall program.

An actual Python implementation fault validated that retention path after
both Lean packages had built, tested and passed their proof audits. In
this isolated worktree only, temporarily apply this exact patch to
`python/p4blo/interp/packet.py`:

```diff
--- a/python/p4blo/interp/packet.py
+++ b/python/p4blo/interp/packet.py
@@ -39,5 +39,7 @@
     def read(self, n: int) -> int:
         """`peek(n)`, then move the cursor; on error the cursor stays."""
+        if n > self.remaining_bits:
+            self.cursor += self.remaining_bits
         value = self.peek(n)
         self.cursor += n
         return value
```

This semantic fault consumes the available remainder before a short read
rejects instead of leaving the cursor unchanged. It is not a build error
or a modified expected answer. With that fault active, the following
tracked-source reproduction command both detects it and writes the exact
five-request bundle automatically (exit **1**):

```sh
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest 'tests/test_firewall_boundaries.py::test_lean_agrees_on_unmodified_boundary_state[48]' -q
nix develop -c uv run python -m p4blo.drt.replay .artifacts/drt/firewall-boundary-cut-48.json
```

The replay command also exited **1**: **3 agreed, 2 diverged, 0 errored**.
The saved sequence is exactly `[truncated(48), *persistence(48)]`: malformed
SYN 12346, valid SYN 12345, malformed SYN 12346, established reply 12345,
unrelated reply 12346. Requests **0 and 2** diverge. Python emits the
34-byte routed Ethernet/IPv4 prefix; Lean emits the correct 48-byte packet
with TCP remainder `303a0050000003e9000000005002`. Complete persistent
state agrees; the packet difference, not a state or build error, kills
this mutant.

The captured bundle is **79,266 bytes**, SHA-256
`960b3340ef5927ec501bf506cf04de9d7a621ded004d72777efca12276dea3a3`.
Local evidence lives at
`/Users/qobilidop/my/work/p4blo-firewall-boundaries/.artifacts/drt/firewall-boundary-cut-48.json`;
an identical hash-verified handoff copy is preserved at
`/Users/qobilidop/my/work/p4blo/.artifacts/drt/firewall-boundary-cut-48.json`.
Both are ignored, not required for source-only reproduction. The exact inputs
are already reconstructed by the tracked test above; no large duplicate
state arrays are committed. Local logs are `/tmp/p4blo-boundaries-mutant-test.log`,
`/tmp/p4blo-boundaries-mutant-replay.log`, and
`/tmp/p4blo-boundaries-restored-replay.log`.

After removing precisely those two added lines, `git diff --exit-code --
python/p4blo/interp/packet.py` exited **0**. Re-running the same replay
command exited **0**: **5 agreed, 0 diverged, 0 errored**. No semantic fault
or production change is included in the final diff. This single Python
cursor mutation supplements, rather than replaces, the previous separate
Python/Lean CRC fault campaigns in
`docs/notes/mutations/firewall-hash-state.md`. It does not claim that all
parser bugs are detected.

Deferred deliberately: generated/seeded structured traffic, non-byte
truncation (the packet API accepts bytes), combinations with IPv4 options,
fragmentation, varying TCP data offsets, checksum rejection, all other
protocols and other architectures. The original tutorial does not validate
all of those packet fields, and this test must not invent checks it lacks.
A follow-up should derive a named generated profile with independent
expected hash/state values, rather than merely increasing sample count.

Independent read-only review cleared the parser/observer separation,
known answers, full-state/prefix protocol and replay retention. The
reviewer independently passed 165 Python and 56 Lean checks, replayed the
restored five-request bundle, and checked original BMv2 cuts 0/48/54 plus
persistence at 48 (seven prefix snapshots). The integration review report
is `docs/notes/reviews/firewall-boundaries.md`.
