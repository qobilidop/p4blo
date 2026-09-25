"""Which of P4-SpecTec's rules p4blo's inputs make its simulator fire.

    python3 tests/oracle/coverage.py build            # once per pin, in the oracle env
    uv run python tests/oracle/coverage.py [--inputs DIR]... [--check]

p4blo claims to share a semantic surface with P4's elaborated IL. The honest
statement of that surface is the set of SpecTec dynamic-semantics rules that
p4blo's inputs exercise when the simulator runs them. This module measures
it and writes tests/oracle/spectec-coverage.json, keyed by the names of the
rule inventory tests/oracle/spectec-rules.json so the two fixtures join.
tests/external/test_spectec_coverage.py checks the report against the hand-written
exclusions in tests/oracle/spectec-coverage-exclusions.json.

What P4-SpecTec measures, at the pinned commit
----------------------------------------------

`p4spectec cover-sim spec -arch v1model -i p4c/p4include -p4-dir D -stf-dir E
-cov FILE [-instr | -dangling] [-e EXCL] [-patch-dir P]` (p4spec/bin/main.ml)
collects every `.p4` under the `-p4-dir`s that includes <v1model.p4>, pairs
it with every `.stf` under the `-stf-dir`s whose directory relative to its
`-stf-dir` is the program's stem (`D/.../prog.p4` with `E/prog/*.stf`), or
that sits beside it with the same stem (p4spec/lib/util/test.ml,
`p4_matches_stf`), simulates every pair in one process and writes one
aggregate report. `-e` names `.exclude` files
listing programs to skip; `-patch-dir` substitutes same-named files. The
flags are `-instr` and `-dangling`, with a dash; written bare, as the help
text suggests, they are taken for spec paths.

The simulator does not run the rules as written. It runs the "structured"
form of the spec (SL, p4spec/lib/pass/structure): each relation's rules,
and each function's clauses, merged into one decision tree of instructions
(case analyses, lets, ifs, premise calls, and a `Result`/`Return` leaf per
rule or clause). Both coverage modes count those instructions:

- instruction coverage (`-instr`): which instructions executed at least
  once. The report prints each definition's source region and then its tree
  with `+` or `-` per instruction, headed by a total such as
  `;; Instruction coverage: 4384/14475 (30.29%)`. It names no rule, and it
  prints neither instruction ids nor instruction regions.
- dangling coverage (`-dangling`): only the fall-through branches of
  partial case analyses, the ones a test generator wants to reach, printed
  as `iid Hit_likely|Hit_unlikely|Miss origin paths`. It says nothing about
  which rules held.

So neither output can be mapped to rule names. The structuring pass does
keep each instruction's source region, and a rule's `Result` leaf carries
the region of that rule's conclusion. This module therefore builds a small
probe (tests/oracle/coverage_probe.ml) against the checkout's own library sources, in a
separate build directory (the checkout is not touched): it registers an
instrumentation handler on the same hook (`Inst.Hook`, `on_instr`) that
`-instr` uses, runs every pair through the same `run_stf_test`, and prints
each instruction's id, kind, enclosing definition, parent and region, and
per vector the execution count of every instruction and the number of
entries into every relation and function (`on_rel_enter`, `on_func_enter`,
which also fire for builtins that have no instructions). The probe runs
with the simulator's result cache off, so that a later vector re-executes
what an earlier one computed and per-vector counts are honest; the union
over all vectors is the same either way. Every run also invokes the stock
`cover-sim -instr` on the same inputs and requires its headline total, and
the hit and total counts of every definition, to equal the probe's, so the
probe cannot drift from what P4-SpecTec itself
reports.

How instructions become rule names
----------------------------------

A rule is hit when its leaf executed: the `Result` instruction whose region
lies in the rule's source span (from the `rule` line to the line before the
next declaration or closing brace). Two corrections are needed:

- A `Result` that is the whole block of a premise call with no iteration
  premises is never executed; the interpreter tail-calls the premise
  instead (interp-sl/interp.ml, `eval_rule_instr`). Such a leaf counts as
  hit when its premise instruction executed. This over-approximates only
  when the tail-called premise fails: the failure raises into the caller's
  rule instruction, which backtracks to its next alternative, so the leaf
  is credited although the rule did not hold. An independent check that
  recorded the interpreter's real tail calls found no such credit over the
  corpus.
- A rule with neither outputs nor path premises gets the relation
  signature's region. Its leaf is attributed to the nearest enclosing
  instruction whose region lies in a rule span, and the report says so
  (`"via": "ancestor"`). That enclosing instruction is often a case
  analysis shared with a sibling rule, which then takes the credit: in
  5-typing, `CallableType_wf/actionTypeIR` holds the leaves of two other
  rules. No in-scope rule needs it at this pin, and
  tests/external/test_spectec_coverage.py fails if one ever does, or has other
  than one leaf outside the named merges below.

Rules with identical premises and conclusions are merged into one leaf by
the structuring pass, which keeps one rule's region; the others have no leaf
and are reported with `"leaves": 0`. At this pin that happens to the
`.apply` abort rules of the parser and control callees, merged into the
table callee's (`Callee_eval/abort`).

A rule group is hit when one of its rules is; a relation or function when
it was entered, wherever that happened, constant folding during typing
included. Syntax productions have no dynamic meaning and are left out.
Definitions the inventory does not list, which are those of 9-arch, are
reported under `outside_inventory`, flagged by section. Only 8-dynamic and
3-operations are in scope; the exclusions test enforces their rules and
functions. The other sections are kept, since typing and instantiation run
on every program too, and a function of theirs that an in-scope file names
is flagged `called_in_scope`, found statically, which says what widening
the scope to the functions the dynamic semantics calls would cost.

A hit rule is exercised, not verified equivalent: the simulator ran it on
one of p4blo's printed programs, which says nothing about whether p4blo's
own semantics agrees with it beyond what the oracle tests check.

Inputs
------

By default the inputs are every corpus program (`tests/corpus/*/*.txtpb`)
and every example (`tests/examples/*/*.txtpb`), printed through the v1model
shim and with their vectors translated exactly as tests/oracle/run.py does,
and a fixed set of generated programs, `GENERATED_SEEDS` of
tests/oracle/generated.py, materialized as its oracle test materializes
them. The seeds were chosen greedily from a pool of 750 (seeds 0 to 399,
and the parser and parser-condition seeds up to 2399 and 1199, the two
families whose programs vary most): each adds the most in-scope items the
corpus and the seeds before it had not hit, and together the 18 hit every
item the pool hits. A change to
the generators changes what the seeds name, so it regenerates this report.
`--inputs DIR` (repeatable) adds directories of `.p4`/`.stf` pairs in
P4-SpecTec's own convention above, already in the simulator's STF dialect;
the report records them, and `--check` reuses the recorded ones.

Run time on an M-series Mac: the probe build takes about ten seconds of
wall time once per pin. A regeneration over the corpus, example and
generated vectors, 93 in all, runs the probe and the stock cross-check side
by side, about forty seconds, spec elaboration included.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "tests" / "oracle" / "spectec-coverage.json"
INVENTORY = ROOT / "tests" / "oracle" / "spectec-rules.json"
BUILD_SCRIPT = ROOT / "tests" / "oracle" / "build.sh"
DEFAULT_ORACLE_DIR = Path.home() / ".cache" / "p4blo" / "p4-spectec"
IN_SCOPE = ("3-operations", "8-dynamic")
# Items whose kind has a dynamic meaning; syntax productions have none.
KINDS = ("dec", "relation", "rule", "rulegroup")
SWITCH = "5.1.0"  # tests/oracle/build.sh's opam switch
TIMEOUT_SECONDS = 1800


# ---------------------------------------------------------------------------
# The probe
# ---------------------------------------------------------------------------

# The probe's source, beside this file. The instruction walk mirrors
# p4spec/lib/coverage/instr/single.ml (`Cover.init_instr`), including not
# descending into a debug instruction, so that the totals agree with
# `cover-sim -instr`.
PROBE_SOURCE = Path(__file__).with_name("coverage_probe.ml")

PROBE_DUNE = "(executable\n (name probe)\n (libraries p4spectec))\n"
# A dune project of its own whose `lib` is a symlink to the checkout's library
# sources: dune builds into this directory and only reads the checkout. The
# package stanza is there because the library declares public names.
PROBE_PROJECT = "(lang dune 3.7)\n(using menhir 2.0)\n(package (name p4spectec))\n"


def pinned_commit() -> str:
    """The commit tests/oracle/build.sh pins, the single source of the pin."""
    for line in BUILD_SCRIPT.read_text(encoding="utf-8").splitlines():
        if line.startswith("P4_SPECTEC_COMMIT="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"{BUILD_SCRIPT} has no P4_SPECTEC_COMMIT line")


def oracle_root(environ: dict[str, str] | None = None) -> Path:
    """The P4-SpecTec checkout, located as tests/oracle/run.py locates it."""
    env = os.environ if environ is None else environ
    if env.get("P4BLO_ORACLE_BIN"):
        return Path(env["P4BLO_ORACLE_BIN"]).expanduser().resolve().parent
    return Path(env.get("P4BLO_ORACLE_DIR") or DEFAULT_ORACLE_DIR).expanduser().resolve()


def checkout_problem(root: Path) -> str | None:
    """Why `root` is not a checkout built at the pin, or None."""
    stamp = root / ".p4blo-built"
    if not (root / "p4spectec").is_file() or not stamp.is_file():
        return f"no P4-SpecTec build at {root}; tests/oracle/build.sh builds one"
    # The stamp is the commit and the digest of the applied patches; the
    # probe measures the spec's rules, which no patch touches.
    built = stamp.read_text(encoding="utf-8").split()[0]
    if built != pinned_commit():
        return f"{root} is built at {built}, not at the pinned {pinned_commit()}"
    return None


def probe_dir(root: Path) -> Path:
    """Where the probe is built: beside the checkout, never inside it."""
    override = os.environ.get("P4BLO_COVERAGE_PROBE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return root.parent / "spectec-coverage-probe"


def probe_stamp() -> str:
    """What a built probe must match: the pin and the probe's own source."""
    source = PROBE_SOURCE.read_text(encoding="utf-8")
    digest = hashlib.sha256((source + PROBE_DUNE + PROBE_PROJECT).encode()).hexdigest()
    return f"{pinned_commit()} {digest[:16]}"


