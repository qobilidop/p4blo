"""The IL bridge on real P4, with explicit v1model stage boundaries.

Pinned original sources retain normalized core-structure comparisons after
checked empty-stage projection and documented golden-only stage splits.
Their vectors compare packet behavior, except the unchanged checksum source
now explicitly rejected for unsupported verify_checksum/checksum_error.

Printer round trips preserve six distinct stages, declarations, table/action
interfaces, packet outcomes and complete extern state on every STF request
and deterministic generated requests. Native standard metadata stays separate
from printed user metadata; byte-identical round trips are not claimed.

Excluded constructs retain named rejection tests. Additional upstream programs
run their original STF vectors, and source probes compare with P4-SpecTec,
including narrowly classified target-policy disagreements.

Missing il-export skips oracle-dependent cases unless
P4BLO_REQUIRE_IL_EXPORT=1 requires the configured oracle.
"""

from __future__ import annotations

import functools
import hashlib
import os
import re
import subprocess
import sys
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

import pytest

from p4blo import arch, stf
from p4blo.arch import v1model
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.case import Case
from p4blo.drt.generate import generate
from p4blo.drt.run import python_outcome
from p4blo.frontend import Excluded, NotTranslated, Translation, translate
from p4blo.frontend.export import Exporter, find_exporter
from p4blo.frontend.normalize import normalize
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracles.v1model_disagreements import ACTUAL, KnownV1ModelDisagreement, known

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.oracles.frontend import catalog, p4c_stf  # noqa: E402
from tests.programs.examples import catalog as examples  # noqa: E402

CORPUS = ROOT / "tests/programs/corpus"
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
            "P4-SpecTec's p4spectec is not built: run tests/oracles/build.sh, "
            "or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR (see tests/oracles/README.md)"
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


def golden(program: str) -> apb.BlockAssembly:
    return arch_wire.load_text(CORPUS / program / f"{program}.txtpb")


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


def test_normalize_does_not_rename_a_local_into_an_action_parameter() -> None:
    """A block local renamed `v0` inside an action whose parameter is
    `v0` would be read as the parameter there."""
    bits8 = pb.Type(bits=8)
    action = pb.Action(
        name="a",
        params=[pb.Param(name="v0", type=bits8, direction=pb.DIRECTION_NONE)],
        body=[pb.Stmt(assign=pb.Assign(target=pb.LValue(var="x"), value=pb.Expr(var="v0")))],
    )
    block = pb.Block(name="c", locals=[pb.Var(name="x", type=bits8)], actions=[action])
    got = normalize(apb.BlockAssembly(blocks=[block])).blocks[0]
    (stmt,) = got.actions[0].body
    assert stmt.assign.target.var == got.locals[0].name != "v0"
    assert stmt.assign.value.var == "v0"


# ---------------------------------------------------------------------------
# 1. The corpus from its original sources
# ---------------------------------------------------------------------------


def _documented_acl(g: apb.BlockAssembly) -> None:
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


def _split_checksum_stage(g: apb.BlockAssembly) -> None:
    """The canonical examples calculate the checksum at the ingress tail;
    their original P4 places that exact computation in ComputeChecksum.
    Split the expected golden only, leaving the imported stage boundary intact.
    """
    ingress = next(b for b in g.blocks if b.name == "MyIngress")
    checksum = deepcopy(ingress.body[-1])
    assert checksum.HasField("conditional")
    assert len(checksum.conditional.then) == 1
    call = checksum.conditional.then[0].call_extern
    assert call.instance == "csum" and call.method == "compute"
    del ingress.body[-1]
    g.blocks.add(
        name="MyComputeChecksum",
        kind=pb.BLOCK_KIND_CONTROL,
        params=ingress.params,
        body=[checksum],
    )
    g.exports.add(role="compute_checksum", block="MyComputeChecksum")


def _documented_forwarder(g: apb.BlockAssembly) -> None:
    """The golden additionally declares unused ingress_port and keeps its
    checksum computation in ingress rather than the source's checksum stage."""
    meta = next(s for s in g.struct_types if s.name == g.metadata)
    assert [f.name for f in meta.fields] == ["ingress_port", "egress_spec"]
    del meta.fields[0]
    _split_checksum_stage(g)


