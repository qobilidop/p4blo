# Firewall CRC: real implementation/model mutations

Campaign date: 2026-09-23. Base: `8328127`, isolated worktree
`/Users/qobilidop/my/work/p4blo-firewall-adversarial`, branch
`work/firewall-adversarial`. This tests faults in the actual production
Python CRC and formal Lean CRC, not merely a malformed authored IR program.
Only one implementation is changed at a time; test code, golden IR,
packets and table entries remain unmodified. No intentional fault is
committed. The final change is this report alone.

## Question and result

A consistent but incorrect hash can preserve firewall packet behavior.
The two 4096-bit Bloom arrays only use the low 12 CRC bits. XORing the
CRC32 result with one permutes those array indices, preserving equal-key
and collision relationships. Packet-only connection/collision checks can
therefore pass although the implementation disagrees with its contract.
The independent known answers and full-state comparison detect this
fault. This is a selected experiment, not general mutation adequacy.

## Exact isolated patches

P10, `python/p4blo/externs/crc.py`, inside `crc32`:

```diff
-    return result ^ 0xFFFFFFFF
+    return result ^ 0xFFFFFFFF ^ 1
```

L6, `ir/P4bloIR/Externs.lean`, inside `crc32`:

```diff
 def crc32 (dataWidth value : Nat) : Nat :=
-  fullCRC 32 0x04c11db7 0xffffffff 0xffffffff dataWidth value
+  (fullCRC 32 0x04c11db7 0xffffffff 0xffffffff dataWidth value) ^^^ 1
```

Each patch was applied once with an anchored edit and reversed before
the other patch was applied. `git diff --exit-code` over both files
confirmed the clean boundary between mutations.

## Reproduction commands and independent observations

All commands below run with the working directory set to the worktree
root above. Paths below use the task-specific shell variable `campaign`
only to make the commands readable; it is that absolute path, never a
home/workspace root used as a destructive target.
For a source-only resumption, create a fresh isolated worktree at the
recorded base commit, substitute its absolute path for `campaign`, and
run the commands there. Neither the original worktree nor its caches
are required to regenerate the inputs and observations.

```sh
campaign=/Users/qobilidop/my/work/p4blo-firewall-adversarial
nix develop -c "$campaign/scripts/check-lean.sh"
nix develop -c uv run pytest \
  tests/test_firewall.py::test_known_packets_and_complete_state \
  tests/test_firewall.py::test_independent_crc_indices \
  tests/test_crc.py::test_known_answers -q
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest \
  tests/test_firewall.py -k lean_agrees -q
```

Baseline: both Lean package builds/audits/tests exit 0; the independent
Python baseline is **19 passed**, exit 0; the dedicated Lean firewall
profiles/mutations are **10 passed, 30 deselected**, exit 0. The four-request
connection comparison below reports **4 agreed, 0 diverged, 0 errored**,
exit 0. The existing authored-IR mutants in those ten tests are separate
regressions; they are not the implementation mutants in this campaign.

The common runtime probe uses the committed `connection()` inputs and
expected packet bytes from `tests/test_firewall.py`. It runs the actual
Python production interpreter and compiled Lean executable, asserts the
packet-only observations still equal those independent expectations,
then lets ordinary DRT compare all extern state. This self-contained
command reconstructs the probe solely from tracked repository inputs:

```sh
mkdir -p "$campaign/.artifacts"
replay_name=firewall-python-crc32.json
nix develop -c uv run python - "$campaign/.artifacts/$replay_name" <<'PY'
import sys
from pathlib import Path
from p4blo import arch
from p4blo.drt import replay
from p4blo.drt.run import compare_program, default_lean_binary, run_python
from tests.corpus.tutorial_firewall.tutorial_firewall import build
from tests.test_firewall import connection

steps = connection()
program = build()
loaded = arch.load(program)
assert [tuple(run_python(loaded, s.case, 4)) for s in steps] == [s.outputs for s in steps]
report = compare_program(program, [s.case for s in steps], 4, [default_lean_binary()])
assert report.protocol_error is None and report.both_errored == 0
for d in report.divergences:
    assert d.python.error is None and d.lean.error is None
    assert d.python.diagnostic is None and d.lean.diagnostic is None
    assert d.python.outputs == d.lean.outputs == steps[d.number].outputs
    for side, result in [("Python", d.python), ("Lean", d.lean)]:
        for state in result.state:
            if state.kind == "register":
                assert state.width == 1 and len(state.values) == 4096
                assert all(v in (0, 1) for v in state.values)
                print(d.number, side, state.name, [i for i, v in enumerate(state.values) if v])
print(report.summary())
if report.divergences:
    replay.save(report, Path(sys.argv[1]))
sys.exit(0 if report.passed else 1)
PY
```

