# Python certificate binding review

2026-09-23, independent read-only review of `0d56d9e`.

The initial 48 tests and Lean build/tests passed, but adversarial probes
found defects that those tests did not cover:

1. The observer retained pre-execution register/counter objects. Replacing
   or deleting the final environment binding could still produce an
   accepted claim about the old object. Resolve final bindings instead.
2. A width-7 cell inside a width-8 register lost its cell width in the
   observation, allowing Lean to accept malformed Python state. Reject
   inconsistent widths and malformed bit/counter representations.
3. A successful peer could leave a child running after closing its protocol
   descriptors. Clean up the owned process group on normal exit as well as
   errors/timeouts.
4. Duplicate verdict keys were silently collapsed by JSON parsing. Reject
   duplicates rather than accept contradictory replies.

The integrator fixed all four and added regressions for replacement and
deletion of each binding, inconsistent register cells, successful-peer
descendants and duplicate verdicts. Formatting, lint, types and 55 focused
tests pass. Independent follow-up on those fixes is pending.

Injected production InterpError and ParseError already preserved correct
partial state and tagged completion, and Lean rejected the claims. Apart
from the findings above, the adapter follows the intended fixed-program
boundary: shared syntax, independently executed Python statements, explicit
seeds and Lean checking of the projected result. This is not a kernel proof
of Python execution or a universal equivalence result.