def probe_binary(root: Path) -> Path:
    return probe_dir(root) / "_build" / "default" / "probe" / "probe.exe"


def probe_problem(root: Path) -> str | None:
    """Why the probe cannot run, or None when it is built for this pin."""
    stamp = probe_dir(root) / "stamp"
    if not probe_binary(root).is_file() or not stamp.is_file():
        return (
            "the coverage probe is not built: run `python3 tests/oracle/coverage.py build` "
            "where tests/oracle/build.sh runs"
        )
    if stamp.read_text(encoding="utf-8").strip() != probe_stamp():
        return "the coverage probe is stale: rerun `python3 tests/oracle/coverage.py build`"
    return None


def build_probe(root: Path) -> Path:
    """Write the probe's sources and build them with the oracle's dune."""
    problem = checkout_problem(root)
    if problem is not None:
        raise SystemExit(problem)
    target = probe_dir(root)
    (target / "probe").mkdir(parents=True, exist_ok=True)
    (target / "dune-project").write_text(PROBE_PROJECT, encoding="utf-8")
    (target / "probe" / "dune").write_text(PROBE_DUNE, encoding="utf-8")
    shutil.copyfile(PROBE_SOURCE, target / "probe" / "probe.ml")
    link = target / "lib"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(root / "p4spec" / "lib", target_is_directory=True)
    (target / "stamp").unlink(missing_ok=True)
    # The Makefile's own invocation, so no `eval $(opam env)` is needed.
    command = ["opam", "exec", f"--switch={SWITCH}", "--", "dune", "build", "./probe/probe.exe"]
    if shutil.which("opam") is None:
        raise SystemExit("opam is not on the path; run this where tests/oracle/build.sh runs")
    result = subprocess.run(command, cwd=target, check=False)
    if result.returncode != 0 or not probe_binary(root).is_file():
        raise SystemExit(f"building the probe failed: {' '.join(command)} in {target}")
    (target / "stamp").write_text(probe_stamp() + "\n", encoding="utf-8")
    return probe_binary(root)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


