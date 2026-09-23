# Independent forwarding-body policy

2026-09-23. Extends the reviewed field-command body without new IR or source
constructs. Generic lowering faithfully executes whatever was authored; it
does not establish the intended application. The compiled destination/source
accessor fault in `lean/ASSURANCE.md` demonstrated that distinction.

## Contract and actual theorem roots

`lean/P4blo/ForwardPolicy.lean` imports the actual `FieldCommandExamples.forward`.
Its independent `Snapshot` contains all sixteen source fields: Ethernet
destination/source/type/validity, IPv4 TTL/protocol/checksum/validity,
metadata port/drop/sentinel, route hit/destination/source/port, and scratch.
Scalars remain Fin values. `observe` and `restore` use source-data constructors,
not authored Ref/Place accessors or an evaluator. Their two inverse laws
kernel-check without axioms; this observation omits nothing.

The independent policy uses natural TTL comparison with 1. On route hit and
TTL greater than 1, copy route MACs/port, take the natural TTL predecessor and
clear drop. Otherwise set drop only. This does not reuse the source's two
equality guards or modular addition by 255. Complete Snapshot equality fixes
checksum, validity, read-only route inputs, scratch and every other field.

- `authored_policy` relates actual command denotation to the policy for every
  Snapshot.
- `source_policy` uses the inverse laws to cover **every Store roots**, not
  just the fixed conformance initializer.
- `execute_policy` composes with the concrete field-command theorem. Under
  actual nominal Index agreement, exact declaration modes, full frame value
  agreement and action-free BlockFrame, real `P4bloIR.execute` succeeds with
  the entire expected policy state, preserved declarations, all non-variable
  Run state and every root outside possible command targets. No arbitrary
  operational-correctness callback appears in its premises.

All five roots are in default `UserProofAudit`: the inverse laws use no
axioms; the remaining three use only propext, Classical.choice and Quot.sound.
Local elaboration depth/transparency settings enable dependent Record/Path
equation rewriting; they are not assumptions or kernel escapes.

There is **no valid-header premise**. The body does not test validity; the
storage theorem covers invalid headers too. This is not a router or a valid-
packet theorem. Parsing, route lookup, checksum maintenance, architecture
fate, caller/copying and general initialization are outside the claim. A
decremented TTL with unchanged checksum is only an intermediate rewrite.

## Independent test anchors

`ForwardPolicyTests` is in the ordinary user test driver. A manually built
asymmetric source Store is paired with an independently written named
Snapshot, checked by both kernel and native tests. Neither side calls the
other conversion. Inverse laws alone permit coordinated wrong labeling.

Seven full-state cases check policy, source denotation and actual reference
execution: a different initial state, initial drop, miss and TTL 0/1/2/255.
They use unequal MACs, nonzero siblings/sentinels/scratch, maximum route port
and an invalid Ethernet header with stored data. Actual frame checks cover
every root and the extra unrelated root. The universal proof supplies
arbitrary-state coverage; finite checks independently anchor the meaning.

## Adversarial campaign

Edits were applied separately in detached `p4blo-forward-policy-mutants`
based on `ab9d5d5`, with candidate policy/tests/audits copied in. Baseline
audit passed. These are proof/test-anchor rejections, **not new runtime
Python divergences**; no execution replay bundle is created.

1. **Wrong destination accessor.** In `FieldCommandExamples.lean`, change
   only `dst`'s final field slot from `.here` to `(.there .here)`, making it
   identical to `src`. `lake build P4blo.FieldCommandExamples` exits 0:
   generic lowering and the execution witness remain valid. Building
   `P4blo.ForwardPolicy` exits 1: the policy proof now needs the false
   unrestricted equality `dst = routeDst`. This closes the earlier accessor
   gap at the application theorem, without changing generic correctness.
2. **Omit the TTL-one guard.** Restore `dst`. Replace the inner
   `(Cmd.ite (ttl.read === bits[8, 1]) reject rewrite)` with `rewrite` in
   `forward`. The source/witness module again builds, exit 0. The policy
   module fails, exit 1, with `False` in the TTL-one branch. An additional
   unused-simp warning is not the semantic rejection evidence.
3. **Paired state relabeling.** Restore the source body. In `restore`, swap
   `s.dst`/`s.src` and `s.routeDst`/`s.routeSrc`; in `observe`'s result swap
   `dst`/`src` and `rd`/`rs`. `lake build UserProofAudit` exits 0: both inverse
   laws and even the universal application policy hold under this coordinated
   relabeling. `lake test` exits 1 at both independent manual-store anchor
   examples. This is kernel rejection of independent expected answers, not
   runtime execution. Do not remove the anchors because universal proofs pass.

Reproduce in a fresh worktree using the tracked modules and only the named
definition edits. Inside the pinned Nix environment, from its `lean/`:

```sh
lake build P4blo.FieldCommandExamples
lake build P4blo.ForwardPolicy
lake build UserProofAudit
lake test
```

Check exits separately: faults 1/2 expect source build 0/policy build 1;
fault 3 expects audit 0/test build 1. Restore, compare example/policy files
byte-for-byte with the candidate, and rerun audit/user tests. Both restored
commands exited 0, including all seven new runtime answers.

## Checks and next boundary

Both Lean packages/default audits and ordinary user tests pass. Required DRT
on the original `ab9d5d5` base passed 393 tests without skips; this is not the
merged checkpoint count. After advancing to `5e7fd81`, both Lean gates pass,
required DRT passes 405 tests without skips, and the full Python/schema gate
passes 1737 tests with five precise expected discrepancies and one explicit
unavailable local XDP-image skip; formatting/lint/types/schema/workflows also
pass. All exits are 0. Current merged counts belong in `docs/status.md`.
Independent review:
`docs/notes/reviews/forward-policy.md`.

Confidence is high in this storage/body contract, not in completeness as a
network application. Next extend readable authoring and choose an explicit
parser/table/checksum boundary rather than infer it from the local theorem.
