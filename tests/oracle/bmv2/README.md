# The BMv2 oracle

The second, optional oracle for [claim 2](../../../docs/design.md#the-four-claims):
the corpus programs, printed to P4 under the v1model shim, replayed on
the reference *implementation* rather than on the specification. p4c's
BMv2 backend compiles the printed program and BMv2's `simple_switch`
runs the same STF vectors `impl/python/p4blo/stf.py` replays on the Python
interpreter. It is built by [`Dockerfile`](Dockerfile), driven by
[`run.py`](run.py) with [`driver.py`](driver.py) inside the container,
and asserted by
[`tests/test_oracle_bmv2.py`](../../test_oracle_bmv2.py), which
skips without Docker or without the image and runs in its own CI job,
[`.github/workflows/oracle-bmv2.yml`](../../../.github/workflows/oracle-bmv2.yml).

It is the *second* oracle: [P4-SpecTec](../README.md) is the first, and
the one that speaks for the specification. This one speaks for what P4
programmers actually run, and the two disagree in useful ways.

## What it checks that P4-SpecTec cannot

- **Longest-prefix matching.** The specification's simulator has no
  longest-prefix rule: `tests/oracle/run.py` has to hand it a priority equal
  to the prefix length, so the *translation* supplies the rule the
  semantics claims (`tests/oracle/README.md`, "The STF dialect"). BMv2's lpm
  tables are real, so `forwarder/lpm_precedence.stf` is decided by the
  switch, from a `table_add ... 0x0a000200/24` the runner writes
  verbatim. This is the main reason the second oracle exists.
- **`const entries` priorities.** `priority/table_entries_priority.stf`
  replays entries the printer emits in descending IR priority, each with
  an explicit `priority = N` under `largest_priority_wins = true`
  (`.agents/decisions.md`, "Printed ternary entries are not const"), and
  BMv2 picks the winner by its own rule rather than by anything this
  repository wrote. The same vector on p4c's own source is the second
  divergence below.
- **Runtime ternary priorities.** `acl/ternary2.stf` installs
  overlapping ternary entries at runtime; BMv2 has the *smaller*
  priority winning, so the runner inverts (below) and the switch, not
  the translation, decides which entry matches.

## What it cannot check

- **`flood`.** The metadata contract's `flood` has no v1model mapping
  (`printer.standard_metadata_binding`), so a program that declares it
  is skipped with that reason. No corpus program declares one today, so
  nothing is skipped in practice.
- **Which input packet an output came from.** This BMv2 build has its
  logging macros compiled out, so there are no per-packet log lines to
  correlate with; the judge compares each port's outputs, in order,
  against that run's `expect` lines (see "Judging" in `run.py`). A
  wrong output that happens to equal a later expectation on the same
  port is therefore not caught here. `tests/test_corpus.py` and the
  differential sweep against Lean check whole outputs per packet.
- **State across a vector that adds entries after a packet.** Entries
  can only be installed before a run's packets, so such a vector takes
  several `simple_switch` runs (below) and a program with registers or
  counters is refused rather than replayed on a fresh switch.
- **Checksums.** The same gap as the first oracle: the shim prints
  empty `MyVerifyChecksum` and `MyComputeChecksum`, so a deliberately
  wrong IPv4 checksum is carried through unchanged
  (`tests/corpus/forwarder/README.md`).

## The pins

Everything the oracle runs comes from three pinned artifacts, all named
in [`Dockerfile`](Dockerfile).

| | |
|---|---|
| p4c (base image) | `ghcr.io/qobilidop/p4lang-builds/p4c@sha256:794edb1682e286792fbf7b1ca5da2ed7be52ddbeab3659a3bbfb4e1906684e48` (`1.2.5.15-noble`; `p4c-bm2-ss` 1.2.5.15, SHA `325e90e`) |
| BMv2 (grafted in) | `ghcr.io/qobilidop/p4lang-builds/bmv2@sha256:3c70f7516440e36a217a7685364a1d1ffb766d0965ab3fbd549f8bbaf7c3cc9d` (`1.15.4-noble`; `simple_switch` 1.15.4) |
| BMv2 source | `behavioral-model-1.15.4.tar.gz`, sha256 `c6236ed842fbb5d2d31a2f49a2b2d6863e858c413178a59963f34b6a1cbe0bd7` |

Both images are pinned by the digest of their multi-architecture index,
so amd64 and arm64 both resolve natively; the official p4c image is
amd64 only and crashed under emulation (`.agents/decisions.md`, "p4c and
BMv2 from Bili's multi-arch builds"). The p4c image carries the
compiler, the BMv2 image the switch, and `COPY --from` grafts the
second's `/usr/local` onto the first. The BMv2 image ships
`simple_switch_CLI` but no Python, so the CLI's modules (`bm_runtime`,
`sswitch_runtime`, `runtime_CLI`, `bmpy_utils`, `sswitch_CLI`) are
generated in the image from the pinned tarball with Ubuntu noble's
`thrift` compiler, whose 0.19.0 matches the `libthrift` the switch
links against.

## Building and running

```
docker build -t p4blo-bmv2 tests/oracle/bmv2                         # a few minutes, then cached
uv run python tests/oracle/bmv2/run.py -v tests/corpus/forwarder/forwarder.txtpb tests/corpus/forwarder/*.stf
uv run pytest tests/test_oracle_bmv2.py -v                     # about 30 seconds for the corpus
```

`run.py` prints the program once, compiles it once in the image, and
replays every vector against that compilation. `--image` or
`$P4BLO_BMV2_IMAGE` names another image. The verdicts are the first
oracle's: **pass**, **fail** (a divergence), **error** (the oracle could
not judge: the compiler rejected the program, a CLI command was refused,
the switch crashed or timed out, Docker failed) and **skip** (`flood`).
The process exits non-zero on any fail or error and prints the exact
`docker run` for the first vector that did not pass. `-v` prints a note
for every line the runner translated and the CLI's output.

