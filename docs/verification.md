# Verification program

Accepted direction, 2026-09-23: a Lean specification whose execution
rules support proofs, and high confidence that the independent Python
implementation implements it. This extends the completed prototype's
single-theorem milestone. It is not a claim that testing proves Python
equivalent to Lean.

## Assurance boundaries

Lean owns abstract syntax, validity and meaning; protobuf owns wire syntax.
Whole-program validity and codec proofs remain in progress. The executable
Lean semantics includes parser errors and explicit extern state. Proofs
establish named properties of those definitions, under stated assumptions.
Differential tests check the Python implementation against the executable
definitions used in proofs. External oracles separately check our account
of P4, subject to the documented closed behaviors and adapter limitations.

Serialization, the harness, compilers and runtimes are separate trust
boundaries. A successful build is not a proof of an unproved property; a
skipped oracle is not successful verification; matching internal failures
are not successful execution of valid inputs.

## What is proved, checked, or still open

These are distinct obligations, not interchangeable confidence scores.

| Evidence | Exact boundary | Does not establish |
|---|---|---|
| `extract_emit` | Packing/extraction round trip under its stated premises | Whole parser/deparser correctness |
| `FieldLaws.read_declared`, `update_declared` | Exact field primitive results, validity/siblings and whole-Run preservation under actual nominal declarations and exact container shape | Stored-value typing, persistent nested lvalue writes, global validity |
| `ScalarTyping.check_sound` | Every accepted closed scalar expression evaluates at its inferred type and preserves the initial Run | Variables, aggregates, whole-program validation, Python |
| `ScalarTyping.checkIn_sound`, `checkIn_complete` | Contextual scalar checking is sound under actual typed-frame agreement and complete for its relation under a well-formed context | Aggregates, statements, whole-program validation, Python |
| `P4blo.Scalar.lower_typed_in`, `evaluate_lower_in` | Typed source expressions lower to contextually typed IR under well-formedness, and evaluate to the exact independent source value with the whole Run unchanged under exact frame agreement | Intended surface elaboration, arbitrary program initialization, writable statements, serialization |
| `Scalar.Env.frame_matches` | Every well-formed source context/environment has a constructively related runtime frame | Declaration agreement or validity of an arbitrary block/program |
| `Scalar.Cmd.steps`, `execute_correct` | Finite scalar command bodies follow the actual machine, produce exact independent source values, preserve unrelated state and leave arbitrary continuations unexecuted under explicit block-frame premises | Aggregate paths, calls, global initialization/validity, Python equivalence |
| `Scalar.CmdWith.steps_with` | One command implementation composes exact per-leaf read/write laws into a finite actual-machine prefix with unchanged continuation; the scalar API concretely discharges its premises | Concrete writable aggregate instantiation until its own leaf laws and permissions are discharged |
| `Scalar.Modes.scope_agrees`, `frame_matches` | Constructive declarations and related frames exist for well-formed source contexts and permissions | Validity of an arbitrary program or a general `Frame.forBlock` theorem |
| `Fields.Ref.evaluate`, `write_matches`, `validities_set` | Exact independent aggregate-store correspondence for actual nested scalar reads/writes, validity and unrelated state under nominal/index/frame premises | Root write permissions, integrated command compilation, whole-program validity |
| `Fields.lower_typed`, `evaluate_lower` | Shared scalar/field expressions lower to the scoped IR relation and evaluate to the independent source value with the entire Run unchanged under concrete declaration/index/frame premises | General aggregate checker, writable commands, initialization, intended surface selection |
| `CodecLaws.literal_roundtrip`, `type_roundtrip`, `keyValue_roundtrip` | Production Literal/Ty/KeyValue encoder/decoder left inverses over JSON values under explicit v0 uint32 representability | Text parsing, Python/protobuf correctness, recursive codecs, semantic validity, accepted-input equivalence or version negotiation |
| `ScalarLaws` | Selected saturation, shift and branch laws of the actual evaluator | Completeness of the scalar semantics against P4 |
| `Execution.Finishes.sound` | A finite trace of the actual step function determines the actual runner's result | Existence of a trace for every valid program |
| `ExecutionCertificate.check_sound` | Accepted bounded checks bind the supplied initial machine, observation and claim to the runner | Codec correctness, universal Python equivalence, unobserved final state |
| Differential tests and semantic mutants | Concrete independent Python/Lean executions and sensitivity to recorded faults | All inputs or all possible implementation defects |
| External oracles | Corpus behavior through the pinned P4 adapters | Correctness outside tested behavior or documented adapter limits |

`ir/ProofAudit.lean`, `ir/CodecProofAudit.lean` and `lean/UserProofAudit.lean` check the proof dependencies
of advertised roots in their respective packages. Independent review checks
the statements and integration, which the
axiom audit cannot do. [certificates.md](certificates.md) specifies the
compiled claim-checking experiment and its additional trust assumptions.