# Seeds of tests/oracle/generated.py measured beside the corpus; see "Inputs".
GENERATED_SEEDS = (
    6,
    21,
    22,
    47,
    103,
    151,
    176,
    192,
    263,
    457,
    495,
    751,
    855,
    1017,
    1471,
    1647,
    1687,
    2111,
)


@dataclass
class Program:
    """One program and its vectors, as the simulator reads them."""

    id: str
    source: str  # repository-relative where it came from
    p4: Path
    vectors: list[Path] = field(default_factory=list)


def materialize_corpus(stage: Path) -> list[Program]:
    """Print every corpus program and example, and translate its vectors,
    into `stage` in the layout `cover-sim` reads: `p4/<id>.p4` beside
    `stf/<id>/<vector>.stf`."""
    # The adapter imports the p4blo package; kept local so that `build`
    # runs with nothing but a Python interpreter.
    sys.path.insert(0, str(ROOT))
    from p4blo import ir, stf
    from p4blo.arch import v1model
    from tests.oracle import run as oracle_run

    programs: list[Program] = []
    sources = [
        ("corpus", sorted((ROOT / "tests" / "corpus").glob("*/*.txtpb"))),
        ("examples", sorted((ROOT / "tests" / "examples").glob("*/*.txtpb"))),
    ]
    for group, paths in sources:
        for txtpb in paths:
            ident = f"{group}-{txtpb.parent.name}"
            index = ir.Index.build(ir.load_text(txtpb))
            p4 = stage / "p4" / f"{ident}.p4"
            p4.parent.mkdir(parents=True, exist_ok=True)
            p4.write_text(v1model.print_program(index.program, index=index), encoding="utf-8")
            program = Program(ident, txtpb.relative_to(ROOT).as_posix(), p4)
            for vector in sorted(txtpb.parent.glob("*.stf")):
                try:
                    translated, _notes = oracle_run.translate(vector.read_text(), index)
                except stf.StfError as e:
                    raise SystemExit(f"{vector}: p4blo cannot resolve the vector: {e}") from e
                out = stage / "stf" / ident / vector.name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(translated, encoding="utf-8")
                program.vectors.append(out)
            if program.vectors:
                programs.append(program)
    return programs


