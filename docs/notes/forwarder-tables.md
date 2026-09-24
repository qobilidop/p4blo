# Constructive bounded forwarder table selection

2026-09-23. Checkpoint 1 of [the accepted table plan](forwarder-table-next.md),
based on `95a784c`. This is installation and lookup, **not** application of
the selected action or a new ingress/pipeline theorem. The runtime, real
Forwarder Program, Python builder and golden are unchanged.

## Exact contract

`ForwarderTables.Config` has the five planned entry sequences: empty, the
canonical `10.0.2.0/24`, the host `10.0.2.2/32`, and both installation orders
of those two routes. Network, host and optional forwarding-default payloads
have independently arbitrary `Fin (2^48)` destination MAC and `Fin 512` port.
Every `Fin (2^32)` query is covered, not just the finite test addresses.

The independent `select` policy uses address equality and the numeric
interval `[167772672, 167772928)`, with host preference. It does not call
`lookup`, the key matcher, `beats`, the executor or authored accessors.
`Decision.result` describes the exact optional action and hit bit. All three
defaults are misses, including explicit forwarding. Absent host override
means the actual program's `drop`; explicit `NoAction` is an actual empty
action, not `Match.action = none`.

`installed_built` proves **actual** `Installed.build` accepts every config.
The accessor's `getD` fallback is consequently unreachable for every member
of the public family. `installed_index`, `installed_entries`,
`installed_default` and the two `installed_other_*` laws characterize the
actual complete map views (including absence of other table keys), actual
index and retained array order. Installation acceptance follows actual
scope/action declarations, literal fitting, key widths/canonicality,
duplicate checking and default checking, not manually fabricated public
installed maps. The existing `Forwarder.index_built` supplies actual Program
index construction. `table_lookup` resolves the exact real declaration.

`lookup_correct` proves actual successful lookup equals that independent
decision for every configuration/query. `order_independent` proves the two
mixed-route installation orders return the same result. `restore_default`
proves passing `none` to `setDefault` restores the program's drop; it cannot
remove this program's default. No original-program host witness is claimed
for optional absent-action dispatch.

Private `consider`/`finish` definitions only name pieces of the *existing*
lookup implementation. The empty/one/two-entry equations prove their
connection to its actual array loop. They are not independent source
semantics, an alternate executor, or assumed correctness callbacks. No
whole-program validity or arbitrary-list/prefix LPM result is claimed.

## Proof engineering and decisions

Confidence is high in the fixed-family semantic contract and medium in this
configuration API's longevity. The family deliberately does not anticipate
arbitrary prefixes or general control-plane programming. Revisit the API
when a second useful route family/application needs composition; do not
silently widen what the current theorem claims.

The accepted feasibility probe's giant symbolic simplification reached
kernel recursion limits. Initial similar attempts here did too. The final
proof separates actual zero/one/two-entry loop equations from a pure natural
quotient/interval lemma, then applies the arithmetic lemma to the 32-bit
matcher. Explicit Boolean equations are retained instead of `simp_all`
rewriting them into unsuitable existential forms. The complete universal
core builds in approximately 3–4 seconds at **default heartbeat and
recursion limits**, with no `sorry`, custom axioms, native-decide proof or
weakened payload/query quantifier.

## Independent executable observations

The test-only `forwarderTables` exporter contains the real Program, complete
Index, actual inputs, complete installed maps and nine actual lookup results
for each of 30 profiles (five shapes × three defaults × two asymmetric
payload sets). It never exports policy-derived expected results. The Python
checker validates its exact inventory, Program against both independent
Python builder and text golden, all Index maps/scopes/declarations, ordered
entries, optional defaults, widths/data, and strict JSON types.

The nine address answers explicitly cover zero, before the network, network
base, host neighbors, the host, network end, after the network and maximum
32-bit address. Membership answers and MAC/port literals are independently
written in both test languages. Native tests check 270 answers, complete
Index/maps and restore-default behavior. Additional native operational
controls cover `/0` and maximum-address `/32`; these are not additional
universal prefix theorems.

Both native and Python tests reject duplicate `/24` and `/32`, noncanonical
network, prefix33, wrong key arity, nonzero priority, undeclared action,
wrong literal width/overflow, wrong table scope, wrong lookup arity and bad
default. These are executable negative examples, not installer completeness
theorems. Python snapshots detach and type-tag the entire installed object,
complete Index, maps and query before every lookup and inspect them after
every operation. First/last-match, false hit, ignored default, type confusion
and state-only corruption faults are retained. A weak return-only observer
explicitly survives the state-only fault before the strong observer rejects
it. The complete native map assertions and this weak control were added
after independent review; final focused/build checks are recorded below.