Nothing is bind-mounted: the program, the vector and the packets cross
into the container as JSON on stdin and the outputs come back as JSON on
stdout, so a `docker run --rm -i` is the whole interface
(`driver.py`'s docstring has the protocol).

## What the runner translates

`run.py` resolves every `add` and `setdefault` with p4blo's own STF
machinery first (`stf.to_entries`), so names, widths, match kinds and
the presence of a priority are checked exactly as the reference replay
checks them, and renders the command from the resolved entry. What it
has to change on the way:

- **Ternary priorities are inverted as `10000 - priority`**, p4c's own
  inversion in `backends/bmv2/bmv2stf.py`, because STF and p4blo have
  the larger priority winning and BMv2 the smaller
  (p4c's `backends/bmv2/bmv2stf.py`; `.agents/decisions.md`,
  "Entry priority: larger wins, everywhere in the IR"). The CLI takes a
  priority exactly on a table whose BMv2 match type is `ternary`, which
  is exactly when p4blo requires one, and a priority above 10000 is an
  error rather than a silent wrap. lpm and exact entries need no
  translation at all: `value/len` goes to the switch as written.
- **`stack[stack.lastIndex]` is printed back as `stack.last`.** The IR
  has no `.last` node -- it is elaborated into an index by `lastIndex`
  (`docs/p4-spec-coverage.md`) -- and p4c compiles the two spellings
  differently for BMv2: `select(stack.last.f)` becomes the `stack_field`
  key, which `simple_switch` understands, while the index form becomes a
  dynamic `last_stack_index` expression it refuses to load ("Invalid
  entry in parse state key ... bad json"). The rewrite is textual, on
  the printed program, because the printer's output is a golden the
  other oracle and the p4c typecheck share. It affects `acl`, `stacks`
  and `subparser_stack`, which cannot start the switch without it.
- **A vector is cut into runs of `simple_switch`.** The switch reads its
  packets from pcap FIFOs that cannot be paused between packets, so a
  run's entries all go in before its packets: the first `add` after a
  `packet` opens a new run, which repeats the entries installed so far,
  so they accumulate as the vector wrote them. `acl/ternary2.stf` takes
  two runs this way. A fresh switch has fresh registers and counters, so
  a program with extern state that would need more than one run is
  refused with an `error` rather than replayed wrongly.
- **`wait` does nothing** and `no_packet` is kept, not dropped: unlike
  the first oracle, the judge here is strict about leftovers per run, so
  `no_packet` needs no translation to keep its meaning.
- **Table and action names are looked up in the BMv2 JSON**, not
  guessed: p4c prefixes them with the control (`MyIngress.ipv4_lpm`,
  `ingress.setbyte_1`), and the runner matches the IR's block-qualified
  name against the JSON's, failing if it is ambiguous. It also checks
  each key's BMv2 match type against the IR's match kind before writing
  the command.

### Register readback

For programs with persistent state the driver has an optional readback
profile, used by the original tutorial firewall's state observations:
`post_commands` may contain only whole-array `register_read <name>`
commands; `completion_packet` is an exact port and byte sentinel expected
exactly once; and the reply's `registers` are complete arrays parsed from
the whole pinned CLI transcript, with sizes and value ranges checked
against the compiled program. Each observation replays a full sequence
prefix on a fresh switch, then sends a distinct non-stateful sentinel
whose route is known; its observed egress is the barrier before reading.
That argument holds for this pinned build, which starts one ingress
thread and processes input packets in FIFO order, and for a program whose
registers are touched only by ingress. It is not a general quiescence
proof: do not reuse the profile for recirculation, multiple ingress
workers or asynchronous externs without a new completion argument.
Missing or duplicate sentinels, extra diagnostics, truncated or duplicate
arrays and invalid cells all fail. The settling heuristic below remains
relevant to output completeness even with the sentinel in place.

### pcap FIFOs and the settle heuristic

Packets reach the switch the way p4c's own runner sends them, through
`--use-files 0` with one pcap FIFO per port (`portN_in.pcap` in,
`portN_out.pcap` out). `simple_switch` opens the input FIFOs at startup
in `-i` order and blocks on each until a writer appears, so `driver.py`
opens them for writing in the same order, writes the pcap header at
once, and only then talks to the Thrift server. The reader thread merges
its files by timestamp, so a phase's packets are written with
timestamps one second apart in vector order, which fixes the order
across ports. Each FIFO is widened to 1 MiB where the kernel allows it,
since a phase's packets are all written before the switch necessarily
reads any.

There is no signal for "every packet has been processed": this build's
logging macros are compiled out, so there are no per-packet debug lines,
and the Thrift API exposes no port counters. As p4c's runner does with a
flat two-second sleep, the run is called complete once the inputs are
closed, at least two seconds have passed, and the output files have
stopped growing for one second (`MIN_RUN` and `SETTLE` in `driver.py`).
That is a heuristic: a genuinely slower switch would look like a missing
packet, reported as a divergence. It has not happened on the corpus, and
the two bounds are the place to raise if it ever does.

## Results

2026-09-22, at the pins above, on all fifteen corpus vectors: fourteen
pass, one is the divergence below. The whole `tests/test_oracle_bmv2.py`
takes about thirty seconds on an M-series Mac, compilations included.

## The divergence: an out-of-range register read

`register_bounds/bounds.stf` fails, and it is a real disagreement, not a
translation artefact. The program reads a `register<bit<8>>(4)` at an
index a packet names, writes the sum back, and reads the cell again into
a header field:

```
r.read(x, (bit<32>) hdr.h.idx);
r.write((bit<32>) hdr.h.idx, x + hdr.h.val);
r.read(hdr.h.got, (bit<32>) hdr.h.idx);
```

p4blo's closed behavior (`docs/arch-supports.md`, "Extern families";
`impl/python/p4blo/arch/externs/register.py`; `spec/arch/P4bloArch/Externs.lean`) is that a
read at or beyond `size` **yields zero** and a write there is ignored.
BMv2 agrees about the write and not about the read: in
`targets/simple_switch/primitives.cpp`, `register_read` on an
out-of-range index logs an error and **returns without touching the
destination**, so `hdr.h.got` keeps whatever the parser put there.

The two vectors that disagree are exactly the ones whose out-of-range
packet carries a non-zero third byte:

| line | packet | p4blo (and the vector) | BMv2 |
|---|---|---|---|
| 46 | `04 07 ff` | `04 07 00` | `04 07 ff` |
| 52 | `ff 01 ff` | `ff 01 00` | `ff 01 ff` |

The third out-of-range packet, `04 07 00` at line 48, passes on both,
because the byte that BMv2 leaves alone is already zero -- which is what
makes the diagnosis certain.

Nothing here says p4blo is wrong. The P4 specification leaves an
out-of-bounds `register` access implementation-defined, and p4blo's
choice is a closed behavior written down and implemented twice. What the
oracle does correct is `tests/corpus/register_bounds/README.md`, which says
the vectors assert "p4blo's, which is BMv2's": they are not BMv2's. That
file and `docs/ir-semantics.md` are outside this directory's scope; the
divergence is carried here and in `tests/test_oracle_bmv2.py` as a
strict `xfail`, so the day either side changes, the test says so.

## The second divergence: p4c's const-entry numbering

`test_original_priority_program_on_bmv2` compiles p4c's own
`table-entries-priority-bmv2.p4` (the pinned copy under
`tests/frontend/p4c/`) instead of the printed golden and replays
`priority/table_entries_priority.stf` on it, capturing ports 0 to 3. It
fails, and it is a real disagreement about what the source means, not a
translation artefact:

| vector line | packet | p4blo, P4-SpecTec and the vector | BMv2 from p4c's source |
|---|---|---|---|
| 29 | `02 1001 00 00 b0` | port 1 | port 3 |
| 34 | `03 1181 00 00 b0` | port 1 | port 3 |

p4c's BMv2 backend (`backends/bmv2/common/control.h`,
`convertTableEntries`) numbers const entries with a running counter,
annotated ones taking their `@priority`, and BMv2 lets the smaller number
win, so the third entry, `@priority(1)`, beats the first, `@priority(3)`.
The language specification (P4 1.2.5 section 14.2.1.4, mechanized as
P4-SpecTec's `$set_priorities_of_tableEntryListIR`) does not read the
annotation, numbers entries without a `priority =` by position, 3, 2, 1,
and has the larger win by default, so the first entry wins; P4-SpecTec, run on p4c's unedited
program and unedited STF file, outputs both packets on port 1 and fails
p4c's expectations of port 3. p4blo follows the specification
(`.agents/decisions.md`, "Entry priority"); the derivation is in
`tests/corpus/priority/README.md`.

The printed golden passes on BMv2, because the printer states each
priority and `largest_priority_wins = true` explicitly and p4c honours
both. The strict `xfail` is restricted to `KnownBMv2PriorityDisagreement`,
raised only for that vector, status `fail` and the exact four-line
mismatch; an oracle error or any other answer fails the test.
