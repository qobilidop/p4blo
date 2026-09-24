# Table declaration codec laws review

Final review: CLEAR. Chronological structural and execution evidence follows;
the final section closes the isolated campaigns and restoration.

2026-09-23. Read-only review of `p4blo-table-codec` against its independently
reviewed test baseline `9640523`. Candidate consumers/campaigns are owned by
the implementer; no candidate source or binary was changed or rebuilt here.

## Universal statement and actual implementation

Read all of TableCodecLaws, new witnesses, public export and five exact default
axiom checks. The four laws use the actual existing Key, ActionCall, Entry and
Table encoders/decoders at arbitrary diagnostic paths. Their hypotheses are
only the inherited Expr/Literal/KeyValue wire bounds, uint32 priority/size,
and universal list/optional membership. Empty or duplicate names, unresolved
references, arbitrary action strings and order, zero widths/sizes, match-kind
combinations, entry arity, const flags and optional-default combinations are
not silently constrained by semantic validity.

The first three laws compose the existing actual leaf/list laws. The Table
proof factors real object lookup rather than branching over every omission
combination. Its private lookup function is connected by a proved equation to
the actual TreeMap.ofList lookup, using reverse search/last occurrence and
the existing null-as-missing behavior. Lookup helpers are not an alternate
decoder or assumed successful callback. Omitted scalar/list values are proved
equivalent to actual defaults; optional ActionCall none versus some empty
object is retained. The actual decoded record includes all seven fields.

The mixed constructive witness covers all MatchKinds/KeyValues, asymmetric
ordered data, large unbounded decimal values, maximum numeric bounds, empty
and nonempty calls, absent/present-empty/present-nonempty defaults and arbitrary
const Bool. It intentionally permits invalid semantic names/arity. Kernel
negative witnesses propagate each relevant overflow, including through the
optional default and nested const entries. Absence explicitly imposes no
optional-call premise. Five audits require only the established standard
three axioms; independent fresh queries remain pending.

No table-selection theorem, full Program roundtrip, universal Python codec
equivalence, or validation/compatibility policy follows from these laws.
The earlier independent 181-request baseline review remains separate evidence;
final review will check that it has not been silently recaptured or weakened.

## Independent stable-candidate execution

Owner released the unchanged final candidate binary while campaigns continued
in a separate worktree. Fresh pinned Lean queries checked all five registered
roots: exactly propext, Classical.choice and Quot.sound. Focused Python suite
passed all 235 checks, exit 0 (4.30 seconds). Direct native endpoint self-test
passed all 106 checks, exit 0, empty stderr.

Independently verified the frozen baseline size/hash, all eleven historical
source hashes against `9640523`, and unchanged actual Json bytes. Matched all
181 distinct ordered requests and independent expected answers to current
tracked fixtures, then reran every request against the current endpoint:
stdout/stderr/status byte-identical to the captured baseline. All 82 actual
successful encoded replies also passed the public protobuf wrapper. Baseline
remains 320,705 bytes, SHA-256
`d801a79376f9bf2f786a176b3173535f851b391aeac947a48951d0e7148cc40c`.
No production candidate edits or builds were needed. Final campaign review
and restoration remain outstanding before clearance.

## Final adversarial evidence and restoration

Read the complete durable recipes and actual logs. The one-sided argument
reversal compiles Json, then breaks the unchanged nonempty-array correspondence.
The paired MatchKind swap compiles all four unchanged laws and the baseline
default audit/endpoint; independent ordinary Python checks reject 29 cases and
native literal anchors reject two. Moving const-flag decoding before default
decoding preserves successful roundtrips but changes two exact error answers.
Present-empty default loss breaks the option correspondence and two independent
runtime answers. These are actual runtime codec edits, not fixture-only changes.

Paired flag inversion is classified carefully: the current proof's stronger
field-body lemma fails, but that is NOT proof that paired roundtrip is false.
The separate empty-table/both-flags kernel witness still checks. Independent
wire/default observers reject 23 cases and six native answers. The baseline
endpoint can still compile when the new proof target rejects; it uses the
already reviewed baseline public/audit layer, not sorry or a weakened candidate
proof. The final candidate retains all five new audits and witnesses.

Reviewed demonstrated false assurance too: corrupting either the Python
MatchKind expectation or the direct Lean descriptor under the paired enum
fault makes all 235 ordinary Python checks pass. The separately literal native
anchors still reject two/four answers respectively. No setup or preflight
failure is counted as semantic detection in these campaigns.

Independently reconstructed all four recorded mutant Json byte strings from
clean source and the documented scoped replacements; hashes match the recorded
fault identities. The default filter uses the documented wrapped continuation,
not an equivalent one-line rendering. Verified historical observer/public/audit
hashes against `9640523` and unchanged new proof hash for every bundle.

Verified raw bundle counts, exact sizes and SHA-256s against the note, distinct
requests within each campaign, tracked expected inputs/answers, clean process
status/stderr, and strict actual-vs-expected mismatches. Every deterministic
shared-harness view matches its raw record. Executed all saved inputs against
BOTH restored endpoints: exact historical clean stdout in every case. There
are 56 fault observations (29/23/2/2) over 52 distinct requests, not 112 inputs
when the 56 harness views are also present. Six whole restored source files
are byte-identical between candidate and fault worktree.

Owner-attributed final gates, corroborated by logs: both Lean packages/default
audits/native gate 0 (540 spec checks), all-codec focused 1,049 pass, required
DRT 1,295 pass/1,696 deselected with no skips; restored fault-tree proof/audit/
endpoints 0, ordinary focused 235 pass and native 106 pass. Independent checks
are separately recorded above. The integrator owns the complete combined
Python/schema/oracle gate and previous-artifact integration; no additional
universal validation, table execution or whole-Program claim is accepted.