One ordinary end-to-end packet example anchors overlap selection in the
unchanged full forwarder. Its literal packet answer includes the host MAC,
port3, old destination as Ethernet source, TTL0→255 and final checksum.
This is runtime evidence, not a newly proved action/application composition.

## Adversarial campaign

All source edits were made in the separate worktree
`/Users/qobilidop/my/work/p4blo-forwarder-tables-mutants`, detached at
`95a784c`, with copies of this checkpoint's new modules/fixture and fresh
Lean caches. Candidate runtime and Program were never mutated.

1. **Actual Lean shortest-prefix runtime:** in `ir/P4bloIR/Tables.lean`,
   replace the unique `else prefixLength entry > prefixLength best` with
   `<`. `lake build P4bloIR.Tables` exits0; rebuilding
   `P4blo.ForwarderTables` exits1 at the false network-vs-host call equality
   in `lookup_correct`. This is a compiling runtime mutation rejected by a
   semantic proof, not a differential runtime kill. Logs:
   `/tmp/p4blo-forwarder-tables-lean-shortest-{compile,kill}.log`.
2. **Actual Lean absent-default clearing:** restore the first fault; replace
   `| none => pure decl.defaultAction` by `| none => pure none` in actual
   `setDefault`. Runtime module compiles0; core exits1 in `restore_default`
   because the actual default map contains `none` instead of `some drop`.
   Logs: `/tmp/p4blo-forwarder-tables-lean-clear-default-{compile,kill}.log`.
3. **Valid but wrong fixture payload:** restore runtime; change only the
   low network source port `2`→`6` in `networkData`. `forwarderTables` builds0
   (the universal theorem correctly accepts either fitting data value).
   Native `#eval ForwarderTableTests.run` exits1 at the independent network
   answer; Python `checked_export` of the compiled exporter exits1 at
   independent input identity. This demonstrates wrong authored intent,
   not a false proof or Lean–Python semantic divergence. Logs:
   `/tmp/p4blo-forwarder-tables-wrong-data-{build,native-kill,python-kill}.log`.
4. **Actual Python shortest-prefix runtime:** replace the unique
   `return prefix_length(entry) > prefix_length(best)` with `<` in
   `python/p4blo/interp/tables.py`. The full internal observer rejects
   `network-host/drop/false` at independent selection. Actual packet DRT
   produces a clean mismatch, saved before output assertions; replay under
   the live source fault reproduces it. Python chooses network MAC/port2;
   Lean chooses host MAC/port3. Returned packets otherwise retain the same
   independently expected rewrite/checksum and extern state, with no error
   or diagnostic. Restore the source and identical-input replay agrees.
   Logs: `/tmp/p4blo-forwarder-tables-python-shortest-{live,restored}.log`.

The new retained bundle is
`.artifacts/drt/forwarder-tables-lpm.json`, 28459 bytes, SHA-256
`18dba3145586f62b4e2559fd461342b7ca58c69f7f15b82339b231620f2ecfc4`.
It contains the exact unchanged corpus Program, `packet_case()`'s complete
two-route entries/packet/ingress request, four ports and seed0. This is a
new input, not the prior action TTL-only witness. Byte-identical copies live
in the candidate and isolated campaign tree. A retained monkeypatch test
also exercises the real comparator and requires internal kill, complete
save, exact live outputs and restored replay; no fake Lean is used.

Reconstruct the actual-source runtime campaign, with that one-line Python
fault active, from the isolated tree using `nix develop -c uv run python`:

```python
from pathlib import Path
from p4blo import ir
from p4blo.drt import replay
from p4blo.drt.run import compare_program
from tests.test_lean_forwarder_tables import observe, packet_case, packet_expected
root = Path('/Users/qobilidop/my/work/p4blo-forwarder-tables-mutants')
program = ir.load_text(root / 'tests/corpus/forwarder/forwarder.txtpb')
try:
    observe(program, 'network-host/drop/false')
except AssertionError as error:
    assert str(error) == 'independent selection'
else:
    raise AssertionError('internal observer survived')
binary = Path('/Users/qobilidop/my/work/p4blo-forwarder-tables/ir/.lake/build/bin/p4blo-lean')
report = compare_program(program, [packet_case()], 4, [binary])
bundle = root / '.artifacts/drt/forwarder-tables-lpm.json'
bundle.parent.mkdir(parents=True, exist_ok=True)
replay.save(report, bundle)
assert report.agreed == 0 and len(report.divergences) == 1
assert report.protocol_error is None and report.both_errored == 0
assert replay.load(bundle) == (program, [packet_case()], 4, 0)
live = replay.replay(bundle, [binary])
assert live.agreed == 0 and len(live.divergences) == 1
failure = live.divergences[0]
assert failure.python.outputs == tuple(packet_expected(False))
assert failure.lean.outputs == tuple(packet_expected())
assert failure.python.state == failure.lean.state
for outcome in [failure.python, failure.lean]:
    assert outcome.error is None and outcome.diagnostic is None
```