def materialize_generated(stage: Path, seeds: Iterable[int]) -> list[Program]:
    """Materialize seeds of tests/oracle/generated.py beside the corpus: the
    program printed as its oracle test prints it, and each vector, whose
    `expect` lines are what Python did, translated as the corpus's are."""
    sys.path.insert(0, str(ROOT))
    from tests.oracle import generated
    from tests.oracle import run as oracle_run

    programs: list[Program] = []
    for seed in seeds:
        drawn = generated.materialize(seed)
        ident = f"generated-{seed:05d}-{drawn.family}"
        prepared = generated.prepare(drawn, stage / "prepared" / ident)
        p4 = stage / "p4" / f"{ident}.p4"
        p4.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(prepared.p4, p4)
        program = Program(ident, f"tests/oracle/generated.py seed {seed}", p4)
        for vector in prepared.vectors:
            translated, _notes = oracle_run.translate(vector.read_text(), prepared.index)
            out = stage / "stf" / ident / vector.name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(translated, encoding="utf-8")
            program.vectors.append(out)
        programs.append(program)
    return programs


def _includes_v1model(p4: Path) -> bool:
    text = p4.read_text(encoding="utf-8", errors="replace")
    return "#include <v1model.p4>" in text or '#include "v1model.p4"' in text


def collect_pairs(directory: Path) -> list[Program]:
    """The `.p4`/`.stf` pairs of an input directory, paired the way
    `cover-sim` pairs them (p4spec/lib/util/test.ml): a vector belongs to a
    program when its directory relative to `directory` is the program's
    stem, or when it sits beside the program with the same stem. Programs that do not
    include v1model.p4 are skipped by `cover-sim`, so they are refused here
    rather than silently measured by one side only."""
    base = directory.resolve()

    def files(suffix: str) -> list[str]:
        # The simulator's walk skips directories named `include`.
        found: list[str] = []
        for path in sorted(base.rglob(f"*{suffix}")):
            relative = path.relative_to(base)
            if "include" in relative.parts[:-1]:
                continue
            found.append(relative.as_posix())
        return found

    stfs = files(".stf")
    programs: list[Program] = []
    try:
        shown = base.relative_to(ROOT).as_posix()
    except ValueError:
        shown = base.as_posix()
    for relative in files(".p4"):
        stem = Path(relative).name.removesuffix(".p4")
        parent = Path(relative).parent.as_posix()
        vectors = [
            base / s
            for s in stfs
            if Path(s).parent.as_posix() == stem
            or (Path(s).parent.as_posix() == parent and Path(s).name.removesuffix(".stf") == stem)
        ]
        if not vectors:
            continue
        p4 = base / relative
        if not _includes_v1model(p4):
            raise SystemExit(f"{p4} does not include v1model.p4; cover-sim would skip it")
        ident = f"{shown}:{relative.removesuffix('.p4')}"
        programs.append(Program(ident, f"{shown}/{relative}", p4, vectors))
    if not programs:
        raise SystemExit(f"{directory} holds no .p4/.stf pairs")
    return programs


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@dataclass
class Instr:
    iid: int
    kind: str
    origin: str
    parent: int
    file: str  # relative to spec/
    line: int
    tail: bool


@dataclass
class Measurement:
    """What the probe printed, joined back to the inputs."""

    instrs: dict[int, Instr]
    defs: list[tuple[str, str, str, int]]  # kind, name, file, line
    vectors: list[tuple[str, str]]  # program id, verdict
    hits: list[dict[int, int]]  # per vector: iid -> executions
    calls: list[dict[tuple[str, str], int]]  # per vector: (kind, name) -> entries


