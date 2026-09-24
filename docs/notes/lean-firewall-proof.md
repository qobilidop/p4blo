# Actual firewall initialization and invalid body

2026-09-23. Follows the independently reviewed source/execution checkpoint
`be2c4b3` / `11d9380` and the accepted `lean-firewall-next.md` boundary.
No application source, interpreter, schema, golden or fixed server changes.

## Exact proof contract

`P4blo.TutorialFirewallProof` builds the actual Program index and resolves the
actual MyIngress scope. Source nominal layouts agree with that index, including
the third TCP header and seven local declarations. The existing authoritative
`Frame.forBlock_initialized` theorem is instantiated after discharging every
actual scope declaration's zeroability. Aggregate headers use proved source-zero
correspondence with the actual runtime budget, not an assumed successful call.

The resulting public facts establish actual `Frame.forBlock` success, exact
scope, no action layers and **every map lookup**, including absent names.
Seven independent literal scalar answers additionally pin all local values
and widths. The zero-answer theorem does not read its expected values from
the source zero function. The `getD` convenience definitions are backed by
successful build equations; failure/fallback is not the witness.

The body theorem intentionally has a different and broader premise:

- Run.index is the actual built firewall index;
- actual action-first `Frame.read? "hdr"` returns a `headers` struct with
  an invalid `ipv4_t` in its real second position.

Ethernet and TCP values, stored IPv4 contents, metadata, all locals, unrelated
bindings, frame scope/action overlays and every shared Run component are
otherwise arbitrary. They need not be freshly initialized or semantically
well typed: neither false branch reads them. In particular this does not
apply a block-only premise inside an active action or assume a two-header
Forwarder layout. The real global field position and actual read rule are
proved, not supplied by an evaluator-correctness callback.

`invalid_guard` proves the exact pure false read. The real two-conditional
`ingress.body` is executed through the actual work machine, including the
empty-list administrative transitions. `Finishes.sound` derives
`(execute ingress.body).run run = (.ok (), run)`: equality of the **entire
Run**, not only outputs or selected fields. `initialized_invalid_body` is a
constructive instance using the separately proved actual initial frame with
explicit argument replacements. This is execution of the body, not complete
block-call entry/copyout, parser behavior or the whole switch pipeline.

Thirteen default audit roots require exactly `propext`, `Classical.choice`,
`Quot.sound`: index_built, scope_lookup, scope_block, roots_agree, frame_built,
frame_scope, frame_no_action, frame_values, frame_locals_zero,
invalid_frame_read, invalid_guard, invalid_ipv4_control_unchanged and
initialized_invalid_body. No admitted proof, unchecked native theorem, fuel
axiom, alternate evaluator or global heartbeat increase is used. Recursion
depth 8192 is local to this ground declaration/aggregate proof module.

## Independent native and Python state checks

The native suite independently constructs all nine expected root values,
including every zero TCP field, and compares the complete actual initialized
map/scope/action layers. Forty-eight operational profiles then vary Ethernet
validity, prior drop, action overlay, dirty locals and three unused TCP shapes.
They include malformed stored IPv4/TCP contents, a nominally unknown struct,
nonzero metadata and all seven locals, a block hdr decoy shadowed by the
actual action-first hdr binding, extra bindings and nonempty shared state.

Native comparisons cover complete scope/index maps, both action layers,
installed tables/defaults, each extern constructor/state, packet bytes/cursor,
emitter and visits. Short Bloom arrays in these arbitrary-state profiles are
intentional; they are not claimed as startup state or a valid loaded program.
The independent startup test is separate and exercises all nine actual roots.

Python's 58 tests comprise one complete initializer answer, the corresponding
48 invalid-body profile shapes, eight delegating side-effect regressions and
one explicitly demonstrated packet-observer survivor. The complete finite
Env is recursively frozen **before** normal execution, with exact types and
detached mutable contents. Production `stmt.execute` completes normally; no
sentinel exception fakes completion. Native and Python shared-state sentinels
need not have identical constructors (native counter, Python register): these
are two independently checked arbitrary-state preservation instances, not
cross-language equality of those different initial internal states.

The eight actual delegating faults alter a local, unused TCP, Bloom cell,
index error map, scope action map, installed entries, integer cursor type,
or action-layer sibling. Each executes once and the full observer rejects it.
The packet/extern DRT control really runs a local-write fault and still agrees
on an ARP packet; the direct whole-Env check rejects its hidden local change.
This documents why packet-plus-extern observations cannot stand in for the
theorem's full-state boundary. It does not claim a universal Python proof.