After restoring the actual source, run `observe(program,
'network-host/drop/false')` and replay the same bundle; require `passed`,
`agreed == 1`, and `both_errored == 0`. Source equality and restored binary
checks are recorded with final gates below.

## Gates and review

All commands below exited0. Run from the implementation worktree with its
Nix environment; no Docker image was built or replaced.

- `nix develop -c scripts/check-lean.sh`: both packages, all default audits
  and native tests, including final complete-map assertions. Log:
  `/tmp/p4blo-forwarder-tables-lean-final.log`. The nine new default theorem
  audits each require exactly `[propext, Classical.choice, Quot.sound]`.
- `nix develop -c uv run pytest -q tests/test_lean_forwarder_tables.py`:
  final 50 passed, including the explicit weak/strong observer control and
  real comparator save/live/restored regression. Log:
  `/tmp/p4blo-forwarder-tables-focused-final.log`.
- `P4BLO_REQUIRE_LEAN=1 nix develop -c uv run pytest tests -k lean_agrees`:
  1517 passed/1728 deselected, before the two final test-only refinements.
  Log: `/tmp/p4blo-forwarder-tables-required.log`.
- `nix develop -c scripts/check.sh`: 3239 passed/5 xfailed/1 skipped, all
  schema/format/lint/type checks pass. The skip is the existing unavailable
  local compile-only XDP image; existing oracle images were only consumed.
  Log: `/tmp/p4blo-forwarder-tables-full.log`. Pytest had already loaded
  before the final native complete-map and Python weak-control refinements,
  so this is **not** described as a broad gate of the later source revision.
  Final focused/native checks cover those refinements; parent integration
  runs the broad gate on the final files.
- Final `uv run ruff format --check`, `uv run ruff check`, and
  `uv run pyright`, each scoped to `tests/test_lean_forwarder_tables.py`,
  pass after the refinements. Logs use the `format-final`, `ruff-final`,
  `pyright-final` suffixes under `/tmp/p4blo-forwarder-tables-`.
- Restored isolated `lake build forwarderTables` and fresh
  `#eval P4blo.ForwarderTableTests.run` pass. Each of the two actual runtime
  sources and two new Lean modules compares byte-identically with candidate
  source: `ir/P4bloIR/Tables.lean`, `python/p4blo/interp/tables.py`,
  `lean/P4blo/ForwarderTables.lean`, and
  `lean/P4blo/ForwarderTableTests.lean`. Candidate runtime/Program diffs are
  empty. All four comparison exit codes were checked separately. The
  isolated Python test helper copy intentionally records the campaign
  revision before the final six-line weak-return control; that test file
  was not a mutated runtime source and is not claimed byte-identical to
  the final candidate. The final candidate's 50 focused tests separately
  exercise that control. Restored exporter and candidate
  baseline/final exporter are byte-identical: 82350 bytes, SHA-256
  `cd34627a55f885e67ff76272fec924446837eaae2e26cdc018d2ece7237ebc42`.
  Captures are `/tmp/p4blo-forwarder-tables-export.json`,
  `/tmp/p4blo-forwarder-tables-final-export.json` and
  `/tmp/p4blo-forwarder-tables-mutant-restored-export.json`.

Independent read-only review is **CLEAR** in
[the review report](reviews/forwarder-tables.md). The reviewer independently
ran all 50 focused tests, native 270 answers/controls and nine fresh audit
queries; checked restored sources/exporter identities and campaign logs;
and source-matched the complete retained packet bundle before reproducing
its restored agreement. Parent integration remains responsible for the
combined broad gate on final merged files.

Next step, after review/integration: checkpoint2's actual `applyTable` proof,
using this constructive lookup result with the committed selected-action
theorem plus real drop/NoAction behavior. No checksum/body continuation or
parser/host API claim is closed here.