def run_probe(root: Path, programs: list[Program]) -> Measurement:
    pairs: list[str] = []
    owner: dict[tuple[str, str], str] = {}
    for program in programs:
        for vector in program.vectors:
            pairs += [str(program.p4), str(vector)]
            owner[(str(program.p4), str(vector))] = program.id
    with tempfile.TemporaryDirectory(prefix="p4blo-coverage-") as tmp:
        out = Path(tmp) / "probe.tsv"
        command = [str(probe_binary(root)), str(out), "spec", "p4c/p4include", *pairs]
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
        if result.returncode != 0 or not out.is_file():
            raise SystemExit(f"the probe failed ({result.returncode}):\n{result.stderr[-4000:]}")
        text = out.read_text(encoding="utf-8")
    measurement = Measurement({}, [], [], [], [])
    for line in text.splitlines():
        tag, *fields = line.split("\t")
        if tag == "I":
            iid, kind, origin, parent, file, number, tail = fields
            measurement.instrs[int(iid)] = Instr(
                int(iid),
                kind,
                origin,
                int(parent),
                file.removeprefix("spec/"),
                int(number),
                tail == "1",
            )
        elif tag == "D":
            kind, name, file, number = fields
            measurement.defs.append((kind, name, file.removeprefix("spec/"), int(number)))
        elif tag == "P":
            index, p4, stf, verdict = fields
            assert int(index) == len(measurement.vectors)
            measurement.vectors.append((owner[(p4, stf)], verdict))
            measurement.hits.append({})
            measurement.calls.append({})
        elif tag == "H":
            index, iid, count = fields
            measurement.hits[int(index)][int(iid)] = int(count)
        elif tag == "C":
            index, kind, name, count = fields
            measurement.calls[int(index)][(kind, name)] = int(count)
    if len(measurement.vectors) != len(pairs) // 2:
        raise SystemExit("the probe did not report every vector")
    broken = [v for v, verdict in measurement.vectors if verdict == "syntax"]
    if broken:
        raise SystemExit(f"the simulator could not load {sorted(set(broken))}")
    return measurement


STOCK_TOTAL = re.compile(r"^;; Instruction coverage: (\d+)/(\d+) ")
STOCK_DEF = re.compile(r"^;; spec/(\S+?):(\d+)\.")
STOCK_DEBUG = re.compile(r"^[+-] +\d+\. Debug: ")


@dataclass
class Stock:
    """What `cover-sim -instr` reports: (hit, total) instructions, overall
    and per definition, the latter keyed by the definition's file and line."""

    total: tuple[int, int]
    per_def: dict[tuple[str, int], tuple[int, int]]


def parse_stock(text: str) -> Stock:
    """The headline and, per `;; spec/FILE:LINE.COL-...` section, the lines
    marked `+` (hit) or `-` (not hit), one per instruction. A debug
    instruction's inner instruction is printed on the next line
    (coverage/instr/log.ml) but, as in the probe's walk, not counted."""
    lines = text.splitlines()
    match = STOCK_TOTAL.match(lines[0] if lines else "")
    if match is None:
        raise SystemExit(f"unexpected cover-sim header: {lines[:1]!r}")
    per_def: dict[tuple[str, int], tuple[int, int]] = {}
    current: tuple[str, int] | None = None
    after_debug = False
    for line in lines[1:]:
        found = STOCK_DEF.match(line)
        if found is not None:
            current = (found.group(1), int(found.group(2)))
            per_def.setdefault(current, (0, 0))
        elif line[:2] in ("+ ", "- ") and current is not None:
            if not after_debug:
                hit, total = per_def[current]
                per_def[current] = (hit + (line[0] == "+"), total + 1)
            after_debug = STOCK_DEBUG.match(line) is not None
            continue
        after_debug = False
    return Stock((int(match.group(1)), int(match.group(2))), per_def)