## Isolated actual source campaigns

Use `/Users/qobilidop/my/work/p4blo-lean-firewall-faults`, with mechanical
copies of the candidate proof/native/Python files. No candidate executable is
rebuilt during consumers; deliberate edits stay isolated and uncommitted.

For each of the two Lean edits separately, in the fault tree's `lean/`:

```text
nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.TutorialFirewall
nix develop -c lake +leanprover/lean4:v4.34.0 build P4blo.TutorialFirewallProof
```

1. Replace only the first body `.conditional ipv4.expr [` with a literal
   true guard. Actual application source builds0; the unchanged proof fails1
   because its false-branch transition does not execute the actual body.
2. Restore it, then replace only the second body `.conditional ipv4.expr`
   immediately before the checksum call with a literal true guard. Source
   builds0; proof fails1 at that second real conditional transition.

These are compiling application-source faults rejected by the body proof,
not runtime DRT mismatches, general IR semantic-law tests or extra packet
witnesses. Logs: `/tmp/p4blo-firewall-body-{first,second}-{source,proof}.log`.
Restore both before the Python campaign and rebuild the actual proof and
fixed executable; `/tmp/p4blo-firewall-body-restored-lean.log` exits0.

In actual Python `interp/stmt.py`, add `Bits` to its existing values imports
and prepend the following to `conditional`:

```python
if (
    env.block.name == "MyIngress"
    and "reg_pos_two" in env.vars
    and i.then
    and i.then[0].HasField("apply")
    and not expect_bool(evaluate(i.condition, env))
):
    env.vars["reg_pos_two"] = Bits(32, 17)
```

Actual `py_compile` passes. Use the exact ARP Case from
`test_lean_agrees_firewall_packet_observer_misses_local_effect`, the unchanged
Python corpus build and clean authoritative Lean executable. Generic DRT
reports one agreement, no joint error; Python emits exactly the original
packet on port0. Then call `observe_body(invalid_env(build(), True, False,
overlay, True, 2))` for overlay false and true. Both normal executions fail
only at complete-Env equality and leave reg_pos_two=17. After removing the
branch and extra import, both succeed. Logs:
`/tmp/p4blo-firewall-body-python-live2.log` and
`/tmp/p4blo-firewall-body-restored.log`.

An initial mutation attempt omitted the Bits import and failed the packet
precondition; it is a setup failure, **not** semantic detection. Only the
corrected compiling/normal-completion experiment above counts. No generic
mismatch bundle is invented for a fault that generic DRT genuinely misses;
tracked internal constructors and the permanent scoped regression reconstruct
the whole-state witness. Existing evidence inventories therefore stay unchanged.

Restore and compare the whole source, fixed main, proof, native tests, Python
body tests and actual stmt module byte for byte with the clean candidate.
Restored whole-Env checks and both fixed exports pass. Export remains 13588
bytes, SHA-256
`5342abef71eb652082d9bf2cf09ba6059b66d3f135ee7742c23fb58380722ecd`.

## Gates and boundaries

Both packages/default audits/native suites pass with 540 spec checks plus
the nine-root and 48-profile native checks. Focused Python 58 pass, required
real-Lean 1476 pass / 1701 deselected with no skips. Ruff, formatting and Pyright
pass. Full Python/schema gate passes 3171 tests, five existing strict expected
discrepancies and one explicit optional local-XDP-image skip; formatting,
lint, types, schema generation/no drift and workflow checks pass, exit 0.
Logs: `/tmp/p4blo-firewall-proof-{lean,required,check}.log` and
`/tmp/p4blo-firewall-body-focused.log`. No code changed during these consumers.
Independent review has checked all 58 focused tests, 13 fresh axiom roots,
native initialization/48 profiles, exact restored source pairs, both exports
and corrected campaign evidence. Final review is CLEAR;
`reviews/lean-firewall-proof.md` records the independent versus owner-attributed
checks. No outstanding finding remains in this bounded checkpoint.

Confidence is high in this exact initialization/body boundary and bounded
Python observations. The broad unused-state contract is intentional and
proved from actual reads, not an assumption of validation. No positive Bloom
property, CRC proof, parser verification, whole-call property, resource bound,
verified complete source compiler or universal Python equivalence is claimed.
Next application property should target monotone Bloom updates or reversed
flow acceptance with explicit collision assumptions, not exact connection
tracking. Define its source policy and real extern/action boundary first.