## Work sequence and acceptance

1. **Reliable comparison and reproduction.** Required CI fails if Lean
   cannot run. Protocol failures and hangs are failures. A replay artifact
   contains the actual program and the whole input sequence from fresh
   extern state, including table snapshots, empty packets and non-bit
   action data that STF cannot represent. A seed is supplementary evidence,
   not the only reproducer.
2. **Observe state and generate programs.** Compare abstract extern state
   as well as outputs. Add shrinking, typed program generation and focused
   component comparisons; retain corpus and external-oracle checks. Test
   the harness against deliberate corruptions and malformed replies.
3. **Proof-friendly execution.** Give statement execution explicit rules
   that Lean's logic can unfold. Ordinary `partial` execution is not that
   boundary. Preserve existing language behavior and test against Python;
   never silently reinterpret an implementation budget as ParserTimeout.
4. **Validity and soundness.** Start with expression checking and its
   connection to actual evaluation; extend to statements and programs.
   Distinguish internal failures from permitted parser errors. State all
   assumptions about stores, table entries and extern implementations.
5. **Stronger execution assurance.** Evaluate a sound certificate checker
   on a small stateful program. Only an accepted, fully bound certificate
   would establish correctness of that execution. This does not prove
   Python termination or universal equivalence.

Each implemented checkpoint receives an independent read-only review and
the relevant gates. `status.md` records what actually landed, the evidence,
and remaining obligations. Proofs must be imported by a checked target;
unchecked axioms and `sorry` are not accepted substitutes for proofs.

## Adversarial iterations

Deliberately mutate both implementations in isolated worktrees. Begin with
a passing baseline, make one anchored semantic change, rebuild when Lean
changes, and run the conformance gate. Record the patch, command and
outcome: killed by a semantic disagreement, survived, or invalid because
the mutant did not build. A compiler failure is not a semantic kill.
Use surviving mutants to add focused component cases or broaden generated
programs, then rerun both the original and mutant. Retain the regression,
never the mutation. Repeat across arithmetic, control flow, packet and
stateful behavior; selected mutants are evidence, not a completeness claim.

## Prior art and choices

Cedar was inspected at `acb0db7daa838249d894d2af64c850e1c9bf0d7d`:
[formal model and proofs](https://github.com/cedar-policy/cedar-spec/tree/acb0db7daa838249d894d2af64c850e1c9bf0d7d/cedar-lean),
[differential targets](https://github.com/cedar-policy/cedar-spec/tree/acb0db7daa838249d894d2af64c850e1c9bf0d7d/cedar-drt),
[comparison relations](https://github.com/cedar-policy/cedar-spec/blob/acb0db7daa838249d894d2af64c850e1c9bf0d7d/cedar-drt/src/tests.rs).
We adopt executable proofs, component-level comparisons, typed generators,
and retained regressions. We retain the process boundary and pure-Python
package: an FFI is a throughput choice, not an additional guarantee.

Keep the models independently implemented. Common wire syntax is useful;
sharing semantic algorithms between the two would weaken differential
testing. Within one implementation, duplicated type analysis can be
consolidated without removing that independence.

## Next concrete extensions

The current checkpoint has contextual scalar checking, exact typed Lean
expression and scalar-command lowering with constructive frame/declaration
witnesses, a proof-visible statement machine, fixed stateful claim checker, typed scalar/stateful
campaigns and bounded original-firewall full-state observations.
Resume with these bounded tasks rather than claiming the roadmap complete:

1. Extend the proved packet/metadata paths and expressions with writable
   commands, preserving siblings and validity under actual Index agreement
   and root permissions. Reuse the scalar command sequencing implementation;
   do not delay fields for every scalar operator. The scoped next plan is
   [notes/typed-fields-plan.md](notes/typed-fields-plan.md); the prior scalar
   plan is implemented and reviewed in `notes/reviews/typed-statements.md`.
2. Generate small validated action/sub-block calls and changing host table
   snapshots across packet sequences. Challenge copy-in/copyback ordering,
   aliasing and fault paths with independent mutations and retained replays.
3. Formalize the validator assumptions needed for machine progress and
   termination: acyclic calls, well-formed stores/externs, finite packet input
   and the parser's no-consumption revisit rule. The current finite-trace
   theorem supplies no proof that every valid program has such a trace.
4. Extend actual codec laws to remaining finite leaves before replacing
   production recursive `partial` decoders with proof-visible recursion.
   Preserve malformed-but-representable syntax and separate known wire answers
   from round trips: paired encoder/decoder faults can satisfy the latter.

Generalizing the claim checker beyond the fixed fragment should follow
explicit validity and observation contracts. A broader JSON interface alone
would not discharge these obligations.
