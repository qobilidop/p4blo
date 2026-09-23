# Validity-guarded forwarding body

2026-09-23; based on checked main `2713999`. Implements checkpoint 3 of
[header-validity-plan.md](header-validity-plan.md). The original
`FieldCommandExamples.forward` and `ForwardPolicy.policy` are unchanged.

## Contract and decisions

`GuardedForwardPolicy.guardedForward` tests Ethernet validity, then IPv4
validity, then executes the existing route-hit/TTL rewrite. Either invalid
header sets **only** metadata drop. It uses existing read-only `HeaderRef`,
`Read`, `Cmd.ite` and scalar places; no new AST, operators or interpreter.

The independent policy is an ordinary Boolean conjunction over the complete
`ForwardPolicy.Snapshot`, followed by its independent natural-number hit/TTL
policy. Its false branch updates only drop. `authored_policy` relates the
body to this policy; `source_policy` quantifies over every representable
source Store via the existing complete observation/reconstruction inverse.
`source_invalid` separately states exact full-state preservation except drop
whenever either header is invalid. No validity premise excludes these cases.

`execute_policy` lifts to actual `P4bloIR.execute`: scoped body typing,
successful execution, exact final frame values, preserved actual root modes,
all non-variable Run components unchanged and unrelated root names preserved.
Premises are actual nominal Index agreement, actual modes/declarations,
exact source/frame agreement and an action-free BlockFrame. Fixed root
well-formedness is proved. `initialized_correct` constructively discharges
these premises using the existing nontrivial agreeing Run at every source
store. This witnesses the premises; it does not prove a caller initializer.

Confidence is high in this narrowly scoped contract. Reuse of the earlier
complete Snapshot and already-verified rewrite avoids redundant application
semantics. Explicit positional HeaderRefs remain a medium-confidence authoring
choice; revisit with a certified named header endpoint constructor or a second
aggregate read operation, without making validity writable. The new namespace
is deliberate: changing the original invalid-storage rewrite would silently
change an already proved policy and its tests.

Still open: parsing, Ethernet type/IP version/length checks, route lookup,
checksum recomputation, caller initialization/copying and architecture packet
fate. Observed `drop` is metadata, not a proved network drop. This is not a
complete forwarder or a universal Python-equivalence claim.

## Independent observations

Lean tests use asymmetric arbitrary-looking Snapshot values and 32 cases:
every validity pair, both hit values and TTL 0/1/2/255. Both prior drop values
give 64 independent policy/source/actual-execution checks. Expectations use
an explicit two-entry finite forwarding table, not the policy or modular
source expression. Three closed kernel anchors pin each single-invalid
case and the valid TTL-two forward. All four roots are checked; unrelated
root, packet, emitter, entry, extern, scope/index and visit observations are
also retained. The theorem is stronger than this finite runtime observation.

The dedicated `guardedForward` exporter supplies only syntax/inputs.
Python validates its exact 32-name/input set and has a separate finite output
table. Wrapper declarations preserve hdr/meta inout, route input and scratch
local; scratch starts at 19, drop starts false. It reuses only the previous
field-command declaration/observer scaffolding and explicitly replaces each
varying initializer (asserting a unique match). Initializers, caller/copyback,
observer and architecture are unverified test scaffolding, not theorem
conclusions. The authored body runs exactly once before the callee snapshots
every stored field, both validity bits, read-only route, scratch and an
unrelated value. Payload `deadbeef` is preserved. All failures are saved as
complete differential bundles before independent expected bytes are asserted.

Test-only identity header muxes distinguish observer validity reads from the
authored member-shaped guards, so an actual guard evaluator fault does not
falsify the independent observer in the same way. This is not a production
normalization. The permanent guard-fault regression exercises production
evaluation, saves and live-replays a mismatch, then restores and replays
agreement; it never mocks Lean.

## Gates and review

Clean baseline and candidate builds used fresh worktree caches, no copied
old namespaces. Both Lean packages/default audits/userTests pass. Four new
public audit roots have exactly `[propext, Classical.choice, Quot.sound]`.
Focused Python: 34 passed. Required real-Lean DRT: **597 passed**, 1425
deselected, no skips, exit 0. Ruff/pyright are clean. Candidate gate logs:
`/tmp/p4blo-guarded-{baseline-build,lean,focused,drt}.log`. Full-repository
integration/schema/oracle checks remain the integrator's gate; no Docker
images were built. Independent reviewer separately ran the 34 focused tests,
compiled userTests, fresh 64 native cases and four audit queries successfully.
Final independent review is **CLEAR** in
[reviews/guarded-forwarding.md](reviews/guarded-forwarding.md): the reviewer
also inspected every mutation outcome, source-matched/hash-checked both saved
bundle copies, replayed restored agreement and verified byte-identical restored
policy/exporter sources and generated syntax. The integrator copies that
independently owned report into the integration checkpoint.

The old fieldCommands exporter is byte-identical before/after, SHA256
`be4beb58c42f1b17e1bcb9e5744ccd3bd5ad945ed64f63a5571574ab0c195280`.
Capture: `.artifacts/guarded-baseline/fieldCommands.jsonl` (ignored); old
source/policy files have no diff. Reconstruct by building parent `2713999`
and running `lean/.lake/build/bin/fieldCommands`; compare the candidate output.

