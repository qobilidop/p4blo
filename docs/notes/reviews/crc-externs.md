# CRC extern and family-dispatch review

Reviewed 2026-09-23: the isolated `p4blo-firewall-crc` worktree's uncommitted
CRC increment and adjacent family-suffix repair. Read-only inspection and
targeted independent probes; report written only in the review worktree.

## Confirmed findings and resolution

1. **Known-disagreement classifier could hide unrelated runtime errors.**
   Initially it inspected only stderr lines beginning `error:`. An
   independent synthetic subprocess result containing the exact known
   mismatch plus `Fatal error: exception Failure(...)`, exit 1 and empty
   stdout was incorrectly accepted as the expected CRC disagreement.
   Fixed: the classifier now requires the entire exact diagnostic and
   footer, optionally preceded by the one exact known sink warning. Tests
   reject extra fatal/error/unknown diagnostics, changed bytes, stdout,
   wrong exit codes and corrected success. This closes the demonstrated
   false acceptance without weakening strict XPASS behavior.
2. **Extra CRC constructor arguments were silently ignored at two APIs.**
   Direct Python registry binding and printing accepted an extra instance
   argument, while Lean binding rejected it. Normal `arch.load` already
   rejected the malformed program through validation, so this was not a
   valid-program execution defect. Fixed narrowly in the new CRC factory
   and printer branch, with regressions for both families; the preexisting
   generic registry/checksum behavior is not silently expanded into this
   commit.
3. **External CRC tests were outside oracle CI selections.** The two
   oracle jobs previously selected only their original dedicated test files,
   while new CRC probes/controls live in `tests/test_crc.py`; ordinary CI
   can skip them without built oracles. The integrator owns the workflow
   fix and has agreed to run that file with `-k spectec` / `-k bmv2` in the
   corresponding jobs. This is an integration requirement, not satisfied
   merely by the implementation agent's local successful runs.

After fixes 1–2, independently invoked all four parameter cases of the
classifier and constructor regressions: **passed**. No remaining algorithmic
or implementation blocker found; verify item 3 in the integrated workflow.

## Algorithm and representation review

- Python uses reflected lookup polynomials `a001` and `edb88320`. Lean uses
  forward polynomials `8005` and `04c11db7`, left-shifting a masked register,
  feeding each input byte's bits least-significant first, then reflecting
  the final register. CRC16 starts/ends with zero; CRC32 uses initial/final
  XOR `ffffffff`. These are materially independent implementations.
- Both consume bytes most-significant first within the declared bit string.
  Python's fixed-length conversion and Lean's width-driven extraction
  preserve leading zero bytes. Binding rejects zero and non-byte-aligned
  input widths; runtime calls reject a width different from the bound one.
  The raw Lean helper's broader numeric parameters are not advertised as
  validated extern inputs.
- CRC observations retain instance identity and algorithm family without
  invented mutable cells. Strict observation decoding rejects additional
  cell fields. Input width remains binding metadata checked at calls, not
  separately asserted as mutable logical state.
- The printer uses base zero and `64w65536` / `64w4294967296` for the full
  result ranges. It does not truncate CRC32's range maximum to bit<32>
  zero. Input-shape/width and fixed return-width checks are explicit. Range
  reduction to the firewall's 4096 entries stays outside these services.
- Independently compared Python CRC32 against standard-library zlib over
  **512 seeded byte strings of lengths 1 through 512**: all matched. Zlib
  was used only as this review's additional check; no native dependency was
  added to the production package.

## External oracle evidence and its limits

The hand-written original P4 probe builds P4 source directly, not via IR or
the p4blo printer. Both original and printed paths are checked against
literal expected full CRC bytes, including the 104-bit tuple, leading zeros,
all-ones and the standard ASCII test string. Separate ordinary passing
SpecTec controls cover CRC16, even-byte CRC32 and explicit leading zero.

Independently inspected the local P4-SpecTec checkout at exactly
`2730cfd9e74048bb5439da0f8afcef124079a064`. `hash.ml`'s `package` applies
`pad_right_to_16`, which increases width without shifting the value. This
does prepend a zero byte on odd-byte input and accounts for the captured
CRC32 discrepancies. The diagnosis is not just inferred from two agreeing
p4blo implementations. The fixed firewall smoke sequence can pass despite
different register indices, so its packet-only success cannot certify CRC
state correspondence.

The discrepancy remains a precisely scoped strict xfail, not a general
permission to tolerate CRC failure. No parser/adapter changes rewrite the
oracle input to manufacture agreement. BMv2 known-answer evidence is
appropriate for this deterministic service while the pinned SpecTec
discrepancy remains documented.

## Adjacent suffix repair

Normalizing the first dot-separated segment at both Lean dispatch sites
matches Python's existing family rule exactly. Shape checking retains the
monomorphic declaration; suffixes are not algorithms. The separate existing-
family regressions exercise empty, single and multiple suffixes, and Lean
rejects unrelated prefix-looking names. Keep this fix and its tests in a
separate logical commit before adding CRC, as proposed.

## Gate provenance

Inspected the implementing agent's pre-hardening logs: 335 Lean checks and
package tests pass, required conformance **101 passed**, and full gate
**1046 passed, 3 expected xfails** (the existing BMv2 divergence plus two
precisely named CRC cases). The classifier/constructor fixes require fresh
relevant/full gates; those are the implementing agent/integrator's work.
This reviewer independently ran only the probes and focused regression
calls described above, not the entire modified checkout's test suite.
No implementation-worktree or main-worktree files were changed or committed.

## Integration follow-up

The reviewer independently inspected the integrator's workflow changes:
SpecTec selects both exact discrepancies, three passing controls and two
classifier variants after building the oracle; BMv2 selects both original
and printed known-answer cases after building its image. Existing corpus
steps remain unchanged. This closes finding 3 when the reviewed CRC test
file is integrated. The matching `semantics.md` contract was also inspected.
