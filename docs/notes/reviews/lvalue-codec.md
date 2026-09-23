# LValue and argument codec review

Final review: clear; chronological investigation follows below. Complete
required/full gate results remain the implementer's integration obligation.

2026-09-23. Candidate `/Users/qobilidop/my/work/p4blo-lvalue-codec`, based on
`cdb7a3c`. Reviewer does not edit or rebuild the implementation worktree.

## Structural review

The actual LValue decoder is changed from partial recursion to checked
structural JSON descent, reusing the established bounded oneof/message
helpers. There is one decoder, no proof-only replacement and no fuel cutoff.
The index's Expr child uses the already-total actual Expr decoder; only the
LValue child recurses through the new descent witness. Arg's nonrecursive
decoder implementation is unchanged.

`LValue.decode_unfold` states exactly the prior proof-erased body for arbitrary
input and path, retaining constructor order and base-before-index error
ordering. The roundtrip theorem reaches the actual encoder and decoder.
LValue representability imposes only the nested Expr wire bounds; Arg selects
the proper existing Expr or new LValue predicate. Empty names, unresolved
members and semantically invalid next/index syntax remain represented. This
does not imply call-direction validity or a full Program/text-parser law.

The test endpoint's LValue and Arg observations independently match semantic
constructors. It does not recover argument tags or operand positions through
the wire encoder. Embedded Expr operator observations retain explicit
constructor matches, preserving the previously repaired independence.

The 39 known-answer cases cover asymmetric indices, nested next/member/index,
both argument variants, unusual/empty names, invalid-but-representable syntax
and uint32 boundaries inside Expr. Public Python protobuf/load/dump roundtrips
are exercised without semantic validation. The 24 exact diagnostic and six
normalization cases preserve missing/null behavior, declared oneof ordering,
first failure paths and unknown-field current behavior. Type-sensitive JSON
comparison and full raw-failure retention use the existing reviewed harness.

Five new default audit roots cover actual LValue/Arg decoding, LValue's
unfolding equation and both universal roundtrips. Native independent branch
and operand answers supplement generic roundtrips and concrete proof witnesses.

No blocking structural finding. Final execution and mutation assessment follow
once the implementer signals restored binaries and supplies the complete note.

## Independently executed restored checks

After the implementer's restored-binary signal:

- Combined leaf, Expr and LValue/Arg Python suites: 388 passed, exit 0.
- Actual `codec-leaves --self-test`: 68 native answers passed, exit 0.
- Pinned Lean stdin audit queries: all five new public roots have exactly
  `[propext, Classical.choice, Quot.sound]`, exit 0.
- Reconstructed all 69 requests and independent expected values from the
  tracked cases/malformed/normalization definitions. Every saved pre-refactor
  transcript matches its tracked case and the restored executable's stdout,
  stderr and exit status byte-for-byte. Baseline SHA256:
  `9a93ac7f5ef00731f4ce6e1c07f76587887ebdc70297af7ba4e6e9afa778e0fe`.
- Read all ten explicitly named retained raw mismatch artifacts, asserting
  exact directory membership, format, exit 0, empty stderr, a unique tracked
  source request/expected-answer match and genuinely unequal saved actual
  answers. Each restored execution agrees with the independent expected
  answer under strict JSON loading and a ten-second timeout.

The restored artifact checks independently cover five LValue-index and five
argument-label failures. The saved filenames identify inputs, not executable
faults; the recorded mutation patches are still needed to reproduce the live
fault. No artifact command string was executed.

Inspected build/test logs confirm the encoder-only index change fails the
roundtrip proof at the actual operand-order equation. Both consistent paired
codec faults compile their proof/audit endpoint, then each selected suite
reports five independent failures and four passing Python controls. These
are distinct evidence from generic proof rejection; re-encoded-wire identity
alone can survive both paired defects.

## Final campaign-note review

Reviewed the completed `lvalue-codec.md` reconstruction section. It explicitly
records the paired index fault's necessary change to the unfolding statement;
this is not disguised as a proof that the old statement survives. Exact
encoder/decoder edits and permanent pytest selectors identify all three
experiments. The two paired campaigns' four encoded-only survivors are
properly contrasted with independent semantic and diagnostic failures.

All ten manifest sizes and SHA256 hashes match this reviewer's independently
computed values. The replay recipe derives five named requests per campaign
from tracked fixture definitions, requires every expected file, checks source
identity, ignores saved executable paths, bounds subprocess execution and
requires clean status/stderr plus strict parsed expected output. Live versus
restored comparisons are explicitly distinguished. The 69-case baseline is
finite evidence, not a claimed theorem equating the old opaque partial
constant with the new total definition on all inputs.

Actual Json byte-compares equal to the pre-mutation candidate; diff whitespace
check passes. No further code or documentation correction requested. The full
and required gates are still running at this review checkpoint, so their final
counts must be recorded before integration rather than inferred from these
focused results.
