# Faithful Lean-authored corpus forwarder

2026-09-23. Implements the bounded port in `lean-forwarder-next.md`.

## Authoring and exact identity

`lean/P4blo/Forwarder.lean` constructs the complete `Program` from ordinary
Lean definitions. It never reads the golden, JSON or Python source. The flat
module avoids another directory for a single example. Its real corpus schemas
feed checked `Ref.named` scalar paths and a read-only `HeaderRef`; parser,
action parameter reads, wrapping subtraction, concatenation, table/default,
extern and whole-program declarations remain visible ordinary IR assembly.
These seams are **not** a verified complete frontend. In particular, no
`BlockFrame` command theorem is applied to an active action frame.

The exact protobuf Program must equal both the independent Python builder and
the unchanged text golden. That checks every declaration, expression, ordered
statement, default and checksum field, not a selected-body projection. The
public Python validator must accept it. This preserves the original behavior:

- IPv4 validity alone guards ingress; no Ethernet-validity/route-hit/TTL guard
  was imported from the separate guarded-forwarding application.
- TTL uses wrapping subtraction, including 0 to 255 and 1 to 0.
- Ethernet source receives the **old destination**, before destination is set.
- Table default is drop. Checksum still runs after a dropping table action.
- Parser extracts fixed-width headers; payload survives. Options and checksum
  verification were not added.

Confidence: high in the exact port contract; medium in these small ordinary
IR declaration helpers as an ergonomic API. Revisit after a second complete
Lean-authored application, or when verified parser/action/table frontends
exist. Do not pre-emptively introduce a second AST or macros.

## Execution boundaries

`leanForwarder` exports syntax; `leanForwarder run` invokes public
`P4blo.prepareSwitch` and `P4blo.runSwitch` directly on the compiled
`Forwarder.program`. Run mode accepts only entries, ingress port and packet,
never a Program. The request encoding uses the project's snake_case protobuf
JSON profile. An early camelCase request-harness draft defaulted `prefix_len`
and was corrected; that was fixture calibration, not a production fix or
semantic mutation kill.

`tests/test_lean_forwarder.py` drives all five existing STF files through the
shared STF parser/replayer, the Python switch, generic decoded Lean DRT, and
the fixed in-memory Lean runner. Literal TTL 0/1 answers independently fix the
old-destination MAC dependency, checksum and payload. DRT mismatches are saved
before packet assertions. The permanent saturating-subtraction evaluator fault
checks exact complete saved inputs, live divergence and restored agreement.

Packet output cannot observe omission of a stateless checksum on a dropped
packet. A Python call observer therefore separately asserts actual post-drop
invocation and stored checksum. Native Lean tests execute the actual body and
check complete final state for this case, with both Ethernet validity values.
The observation is test instrumentation, not a whole-pipeline proof.

## Scoped theorem

`ForwarderProof.lean` constructs the actual `Index.build program` and actual
`Frame.forBlock index ingress`. Successful initialization is derived from
the existing general frame-loop and source-zero laws; it is not an assumed
callback or a declaration-only block with a different body.

`invalidHeaders` independently constructs a headers struct containing a
false-validity IPv4 header. Its stored IPv4 fields and Ethernet value are
arbitrary (even malformed values are permitted because they are not read).
`invalidFrame` populates the actual initialized frame with this input and
arbitrary metadata. `invalid_ipv4_control_unchanged` proves the actual
`execute ingress.body` returns `.ok ()` with the **identical whole Run** for
every initial shared state whose index/frame match these constructions.
Both actual guards read false, so table and checksum work is never scheduled.
Its seven-transition trace uses the real machine and `Finishes.sound`, not
a new executor. This is not a proof of parser/deparser, outer `runControl`,
selected action/table matching/checksum semantics, switch fate, arbitrary
initialization or whole-program validity. The non-IPv4 STF supplies separate
finite end-to-end evidence, not an extension of the theorem's statement.

Native coverage includes 24 invalid-input complete-state cases, two
post-drop checksum cases and four direct in-memory switch answers. Full map
comparators reuse the committed test helper (order-independent index/scope,
installed entries/defaults, externs, packet, emitter, visits and frame values).
The production authoring/proof modules do not import synthetic example/test
fixtures. Seven default audits expect precisely the standard Lean foundations
`propext`, `Classical.choice`, `Quot.sound`; no `sorry` or native proof escape.

