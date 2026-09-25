"""The IL bridge on real P4: P4 source through P4-SpecTec into p4blo IR.

`p4blo.frontend` translates what P4-SpecTec's typing and instantiation make
of a P4 program (the `il-export` command of tests/oracle/patches/). Four
questions, each against P4 nobody wrote for p4blo:

1. **The corpus from its original sources.** Each corpus program with a
   P4 original (tests/frontend/catalog.py) is translated and compared with
   its golden: byte for byte, or after `normalize`, or after the golden is
   adjusted by exactly the differences documented below; its vectors then
   run on both and must agree packet by packet.
2. **The printer inverted.** Every corpus and example golden is printed
   through the v1model shim, translated back, and must equal the golden up
   to `normalize`: the bridge reads back what the printer writes.
3. **Excluded rows.** A program using a construct docs/p4-spec-coverage.md
   excludes is refused with an error naming the row; every row the bridge
   can name is a row of the page.
4. **New programs.** Five p4c programs the corpus does not include run from
   source on the Python interpreter against p4c's own STF vectors.
5. **Probes.** Small programs written for what the corpus misses (the
   bridge review's defects and the rows no corpus program reaches) pass a
   vector of P4-SpecTec's exact outputs, on its simulator and translated.

Without a P4-SpecTec checkout that has `il-export` every test that needs
it skips, as tests/test_oracle.py does, unless `P4BLO_REQUIRE_IL_EXPORT=1`
makes it fail; the pins and the page check run regardless.
"""

from __future__ import annotations

import functools
import hashlib
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from p4blo import arch, ir, stf
from p4blo.arch import v1model
from p4blo.frontend import Excluded, NotTranslated, Translation, translate
from p4blo.frontend.export import Exporter, find_exporter
from p4blo.frontend.normalize import normalize
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.examples import catalog as examples  # noqa: E402
from tests.frontend import catalog, p4c_stf  # noqa: E402

CORPUS = ROOT / "tests" / "corpus"
FRONTEND = ROOT / "impl" / "python" / "p4blo" / "frontend"
COVERAGE = ROOT / "docs" / "p4-spec-coverage.md"
PROBES = catalog.HERE / "probes"


# The oracle workflow sets this, so that a checkout without `il-export`
# fails there instead of skipping.
REQUIRE = os.environ.get("P4BLO_REQUIRE_IL_EXPORT") == "1"


@pytest.fixture(scope="module")
def exporter() -> Exporter:
    found = find_exporter()
    if found is None:
        reason = (
            "P4-SpecTec's p4spectec is not built: run tests/oracle/build.sh, "
            "or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR (see tests/oracle/README.md)"
        )
    else:
        missing = found.missing()
        reason = None if missing is None else f"the oracle checkout cannot export IL: {missing}"
    if reason is not None:
        if REQUIRE:
            pytest.fail(reason)
        pytest.skip(reason)
    assert found is not None
    return found


@functools.cache
def _translated(exporter: Exporter, source: Path, name: str) -> Translation:
    return translate(exporter.export(source), name)


def golden(program: str) -> pb.Program:
    return ir.load_text(CORPUS / program / f"{program}.txtpb")


