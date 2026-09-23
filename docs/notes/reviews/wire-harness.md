# Differential wire boundary review

Read-only baseline and completed-candidate review on 2026-09-23 of
`p4blo-wire-harness` at `602d349`. **Clear for integration.** No unresolved
implementation finding remains; no candidate builds were performed.

Final evidence qualification closed: inspected the implementer's fresh
`/tmp/p4blo-wire-full-fixed.log`, ending in **1467 passed, 5 existing strict
xfails**, no skips, and `all checks passed`; implementer reports exit 0.
The final note records this gate and the earlier incorrect test-premise
failure separately. This full gate is attributed evidence, not an additional
reviewer-run full suite.

## Independently reproduced baseline problems

Direct calls using the actual Python modules reproduced:

- A reply with two `outputs` keys accepts only the second, silently losing
  an output packet.
- A nested extern object with two `values` keys similarly loses observed
  cells before the otherwise strict state decoder sees them.
- An error reply carrying `diagnostic: []` discards the malformed diagnostic.
- Replay versions `true` and `1.0` pass equality against version 1.
- Replay `program: []`, `program: ""`, and request `entries: []` are
  accepted by protobuf parsing as empty messages despite not being objects.
- An unknown program field raises protobuf `ParseError`; the replay CLI's
  existing exception list does not contain its exception hierarchy.

Tests used a scoped `Path.read_text` mock to supply envelope bytes without
writing any implementation file. No Lean builds or execution were needed.

## Recommended narrow boundary

Reject repeated JSON object keys recursively before dictionary conversion,
including within state/program/entries, and reject nonstandard NaN/Infinity
constants. Require exact integer version/ports/seed types and explicit
program/request/entries object shapes. Convert protobuf parse failures to a
clean documented envelope error. Decide error-plus-diagnostic handling
explicitly rather than dropping malformed fields silently.

Crucially, preserve semantically invalid IR replay: an object-shaped empty
program, unknown installation target, boolean action literal or negative
ingress may be the exact experiment that found an interpreter discrepancy.
Do not introduce the program validator into replay loading. Outer JSON
shape/ambiguity and protobuf syntactic representability are different from
validity of the represented program and requests.

Unknown JSON fields, ProtoJSON aliases/defaults, arbitrary codec equivalence,
resource-exhaustion limits and whole-program validation should not become
implicit new claims of this small patch. Existing valid bundles and all
deliberately invalid replay tests must keep round-tripping. A subprocess
peer should demonstrate malformed duplicate replies yield `ProtocolError`
with retained full inputs, not successful comparison or lost failure data.

## Candidate assessment and independent execution

The shared private parser now rejects duplicate keys at every object level,
including escaped equal spellings, and rejects nonstandard numeric tokens.
`parse_reply` converts those failures to retained `ProtocolError`, and checks
diagnostic types before selecting the error branch. It deliberately preserves
well-typed optional diagnostics on errors and the existing comparison policy.

Replay loading enforces the exact version type and explicit object/array/
string envelopes, wraps protobuf parse failures as `ValueError`, and preserves
negative ingress and semantically invalid object-shaped programs/installations.
No semantic validator is added. Unknown ordinary extension fields and broader
ProtoJSON behavior remain unchanged and explicitly excluded from new claims.

Real subprocess tests manufacture duplicate output/state/diagnostic fields
whose last values would otherwise agree with Python. Each now yields a
protocol failure with zero completed requests and full exact program/inputs;
the saved experiment can replay against the valid peer. This tests actual
false agreement, not merely the new parser helper in isolation.

Independently ran `test_drt.py`, `test_drt_replay.py`, `test_drt_protocol.py`
and `test_drt_state.py` with candidate imports, isolated temporary files and
no implementation cache writes: **139 passed**, process exit 0. The first
run reproduced two test failures from assuming the C JSON decoder's depth
limit followed `sys.getrecursionlimit`. The corrected tests explicitly inject
`RecursionError` and verify normalization; they no longer pretend to enforce
a fixed nesting/resource policy. The actual duplicate/shape regressions and
subprocess tests remain unchanged, so this corrects the test premise rather
than masking a production mismatch.

Independently replayed five preserved real mutation bundles through the new
loader and stable Lean binary: **12 requests agreed, no divergences/errors**:
firewall CRC (four), truncation (five), generated missing direction (one),
typed frame read (one), and typed statement write (one). The old deliberately
invalid replay round-trip tests also passed in the 139-test run.

Implementer-attributed evidence includes both Lean package gates, 233 required
Lean comparisons and 25 genuine pre-fix negative failures. Final restored
full-suite results and the completed note were still pending at this review
checkpoint and are not represented as green here. No general codec proof,
full unknown-field policy or resource-exhaustion guarantee is added.
