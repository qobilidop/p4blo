# Lean-authored tutorial firewall: execution checkpoint

2026-09-23. First implementation slice of `lean-firewall-next.md`.
This checkpoint establishes independent authoring and bounded persistent
execution, **not** the planned initialization or invalid-body theorem.
Those remain the immediate next proof obligations before scoped Bloom laws.

## Boundary and source identity

`P4blo.TutorialFirewall.program` is authored directly in Lean. It neither
imports Python nor reads a golden. Complete public protobuf comparison matches
the independently authored Python corpus and unchanged text golden; validation
also succeeds. The exported JSON is 13,588 bytes, SHA-256
`5342abef71eb652082d9bf2cf09ba6059b66d3f135ee7742c23fb58380722ecd`.

Named field paths use the typed source library. Ordinary parser, action,
table, extern and operator assembly remains an explicitly unverified seam.
Shared Ethernet/IPv4/metadata layouts and the checksum expression come from
Forwarder as data. No two-header frame assumption or proof is reused. The
firewall has a third TCP header and seven locals, not the forwarder's frame.

The exact existing policy is preserved: actual direction-table hit guarding,
forward/reverse 104-bit hash tuples, separate CRC16/CRC32 masked indices, two
4096-cell bit arrays, insertion when the SYN bit is set (not pure SYN only),
both-bit inbound acceptance, double-collision false positives, wrapping TTL,
old-destination source MAC, drop plus egress511 and checksum even after drop.
No new core construct, extern service, options parser or checksum verification
is introduced. Original BMv2 and SpecTec evidence/exclusions remain unchanged.

`leanTutorialFirewall run` prepares the same in-memory Program through the
public API. Only entries, ingress and packet bytes enter its request protocol;
returned extern state persists between requests. The executable is a default
target and the source module is publicly imported. Four output ports match
the independent test profile. This is not an arbitrary-Program server.

## Independent execution observations

`tests/test_lean_firewall.py` tests both unchanged STF files, six known
sequence profiles (including both collision orders), all 55 byte cuts,
54 established/malformed/reply sequences, three named host-policy sequences
and 40 deterministic shrinking generated campaigns. It reuses independently
authored expected packets and all 8192 register cells, not interpreter output
as the policy oracle. Dynamic installed entries are Python/Lean evidence,
not a claim about original BMv2's constant-rule prefixes. It does not send the
separate parser-observer clone to the immutable fixed runner.

The fixed reply observer requires exactly the five expected externs, both
array lengths and bit widths, canonical hexadecimal cell values and no
diagnostic. Comparisons freeze exact types, so Boolean/integer equality
cannot erase a value-level distinction in the observed logical state.
Four malformed-state controls reject truncation, Boolean width, omitted
externs and unknown reply fields. These are complete logical extern
observations, not a proof of every internal Python object invariant.

Ordinary exported-IR DRT runs and saves first. A fixed-server-only defect can
survive it, so fixed execution separately checks its entire request sequence
against fresh persistent Python execution. On a completed-process mismatch it
retains exact stdin/stdout/stderr/status and the reference Program in a
`p4blo.lean-firewall.fixed.v0` transcript. This is deliberately not labeled a
generic DRT divergence. The permanent restart regression runs the actual
native server freshly for each request, demands retention, checks the lost
state and then checks the restored persistent server.

## Isolated compiling faults

Campaign tree: `/Users/qobilidop/my/work/p4blo-lean-firewall-faults`, base
`61dc681`, with mechanical copies of the candidate source/test additions and
fresh package caches. No candidate binary was rebuilt under its consumers.

1. **Reset native state.** In `TutorialFirewallMain.lean`, change the single
   `P4blo.runSwitch sw externs entries port packet` call to use `initial`.
   Building the actual executable succeeds. Ordinary generic DRT still agrees
   on all four `connection()` requests. `fixed_run` fails: the SYN appears to
   insert, but the third request loses both arrays and drops the established
   reply. Its saved exact transcript is 331,679 bytes, SHA-256
   `6dd40faa8dbd00129dd11f6831bc42e3c5b35046beba3bf8324b5fd2a1d6f161`.
   Replaying the same stdin against the restored server produces all four
   independent packet/full-state answers. The reviewed copy is retained at
   `.artifacts/fixed-firewall/state-reset.json`; the capture helper initially
   writes `lean-firewall-fixed-6dd40faa8dbd00129dd11f68.json` in its failure dir.
