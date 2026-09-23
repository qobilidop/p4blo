# Differential harness JSON boundary

## Contract before implementation (2026-09-23)

Base `602d349`. This increment hardens the **test harness envelopes**, not
IR semantics or general Python/Lean ProtoJSON equivalence. Preserve exact
invalid semantic inputs in replays: empty program objects, negative ingress
ports and invalid table installations remain representable. Do not invoke
the semantic validator while loading a replay.

Both JSON consumers reject duplicate object keys recursively, including
escaped spellings of the same key, before a dictionary can erase a packet
or state cell. Reject nonstandard `NaN`, `Infinity` and `-Infinity` tokens
everywhere. A tiny shared private parser owns those two syntactic rules;
the existing certificate parser is prior art, not modified in this task.

Replay version must be the exact integer 1, not Python-equal `true` or
`1.0`. Require object envelopes for program, each request and its entries;
require an array of requests and string packet data. Preserve the existing
positive integer switch-port count and integer seed/ingress rules. Normalize
protobuf parse failures to a documented load `ValueError`, so malformed
files get CLI exit 2 rather than an uncaught traceback. Distinguish malformed
JSON, unsupported replay version and malformed envelope shape.

Responses retain their current error/output union, required complete extern
state, and diagnostic comparison policy. Validate diagnostic types even
when the response contains an error; malformed telemetry must not be ignored
merely because another field selects the error branch. Error agreement still
compares normalized reason and state, not diagnostic text.

Confidence: high on rejecting syntactic ambiguity and exact envelope types.
Unknown envelope fields and the broader ProtoJSON alias/unknown-field policy
remain deliberately unchanged pending a versioned codec decision. No wire
equivalence proof, resource-limit policy or IR codec change is claimed.

## Reproduced baseline defects

Twenty-five new negative cases failed on unchanged `602d349` before the
production fix (exit 1, `/tmp/p4blo-wire-baseline-negative.log`). They
include these concrete losses, not merely hypothetical malformed input:

```json
{"outputs": [[1, "ab"]], "outputs": [], "state": {}}
{"outputs": [], "state": {"r": {"kind": "counter", "values": ["0x1"], "values": []}}}
{"outputs": [], "state": {}, "diagnostic": "fault", "diagnostic": null}
```

Plain `json.loads` selects the final duplicate. The old observer therefore
lost a packet, counter cells, or diagnostic presence respectively. The
regressions also cover duplicate instance names, duplicate errors, and
escaped equivalent key spelling (`outp\u0075ts`). Duplicate replay program
and entries fields are tested **without a duplicate outer key**, so a
root-only check cannot accidentally pass the nested cases.

Replay versions `true` and `1.0` previously compared equal to integer 1.
Empty arrays/strings supplied as `program` or `entries` could become empty
protobuf objects. Non-object request values escaped as type errors. An
unknown protobuf program field raised `google.protobuf.json_format.ParseError`
past the CLI's handled exceptions instead of a controlled replay failure.
The corrected loader distinguishes these malformed envelopes from a real
empty **object**, which is still a representable semantically invalid IR.

## Implementation and observer challenge

`python/p4blo/drt/_json.py` implements the two shared syntax checks with
`object_pairs_hook` and `parse_constant`. Duplicate detection runs at every
object depth before dictionary construction. It also normalizes a decoder-
raised `RecursionError` to `ValueError`; it defines **no fixed depth limit**.
The response adapter wraps parse failures as `ProtocolError`; the replay
adapter exposes controlled `ValueError` failures and CLI exit 2.

The first two recursion-path tests incorrectly assumed CPython's JSON C
decoder used `sys.getrecursionlimit()` as its direct depth threshold. They
failed, and were replaced by explicit injected `RecursionError` tests of
normalization. This is an error-path check, not an observed resource bound;
no global recursion limit was changed. The first full run containing the
bad test assumptions finished with **2 failed, 1465 passed, 5 xfailed**
(exit 1, `/tmp/p4blo-wire-full.log`) and is not counted as a passing gate.