## Gates and adversarial record

Candidate both-package builds/audits/native tests pass; focused suite has
50 passing cases; focused Ruff format/lint and Pyright pass. The expanded final
required gate passes 867 cases (1570 deselected). The broad
`nix develop -c scripts/check.sh` exits 0: 2431 passed, 1 skipped, 5 expected
failures, plus formatting/lint/types/schema generation drift/actionlint gates.
No Docker images built or changed. Logs: `/tmp/p4blo-forwarder-lean.log`,
`required-final.log`, `focused-final.log`, `full.log` under the same prefix.
The one skip is the unavailable optional XDP compile image, independently
confirmed by `uv run pytest tests/test_xdp_build.py -q -rs` (16 passed, 1
skipped). It is not an executed XDP compile or kernel oracle.

The last full pytest process had already loaded the fixture before two final
nonvacuity assertions were added: the five named STF files must be present
(additional files are allowed), and each vector must collect at least one
packet before comparison. All 50 focused tests, Ruff format/lint and Pyright
were rerun on the final file and pass. The integrator will run the broad gate
on the final merged files; do not describe the earlier in-flight broad run as
having loaded these two assertions. This is test hardening, not another
semantic mutation campaign.

Candidate exporter capture `/tmp/p4blo-forwarder-candidate.json`: 6085 bytes,
SHA-256 `c1f7c1c16d10c1c11f536cb0a5ff54a42fd11d6a2c30c8a4ac06633d6adc4669`.
Source campaign runs only in `/Users/qobilidop/my/work/p4blo-forwarder-mutants`,
with fresh caches and exact copied candidate source, not shared mutable builds.

Independent review found a genuine observation survivor: after delegating the
production `stmt.execute_one`, changing `meta.ingress_port` to `Bits(9,7)` on
the actual MyIngress conditional executed 40 times while all original 15 tests
passed. A prior reviewer probe on `run_block` executed zero times and is not
evidence (public control execution imports `execute` directly).

The repair adds 24 Python profiles from actual `Env.for_block`, running the
actual `stmt.execute` body. `freeze` detaches and type-tags every dataclass,
protobuf message, map/container, packet/emitter slot and extern-instance
state. It covers the complete Index/scope as well as variable values and
shared state. Retained ingress-write, cursor int-to-float, entries clearing,
Index, scope and extern-state faults all fail the stronger observation.
The ingress fault explicitly still executes and survives the weaker real
packet DRT with exact ARP output before the complete-state check rejects it.
Strict fixed-runner response tests reject duplicate JSON keys, Boolean/float
ports and stderr. A separately labeled transport-error handling unit test
checks that `ProtocolError.report` retains complete inputs before failing;
this is not counted as a semantic mutation or simulated Lean execution.

### Isolated source campaigns

All edits below were made individually in the isolated mutant worktree and
restored before the next mutation. Working directory for Lake commands is
`/Users/qobilidop/my/work/p4blo-forwarder-mutants/lean`; for pytest/replay it is
`/Users/qobilidop/my/work/p4blo-forwarder-mutants`. Commands use
`nix develop -c` and the pinned `lake +leanprover/lean4:v4.34.0`.

| Fault in actual authored source | Default build/audits | Independent observation |
|---|---|---|
| `ipv4` HeaderRef selects first (Ethernet) slot rather than second | Exit 1, `invalid_guard` cannot prove false for arbitrary Ethernet | `build leanForwarder` alone exits 0; exact Program identity fails |
| Table default `drop` to `NoAction` | Exit 0 | Exact Program identity fails |
| Swap Ethernet destination/source assignment order | Exit 0 | Exact Program identity fails |
| Checksum result `hdrChecksum.lvalue` to `identification.lvalue` | Exit 0 | Exact Program identity fails |