## Adversarial campaigns

Candidate source was never mutated. A separate detached worktree at the same
base, `p4blo-guarded-mutants`, received the candidate files and a fresh clean
build (no copied caches). All following edits were restored.

1. **Missing Ethernet guard:** replace the body's final expression with
   `Cmd.ite ipv4.isValid forward reject`. Building `P4blo.GuardedForwardPolicy`
   exits 1 at `authored_policy`, on the false-Ethernet/true-IPv4 equation.
2. **Inverted Ethernet guard:** replace it with
   `Cmd.ite ethernet.isValid reject (Cmd.ite ipv4.isValid forward reject)`.
   The same universal application theorem rejects the wrong branch equations
   (build 1). Both are proof rejection, not runtime differential detection.
3. **Coordinated code/policy omission:** use fault 1, change independent
   policy's condition to `s.ipv4Valid`, and adjust the false/true proof case to
   `ForwardPolicy.authored_policy _`. The authored correspondence then holds,
   but the retained `source_invalid` contract rejects the false-Ethernet case
   (build 1). To diagnose the *additional* independent answer boundary, only
   in this isolated experiment temporarily omit the entire `source_invalid`
   declaration and build `P4blo.GuardedForwardTests`. The remaining policy
   module compiles, but `decide +kernel` proves the closed single-invalid
   expected answer false (build 1). This diagnostic intentionally lacks the
   removed contract/default audit: it is **not** a passing proof mutant or a
   runtime kill. The production invalid-state theorem is unchanged/restored.
4. **Exporter-only wrong intent:** restore all proofs, then replace only
   `GuardedForwardMain`'s body export with
   `P4blo.FieldCommandExamples.forward.lower`. Full default build/audits pass.
   Both interpreters agree on the wrong exported body, then the independent
   packet assertion fails for invalid headers (TTL 2 and 255, test exit 1).
   This is a genuine runtime known-answer kill, not a differential mismatch;
   there is no mismatch bundle to save for agreement on unintended syntax.
5. **Actual Python guard bypass:** restore the exporter, then insert the
   following exact guard immediately under `case "is_valid":` in production
   `python/p4blo/interp/expr.py`, leaving its existing return afterward:

   ```python
   if (
       env.block.name == "RewriteBody"
       and expr.is_valid.header.HasField("member")
       and expr.is_valid.header.member.base == pb.Expr(var="hdr")
       and expr.is_valid.header.member.field in ("ethernet", "ipv4")
   ):
       return True
   ```

   This affects authored guards but not identity-mux observer reads. Run the
   exact selected test below: exit 1 saves the complete mismatch before any
   independent answer assertion. Live replay exits 1 with one divergence and
   no errors. Both header validity bytes remain false, but Python incorrectly
   rewrites both MACs, TTL 2→1, port 3→7 and drop false. Lean sets drop true
   and leaves all other stored values unchanged. Remove only the injected
   guard: the same retained input replays with one agreement, no errors,
   exit 0. The permanent scoped production-evaluator monkeypatch regression
   asserts these exact outputs, input identity and live/restored outcomes.

Complete reconstruction, from a built checkout's repository working directory
with fault 5 active (the tracked helper reconstructs declarations, inputs and
post-body observations; no temporary script or generated expected output):

```sh
nix develop -c uv run pytest 'tests/test_lean_edsl_guarded_forwarding.py::test_lean_agrees_on_guarded_forwarding[guard-false-false-true-2]' -q
nix develop -c uv run python -m p4blo.drt.replay .artifacts/drt/lean-guard-false-false-true-2.json
# Restore only the injected evaluator guard, then repeat the replay command.
```

The saved program must equal
`exported_programs(Path('lean/.lake/build/bin/guardedForward'))['guard-false-false-true-2']`
from `tests.test_lean_edsl_guarded_forwarding`; one request is
`Case(pb.Entries(), 0, bytes.fromhex('deadbeef'))`, with **4 ports** and seed 0.
Final bundle `.artifacts/drt/lean-guard-false-false-true-2.json` is byte-identical
in the candidate and isolated tree, SHA256
`3ef594c90fab7df89131d2983c3bab3cfe8004dbc22dfdf0c3017182376d6fe3`.
The ignored bundle is convenience evidence; the tracked recipe is authoritative
for reconstruction. Exact output bytes:

```text
Lean/restored: 1112131415162122232425260800000206abcd00000301123401aabbccddeeff102030405060000713a5deadbeef
Faulty Python: aabbccddeeff1020304050600800000106abcd00000700123401aabbccddeeff102030405060000713a5deadbeef
```

Logs under `/tmp/p4blo-guarded-mutant-`:
`missing.log`, `inverted.log`, `paired-contract.log`, `paired-anchor.log`,
`export-build.log`, `export-test.log`, `export-restored.log`,
`python-test.log`, `python-live.log`, `python-restored.log`,
`restored-build.log`, `restored-focused.log`.
After restoration, both complete Lean packages/default audits/userTests pass;
source policy/exporter compare byte-identical with the candidate and production
`expr.py` has no diff. Candidate also independently replays the saved bundle
successfully. Restored focused tests: 34 passed, exit 0.
