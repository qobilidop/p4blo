# Bounded execution certificate review

2026-09-23. Independent read-only review of `827fe74`. No confirmed defect.

The checker executes the actual `Execution.step`; `bounded_finishes`
constructs a finite trace, `bounded_sound` connects it to `Execution.drive`,
and `check_sound` binds the exact supplied initial machine, projection and
claim. Exhaustion is a separate verdict, never a P4 fault. The final
terminal transition consumes budget, so the example needs ten steps.

Clean build and 275 Lean checks passed. Independent probes rejected
budgets 0, 1 and 9 and accepted 10, 11 and 100. Seven altered observations
were rejected: register width/cell count, counter presence/value, local
width/value and fault class. Initial pending parser faults were bound to
the corresponding fault observation, not accepted as a fault-free run.
Tests also cover altered seeds/work, internal errors, wrapping at 255,
and rejecting register seed 256. All three theorem roots depend only on
standard Lean foundations. Review tracked files remained unchanged.

The projection includes completion/message, register width/cells, counter
cells and local width/value, not every machine field. The fixture is a
standalone control fragment, not a validated whole-switch program. Python
integration must reconstruct precisely that experiment. The theorem does
not prove universal Python equivalence, termination or codec correctness.
The concrete hash-map example is runtime checked; `by decide` did not
kernel-reduce it. Artifacts are claims checked by a compiled sound checker,
not standalone kernel-checked proof terms.