# ---------------------------------------------------------------------------
# Pins, which need no oracle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(catalog.SHA256), ids=str)
def test_sources_are_the_pinned_copies(path: str) -> None:
    data = (catalog.HERE / path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == catalog.SHA256[path]


def test_every_source_file_is_pinned() -> None:
    on_disk = {
        str(p.relative_to(catalog.HERE))
        for p in catalog.HERE.rglob("*")
        if p.suffix in (".p4", ".stf") and p.parent != PROBES
    }
    assert on_disk == set(catalog.SHA256)


def _coverage_rows() -> list[str]:
    rows: list[str] = []
    for line in COVERAGE.read_text().splitlines():
        if line.startswith("| ") and not line.startswith(("| IL construct", "| Status")):
            rows.append(line.split(" | ")[0][2:].replace("`", ""))
    return rows


def test_every_excluded_row_the_bridge_names_is_on_the_coverage_page() -> None:
    named: set[str] = set()
    for source in FRONTEND.glob("*.py"):
        for m in re.finditer(r'Excluded\(\s*((?:"[^"]*"\s*)+),', source.read_text()):
            named.add("".join(re.findall(r'"([^"]*)"', m.group(1))))
    assert named, "the pattern found no Excluded row"
    rows = _coverage_rows()
    missing = sorted(r for r in named if not any(row.startswith(r) for row in rows))
    assert missing == []


# ---------------------------------------------------------------------------
# 1. The corpus from its original sources
# ---------------------------------------------------------------------------


def _body_without(stmts: list[pb.Stmt], drop: Callable[[pb.Stmt], bool]) -> list[pb.Stmt]:
    return [s for s in stmts if not drop(s)]


def _documented_acl(g: pb.Program) -> None:
    """The acl README's choices the bridge does not make. Key names: the
    golden uses p4c's STF names (`data.f1`, `extra[0].h`), the bridge P4's
    control-plane names, which are the expressions' own paths
    (`hdrs.data.f1`) and so need no `Key.name` except on the stack element.
    Markers: the golden also marks `setbyte` (4) in the action_run
    elaboration, which no switch label reads."""
    ingress = next(b for b in g.blocks if b.name == "ingress")
    for table in ingress.tables:
        for key in table.keys:
            key.name = "hdrs.extra[0].h" if key.name == "extra[0].h" else ""
    setbyte = next(a for a in ingress.actions if a.name == "setbyte")
    del setbyte.body[-1]


def _mark_to_drop_as_v1model(g: pb.Program, block: str) -> None:
    """The golden's `drop` action sets the contract's `drop`, and in the
    firewall also the port 511; v1model's `mark_to_drop` writes only the
    port 511, whose packet p4blo's switch then drops as sent to no port
    (docs of p4blo.frontend.v1model). So the action writes the port alone
    and `M` has no `drop`, which nothing else writes."""
    meta = next(s for s in g.struct_types if s.name == g.metadata)
    fields = [f for f in meta.fields if f.name != "drop"]
    del meta.fields[:]
    meta.fields.extend(fields)
    drop = next(a for a in next(b for b in g.blocks if b.name == block).actions if a.name == "drop")
    port = pb.LValue(member=pb.LMember(base=pb.LValue(var="meta"), field="egress_port"))
    value = pb.Expr(literal=pb.Literal(bits=pb.BitsLiteral(width=9, value="511")))
    del drop.body[:]
    drop.body.append(pb.Stmt(assign=pb.Assign(target=port, value=value)))


def _documented_forwarder(g: pb.Program) -> None:
    """The golden declares the contract's `ingress_port`, which the source
    never reads; and `mark_to_drop` is v1model's (above)."""
    meta = next(s for s in g.struct_types if s.name == g.metadata)
    fields = [f for f in meta.fields if f.name != "ingress_port"]
    del meta.fields[:]
    meta.fields.extend(fields)
    _mark_to_drop_as_v1model(g, "MyIngress")


def _documented_tutorial_firewall(g: pb.Program) -> None:
    """`mark_to_drop` is v1model's (above)."""
    _mark_to_drop_as_v1model(g, "MyIngress")


def _documented_priority(g: pb.Program) -> None:
    """P4-SpecTec reads `@priority(n)` as the entry's priority with the
    larger winning (its typed IL carries 3, 2, 1); the golden follows p4c
    and BMv2, where the smaller wins, as `IR = 4 - p4c`. The bridge takes
    the IL's reading, which is also the language's list order here."""
    ingress = next(b for b in g.blocks if b.name == "ingress")
    for table in ingress.tables:
        for entry in table.const_entries:
            entry.priority = 4 - entry.priority


def _documented_stateful(g: pb.Program) -> None:
    """The stateful README's "Added" section: a counter and a seed guard
    the donor does not have, and the merged control named `pipeline`."""
    kept = [t for t in g.extern_types if t.name != "counter"]
    del g.extern_types[:]
    g.extern_types.extend(kept)
    instances = [i for i in g.extern_instances if i.name != "pkts"]
    del g.extern_instances[:]
    g.extern_instances.extend(instances)
    block = next(b for b in g.blocks if b.name == "pipeline")
    block.name = "ingress"
    body: list[pb.Stmt] = []
    for s in block.body:
        kind = s.WhichOneof("kind")
        if kind == "call_extern" and s.call_extern.instance == "pkts":
            continue
        if kind == "conditional":
            body.extend(s.conditional.then)
            continue
        body.append(s)
    del block.body[:]
    block.body.extend(body)
    for e in g.exports:
        if e.block == "pipeline":
            e.block = "ingress"


DOCUMENTED: dict[str, Callable[[pb.Program], None]] = {
    "acl": _documented_acl,
    "forwarder": _documented_forwarder,
    "priority": _documented_priority,
    "stateful": _documented_stateful,
    "tutorial_firewall": _documented_tutorial_firewall,
}

# Vectors on which the translation and the golden are expected to differ,
# with why. Everything else must agree packet for packet.
DISAGREEING_VECTORS: dict[str, str] = {
    "priority/table_entries_priority": "P4-SpecTec's reading of @priority (see above)",
    "stateful/persist": "exercises the golden's added seed guard",
}


@pytest.mark.parametrize("entry", catalog.CORPUS, ids=lambda e: e.program)
def test_corpus_program_from_its_original_source(
    exporter: Exporter, entry: catalog.CorpusSource
) -> None:
    got = _translated(exporter, entry.source, entry.program).program
    want = golden(entry.program)
    match entry.status:
        case "identical":
            assert ir.dump_text(got) == ir.dump_text(want)
        case "normalized":
            assert ir.dump_text(got) != ir.dump_text(want), "now identical: update the catalog"
            assert ir.dump_text(normalize(got)) == ir.dump_text(normalize(want))
        case "documented":
            assert ir.dump_text(normalize(got)) != ir.dump_text(normalize(want))
            DOCUMENTED[entry.program](want)
            assert ir.dump_text(normalize(got)) == ir.dump_text(normalize(want))
        case _:
            raise AssertionError(entry.status)


def _outputs(
    program: pb.Program, vector: Path, entries_of: ir.Index
) -> list[tuple[int, list[tuple[int, bytes]]]]:
    """Every packet's outputs, entries resolved against `entries_of` (the
    golden's names, which vectors use) and installed by position."""
    loaded = arch.load(program)
    run = arch.stf_driver(arch.Switch(ports=4), loaded)
    roles = {e.role: e.block for e in program.exports}
    golden_roles = {e.block: e.role for e in entries_of.program.exports}
    installed: list[stf.Add | stf.SetDefault] = []
    out: list[tuple[int, list[tuple[int, bytes]]]] = []
    for s in stf.parse(vector.read_text()):
        if isinstance(s, stf.Add | stf.SetDefault):
            installed.append(s)
        elif isinstance(s, stf.Packet):
            entries = stf.to_entries(entries_of, installed)
            for t in entries.tables:
                t.block = roles.get(golden_roles.get(t.block, ""), t.block)
            out.append((s.line, run(entries, s.port, s.data)))
    return out


CORPUS_VECTORS = [
    (entry, vector)
    for entry in catalog.CORPUS
    for vector in sorted((CORPUS / entry.program).glob("*.stf"))
]


@pytest.mark.parametrize(
    ("entry", "vector"),
    CORPUS_VECTORS,
    ids=[f"{e.program}/{v.stem}" for e, v in CORPUS_VECTORS],
)
def test_corpus_vectors_agree_with_the_golden(
    exporter: Exporter, entry: catalog.CorpusSource, vector: Path
) -> None:
    got = _translated(exporter, entry.source, entry.program).program
    want = golden(entry.program)
    index = ir.Index.build(want)
    ours, theirs = _outputs(got, vector, index), _outputs(want, vector, index)
    differ = [line for (line, a), (_, b) in zip(ours, theirs, strict=True) if a != b]
    key = f"{entry.program}/{vector.stem}"
    if key in DISAGREEING_VECTORS:
        assert differ, f"{key} now agrees: {DISAGREEING_VECTORS[key]} no longer holds"
    else:
        assert differ == [], f"packets at lines {differ} differ from the golden"


def test_priority_disagreement_is_the_order_of_two_overlapping_entries(
    exporter: Exporter,
) -> None:
    """The one packet both readings route alike passes; the two the source's
    comments describe as won by the third entry go to port 1 instead."""
    entry = next(e for e in catalog.CORPUS if e.program == "priority")
    got = _translated(exporter, entry.source, entry.program).program
    vector = CORPUS / "priority" / "table_entries_priority.stf"
    ours = _outputs(got, vector, ir.Index.build(golden("priority")))
    assert [[port for port, _ in out] for _, out in ours] == [[1], [1], [1]]


# ---------------------------------------------------------------------------
# 2. The printer inverted
# ---------------------------------------------------------------------------

ROUND_TRIP = [
    *(
        (name, CORPUS / name / f"{name}.txtpb")
        for name in sorted(p.name for p in CORPUS.iterdir() if (p / f"{p.name}.txtpb").exists())
    ),
    *((f"examples/{name}", examples.DATA / name / "program.txtpb") for name in examples.NAMES),
]
# The printer writes a ternary table's entries as P4 1.2.5's mutable
# `entries` with priorities, since p4c refuses priorities on const entries;
# the IR has const entries only, a row the coverage page excludes by scope.
ROUND_TRIP_EXCLUDED = {"priority": "tableEntriesPropertyIR without const, and a per-entry constIR"}


@pytest.mark.parametrize(("name", "path"), ROUND_TRIP, ids=[n for n, _ in ROUND_TRIP])
def test_printed_golden_translates_back_to_itself(
    exporter: Exporter, tmp_path: Path, name: str, path: Path
) -> None:
    program = ir.load_text(path)
    source = tmp_path / f"{Path(name).name}.p4"
    source.write_text(v1model.print_program(program))
    if name in ROUND_TRIP_EXCLUDED:
        with pytest.raises(Excluded) as e:
            translate(exporter.export(source), program.name)
        assert e.value.row == ROUND_TRIP_EXCLUDED[name]
        return
    got = translate(exporter.export(source), program.name).program
    assert ir.dump_text(normalize(got)) == ir.dump_text(normalize(program))


@pytest.mark.parametrize("name", catalog.NO_SOURCE)
def test_edsl_only_program_runs_the_same_after_the_round_trip(
    exporter: Exporter, tmp_path: Path, name: str
) -> None:
    """The corpus programs with no P4 original: the printed and translated
    program runs every vector exactly as the golden does."""
    want = golden(name)
    source = tmp_path / f"{name}.p4"
    source.write_text(v1model.print_program(want))
    got = translate(exporter.export(source), name).program
    index = ir.Index.build(want)
    for vector in sorted((CORPUS / name).glob("*.stf")):
        assert _outputs(got, vector, index) == _outputs(want, vector, index), vector.name


# ---------------------------------------------------------------------------
# 3. Excluded rows
# ---------------------------------------------------------------------------

TEMPLATE = """\
#include <core.p4>
#include <v1model.p4>
header h_t {{ bit<8> f; }}
struct H {{ h_t h; }}
struct M {{ }}
{top}
parser P(packet_in pkt, out H hdr, inout M meta, inout standard_metadata_t sm) {{
    state start {{ pkt.extract(hdr.h); transition accept; }}
}}
control V(inout H hdr, inout M meta) {{ apply {{ }} }}
control I(inout H hdr, inout M meta, inout standard_metadata_t sm) {{
    {decls}
    apply {{ {body} }}
}}
control E(inout H hdr, inout M meta, inout standard_metadata_t sm) {{ apply {{ }} }}
control C(inout H hdr, inout M meta) {{ apply {{ }} }}
control D(packet_out pkt, in H hdr) {{ apply {{ pkt.emit(hdr.h); }} }}
V1Switch(P(), V(), I(), E(), C(), D()) main;
"""

# (id, top-level declarations, control declarations, apply body, row)
EXCLUDED_CASES = [
    ("exit", "", "", "exit;", "exitStatementIR"),
    ("return", "", "", "if (hdr.h.f == 0) { return; }", "returnStatementIR"),
    (
        "header_union",
        "header g_t { bit<8> g; } header_union U { h_t a; g_t b; }",
        "U u;",
        "u.a.setValid();",
        "headerUnionTypeIR",
    ),
    ("int8", "", "int<8> x;", "x = 1; hdr.h.f = (bit<8>) x;", "fixedIntTypeIR (INT<n>)"),
    (
        "varbit",
        "header v_t { varbit<8> x; }",
        "v_t v;",
        "v.setValid();",
        "varBitTypeIR (VARBIT<n>)",
    ),
    (
        "for",
        "",
        "",
        "for (bit<8> i = 0; i < 2; i = i + 1) { hdr.h.f = i; }",
        "forStatementIR (all three forms), forInitStatementIR, forUpdateStatementIR, "
        "forCollectionExpressionIR",
    ),
    (
        "range_key",
        "",
        "action a() { } table t { key = { hdr.h.f : range; } actions = { a; } }",
        "t.apply();",
        "tableKeyIR: match kinds range, optional",
    ),
    (
        "mutable_entries",
        "",
        "action a() { } table t { key = { hdr.h.f : exact; } actions = { a; } "
        "entries = { 1 : a(); } }",
        "t.apply();",
        "tableEntriesPropertyIR without const, and a per-entry constIR",
    ),
    (
        "intrinsic_field",
        "",
        "",
        "hdr.h.f = (bit<8>) sm.instance_type;",
        "standard_metadata and other intrinsic metadata parameters",
    ),
    (
        "architecture_function",
        "",
        "",
        "resubmit_preserving_field_list(0);",
        "externFunctionDeclarationIR: an architecture's functions",
    ),
]


@pytest.mark.parametrize(
    ("top", "decls", "body", "row"),
    [c[1:] for c in EXCLUDED_CASES],
    ids=[c[0] for c in EXCLUDED_CASES],
)
def test_excluded_row_is_refused_by_name(
    exporter: Exporter, tmp_path: Path, top: str, decls: str, body: str, row: str
) -> None:
    source = tmp_path / "excluded.p4"
    source.write_text(TEMPLATE.format(top=top, decls=decls, body=body))
    with pytest.raises(Excluded) as e:
        translate(exporter.export(source), "excluded")
    assert e.value.row == row
    assert any(r.startswith(row) for r in _coverage_rows())


def test_the_template_itself_translates(exporter: Exporter, tmp_path: Path) -> None:
    source = tmp_path / "plain.p4"
    source.write_text(TEMPLATE.format(top="", decls="", body="hdr.h.f = hdr.h.f + 1;"))
    translate(exporter.export(source), "plain")


def test_what_the_bridge_does_not_attempt_is_named_by_production(
    exporter: Exporter, tmp_path: Path
) -> None:
    source = tmp_path / "early_return.p4"
    source.write_text(
        TEMPLATE.format(
            top="bit<8> f(in bit<8> x) { if (x == 0) { return 1; } return 2; }",
            decls="",
            body="hdr.h.f = f(hdr.h.f);",
        )
    )
    with pytest.raises(NotTranslated) as e:
        translate(exporter.export(source), "early_return")
    assert e.value.production == "functionDeclarationIR"


# ---------------------------------------------------------------------------
# 4. New programs, from source, against p4c's vectors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(catalog.NEW_PROGRAMS))
def test_new_p4c_program_passes_its_own_vectors(exporter: Exporter, name: str) -> None:
    source = catalog.HERE / "p4c" / f"{name}.p4"
    program = _translated(exporter, source, name).program
    assert p4c_stf.replay(program, source.with_suffix(".stf").read_text()) == []


# ---------------------------------------------------------------------------
# 5. Probes, against P4-SpecTec's simulator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(p.stem for p in PROBES.glob("*.p4")))
def test_probe_agrees_with_spectec(exporter: Exporter, name: str) -> None:
    """Each probe says in its first lines what it checks. Its vector's
    expectations are exact bytes: P4-SpecTec's simulator must pass it, on
    the source, and so must the translation, on the Python interpreter."""
    source = PROBES / f"{name}.p4"
    vector = source.with_suffix(".stf")
    command = [str(exporter.binary), "sim", str(exporter.spec), "-arch", "v1model"]
    command += ["-i", str(exporter.include), "-p", str(source), "-stf", str(vector)]
    done = subprocess.run(
        command, cwd=exporter.root, capture_output=True, text=True, timeout=300, check=False
    )
    assert done.returncode == 0, f"P4-SpecTec fails the vector:\n{done.stderr[-2000:]}"
    program = _translated(exporter, source, name).program
    assert p4c_stf.replay(program, vector.read_text()) == []


def test_fields_synchronized_as_the_printer_does_are_the_contract_fields(
    exporter: Exporter,
) -> None:
    """The shimsync probe copies its M's contract-named fields to and from
    standard_metadata exactly as the printer does, so the translation reads
    them as the contract fields, with no copies left; collide and dropflag,
    which do not, keep them renamed."""
    got = _translated(exporter, PROBES / "shimsync.p4", "shimsync")
    meta = next(s for s in got.program.struct_types if s.name == got.program.metadata)
    assert [f.name for f in meta.fields] == ["ingress_port", "parser_error", "egress_port", "drop"]
    assert sum("is the contract field" in n for n in got.notes) == 4
    for name in ("collide", "dropflag"):
        other = _translated(exporter, PROBES / f"{name}.p4", name)
        assert any("renamed" in n and "user metadata" in n for n in other.notes)