def run_stock(root: Path, p4_dirs: list[Path], stf_dirs: list[Path]) -> Stock:
    """`cover-sim -instr` on the same inputs."""
    with tempfile.TemporaryDirectory(prefix="p4blo-coverage-") as tmp:
        cov = Path(tmp) / "instr.cov"
        command = ["./p4spectec", "cover-sim", "spec", "-arch", "v1model", "-i", "p4c/p4include"]
        for d in p4_dirs:
            command += ["-p4-dir", str(d)]
        for d in stf_dirs:
            command += ["-stf-dir", str(d)]
        command += ["-cov", str(cov), "-instr"]
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
        if result.returncode != 0 or not cov.is_file():
            raise SystemExit(f"cover-sim failed ({result.returncode}):\n{result.stderr[-4000:]}")
        return parse_stock(cov.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# From instructions to the inventory's names
# ---------------------------------------------------------------------------

# A line that starts a declaration or closes a group ends the span of the
# rule before it.
DECLARATION = re.compile(r"^\s*(syntax|relation|rule|rulegroup|dec|def|var|})(\s|$)")


FUNCTION_NAME = re.compile(r"\$[A-Za-z_][A-Za-z0-9_']*")


def called_in_scope(spec: Path, items: list[dict[str, Any]]) -> set[str]:
    """The functions the in-scope sections name, statically: every `$name`
    written in a file of 3-operations or 8-dynamic outside the line that
    declares it. A function of another section that the dynamic semantics
    calls is part of what it runs, whichever section defines it."""
    declared = {(str(i["file"]), int(i["line"])) for i in items if i["kind"] == "dec"}
    names: set[str] = set()
    for section in IN_SCOPE:
        for path in sorted((spec / section).rglob("*.watsup")):
            file = path.relative_to(spec).as_posix()
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if (file, number) not in declared:
                    names.update(FUNCTION_NAME.findall(line))
    return names


def spans(spec: Path, items: list[dict[str, Any]]) -> dict[tuple[str, int], tuple[int, int]]:
    """(file, line) of every rule and rule group -> its (first, last) line."""
    result: dict[tuple[str, int], tuple[int, int]] = {}
    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if item["kind"] in ("rule", "rulegroup"):
            by_file[item["file"]].append(item)
    for file, members in by_file.items():
        lines = (spec / file).read_text(encoding="utf-8").splitlines()
        starts = [n for n, text in enumerate(lines, start=1) if DECLARATION.match(text)]
        for item in members:
            first = int(item["line"])
            if item["kind"] == "rule":
                later = [n for n in starts if n > first]
                last = later[0] - 1 if later else len(lines)
            else:
                # A group runs to its closing brace in column one.
                closing = [n for n in range(first + 1, len(lines) + 1) if lines[n - 1] == "}"]
                last = closing[0] if closing else len(lines)
            result[(file, first)] = (first, last)
    return result


def _key(item: dict[str, Any]) -> tuple[str, str, str, int]:
    return (str(item["kind"]), str(item["name"]), str(item["file"]), int(item["line"]))


def attribute(
    measurement: Measurement,
    items: list[dict[str, Any]],
    span: dict[tuple[str, int], tuple[int, int]],
) -> tuple[dict[tuple[str, str, str, int], list[tuple[int, str]]], list[int]]:
    """Each rule's leaves, as (iid, how it was attributed), and the leaves
    that no rule span contains."""
    rules_by_file: dict[str, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
    for item in items:
        if item["kind"] == "rule":
            first, last = span[(item["file"], int(item["line"]))]
            rules_by_file[item["file"]].append((first, last, item))

    def rule_at(instr: Instr) -> dict[str, Any] | None:
        for first, last, item in rules_by_file.get(instr.file, []):
            if first <= instr.line <= last:
                return item
        return None

    leaves: dict[tuple[str, str, str, int], list[tuple[int, str]]] = defaultdict(list)
    stray: list[int] = []
    for instr in measurement.instrs.values():
        if instr.kind != "result":
            continue
        owner, via = rule_at(instr), "region"
        cursor = instr
        while owner is None and cursor.parent in measurement.instrs:
            cursor = measurement.instrs[cursor.parent]
            owner, via = rule_at(cursor), "ancestor"
        if owner is None:
            stray.append(instr.iid)
        else:
            leaves[_key(owner)].append((instr.iid, via))
    return leaves, stray


def leaf_fired(measurement: Measurement, iid: int, hits: dict[int, int]) -> bool:
    """Whether a rule's leaf fired in one vector, counting a tail call."""
    if hits.get(iid):
        return True
    parent = measurement.instrs.get(measurement.instrs[iid].parent)
    return bool(parent and parent.kind == "rule" and parent.tail and hits.get(parent.iid))


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


def cross_check(measurement: Measurement, per_origin: dict[str, list[int]], stock: Stock) -> None:
    """Every definition's hit and total instructions, as the probe counts
    them, equal what `cover-sim -instr` prints for it; totals alone could
    hide two errors that cancel."""
    where: dict[str, tuple[str, int]] = {}
    for _kind, name, file, line in measurement.defs:
        if name in where and where[name] != (file, line):
            raise SystemExit(f"two definitions are named {name!r}; the cross-check needs one")
        where[name] = (file, line)
    probe = {where[name]: (hit, total) for name, (hit, total) in per_origin.items()}
    stocked = {key: value for key, value in stock.per_def.items() if value[1]}
    if probe != stocked:
        differ = sorted(
            f"{file}:{line}: probe {probe.get((file, line))}, cover-sim {stocked.get((file, line))}"
            for file, line in probe.keys() | stocked.keys()
            if probe.get((file, line)) != stocked.get((file, line))
        )
        raise SystemExit(
            "the probe and cover-sim disagree per definition:\n" + "\n".join(differ[:20])
        )


def build_report(
    root: Path,
    programs: list[Program],
    extra: list[str],
    measurement: Measurement,
    stock: Stock,
) -> dict[str, Any]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    commit = pinned_commit()
    if inventory["commit"] != commit:
        raise SystemExit(f"{INVENTORY} is at {inventory['commit']}, not the pinned {commit}")
    items = [i for i in inventory["items"] if i["kind"] in KINDS]
    span = spans(root / "spec", items)
    leaves, stray = attribute(measurement, items, span)
    called = called_in_scope(root / "spec", items)
    n = len(measurement.vectors)

    # Instruction universe per definition and per rule span.
    universe = measurement.instrs
    union = {iid for hits in measurement.hits for iid in hits if iid in universe}
    if (len(union), len(universe)) != stock.total:
        raise SystemExit(
            f"the probe counts {len(union)}/{len(universe)} instructions but cover-sim "
            f"reports {stock.total[0]}/{stock.total[1]}; the probe no longer measures what "
            "P4-SpecTec does"
        )
    per_origin: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for instr in universe.values():
        per_origin[instr.origin][1] += 1
        per_origin[instr.origin][0] += instr.iid in union
    cross_check(measurement, per_origin, stock)

    def in_span(item: dict[str, Any]) -> list[int]:
        first, last = span[(item["file"], int(item["line"]))]
        chosen = [
            i for i in universe.values() if i.file == item["file"] and first <= i.line <= last
        ]
        return [sum(i.iid in union for i in chosen), len(chosen)]

    def calls_of(kind: str, name: str) -> tuple[int, int]:
        total = sum(calls.get((kind, name), 0) for calls in measurement.calls)
        vectors = sum(1 for calls in measurement.calls if calls.get((kind, name), 0))
        return total, vectors

    rows: list[dict[str, Any]] = []
    rule_vectors: dict[tuple[str, str, str, int], set[int]] = {}
    for item in items:
        if item["kind"] != "rule":
            continue
        fired = {
            v
            for v, hits in enumerate(measurement.hits)
            for iid, _via in leaves.get(_key(item), [])
            if leaf_fired(measurement, iid, hits)
        }
        rule_vectors[_key(item)] = fired
    for item in items:
        row: dict[str, Any] = {k: item[k] for k in ("kind", "name", "section", "file", "line")}
        if item["kind"] == "rule":
            mine = leaves.get(_key(item), [])
            fired = rule_vectors[_key(item)]
            row |= {"hit": bool(fired), "vectors": len(fired), "leaves": len(mine)}
            if any(via == "ancestor" for _, via in mine):
                row["via"] = "ancestor"
            row["instructions"] = in_span(item)
        elif item["kind"] == "rulegroup":
            first, last = span[(item["file"], int(item["line"]))]
            members = [
                key for key in rule_vectors if key[2] == item["file"] and first < key[3] <= last
            ]
            fired = set().union(*(rule_vectors[k] for k in members)) if members else set()
            row |= {
                "hit": bool(fired),
                "vectors": len(fired),
                "rules": [sum(1 for k in members if rule_vectors[k]), len(members)],
            }
        else:
            kind = "relation" if item["kind"] == "relation" else "function"
            name = str(item["name"]).removeprefix("$")
            total, vectors = calls_of(kind, name)
            row |= {"hit": total > 0, "vectors": vectors, "calls": total}
            if name in per_origin:
                row["instructions"] = per_origin[name]
        row["in_scope"] = item["section"] in IN_SCOPE
        if item["kind"] == "dec" and item["section"] not in IN_SCOPE:
            row["called_in_scope"] = str(item["name"]) in called
        rows.append(row)
    rows.sort(key=_key)

    # Definitions the inventory does not list (9-arch's), flagged by section.
    listed = {str(i["name"]).removeprefix("$") for i in items if i["kind"] in ("relation", "dec")}
    outside: list[dict[str, Any]] = []
    for kind, name, file, line in sorted(measurement.defs, key=lambda d: (d[2], d[3], d[1])):
        if name in listed:
            continue
        total, vectors = calls_of(kind, name)
        entry: dict[str, Any] = {
            "kind": kind,
            "name": name if kind == "relation" else f"${name}",
            "section": file.split("/", 1)[0],
            "file": file,
            "line": line,
            "hit": total > 0,
            "vectors": vectors,
            "calls": total,
        }
        if name in per_origin:
            entry["instructions"] = per_origin[name]
        outside.append(entry)

    totals: dict[str, dict[str, dict[str, int]]] = {}
    for row in rows:
        section = totals.setdefault(row["section"], {})
        counts = section.setdefault(row["kind"], {"total": 0, "hit": 0})
        counts["total"] += 1
        counts["hit"] += row["hit"]
    by_section: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for instr in universe.values():
        by_section[instr.file.split("/", 1)[0]][1] += 1
        by_section[instr.file.split("/", 1)[0]][0] += instr.iid in union

    vectors_per_program: dict[str, int] = defaultdict(int)
    runtime: dict[str, int] = defaultdict(int)
    for ident, verdict in measurement.vectors:
        vectors_per_program[ident] += 1
        runtime[ident] += verdict == "runtime"
    inputs = [
        {"id": p.id, "source": p.source, "vectors": vectors_per_program[p.id]}
        | ({"runtime_failures": runtime[p.id]} if runtime[p.id] else {})
        for p in programs
    ]
    return {
        "commit": commit,
        "measured_by": (
            "tests/oracle/coverage.py's probe on P4-SpecTec's instruction hook, "
            "checked against `p4spectec cover-sim -instr`"
        ),
        "in_scope": list(IN_SCOPE),
        "input_description": (
            "every corpus program and example, printed through the v1model shim, "
            "with its STF vectors translated as tests/oracle/run.py does, and the "
            "generated programs of tests/oracle/generated.py at the listed seeds"
            + (", plus the pairs under the extra input directories" if extra else "")
        ),
        "generated_seeds": list(GENERATED_SEEDS),
        "extra_input_dirs": extra,
        "totals": {
            "programs": len(programs),
            "vectors": n,
            "instructions": {"hit": stock.total[0], "total": stock.total[1]},
            "instructions_by_section": {
                s: {"hit": h, "total": t} for s, (h, t) in sorted(by_section.items())
            },
            "items_by_section": {s: totals[s] for s in sorted(totals)},
            "unattributed_leaves": len(stray),
        },
        "inputs": inputs,
        "items": rows,
        "outside_inventory": outside,
    }


LISTS = ("inputs", "items", "outside_inventory")


def render(report: dict[str, Any]) -> str:
    """Stable JSON with one list entry per line, so a diff reads entry by
    entry, as spectec-rules.json does."""
    parts: list[str] = []
    for key, value in report.items():
        if key in LISTS:
            body = ",\n".join(json.dumps(entry, separators=(",", ":")) for entry in value)
            parts.append(f'"{key}": [\n{body}\n]')
        else:
            parts.append(f'"{key}": {json.dumps(value)}')
    return "{" + ",\n".join(parts) + "}\n"


def regenerate(root: Path, extra_dirs: Iterable[str]) -> str:
    extra = sorted(set(extra_dirs))
    with tempfile.TemporaryDirectory(prefix="p4blo-coverage-stage-") as tmp:
        stage = Path(tmp)
        programs = materialize_corpus(stage) + materialize_generated(stage, GENERATED_SEEDS)
        p4_dirs, stf_dirs = [stage / "p4"], [stage / "stf"]
        for directory in extra:
            path = (ROOT / directory) if not Path(directory).is_absolute() else Path(directory)
            programs += collect_pairs(path)
            p4_dirs.append(path.resolve())
            stf_dirs.append(path.resolve())
        # Two independent processes of about fifteen seconds each.
        with ThreadPoolExecutor(max_workers=2) as pool:
            stock = pool.submit(run_stock, root, p4_dirs, stf_dirs)
            measurement = run_probe(root, programs)
            return render(build_report(root, programs, extra, measurement, stock.result()))


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tests/oracle/coverage.py",
        description="measure which P4-SpecTec rules p4blo's inputs exercise",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["build", "report"],
        default="report",
        help="`build` the probe (needs the oracle's opam), or write the `report` (default)",
    )
    parser.add_argument(
        "--inputs",
        action="append",
        default=None,
        metavar="DIR",
        help="a directory of .p4/.stf pairs to add (repeatable)",
    )
    parser.add_argument(
        "--check", action="store_true", help="compare with the committed report instead"
    )
    parser.add_argument("--out", type=Path, default=REPORT, help="where to write the report")
    args = parser.parse_args(argv)

    root = oracle_root()
    if args.command == "build":
        print(build_probe(root))
        return 0
    for problem in (checkout_problem(root), probe_problem(root)):
        if problem is not None:
            print(problem, file=sys.stderr)
            return 2
    extra = args.inputs
    if extra and not args.check and args.out.resolve() == REPORT:
        # The committed report records its inputs, and --check reruns them.
        outside = [d for d in extra if not (ROOT / d).resolve().is_relative_to(ROOT)]
        if outside:
            print(
                f"--inputs outside the repository cannot go into {REPORT.name}: {outside}; "
                "write an ad hoc report with --out",
                file=sys.stderr,
            )
            return 2
    if extra is None and args.check and args.out.is_file():
        # The committed report says which extra inputs it was made from.
        recorded = json.loads(args.out.read_text(encoding="utf-8"))
        extra = recorded.get("extra_input_dirs", [])
    text = regenerate(root, extra or [])
    if args.check:
        if not args.out.is_file() or args.out.read_text(encoding="utf-8") != text:
            print(f"{args.out} differs from a fresh measurement; rerun without --check")
            return 1
        print(f"{args.out} matches a fresh measurement at {pinned_commit()}")
        return 0
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