Each identity kill runs the exact node
`uv run pytest tests/test_lean_forwarder.py::test_lean_agrees_forwarder_program_identity -q`
and exits 1 at independent Python-builder comparison (the golden comparison
is an additional baseline identity). These are compiled application-intent
faults. Faithful interpreters can agree on wrong authored syntax; do not call
these Python–Lean runtime inconsistencies. The default/MAC/checksum faults
correctly leave the narrower invalid-only theorem true. The guard's kernel
rejection is proof evidence, separately from its compiled identity failure.

Actual Python source fault, `python/p4blo/interp/expr.py`, only SUB case:

```python
# original
return Bits.wrap(n, x.value - y.value)
# deliberate fault
return Bits(n, max(x.value - y.value, 0))
```

With the restored Lean source/binary, run:

```sh
nix develop -c uv run pytest 'tests/test_lean_forwarder.py::test_lean_agrees_forwarder_wrapping_ttl[0]' -q
nix develop -c uv run python -m p4blo.drt.replay /Users/qobilidop/my/work/p4blo-forwarder-mutants/.artifacts/drt/lean-forwarder-ttl-0.json --lean /Users/qobilidop/my/work/p4blo-forwarder-mutants/ir/.lake/build/bin/p4blo-lean
```

Both commands exit 1 while the fault is active: one request, zero agreements,
one divergence, no interpreter/protocol error. The Lean packet has TTL/checksum
`ff11a4cf`; Python has `0011a3d0`; both have port 2, the old-destination source
MAC and unchanged payload. The test saves before its independent assertions.
Restore the single Python source line and rerun the exact replay command:
exit 0, one agreement, no divergence or interpreter error.

The complete retained bundle is `.artifacts/drt/lean-forwarder-ttl-0.json` in
both candidate and isolated tree, byte-identical: 27697 bytes, SHA-256
`27376cf7dfe17455b40b849323b35186b471c0b432b01495aa7bd3d9dc0b9c4b`.
Its source can be reconstructed entirely from tracked code:
`authored_program()` and `[edge_case(0)[0]]` from `tests.test_lean_forwarder`,
ports 4, seed 0. It is a new real-corpus input, not the earlier synthetic
guarded-forwarding bundle. The permanent process-local evaluator fault test
repeats this full save/live/replay/restore discipline in every suite run.

Logs under `/tmp/p4blo-forwarder-` are `guard-proof-kill.log`,
`guard-executable.log`, `guard-identity-kill.log`, `default-build.log`,
`default-identity-kill.log`, `mac-build.log`, `mac-identity-kill.log`,
`checksum-build.log`, `checksum-identity-kill.log`, `python-kill.log`,
`python-live-replay.log`, `python-restored-replay.log`, `restored-lean.log`.
The restored isolated both-package/default-audit/native gate exits 0; authored
source compares byte-identically with the candidate, Python runtime has no
diff, and restored exporter bytes match the 6085-byte candidate capture.
Temporary logs are convenience evidence, not a dependency for reproduction.

Independent review: **CLEAR**, by `architecture_review`, recorded in
`docs/notes/reviews/lean-forwarder.md`. It independently checked native
execution/audits, all 50 final focused tests, exact bundle/source/input/hash
identity, restored replay, restored source and both live exporter bytes.
The full repository gate is separately executed evidence, not a result inferred
from that review; the final nonvacuity guard addendum is also CLEAR.

## Next limit

Root integration at `f1493d8` passes both Lean packages/default/native gates
(506 spec checks plus the expanded user suite), all **867 required** checks,
and the full gate on the final files: **2431 passed / 5 strict expected
discrepancies / 1 unavailable-local-XDP skip**, exit 0, 385.35 seconds.
Static, schema/no-drift and workflow checks pass too. Logs:
`/tmp/p4blo-forwarder-integrated-{lean,drt,check}.log`.
The integrated exporter byte-matches the reviewed 6085-byte capture. Root
checked the new bundle's exact hash, Program/edge-request/configuration identity
and restored replay. All 17 earlier execution bundles (24 requests), 49
codec fault observations and 59+69+79 raw codec baselines also pass. The new
bundle makes 18 execution bundles / 25 requests; codec counts do not change.

The next meaningful proof is the original `ipv4_forward` selected table action,
with directionless action parameters and correct block/action-layer restore,
not an application of the scalar block-only command theorem. Follow the
separately reviewed `forwarder-action-next.md` after this interface is committed.
