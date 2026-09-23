# Normal plain-root return checkpoint

2026-09-23. Implements the reviewed [bounded plan](plain-call-return-plan.md)
against committed `ac69759`. This is normal return only, not a complete call.

## Exact contract and limits

`P4bloIR.PlainCallReturn` uses the existing four `PlainCallEntry.params/args`
and actual `copyBack`/`Execution.dispatch`, not a second binder. Three actual
callee reads supply arbitrary operational Values. Three existing original
caller roots and `BlockFrame caller` allow writes. There is no hidden typing,
declaration validation, zeroability, callee action compatibility, input-route
read, or whole-copyback callback premise.

`copyBack_three` reduces the actual loop to source_hdr, source_meta, hdr
writes in parameter order. `dispatch_return` restores the original caller
frame with precisely those three inserts, preserving the **current** Run's
entire non-frame state. It does not reset body/observer effects to old entry
state. `return_step` consumes exactly one blockReturn and leaves arbitrary
continuation K pending, with fault none; `return_steps` lifts it to Steps.
Scope/action-free restoration and exact lookup/absence preservation outside
the three roots are exported.

The closed `returnedFrame` record is the result expression, not another
initializer or interpreter. The distinct writes commute in final state:
neither its final-state equation nor successful-run extensional equality
alone establishes an externally visible ordering trace. The proof unfolds
the actual loop in order, and the Python observer additionally records the
three writes using a spy delegating to the real write implementation.

This does not establish reaching the return boundary, body or observer
correctness, caller construction, argument validation, full wrapper/parser
execution, action calls, overlapping writable arguments, arbitrary lvalues,
fault unwinding, or rollback after failed copyback. There is no source adapter
in this increment. Confidence high for the fixed operational profile; revisit
a generic list lemma or typed corollary only when a second concrete client
needs it.

## Constructive and independent answers

`CallReturnTests.concrete_return` is kernel checked for every Boolean validity
pair; it reuses the actual Index.build declaration fixture from committed
CallEntry. The default audit includes that concrete theorem and all eight
public generic theorem roots, with exactly propext/Classical.choice/Quot.sound.
The actual H/Result layout and all four parameters of the fixed profile
(three inout, one in) are retained; this is not a separate out-parameter
contract. Native IR tests additionally exercise arbitrary bool/bits/error
Values, absent route, missing writable caller roots, missing callee reads,
and exclusion of action-layered caller frames.

The operational fixture has extra callee destination decoys and a caller
scope without declarations. These intentionally are not globally validated
or typed frames. Its actual-built callee scope is retained verbatim. The
full declaration/param/argument projection is independently compared with
tracked Python `field_command_program`; the declaration-only fixture does
not prove that packet wrapper or its body.

Python constructs independent old/new headers, metadata and H/Result answers
with asymmetric fields and sentinels. All four unique Boolean validity pairs
are required. False Ethernet cases omit callee route entirely; true cases
give it a distinct value. Caller route, scratch, unrelated and caller_only
must survive unchanged; callee scratch/unrelated/destination decoys must not
escape. Current packet/emitter/register/entries/visits values deliberately
differ from entry's historical fixture, including a nonempty installed-entry
array and default action. The continuation would fault if incorrectly run.

The native exporter projects full Index lookup maps, scopes, frame values,
action layers, and all current shared-state fields. Compound map keys use
JSON string-pair encoding, not an ambiguous delimiter. Python compares strict
JSON values (Boolean is not integer), detached whole Index/scope dataclasses,
and additional object identities. Its actual `stmt.copy_back` observer freezes
both complete environments before execution; no expected snapshot is passed
to runtime. Subsequent actual caller member writes in Ethernet, IPv4, Metadata
and H.Result must each leave the retained callee unchanged. Every reachable
mutable Header/Struct object and fields list in the three copied fixture
values must also be detached from all three originals; immutable leaves may
be shared. This is not a Stack or cyclic-Value isolation claim. Python's
separate Env objects do not separately
prove Lean machine restoration; the Lean equation/native snapshot cover it.

These are entry-level/return-level known-answer observations, **not packet
DRT replay**. Required-suite discovery runs them alongside packet tests but
does not change their claim.

## Validation and adversarial evidence

Four faults were applied separately to actual `ir/P4bloIR/Exec.lean` in this
isolated worktree. Each `lake build P4bloIR.Exec` exited 0, then
`lake build P4bloIR.PlainCallReturn` exited 1 with a semantic proof goal,
not merely a syntax failure. Both commands used pinned
`nix develop -c lake +leanprover/lean4:v4.34.0` in the IR package.

| Actual edit, restored before the next fault | Rejecting goal |
|---|---|
| Before `writeLValue lv v`, replace `.var "source_hdr"` with `.var "source_meta"` | `copyBack_three`: wrong first write |
| Remove blockReturn's `setFrame caller` (rename unused binder `_caller`) | `dispatch_return`: writes still run in callee frame |
| Add `.in` to copyBack's direction guard and accept `.expr (.var name)` as `.var name` | `copyBack_three`: extra route read/write remains |
| After copyBack in blockReturn, `modify fun run => { run with visits := {} }` | `dispatch_return`: current visits are lost |