def _documented_tutorial_firewall(g: apb.BlockAssembly) -> None:
    """Expose the original P4's checksum boundary in the expected golden."""
    _split_checksum_stage(g)


def _documented_stateful(g: apb.BlockAssembly) -> None:
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
    # The source's ingress reads and seeds the register; egress reads, adds,
    # writes and publishes it. The canonical example deliberately combines them.
    assert len(block.body) == 6
    assert [v.name for v in block.locals] == ["x", "tmp"]
    assert [s.WhichOneof("kind") for s in block.body] == [
        "call_extern",
        "call_extern",
        "call_extern",
        "assign",
        "call_extern",
        "assign",
    ]
    egress_body = [deepcopy(stmt) for stmt in block.body[2:]]
    egress_local = deepcopy(block.locals[1])
    del block.body[2:]
    del block.locals[1]
    g.blocks.add(
        name="egress",
        kind=pb.BLOCK_KIND_CONTROL,
        params=block.params,
        locals=[egress_local],
        body=egress_body,
    )
    g.exports.add(role="egress", block="egress")


DOCUMENTED: dict[str, Callable[[apb.BlockAssembly], None]] = {
    "acl": _documented_acl,
    "forwarder": _documented_forwarder,
    "stateful": _documented_stateful,
    "tutorial_firewall": _documented_tutorial_firewall,
}

# Vectors on which the translation and the golden are expected to differ,
# with why. Everything else must agree packet for packet.
DISAGREEING_VECTORS: dict[str, str] = {
    "stateful/persist": "exercises the golden's added seed guard",
}


STAGES = {
    "parser": pb.BLOCK_KIND_PARSER,
    "verify_checksum": pb.BLOCK_KIND_CONTROL,
    "ingress": pb.BLOCK_KIND_CONTROL,
    "egress": pb.BLOCK_KIND_CONTROL,
    "compute_checksum": pb.BLOCK_KIND_CONTROL,
    "deparser": pb.BLOCK_KIND_DEPARSER,
}


def _assert_six_stages(program: apb.BlockAssembly) -> None:
    roles = {e.role: e.block for e in program.exports}
    assert set(roles) == set(STAGES)
    assert len(program.exports) == len(set(roles.values())) == 6
    blocks = {b.name: b for b in program.blocks}
    for role, name in roles.items():
        assert blocks[name].kind == STAGES[role]


def _without_empty_stages(program: apb.BlockAssembly) -> apb.BlockAssembly:
    """Comparison projection: remove only proven empty optional controls.

    Retain every nonempty stage, declaration and statement. Required entry
    blocks and arbitrary non-exported blocks are never removed.
    """
    result = deepcopy(program)
    optional = {
        e.block
        for e in result.exports
        if e.role in {"verify_checksum", "egress", "compute_checksum"}
    }
    empty: set[str] = set()
    for block in result.blocks:
        if block.name not in optional or block.body:
            continue
        assert block.kind == pb.BLOCK_KIND_CONTROL
        assert not (block.locals or block.actions or block.tables or block.states)
        assert not block.start_state
        assert [(p.direction, p.type.struct) for p in block.params] == [
            (pb.DIRECTION_INOUT, result.headers),
            (pb.DIRECTION_INOUT, result.metadata),
        ]
        empty.add(block.name)
    blocks = [b for b in result.blocks if b.name not in empty]
    exports = sorted((e for e in result.exports if e.block not in empty), key=lambda e: e.role)
    del result.blocks[:]
    result.blocks.extend(blocks)
    del result.exports[:]
    result.exports.extend(exports)
    return normalize(result)


def _unsupported_checksum_source(exporter: Exporter, entry: catalog.CorpusSource) -> None:
    assert entry.program == "csum16"
    with pytest.raises(
        Excluded, match="verify_checksum requires unsupported checksum_error metadata"
    ) as error:
        _translated(exporter, entry.source, entry.program)
    assert error.value.row == "externFunctionDeclarationIR: an architecture's functions"


