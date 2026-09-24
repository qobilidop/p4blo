# Tutorial firewall and BMv2 readback review

Independent read-only review, 2026-09-23, of the pending
`p4blo-firewall-port` worktree. No blocking implementation finding remains.
Only this report was written in the review worktree; implementation files,
default Docker image and the integrator's worktree were not modified.

## Observer boundary

- Optional post-traffic commands allow only whole-array register reads,
  with no newline, indexed read, write or duplicate command escape.
  Sentinel port/data shape is checked before switch execution.
- Readback follows output settling and an exact port/bytes sentinel seen
  once, with process-liveness checks both before accepting completion and
  after readback. The final packet judge still rejects missing, duplicate,
  reordered or extra outputs; the sentinel does not replace that judge.
- Parsing checks the complete pinned CLI transcript, not selected lines.
  Unexpected diagnostics, truncated/duplicate arrays, wrong names,
  noncanonical/negative/out-of-range cells and wrong sizes fail. Expected
  size/width comes from the compiled program. The application comparison
  independently requires both complete 4096-cell arrays, including zeros.
- Fresh-switch prefix replay preserves each prefix's internal history;
  it does not reset between packets within a prefix. Distinct sequence
  numbers and sentinel bytes prevent the known aggregate-output ambiguity
  from accepting a premature ACK in these examples.
- The sentinel argument is scoped, not a general asynchronous completion
  proof. The independently inspected [BMv2 1.15.4 source](https://github.com/p4lang/behavioral-model/blob/1.15.4/targets/simple_switch/simple_switch.cpp)
  starts one ingress worker and processes ordinary packets FIFO. The
  original firewall touches registers only in ingress; a final non-TCP
  sentinel cannot change them. Timestamp-ordered file input plus this
  source restriction supports the readback barrier. Parallel egress still
  relies on settling and exact final packet comparison. Recirculation,
  asynchronous externs or another ingress-worker model require a new
  argument, as the implementation note explicitly warns.

Minor finding resolved: the first diff imposed the new 60-second deadline
on old requests too, contradicting its compatibility claim. The final
condition limits that deadline to requests with the optional barrier.
That one-line correction was inspected; the development image used for
the independent runs below preceded the correction. Optional-profile
behavior is unchanged. The implementer rebuilt the isolated image before
final gates. The additional eighth driver test was independently invoked
and passed: legacy non-barrier output still waits past 60 seconds for
settling, rather than acquiring the new readback deadline.

## Port and independent expectations

The typed port preserves the original header order/widths, fixed extraction,
direction-hit guard, SYN-only writes, reverse tuple hashing, both-register
acceptance condition, MAC/TTL updates and final checksum stage. Modulo 4096
is represented by masking, with full CRC services; no new IR or hidden flow
logic is added. Drop sets both architecture drop metadata and the original
511 egress lookup value. Empty stages are removed only within the explicit
two-port profile.

Expected packets use test-only checksum arithmetic and known transformations,
not interpreter output. Expected state uses fixed independently checked
indices, and unchanged original-P4 register observations anchor those
constants externally. Both collision orders reject a partial match and
preserve the Bloom false positive after both bits are set. Scope remains
bounded; there is no Lean-authored port or application equivalence theorem.

Four deliberate ports remain validator-accepted and run without runtime
errors, but their packet/state results disagree with known answers. This
is meaningful translation mutation coverage, not a claim of new mutations
inside the Python or Lean interpreter.

## Independently reproduced checks

All commands below exited zero; Python source bytecode writing was disabled
and temporary program files were outside implementation worktrees.

- **24** observer/profile/packet-state/index/fixture/mutant cases passed:
  eight driver cases, six Python sequence profiles, four index constants,
  four valid port mutants, source-fixture preservation and synthetic
  original-observer corruption checks.
- Using only `p4blo-bmv2-firewall-port`, compiled the hash-checked unchanged
  original P4, then replayed **seven collision prefixes and four edge
  prefixes**. Every boundary passed the exact packet judge and complete
  **8192-cell** state comparison. No default-image rebuild was performed.
- **Ten Lean cases** passed against the review worktree's independently
  built `411ba82` executable: six known-answer profiles and all four valid
  mutation detections. No implementation-worktree build was invoked.
- Both original and printed route-miss probes independently raised only
  the exact `KnownSpecTecTableMaskDisagreement`, not a generic oracle error.
  The pinned local SpecTec checkout was verified as
  `2730cfd9e74048bb5439da0f8afcef124079a064`; its table-interface line 218
  really casts the base expression where the computed mask is required.
  The diagnosis is therefore supported by source and reproduction.
- The xfail uses the already-hardened complete-transcript classifier and
  a dedicated exception with strict xfail: arbitrary crashes, extra output
  and corrected behavior are not silently accepted. Passing edge controls
  remain separate, and BMv2/Python/Lean retain the route-miss rejection case.

The implementer reports the pre-final-regression full gate passed **1129
tests / 5 exact strict expected divergences / no skips**, and required DRT
passed **125** tests; the final full rerun was still active at review close.
Those gates are implementer-owned, not independently reproduced in full.
This review does not claim to have repeated all six original-source BMv2
profiles or the full oracle suite. Integration must add the documented
`tests/test_firewall.py -k spectec` / `-k bmv2` CI selections, rebuild the
ordinary image with the new driver, and run the integrator's gates. Ordinary
corpus discovery must include both new vectors. These are integration
obligations, not additional implementation defects found by this review.

## Integration follow-up at `8328127`

Independently inspected the integrator's pending workflow/document updates.
Both oracle jobs select the new firewall probes after building their oracle;
existing CRC probes and ordinary corpus replay remain selected. Read-only
pytest collection confirmed **six BMv2 profiles**, **six passing SpecTec
profiles**, and **two strict original/printed table-mask probes**. No test
execution or rebuild was repeated in the integrator's worktree.

Direct discovery checks confirmed all three corpus replay suites see the
same **11 programs / 17 vector files**, and the six original BMv2 profiles
contain **30 prefix boundaries**. README, decisions and implementation
checklist retain the bounded-profile and open-Lean-proof qualifications.
The documentation distinguishes two underlying SpecTec defects from their
four original/printed discrepancy probes and does not excuse a whole
firewall corpus vector. The integrator reports the ordinary image rebuilt,
both Lean gates passed and required DRT **167 passed**; the full gate was
still running. CI integration obligations above are therefore closed by
inspection, with final full-gate completion still integrator-owned.

One nonblocking wording correction was suggested: the status corpus row
should say six bounded profiles, not six additional profiles, since the
connection/collision profiles are included in that total.