Retained local diagnostic paths are `/tmp/p4blo-return-{wrongroot,skiprestore,
input,nonframe}-{runtime,proof}.log` (expand each brace combination).
The first three runs used the original Steps wrapper; adding an explicit
one-step corollary afterward did not change any rejecting lemma. The fourth
run includes both wrappers. Unused-simp follow-on diagnostics in skipped
restoration are secondary; its primary failure is the displayed unequal Run.
These four results are **proof rejections**, not native executions or packet
differential mismatches. Actual Exec source was restored byte-for-byte:
SHA-256 `ae4bef02b3ce8255a919d8e69375439fcaecd4f87cdd90702dd3e3b655235e75`.

Permanent strict-snapshot challenges reject malformed validity/fault Boolean
encodings, duplicate/missing/extra cases, caller/callee corruption, scope,
Index, and shared packet changes. Delegating actual Python boundary challenges
exercise wrong destinations, skipped copies, input copying, wrong destination
frame, reversed order, aliasing, full shared metadata/state and action layers.
An exported argument remapping paired with the same swapped result model is
rejected by the independent tracked-wrapper declaration/argument anchor.

### Actual Python cursor fault: complete reproduction

In a clean isolated worktree containing this checkpoint, first build both
Lean packages. Do not rebuild native executables while pytest consumes them.
In actual `python/p4blo/interp/stmt.py`, append these two lines immediately
after the for-loop in `copy_back` (at function indentation, before `call_block`):

```python
    if env.packet is not None:
        env.packet.cursor += 1
```

Run from that worktree root:

```text
nix develop -c uv run pytest tests/test_lean_call_return.py -k test_lean_agrees_on_call_return -q
```

The live run exited 1: four actual Python cases failed at strict whole-caller
Run comparison, after the native comparison and ordered-write assertion had
passed; declaration correspondence passed. This fault leaves the normal
copyback writes and every shared object's identity unchanged. Remove exactly
the two injected lines and rerun the entire file: exit 0, 37 passed. Retained
logs: `/tmp/p4blo-return-python-cursor-live.log` and
`/tmp/p4blo-return-python-restored.log`. The permanent `[cursor]` observer
challenge delegates to actual copy_back then injects the same state effect;
it is a replayable boundary regression, not a packet-level DRT artifact.

Restored stmt.py SHA-256:
`4aeb566ca2281d10935c60883a7acad7dd80385c29258c8e9d02e5fd1226a014`.
`git diff --exit-code -- ir/P4bloIR/Exec.lean python/p4blo/interp/stmt.py`
exited 0. No intentional runtime edits are retained.

### Gates

- Pinned `scripts/check-lean.sh`: exit 0 after restoration and final Lean
  edits, both default builds/audits and both native test drivers (494 IR
  `ok` checks, including six new return checks). Log:
  `/tmp/p4blo-return-restored-lean.log`.
- Focused Python file after independent-review refinement: exit 0, 41 passed,
  including twenty-three delegating actual-boundary faults and eleven
  malformed exported snapshots. Log `/tmp/p4blo-return-reviewed-focused.log`.
- Focused ruff formatting/lint and pyright: exit 0.
- Required Lean/Python suite: exit 0, 607 passed / 1481 deselected in 62.95 s;
  log `/tmp/p4blo-return-required.log`. Final repeat after strengthening
  the Boolean alias regression: exit 0, same counts in 50.27 s; log
  `/tmp/p4blo-return-final-required.log`.
- Post-review required repeat: exit 0, 607 passed / 1485 deselected in 48.61 s;
  log `/tmp/p4blo-return-reviewed-required.log`.
- No Docker, oracle rebuild, whole-packet wrapper proof, or full external
  oracle gate was attempted in this proof-only increment.

### Independent-review refinement

The reviewer independently demonstrated three genuine observer survivors:
delegating to actual copy_back then aliasing only caller source_meta to callee
meta, caller hdr to callee observer, or the copied Headers IPv4 child to its
callee child. Each passed the original complete snapshots and Ethernet-only
follow-up write. Those earlier checks did not justify complete aggregate
isolation. The observer now checks all mutable containers/lists for detachment
and performs the four branch-specific actual writes described above. All three
selective aliases plus a separate shared fields-list fault are permanent
regressions. No runtime or Lean proof changes were needed.

[Independent review](reviews/plain-call-return.md) is clear: fresh both-package
builds/native tests, all nine audit roots, final 41 focused tests, and the three
previous selective-alias probes were independently checked; the latter now
reject at the mutable-container assertion after one delegated copy_back call.
Mutation proof/runtime distinctions and restored source hashes were inspected.
Root owns the review's integration and shared status/decision updates.