2. **Ignore the hit guard.** Restore the server; replace the source's unique
   `.conditional checkPortsHit.expr filterBody []` with a literal true guard.
   The actual Lean executable compiles. Whole Program identity rejects it.
   Both interpreters agree when given that same wrong Program, but the
   independent `missing-direction-syn` profile observes unintended insertion
   in both arrays. Its packet is unchanged. This is a source-intent kill,
   not an engine disagreement or a proof rejection.
3. **Skip Python Bloom writes.** Restore the Lean source. In actual
   `Register.call`, immediately after the write-argument type assertion,
   return `ExternResult()` when `self.width == 1 and len(self.cells) == 4096`.
   Python compilation succeeds. Save `compare_program(build(), cases, 4,
   [binary])` for `cases = [s.case for s in connection()]` before asserting
   policy answers. Three clean divergences and one agreement occur; all
   Python cells stay zero while Lean retains the inserted flow. Live replay
   reproduces them. Restoring the source gives four agreements.

The third capture is 76,260 bytes, SHA-256
`c547f2999038dae030dfd93402e7e26a73782f0424384fda9633a5ee7e886103`.
It is byte-identical to the existing `.artifacts/drt/firewall-crc32.json`:
the same complete four-request input under a different fault, **not a new
distinct execution witness**. The fixed-server transcript likewise observes
those same inputs through a different protocol; it adds evidence, not inputs.

Reconstruct campaigns using the three exact edits above, one at a time.
Build the fixed executable from the isolated tree's `lean/` directory with
`nix develop -c lake +leanprover/lean4:v4.34.0 build leanTutorialFirewall`.
Use the tracked `connection`, `fixed_run`, `assert_program_identity`,
`targeted` and `model` helpers and public DRT save/load/replay APIs; never
execute commands from artifact metadata. For reset reconstruction call
`fixed_run([s.case for s in connection()])` and require its saved-transcript
AssertionError. For the guard, decode the actual export then require identity
failure and disagreement with `model(targeted()['missing-direction-syn'])`.
For Python, save/load the complete bundle, require three clean live divergences,
restore and require four agreements. Both protocols use four ports, and the
generic bundle uses seed0. The tracked restart regression additionally
reconstructs the reset observer challenge without changing source files.

Restoration compares four whole source files byte for byte with the clean
candidate: TutorialFirewall, its main, the Python test and Register. Actual
restored export identity and fixed/generic replay pass. Logs in `/tmp/`:
`p4blo-firewall-reset-{build,live}.log`,
`p4blo-firewall-hitguard-{build,kill}.log`,
`p4blo-firewall-python-live.log`, `p4blo-firewall-restored{,-build}.log`.
Temporary logs are supplemental; the edits, helpers and hashes above survive
their loss. No intentional fault is committed.

## Gates and next step

Both package/default-audit/native gates pass (540 spec checks). The focused
suite has 128 passing tests, including independent reviewer execution. Required
real-Lean conformance passes 1418 tests with 1701 deselected and no skips.
The complete Python/schema gate passes **3113 tests / 5 existing strict
expected discrepancies / 1 explicit local-XDP-image skip**, exit 0. Formatting,
lint, types, schema generation/no drift and workflow checks also pass. Logs:
`/tmp/p4blo-lean-firewall-{lean,focused3,required,check}.log`. Candidate code
is unchanged since the full gate began. Independent final review is CLEAR:
128 focused checks, exact source restoration, both exports, retained input
identity and live/restored evidence were checked independently. Full and
required gates are owner-attributed. Review: `reviews/lean-firewall-port.md`.
Its fixed-runner retention and diagnostic findings were closed before clearance.

Confidence is high in exact authoring and these finite packet/state profiles,
not universal Python equivalence. Medium confidence in keeping two small
fixed-server wrappers rather than abstracting their protocol now; revisit on
a third application or a behavioral divergence, with both protocols tested.
Next: prove successful actual nine-root/seven-local initialization separately
from whole-Run identity of the real invalid-IPv4 body. The latter should permit
arbitrary unused TCP/local/shared state wherever actual reads allow it.
No complete pipeline, source compiler, parser, checksum or Bloom theorem is
claimed by this execution checkpoint.