@pytest.mark.parametrize("entry", catalog.CORPUS, ids=lambda e: e.program)
def test_corpus_program_from_its_original_source(
    exporter: Exporter, entry: catalog.CorpusSource
) -> None:
    if entry.status == "excluded":
        _unsupported_checksum_source(exporter, entry)
        return
    assert entry.status == "projected"
    got = _translated(exporter, entry.source, entry.program).program
    _assert_six_stages(got)
    want = golden(entry.program)
    if entry.program in DOCUMENTED:
        DOCUMENTED[entry.program](want)
    assert _without_empty_stages(got) == _without_empty_stages(want)


def _outputs(
    program: apb.BlockAssembly, vector: Path, entries_of: BoundIndex
) -> list[tuple[int, list[tuple[int, bytes]]]]:
    """Every packet's outputs, entries resolved against `entries_of` (the
    golden's names, which vectors use) and installed by position."""
    loaded = v1model.load(program)
    run = arch.stf_driver(v1model.V1Model(ports=4), loaded)
    roles = {e.role: e.block for e in program.exports}
    golden_roles = {e.block: e.role for e in entries_of.bindings.exports}
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
    if entry.status == "excluded":
        _unsupported_checksum_source(exporter, entry)
        return
    got = _translated(exporter, entry.source, entry.program).program
    want = golden(entry.program)
    index = BoundIndex.build(want)
    ours, theirs = _outputs(got, vector, index), _outputs(want, vector, index)
    differ = [line for (line, a), (_, b) in zip(ours, theirs, strict=True) if a != b]
    key = f"{entry.program}/{vector.stem}"
    if key in DISAGREEING_VECTORS:
        assert differ, f"{key} now agrees: {DISAGREEING_VECTORS[key]} no longer holds"
    else:
        assert differ == [], f"packets at lines {differ} differ from the golden"


def test_priority_translation_numbers_entries_as_the_specification(
    exporter: Exporter,
) -> None:
    """The typed IL numbers the const entries by P4-SpecTec's
    `$set_priorities_of_tableEntryListIR`, which reads `priority = n` and
    not p4c's `@priority(n)` annotation: none of the three has a priority,
    so they take 3, 2, 1 by position and the larger wins. The golden
    follows the same rule (.agents/decisions.md, "Entry priority"), so the
    source's comment, which expects the third entry to win, does not hold."""
    entry = next(e for e in catalog.CORPUS if e.program == "priority")
    got = _translated(exporter, entry.source, entry.program).program
    ingress = next(b for b in got.blocks if b.name == "ingress")
    (table,) = ingress.tables
    assert [e.priority for e in table.const_entries] == [3, 2, 1]


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
# `entries` with explicit priorities and `largest_priority_wins`, since p4c
# refuses priorities on const entries and a `@priority` annotation is
# p4c's, not the language's; the IR has const entries only, and mutable
# entries are a row the coverage page excludes by scope. The priority
# program's original source retains projected structural equality (question 1).
ROUND_TRIP_EXCLUDED = {"priority": "tableEntriesPropertyIR without const, and a per-entry constIR"}


@pytest.mark.parametrize(("name", "path"), ROUND_TRIP, ids=[n for n, _ in ROUND_TRIP])
def test_printed_golden_preserves_stages_and_behavior(
    exporter: Exporter, tmp_path: Path, name: str, path: Path
) -> None:
    program = arch_wire.load_text(path)
    source = tmp_path / f"{Path(name).name}.p4"
    source.write_text(v1model.print_program(program))
    if name in ROUND_TRIP_EXCLUDED:
        with pytest.raises(Excluded) as e:
            translate(exporter.export(source), program.name)
        assert e.value.row == ROUND_TRIP_EXCLUDED[name]
        return
    got = translate(exporter.export(source), program.name).program
    _assert_six_stages(got)
    before, after = normalize(program), normalize(got)
    assert before.header_types == after.header_types
    assert before.enum_types == after.enum_types
    original_roles = {e.role: e.block for e in before.exports}
    returned_roles = {e.role: e.block for e in after.exports}
    assert all(returned_roles[role] == block for role, block in original_roles.items())
    returned = {block.name: block for block in after.blocks}
    for block in before.blocks:
        other = returned[block.name]
        assert block.kind == other.kind
        assert [(a.name, list(a.params)) for a in block.actions] == [
            (a.name, list(a.params)) for a in other.actions
        ]
        assert [
            (
                t.name,
                list(t.actions),
                list(t.const_entries),
                t.default_action,
                t.const_default_action,
                t.size,
                [k.match_kind for k in t.keys],
            )
            for t in block.tables
        ] == [
            (
                t.name,
                list(t.actions),
                list(t.const_entries),
                t.default_action,
                t.const_default_action,
                t.size,
                [k.match_kind for k in t.keys],
            )
            for t in other.tables
        ]
    # Native standard metadata and its printed user-M copies stay distinct, so
    # byte identity is not the round-trip contract. Check all packet outputs,
    # diagnostics/errors and complete extern observations after every request.
    index = BoundIndex.build(program)
    vectors = sorted(path.parent.glob("*.stf"))
    assert vectors
    for vector in vectors:
        assert _outcomes(after, _vector_cases(index, vector)) == _outcomes(
            before, _vector_cases(index, vector)
        ), vector.name
    cases = generate(index, seed=0x413, count=24, ports=4)
    assert _outcomes(after, cases) == _outcomes(before, cases)


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
    index = BoundIndex.build(want)
    for vector in sorted((CORPUS / name).glob("*.stf")):
        assert _outputs(got, vector, index) == _outputs(want, vector, index), vector.name