Three live subprocess regressions go beyond unit parsing. Each peer emits
conflicting duplicate outputs, state, or diagnostic fields whose **last**
values match Python exactly. With the previous lossy decoder temporarily
restored by assigning `run.strict_json_loads = json.loads` inside an isolated
diagnostic subprocess, all three runs incorrectly reported **1 agreed,
0 diverged, 0 errored** (exit 0; `/tmp/p4blo-wire-lax-control.log`). No file
or interpreter semantics was mutated for that diagnostic control.

The hardened path rejects all three with `ProtocolError`, retains their
complete program/request in the attached report, saves a replay, and
successfully replays against the healthy Python-backed peer. Thus the
observer itself is challenged: agreement cannot be manufactured by losing
an earlier duplicate value. These permanent tests are
`test_ambiguous_peer_cannot_produce_false_agreement` in
`tests/test_drt_replay.py`; the full raw peer response is assembled there
from a concrete `register_bounds` request and independently observed healthy
output/state.

## Compatibility and trust boundary

The regression suite preserves all of the following:

- semantically invalid `{}` programs remain loadable (execution may reject
  them later); invalid table installations, boolean action data, negative
  ingress and empty packets still round-trip without semantic validation;
- healthy responses, complete extern snapshots and the existing output/error
  union are unchanged;
- unknown envelope extension fields retain their former ignored behavior;
  diagnostic strings on errors remain well-typed but are ignored by the
  existing error-reason/state comparison policy;
- protobuf unknown fields retain protobuf's rejection policy, now surfaced
  as a controlled load/CLI error rather than an uncaught exception;
- historical `divergences`/`completed_requests`/`protocol_error` summaries
  are not trusted as verdicts: replay re-executes the stored inputs.

All five real, preserved mutation bundles were replayed successfully with
the newly built Lean binary in this worktree, every command exit **0**:

| Bundle under main `.artifacts/drt/` | Requests agreeing |
| --- | --- |
| `firewall-crc32.json` | 4 |
| `firewall-boundary-cut-48.json` | 5 |
| `firewall-generated-03ed36a5b3105147c8cd9b56.json` | 1 |
| `typed-frame-read-x.json` | 1 |
| `lean-statements-update-dependent.json` | 1 |

All twelve requests have zero divergences and zero matching errors. These
local bundles are supplementary, ignored evidence; their tracked source
reconstruction recipes remain in the corresponding firewall/authoring
notes. The ordinary replay tests reconstruct their own fixtures from
tracked IR, including the stateful prefix and deliberately invalid cases.
Actual Python/Lean conformance remains separately exercised by the required
real-Lean suite, not inferred from the fake-peer tests.

This does not establish arbitrary ProtoJSON acceptance parity. Distinct
ProtoJSON aliases naming the same semantic field, unknown-field policy
across Lean/Python, global resource bounds, numeric representability and
codec refinement proofs are open, deliberately outside this harness fix.
Lexically duplicate keys are now rejected; that is not a claim to have
resolved every possible semantic alias.

## Reproduction and gates

```sh
nix develop -c scripts/check-lean.sh
nix develop -c uv run pytest tests/test_drt.py tests/test_drt_replay.py -k 'not lean_agrees' -q
P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees -q
nix develop -c scripts/check.sh
```

To replay any preserved bundle, use
`nix develop -c uv run python -m p4blo.drt.replay /absolute/path/to/bundle.json`.
Both Lean package build/test/audit gates pass at this branch's base (357
spec checks, 21 user known answers and nine negative typing checks).
Required real-Lean comparison gate: **233 passed**, exit 0, 36.40 seconds.
The smaller count is from this isolated branch's pinned base, not a drop
in the newer integrated main suites. The corrected focused harness gate
passes **92 tests**, with 13 real-Lean tests deselected for that command.
Independent read-only review passed 139 focused harness/protocol/state
checks and independently replayed all five retained bundles (12 requests
agreeing). Independent review is clear. The final full gate passes with
**1467 passed, 5 xfailed**, no skips, exit 0 (308.12 seconds;
`/tmp/p4blo-wire-full-fixed.log`). All five expected failures are existing
strict oracle discrepancies, not exceptions introduced by this change.
Formatting, lint, type, schema/generated-code and workflow checks also pass.
No Docker image is rebuilt by this work.
