# Actual statement-codec review

Final review: clear; chronological investigation follows below.

2026-09-23. Read-only review of `/Users/qobilidop/my/work/p4blo-stmt-codec`
against the separately committed test-only baseline `5cbbc85`, following
`stmt-codec-plan.md` and `reviews/stmt-codec-baseline.md`. The owner began a
controlled fault campaign after the clean build. This reviewer has not run
or rebuilt candidate binaries during that campaign. Clean saved source copies
were used where needed; no implementation files were edited.

## Actual recursion and erasure

This changes the sole production `Stmt.decode`, not a proof-only substitute.
All recursive calls are statement members of the conditional's then/otherwise
arrays. Existing total expression/lvalue decoding and nonrecursive argument
decoding remain the actual callees for other fields.

Termination descends by `sizeOf` through the selected oneof payload, actual
object field and genuine array membership. The new array bound uses core
Array membership/size facts; it has no cached TreeMap-size or map-ordering
well-formedness assumption. The existing object bounds supply the parent
steps. Missing/null repeated fields return empty lists without synthesizing
recursive children.

The bounded array helper traverses attached elements with their true indices.
Its proof erases attachment into the original `Array.mapIdxM` via an explicit
List.mapIdxM accumulator law. Thus it preserves left-to-right sequencing,
indices and Except's first error, not only success values. The repeated-field
erasure splits the actual get? result and retains nonobject errors, absent/null
defaults and present-array errors. Both public erasure laws quantify over
arbitrary decoders/paths and return complete Except equality; they are not
restricted to encoder outputs or semantically valid inputs.

The actual definition has explicit `termination_by sizeOf j`. Its unfolding
theorem rewrites that definition through the helper erasure laws into the old
ordinary-helper recurrence. This reviewer mechanically extracted and compared
the theorem's complete recurrence against the committed prior partial body:
**byte-identical**, including constructor-case order, field order and all
diagnostic/default paths. This is not claimed to prove equality with the old
opaque partial constant itself; the retained 79 raw transcripts cover finite
observations of that historical executable.

## Representability and universal law

StmtRepresentable imposes only recursive existing expression/lvalue/argument
wire bounds and uint32 bounds on push/pop counts. Names, arity, directions,
types, writable roots, nonempty names and program validity are not required.
Empty names and unresolved references remain representable. Both optional
targets are handled at None and Some, empty strings are discharged separately,
and omitted zero counts and omitted empty lists have explicit proof cases.

The public theorem covers every statement constructor and arbitrary diagnostic
path. Its mutual recursor motive covers list members at every path, allowing
the conditional proof to use both full nested branches, not merely a bounded
depth or a special generated subset. The generic array success law requires
the member codec law at every path; concrete call constructors discharge it
through the existing Arg theorem, and conditional branches discharge it
through the actual statement induction. There is no roundtrip premise on the
whole input supplied by the caller.

The nonvacuity witness contains all fourteen constructors, with unequal nested
branches on both sides, empty/unresolved names, optional targets, zero and
maximum counts, and an arbitrarily large decimal bits payload. Its
representability and actual roundtrip are checked theorems. Negative witnesses
exclude overflowing push/pop counts, a nested otherwise expression width,
and an overflowing slice in an extern argument; an actual decoder equation
also checks the overflow error. These restrictions are representability,
not semantic validity.

The default CodecProofAudit now includes array membership, both new erasure
laws, the actual decoder, its unfolding, array roundtrip, universal statement
roundtrip and the nested witness. The explicit expectations are the existing
three standard foundations, with no new axiom or sorry accepted. Fresh audit
queries and runtime observation are deferred until the owner releases the
restored binary window.

## Current disposition and remaining checks

No blocking structural finding. The new production diff is confined to the
required array helpers/bound and the actual statement decoder; encoder,
protobuf schema, Python production implementation and other decode semantics
are unchanged at this stage.

The owner reports clean two-package/default audits, 495 focused checks and
all 79 baseline byte transcripts passing before deliberate faults. Those are
attributed, not independent restored runs in this report. Final clearance
requires source restoration identity, fresh relevant audits/native/focused
checks, exact source-matched raw baseline replay, and examination of the
one-sided and paired compiled-fault evidence. Mathematical termination is
not a practical resource bound, and no universal raw-text/Python codec or
whole-program/execution guarantee is asserted.

## Final independent execution and provenance

After the owner reported all intentional changes restored and no active
consumers/builds, this reviewer independently executed:

- Focused old/new codec suite: **495 passed**, exit 0, 6.49 seconds.
- Actual `codec-leaves --self-test`: **72** native codec anchors pass, exit 0.
- Actual compiled IR test driver: **498 checks**, exit 0; compiled userTests
  also passes, exit 0. These are restored binary runs, not a fresh rebuild.
