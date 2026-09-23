# Verification program

Accepted direction, 2026-09-23: a Lean specification whose execution
rules support proofs, and high confidence that the independent Python
implementation implements it. This extends the completed prototype's
single-theorem milestone. It is not a claim that testing proves Python
equivalent to Lean.

## Assurance boundaries

The schema and validity rules determine admissible programs. Lean gives
their meaning, including parser errors and explicit extern state. Proofs
establish named properties of those definitions, under stated assumptions.
Differential tests check the Python implementation against the executable
definitions used in proofs. External oracles separately check our account
of P4, subject to the documented closed behaviors and adapter limitations.

Serialization, the harness, compilers and runtimes are separate trust
boundaries. A successful build is not a proof of an unproved property; a
skipped oracle is not successful verification; matching internal failures
are not successful execution of valid inputs.

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