def _vector_cases(index: BoundIndex, vector: Path) -> list[Case]:
    installed: list[stf.Add | stf.SetDefault] = []
    cases: list[Case] = []
    for statement in stf.parse(vector.read_text()):
        if isinstance(statement, stf.Add | stf.SetDefault):
            installed.append(statement)
        elif isinstance(statement, stf.Packet):
            cases.append(Case(stf.to_entries(index, installed), statement.port, statement.data))
    assert cases, vector.name
    return cases


def _outcomes(program: apb.BlockAssembly, cases: list[Case]) -> list[object]:
    loaded = v1model.load(program)
    return [python_outcome(loaded, case, 4) for case in cases]


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


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(
            name,
            marks=pytest.mark.xfail(
                strict=True,
                raises=KnownV1ModelDisagreement,
                reason="Pinned P4-SpecTec egress behavior; docs/oracle-discrepancies.md",
            ),
        )
        if name in ACTUAL
        else name
        for name in sorted(p.stem for p in PROBES.glob("*.p4"))
    ],
)
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
    program = _translated(exporter, source, name).program
    assert p4c_stf.replay(program, vector.read_text()) == []
    if known(name, done):
        raise KnownV1ModelDisagreement(done.stderr)
    assert done.returncode == 0, f"P4-SpecTec fails the vector:\n{done.stderr[-2000:]}"


def test_user_metadata_stays_distinct_from_native_standard_metadata(
    exporter: Exporter,
) -> None:
    """Recognizing a synchronization pattern must not alias two P4 stores."""
    got = _translated(exporter, PROBES / "shimsync.p4", "shimsync")
    meta = next(s for s in got.program.struct_types if s.name == got.program.metadata)
    assert [f.name for f in meta.fields] == [
        "ingress_port_",
        "parser_error_",
        "egress_port_",
        "drop_",
        "ingress_port",
        "parser_error",
        "egress_spec",
    ]
    assert got.notes == [
        f"M.{name} renamed {name}_: user metadata, not the contract field"
        for name in ["ingress_port", "parser_error", "egress_port", "drop"]
    ]
    parser = next(block for block in got.program.blocks if block.kind == pb.BLOCK_KIND_PARSER)
    metadata = parser.params[1].name
    copy = parser.states[0].body[0].assign
    assert copy.target == pb.LValue(
        member=pb.LMember(base=pb.LValue(var=metadata), field="ingress_port_")
    )
    assert copy.value == pb.Expr(member=pb.Member(base=pb.Expr(var=metadata), field="ingress_port"))
    for name, user_field in [("collide", "egress_port_"), ("dropflag", "drop_")]:
        other = _translated(exporter, PROBES / f"{name}.p4", name)
        metadata_type = next(
            t for t in other.program.struct_types if t.name == other.program.metadata
        )
        assert [field.name for field in metadata_type.fields] == [user_field, "egress_spec"]
        assert any("renamed" in note and "user metadata" in note for note in other.notes)