The recorded `.artifacts/firewall-hash-probe.py` additionally labels
packet-only passes and prints common output bytes; these diagnostics do
not alter comparison. Invoke it on stdin so imports resolve from the
worktree root:

```sh
nix develop -c uv run python - "$campaign/.artifacts/firewall-python-crc32.json" \
  < "$campaign/.artifacts/firewall-hash-probe.py"
nix develop -c uv run python -m p4blo.drt.replay \
  "$campaign/.artifacts/firewall-python-crc32.json"
```

For the Lean mutant, replace `firewall-python-crc32.json` with
`firewall-lean-crc32.json`. The bundles hold the complete IR and all four
requests from fresh state; replay never relies on surviving interpreter
objects or the generator's random seed.

### P10: production Python mutation

With only P10 applied:

```sh
nix develop -c uv run pytest tests/test_corpus.py -k tutorial_firewall -q
nix develop -c uv run pytest tests/test_crc.py::test_known_answers \
  tests/test_firewall.py::test_independent_crc_indices \
  'tests/test_firewall.py::test_known_packets_and_complete_state[connection]' \
  -q --tb=short
```

The ordinary corpus gate **survives: six passed, exit 0**. That includes
both connection and collision packet vectors, both architecture fate
checks, validation and golden reconstruction. The stronger focused gate
**kills P10: 14 failed, exit 1**: nine CRC known answers, four independent
indices and the connection's complete-state assertion. These are runtime
numeric/state failures, not compile/import failures.

The DRT probe and its live replay each exit 1 with **one agreed, three
diverged, zero shared errors**. All four requests' exact output packets
are unchanged; only register state differs. The first divergent request
is zero-based request 1, the outbound SYN:

| Observation after SYN | Correct Lean | Mutant Python |
|---|---|---|
| `bloom_filter_1` nonzero indices | `[1990]` | `[1990]` |
| `bloom_filter_2` nonzero indices | `[1987]` | `[1986]` |
| Every other cell | zero | zero |
| Output port | 2 | 2 |

The exact shared SYN output is:

```text
000000000022000000000001080045000028000000003f0667ce0a0000010a0000023039005000000002000000005002200000000000
```

The established ACK (request 2) still forwards on port 1, and the unrelated
ACK (request 3) still drops. Both retain the same state-only disagreement.

### L6: formal Lean model mutation

Python is restored first. Before executing any Lean mutant comparison,
build both packages with their default proof audits, but **do not use a
failing `lake test` as a mutant kill**:

```sh
nix develop -c lake +leanprover/lean4:v4.34.0 -d "$campaign/ir" build
nix develop -c lake +leanprover/lean4:v4.34.0 -d "$campaign/lean" build
```

Both builds exit 0, including `ProofAudit` and `UserProofAudit`. Then:

```sh
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest \
  'tests/test_firewall.py::test_lean_agrees_with_independent_firewall_expectations[connection]' \
  tests/test_crc.py::test_lean_agrees_on_crc_known_answers \
  tests/test_crc.py::test_lean_agrees_on_typed_crc_authoring -q --tb=short
```

All **three tests fail, exit 1**, at runtime numeric/state comparisons.
The first failure is the firewall's complete-state assertion. The two
CRC comparisons report three and one divergent requests respectively,
without shared errors. The common connection probe and its live replay
each report **one agreed, three diverged, zero shared errors**, exit 1.
Now correct Python has CRC32 cell 1987 set, while mutant Lean sets 1986;
CRC16 cell 1990 and every output packet remain identical. No build failure
or failing Lean unit test is counted as this detection.

The deliberately weaker packet-only check exits 0 even on the compiled
Lean mutant. Its exact command is:

```sh
nix develop -c uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from p4blo import ir
from p4blo.drt.run import LeanRunner, default_lean_binary
from tests.corpus.tutorial_firewall.tutorial_firewall import build
from tests.test_firewall import connection
with TemporaryDirectory() as directory:
    path = Path(directory) / "firewall.json"
    path.write_text(ir.dump_json(build()))
    with LeanRunner([default_lean_binary()], path, 4) as runner:
        for number, step in enumerate(connection()):
            actual = runner.run(step.case)
            assert actual.error is None and actual.diagnostic is None
            assert actual.outputs == step.outputs
            print(number, [(port, data.hex()) for port, data in actual.outputs])
print("Lean packet-only connection: 4 passed")
PY
```

This check intentionally ignores state; it is an experimental weak oracle,
not a proposed replacement gate. Its four observations are drop, SYN
forward on port 2, established ACK forward on port 1, unrelated ACK drop.

## Artifacts, restoration and conclusion

The saved replay files are:

- `.artifacts/firewall-python-crc32.json`
- `.artifacts/firewall-lean-crc32.json`

Each is **76,260 bytes**, SHA-256
`c547f2999038dae030dfd93402e7e26a73782f0424384fda9633a5ee7e886103`.
They are identical because they contain the same complete input program,
four requests and divergent request indices, not runtime-side-specific
state logs. Which side is wrong depends on the independently applied patch.
They contain no duplicate 8192-cell output arrays. The integrator retains
an exact copy at the ignored local handoff path
`/Users/qobilidop/my/work/p4blo/.artifacts/drt/firewall-crc32.json`, with
the size and SHA-256 above independently verified. No duplicate permanent
fixture is needed because the golden/source, `connection()` fixture and
complete reconstruction command above are already tracked.

Both source faults were restored with inverse patches; `git diff
--exit-code -- python/p4blo/externs/crc.py ir/P4bloIR/Externs.lean` exits 0.
Restoration used these gates, all exiting 0:

```sh
nix develop -c "$campaign/scripts/check-lean.sh"
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest \
  tests/test_crc.py tests/test_firewall.py tests/test_corpus.py \
  -k 'not spectec and not bmv2' -q
nix develop -c env P4BLO_REQUIRE_LEAN=1 uv run pytest tests -k lean_agrees -q
nix develop -c uv run python -m p4blo.drt.replay \
  "$campaign/.artifacts/firewall-python-crc32.json"
nix develop -c uv run python -m p4blo.drt.replay \
  "$campaign/.artifacts/firewall-lean-crc32.json"
git diff --exit-code -- python/p4blo/externs/crc.py ir/P4bloIR/Externs.lean
git diff --check
```

Both Lean packages/audits pass, including **348 specification checks**
and the user package's scalar/API checks. Focused baseline is **110 passed,
27 deselected, no skips**. Both complete saved sequences replay with
**four agreed, zero diverged, zero errors**. The full repository/external
oracle gate was not rerun for this report-only campaign; the focused gate
deliberately deselects external-oracle cases and some names containing
`spectec`, and must not be described as those oracle checks passing.
The subsequently rerun full required differential gate also passes:
**167 passed, 1010 deselected, exit 0**. Independent read-only review
verified the artifact hashes, reconstructed inputs against tracked
`build()`/`connection()`, checked mutation/build/restoration logs and
replayed both restored bundles successfully; no corrections were requested.

The original logs remain locally under `/tmp/p4blo-hash-*.log`: baseline
build/Python/probe/DRT, Python corpus/tests/probe/replay, Lean mutant
build/user-build/tests/packet-only/probe/replay, and restored build/tests/
replays. Their essential results and exact recipes are recorded above;
resumption does not require those temporary logs. Final worktree status
contains this report only, with no remaining production or model diff.

Existing complete-state and numeric-contract coverage kills both selected
mutants, so this round finds no uncovered strong-gate survivor requiring
new production/test code. The packet-only survivors are intentional
evidence of a weaker claim: even full packet sequences, including Bloom
collisions, cannot establish correct hash values or register addresses.
The Lean proof audits passing the wrong CRC is also expected: existing
proofs do not state that CRC32 implements the intended external algorithm.
They retain their scoped structural/semantic claims under the changed
definition. A future CRC refinement theorem needs an independent intended
CRC specification, not a theorem restating the same implementation.

This campaign does not establish universal Python/Lean equivalence, full
mutation coverage, correctness of the P4 oracle, or adversarial assurance
for untested malformed packets. No external oracle or Docker image was
changed or rerun; the report relies on the previously pinned independent
known answers and original-source state evidence for the intended contract.