- Fresh pinned Lean queries for all eight new advertised audit roots: exactly
  `[propext, Classical.choice, Quot.sound]`, with no extra axiom.
- All **79** old transcripts: current fixture request/expected pairs match,
  exact compact-JSON-plus-LF stdin matches, recorded status is an actual
  integer zero and stderr empty, and current stdout/stderr/status equal the
  recorded bytes/status. Baseline format/size/hash are unchanged; every old
  source SHA matches `git show 5cbbc85:PATH`, not current modified sources.
- All **25** live-fault transcript rows match tracked independent requests
  and companion leaf envelopes, have clean native status/stderr and genuine
  unequal live responses, and now replay successfully to the independent
  expected response. Per-set request uniqueness and exact companion artifact
  counts and every request-derived leaf filename are verified. There are
  **20 distinct requests** across the four
  sets, not 25 distinct inputs.

One initial reviewer query appended nonexistent `CodecLawTests.run` after
the successful axiom queries and therefore exited1. It was corrected to use
the actual endpoint's `--self-test` interface; this is a reviewer command
mistake, not a failed project test or an adversarial detection.

The restored Json.lean and CodecLaws.lean each byte-match their pre-campaign
clean copies and documented SHA-256:

- Json: `0d8443121ef018d047e8c7ea87ad8401a02e39f74eff138370db4721f95c443e`.
- Laws: `4a30dac813bb325ff941b2e69a3cf928479774d26639aeacbee9cab94a175db2`.

The four live-raw bundle hashes independently match the inventory in the
note: tags `4a6cbd47…`, branches `d87bd23c…`, index `ffcd88cb…`, null
`d21e05f7…`. The unchanged Python fixture still provides exactly79 requests;
the descriptor's subsequent change is the reviewed kernel-witness addition,
not a rewrite of expected semantic observations to fit a new decoder.

## Adversarial evidence assessment

All six exact source recipes and actual retained build/test logs were read.
The counts and distinctions are supported:

| Fault | Actual compiling/proof result | Independent detection |
| --- | --- | --- |
| Encoder-only branch exchange | Actual Json builds; unchanged statement laws fail a genuine branch-body equality | Proof rejection, not runtime detection |
| Missing repeated fields rejected in both ordinary/bounded helpers | Actual Json, helper erasure and unfolding build after linter-only adjustment; laws fail empty-list constructor cases | Proof rejection; the earlier unused-simp failures are correctly excluded |
| Paired set-valid/set-invalid wire mapping | Decoder, encoder, advertised unfolding and all roundtrip audits compile | Five Python responses fail plus native constructor anchors |
| Paired then/otherwise wire mapping | Actual pair, advertised unfolding and two local proof diagnostic paths are changed consistently; universal theorem/predicate remain unchanged and audits compile | Four Python responses fail plus native branch/order/error anchors |
| One-based shared array diagnostic index | Actual helper and all roundtrip audits compile | Seven exact path failures and native error anchor |
| Null no longer means absent in shared get? | Actual helper and roundtrip audits compile | Nine statement failures plus native default/decimal anchors |

The paired experiments explicitly changed their unfolding statements to agree
with the faulty implementation. Passing those audits therefore does **not**
show preservation of the old recurrence under the fault; it shows the limits
of mutual codec consistency, which the separate frozen descriptors/errors
then expose. Likewise roundtrip laws for encoded values cannot establish
arbitrary null-input policy or diagnostic spelling. These are precisely the
boundaries the independent runtime anchors cover.

The live evidence is clean codec-response disagreement, not a process crash,
timeout, malformed JSON masquerading as a semantic mismatch, or a packet
execution claim. Source-matched raw inputs and strict expected answers remain
replayable after restoration; counts alone were not used as evidence.

## Final disposition

Clear for this scoped actual statement-codec checkpoint. No remaining blocking
finding. Default-target registration already covers CodecProofAudit and the
endpoint, the ordinary native driver imports the tests, and the public spec
root exports CodecLaws. Owner final two-package builds and required discovery
are attributed: **692 passed, 1526 deselected**, exit 0 on this isolated base;
scoped static checks also pass. This reviewer did not rebuild the candidate,
rerun the broad required suite or execute external oracles. Root retains the
integrated full-gate obligation.

The resulting claim is total finite-JSON statement decoding and exact
representable encode/decode roundtrip, with an all-input ordinary-helper
recurrence and independently challenged finite compatibility evidence. It is
not a universal Python equivalence proof, a complete program/declaration
codec theorem, a text-parser proof or an unbounded physical-resource promise.
