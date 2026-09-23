# Generated firewall profile review

Independent read-only review on 2026-09-23 of the two-file candidate in
`p4blo-firewall-generated`, based on `8b2ebdd`. No production change or
new semantic construct. **No blocker found; clear subject to completed
restored external/full gates and CI wiring.** No Docker images built or
Docker tests run by this reviewer for this increment.

## Model and observation boundary

The model is independent of both production CRC implementations and the
application body. CRC16 uses polynomial long division with explicit
reflection; CRC32 uses test-only zlib. Known published check strings and
four previously original-BMv2-observed tuple constants guard that reference.
The forward/reverse tuple selection correctly combines wire direction and
configured table direction, including swapped policy. Missing rules bypass
without inserting; direction zero inserts only with SYN; direction one
requires both existing Bloom bits. The model deliberately permits Bloom
false positives, not exact-flow membership.

Full array snapshots are copied after each event. Expected packet bytes use
previously reviewed independent assembly/routing helpers, not interpreter
outputs. The generator chooses small reusable client-port pools, all flag
bytes and independent optional rule directions, giving useful cross-packet
correlations while remaining valid during shrinking. Named scenarios pin
missing rules, policy replacement, persistence and a two-flow false positive.
No `assume` or rejection filter hides inconvenient configurations.

The original oracle input remains unchanged pinned P4. Its three proposed
scenarios have constant policy throughout each prefix; fixed commands are
consistent with their requests. The completion sentinel is non-TCP and
therefore does not acquire new state effects under swapped policy. Distinct
packet sequence fields prevent aggregate-output aliasing. The document
correctly excludes original-BMv2 coverage of mid-sequence host replacement;
that behavior is checked only against Python/Lean and the independent model.

Comparison/save precedes independent known answers. Replay identities cover
the concrete program and complete ordered requests, including host snapshots;
the new regression distinguishes shortened sequences and changed policy with
unchanged packet bytes. Fixed ports/seed are retained in the bundle. The
96-bit hash filename is practical collision resistance, not a mathematical
proof of filename uniqueness. No broader collision-proof claim is needed.

## Independently executed evidence

Directly invoked all **11 non-Docker checks**, including both deterministic
40-example Hypothesis campaigns, named Python/Lean cases and replay-identity
tests, using stable candidate binaries: exit 0. Temporary Hypothesis/test
data stayed outside the implementation tree; no build or source mutation.

Verified the minimal saved bundle equals the tracked missing-direction SYN
program/request exactly (client port zero, sequence 2000, routes but no
direction entries, four ports, seed zero). Its size/hash match the note:
65,928 bytes, SHA-256
`4996340ee0b17b703d9455627de46fb2d6a88db9478bf08e437793cecc97557c`.
Independently restored replay: one agreement, no divergences/errors, exit 0.

Inspected the actual mutant/shrink and witness logs: a real Python table-hit
lie shrank to one missing-rule SYN; packets still agree, but only Python sets
CRC cells 3978 and 2158. Live replay fails; restored replay agrees. Thus
packet-only observation would miss this fault while complete state catches
it. The source fault is absent from the final tracked diff. The documented
exact patch and deterministic targeted-test reconstruction remove dependence
on Hypothesis cache or the ignored bundle surviving across sessions.

The implementer reports both Lean package gates and 237 required DRT cases
passed. External original-source checks and full gates were still running
at review time following the disk-pressure pause; this report does not
present them as independently completed. Integrator must add this test file
to the BMv2 CI selector, record actual external/full results, and rerun
merged-main gates. No new expected-failure exception is introduced.
