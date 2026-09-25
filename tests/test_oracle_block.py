"""Block semantics against block semantics, on P4-SpecTec.

`tests/test_oracle.py` replays every corpus vector through the v1model shim
and the simulator's V1Model architecture, so what it compares is a
pipeline: a disagreement could be in a block, in the shim or in the
architecture. Here every parser, control and deparser run the reference
interpreter makes while replaying a vector is repeated on the simulator's
p4blo block architecture (tests/oracle/block.py) with the same inputs, and
each block's outputs are compared on their own: headers, metadata, bits
consumed, acceptance and error for a parser; headers and metadata for a
control; the bytes for a deparser; and after every block the registers and
counters. Extern state is carried from request to request in the
simulator's own form, as the reference interpreter carries it in `Loaded`.

The blocks are chained as the switch chains them (`p4blo.arch.Switch`):
the parser gets zero metadata with `ingress_port`, the control the parser's
headers and metadata with `parser_error`, the deparser the control's
headers. That choice only picks the inputs; nothing architectural runs on
the simulator's side. Without a patched build every test that needs the
simulator skips and says so; the printer and value tests run anyway.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from p4blo import arch, interp, ir, stf
from p4blo.arch import spectec_block
from p4blo.arch.externs.crc import CRC, crc32
from p4blo.drt.state import snapshot
from p4blo.interp import ExternResult
from p4blo.interp.values import Bits, Header, Stack, Struct, Value, copy, zero
from p4blo.v0 import p4blo_pb2 as pb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.oracle import block as oracle_block  # noqa: E402
from tests.test_oracle import VECTORS, program_of  # noqa: E402

PROGRAMS = sorted({program_of(v) for v in VECTORS})


def load(path: Path) -> arch.Loaded:
    return arch.load(ir.load_text(path.read_text()))


@pytest.fixture(scope="module")
def runner() -> Iterator[oracle_block.BlockRunner]:
    found = oracle_block.find_block_oracle()
    if found is None:
        pytest.skip(
            "P4-SpecTec's p4spectec is not built: run tests/oracle/build.sh, "
            "or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR (see tests/oracle/README.md)"
        )
    reason = found.missing()
    if reason is not None:
        pytest.skip(f"the oracle checkout cannot run blocks: {reason}")
    with oracle_block.BlockRunner(found) as running:
        yield running


# ---------------------------------------------------------------------------
# The printer and the value shapes, which need no oracle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", PROGRAMS, ids=lambda p: p.parent.name)
def test_block_printer_has_no_shim(path: Path) -> None:
    loaded = load(path)
    text = spectec_block.print_program(loaded.index.program, index=loaded.index)
    assert "#include <p4blo.p4>" in text
    assert "v1model" not in text
    assert "standard_metadata" not in text
    parts = [loaded.block(role) for role in arch.ROLES]
    assert text.rstrip().endswith(f"P4blo({', '.join(f'{p}()' for p in parts)}) main;")


def test_block_printer_supplies_missing_roles() -> None:
    loaded = load(ROOT / "tests/corpus/forwarder/forwarder.txtpb")
    program = pb.Program()
    program.CopyFrom(loaded.index.program)
    # Export only the control, and free the names the printer gives the
    # blocks it supplies.
    for block in program.blocks:
        block.name = {"MyParser": "Parse", "MyDeparser": "Deparse"}.get(block.name, block.name)
    del program.exports[:]
    program.exports.add(role="control", block="MyIngress")
    text = spectec_block.print_program(program)
    assert "parser MyParser(packet_in packet, out headers hdr, inout metadata meta)" in text
    assert "control MyDeparser(packet_out packet, in headers hdr)" in text
    assert "parser Parse(packet_in packet, out headers hdr, inout metadata meta)" in text
    assert text.rstrip().endswith("P4blo(MyParser(), MyIngress(), MyDeparser()) main;")


def test_block_printer_refuses_a_declared_name() -> None:
    loaded = load(ROOT / "tests/corpus/forwarder/forwarder.txtpb")
    program = pb.Program()
    program.CopyFrom(loaded.index.program)
    program.struct_types[0].name = "P4blo"
    with pytest.raises(spectec_block.PrintError, match="P4blo"):
        spectec_block.print_program(program)


def test_include_declares_what_the_printer_assumes() -> None:
    text = (oracle_block.INCLUDE_DIR / spectec_block.INCLUDE).read_text()
    for name in spectec_block.DECLARED - {"main"}:
        assert name in text, name
    for name in ("extern counter", "extern register<T>", "extern void hash<"):
        assert name in text, name


@pytest.mark.parametrize("path", PROGRAMS, ids=lambda p: p.parent.name)
def test_values_roundtrip_through_json(path: Path) -> None:
    index = load(path).index
    for type_ in (pb.Type(struct=index.program.headers), pb.Type(struct=index.program.metadata)):
        value = zero(type_, index)
        _set_everything_valid(value)
        encoded = oracle_block.to_json(value, index)
        assert oracle_block.from_json(encoded, index) == value


def _set_everything_valid(value: Any) -> None:
    match value:
        case Header():
            value.valid = True
        case Struct(_, fields):
            for f in fields:
                _set_everything_valid(f)
        case Stack(_, elements, _):
            for e in elements:
                _set_everything_valid(e)
            value.next_index = len(elements)
        case _:
            pass


def test_from_json_refuses_a_foreign_shape() -> None:
    index = load(ROOT / "tests/corpus/forwarder/forwarder.txtpb").index
    with pytest.raises(oracle_block.BlockError):
        oracle_block.from_json({"unknown": "{#}"}, index)
    with pytest.raises(oracle_block.BlockError):
        oracle_block.from_json(
            {"struct": {"type": "metadata", "fields": {"drop": {"boolean": True}}}}, index
        )


def _with_second_block_declaring(table: str) -> tuple[ir.Index, pb.Entries]:
    """The forwarder with an unexported control that declares a table of the
    same name as the ingress's, and one entry for the ingress's."""
    program = pb.Program()
    program.CopyFrom(load(ROOT / "tests/corpus/forwarder/forwarder.txtpb").index.program)
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    original = next(t for t in ingress.tables if t.name == table)
    other = program.blocks.add(name="Other", kind=pb.BLOCK_KIND_CONTROL)
    other.params.extend(ingress.params)
    other.actions.extend(a for a in ingress.actions if a.name in original.actions)
    other.tables.add().CopyFrom(original)
    return ir.Index.build(program), _entries_for("MyIngress", table)


def _entries_for(block: str, table: str) -> pb.Entries:
    """Entries naming one table; the refusal comes before any entry is read."""
    entries = pb.Entries()
    entries.tables.add(block=block, table=table)
    return entries


def test_entries_for_a_table_two_blocks_declare_are_refused() -> None:
    # The simulator finds an entry's table by its unqualified name, as
    # V1Model's STF runner does after its name rewrites, which this
    # architecture does not repeat; with two tables of that name it would
    # pick one silently.
    index, entries = _with_second_block_declaring("ipv4_lpm")
    with pytest.raises(oracle_block.BlockError, match="ipv4_lpm.*MyIngress, Other"):
        oracle_block.entries_to_stf(index, entries)


def test_entries_for_a_valid_key_name_are_refused() -> None:
    # V1Model's STF runner rewrites `$valid$` in a key name to `isValid()`;
    # this architecture does not, so such a key would match differently.
    program = pb.Program()
    program.CopyFrom(load(ROOT / "tests/corpus/forwarder/forwarder.txtpb").index.program)
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    table = ingress.tables[0]
    table.keys[0].name = "hdr.ipv4.$valid$"
    index = ir.Index.build(program)
    entries = _entries_for("MyIngress", table.name)
    with pytest.raises(oracle_block.BlockError, match=r"\$valid\$"):
        oracle_block.entries_to_stf(index, entries)


# ---------------------------------------------------------------------------
# The simulator's own checks
# ---------------------------------------------------------------------------


def test_state_from_another_session_is_refused(runner: oracle_block.BlockRunner) -> None:
    loaded = load(ROOT / "tests/corpus/stateful/stateful.txtpb")
    inputs = oracle_block.BlockInputs(
        packet=b"\x00" * 64,
        metadata=loaded.metadata.zero(),
        state={"session": "not-this-one", "objects": {}},
    )
    with pytest.raises(oracle_block.BlockError, match="session"):
        runner.run_block(loaded.index, "parser", inputs)


def _stateful_parser_state(runner: oracle_block.BlockRunner) -> Any:
    loaded = load(ROOT / "tests/corpus/stateful/stateful.txtpb")
    inputs = oracle_block.BlockInputs(packet=b"\x00" * 64, metadata=loaded.metadata.zero())
    return runner.run_block(loaded.index, "parser", inputs).state


def test_state_from_another_program_is_refused(runner: oracle_block.BlockRunner) -> None:
    # stateful's register `main.c.r` is renamed nowhere: register_bounds has
    # an object of the same id, of another size and cell type.
    state = _stateful_parser_state(runner)
    loaded = load(ROOT / "tests/corpus/register_bounds/register_bounds.txtpb")
    inputs = oracle_block.BlockInputs(
        packet=b"\x00" * 64, metadata=loaded.metadata.zero(), state=state
    )
    with pytest.raises(oracle_block.BlockError, match="extern state of program"):
        runner.run_block(loaded.index, "parser", inputs)


def test_state_that_does_not_parse_is_refused(runner: oracle_block.BlockRunner) -> None:
    state = _stateful_parser_state(runner)
    assert state["objects"], "stateful has extern objects"
    name = next(iter(state["objects"]))
    state["objects"][name] = {"garbage": 1}
    loaded = load(ROOT / "tests/corpus/stateful/stateful.txtpb")
    inputs = oracle_block.BlockInputs(
        packet=b"\x00" * 64, metadata=loaded.metadata.zero(), state=state
    )
    with pytest.raises(oracle_block.BlockError, match=f"the state of {name} does not parse"):
        runner.run_block(loaded.index, "parser", inputs)


def _stacks_control_request(runner: oracle_block.BlockRunner, change: Any) -> dict[str, Any]:
    """A control request on the stacks program whose headers `change` edits."""
    loaded = load(ROOT / "tests/corpus/stacks/stacks.txtpb")
    index = loaded.index
    headers = oracle_block.to_json(zero(pb.Type(struct=index.program.headers), index), index)
    change(headers["struct"]["fields"])
    return {
        "program": str(runner.program_path(index)),
        "block": "control",
        "headers": headers,
        "metadata": oracle_block.to_json(loaded.metadata.zero(), index),
        "entries": "",
        "state": None,
    }


def _set_next_index(value: int) -> Any:
    def change(fields: dict[str, Any]) -> None:
        fields["h2"]["stack"]["next_index"] = value

    return change


def _set_h1(key: str, value: Any) -> Any:
    def change(fields: dict[str, Any]) -> None:
        h1 = fields["h1"]["header"]
        if key == "type":
            h1["type"] = value
        else:
            h1["fields"][key]["bits"]["value"] = value

    return change


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (_set_next_index(6), "next_index 6 of a stack of 5 elements"),
        (_set_next_index(-1), "next_index -1 of a stack of 5 elements"),
        (_set_h1("hdr_type", "256"), "256 does not fit in bit<8>"),
        (_set_h1("hdr_type", "-1"), "-1 does not fit in bit<8>"),
        (_set_h1("type", "bogus_t"), "a value of type bogus_t where h1_t is expected"),
    ],
    ids=["next-index-above", "next-index-negative", "bits-above", "bits-negative", "type-name"],
)
def test_values_outside_their_type_are_refused(
    runner: oracle_block.BlockRunner, change: Any, message: str
) -> None:
    request = _stacks_control_request(runner, change)
    with pytest.raises(oracle_block.BlockError, match=message):
        runner.request(request)


def test_a_struct_of_another_type_is_refused(runner: oracle_block.BlockRunner) -> None:
    request = _stacks_control_request(runner, lambda fields: None)
    request["metadata"] = json.loads(
        json.dumps(request["metadata"]).replace('"metadata"', '"bogus"')
    )
    with pytest.raises(oracle_block.BlockError, match="a value of type bogus"):
        runner.request(request)


def test_an_error_reply_leaves_the_session_usable(runner: oracle_block.BlockRunner) -> None:
    with pytest.raises(oracle_block.BlockError, match="unknown block"):
        runner.request({"program": "nowhere.p4", "block": "egress"})
    loaded = load(ROOT / "tests/corpus/forwarder/forwarder.txtpb")
    inputs = oracle_block.BlockInputs(packet=bytes(14), metadata=loaded.metadata.zero())
    outputs = runner.run_block(loaded.index, "parser", inputs)
    assert outputs.accepted and outputs.consumed_bits == 112


# ---------------------------------------------------------------------------
# Every block of every vector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One block output that differs. `tag` names a documented kind of
    difference when the value paths show one, and is None otherwise."""

    where: str
    what: str
    python: object
    spectec: object
    tag: str | None = None

    def __str__(self) -> str:
        return (
            f"{self.where}: {self.what}\n"
            f"    python:  {self.python!r}\n    spectec: {self.spectec!r}"
        )


# The ledger entry for push_front and pop_front (docs/ir-semantics.md,
# "Statements and calls", class deviates): the simulator invalidates the
# vacated elements with `$invalidate_value`, which keeps their stored
# fields, and pops to `nextIndex = S - n`. An element invalid on both sides
# with different stored fields, and a different `next_index`, are those.
STACK_FIELD = "stack-invalid-element-field"
STACK_INDEX = "stack-next-index"


def differences(
    ours: Value, theirs: Value, path: str = "", *, in_stack: bool = False
) -> Iterator[tuple[str, object, object, str | None]]:
    """Every leaf, validity bit and stack index where two values differ, by
    path (`.ipv4.ttl`, `.hs[1].valid`, `.hs.next_index`), each tagged when it
    is one of the stack differences above."""
    match ours, theirs:
        case Struct(_, fs), Struct(_, gs) if len(fs) == len(gs):
            for name, f, g in zip(_field_names(ours), fs, gs, strict=True):
                yield from differences(f, g, f"{path}.{name}")
        case Header(_, va, fs), Header(_, vb, gs) if len(fs) == len(gs):
            if va != vb:
                yield f"{path}.valid", va, vb, None
            tag = STACK_FIELD if in_stack and not va and not vb else None
            for name, f, g in zip(_field_names(ours), fs, gs, strict=True):
                if f != g:
                    yield f"{path}.{name}", f, g, tag
        case Stack(_, es, na), Stack(_, fs, nb) if len(es) == len(fs):
            if na != nb:
                yield f"{path}.next_index", na, nb, STACK_INDEX
            for i, (e, f) in enumerate(zip(es, fs, strict=True)):
                yield from differences(e, f, f"{path}[{i}]", in_stack=True)
        case _:
            if ours != theirs:
                yield path, ours, theirs, None


_NAMES: dict[str, list[str]] = {}


def _field_names(value: Header | Struct) -> list[str]:
    return _NAMES.get(value.type_name) or [str(i) for i in range(len(value.fields))]


class Findings:
    """Disagreements, each with where it happened; empty means agreement."""

    def __init__(self) -> None:
        self.items: list[Finding] = []

    def check(self, where: str, what: str, python: object, spectec: object) -> None:
        if python == spectec:
            return
        if isinstance(python, Struct) and isinstance(spectec, Struct):
            for path, ours, theirs, tag in differences(python, spectec):
                self.items.append(Finding(where, f"{what}{path}", ours, theirs, tag))
            return
        self.items.append(Finding(where, what, python, spectec))

    def check_externs(
        self, where: str, python: dict[str, tuple[int, ...]], spectec: dict[str, tuple[int, ...]]
    ) -> None:
        """Registers and counters, reported by the cells that differ, since
        whole arrays are too long to read."""
        if python.keys() != spectec.keys():
            self.check(where, "extern instances", sorted(python), sorted(spectec))
            return
        for name in sorted(python):
            ours, theirs = python[name], spectec[name]
            if len(ours) != len(theirs):
                self.check(where, f"{name} size", len(ours), len(theirs))
                continue
            for i, (a, b) in enumerate(zip(ours, theirs, strict=True)):
                self.check(where, f"{name}[{i}]", a, b)

    def untagged(self) -> list[Finding]:
        return [f for f in self.items if f.tag is None]

    def report(self, vector: Path, items: list[Finding] | None = None) -> str:
        items = self.items if items is None else items
        listed = "\n".join(str(f) for f in items[:40])
        more = f"\n... and {len(items) - 40} more" if len(items) > 40 else ""
        return f"{len(items)} block output(s) differ on {vector.relative_to(ROOT)}\n{listed}{more}"


def observe_spectec(externs: dict[str, Any], index: ir.Index) -> dict[str, tuple[int, ...]]:
    """The simulator's registers and counters by instance name. Object ids
    are qualified by where the printer instantiated them (`main.c.r` inside
    an exported block, `r` at top level); the last part is the IR name."""
    observed: dict[str, tuple[int, ...]] = {}
    for name, extern in externs.items():
        values: list[int] = []
        for raw in extern["values"]:
            if extern["kind"] == "register":
                value = oracle_block.from_json(raw, index)
                values.append(getattr(value, "value", int(bool(value))))
            else:
                values.append(int(raw))
        observed[name.rsplit(".", 1)[-1]] = tuple(values)
    return observed


def observe_python(loaded: arch.Loaded) -> dict[str, tuple[int, ...]]:
    return {o.name: o.values for o in snapshot(loaded) if o.kind in ("register", "counter")}


class PaddedCRC32(CRC):
    """CRC32 as the pinned simulator computes it: every hash input is padded
    to an even byte count by prepending a zero byte (docs/assurance.md,
    "Pinned P4-SpecTec: odd-byte CRC32"). CRC16 starts at zero, so the
    extra byte changes nothing there."""

    def call(self, method: str, args: list[Value]) -> ExternResult:
        result = super().call(method, args)
        (data,) = args
        assert isinstance(data, Bits)
        payload = data.value.to_bytes(self.data_width // 8, "big")
        if len(payload) % 2:
            return ExternResult(returns=Bits(32, crc32(b"\x00" + payload)))
        return result


def with_padded_crc32(loaded: arch.Loaded) -> int:
    """Replace every odd-byte CRC32 binding by the simulator's; the count."""
    replaced = 0
    for name, extern in list(loaded.externs.items()):
        if isinstance(extern, CRC) and extern.output_width == 32 and (extern.data_width // 8) % 2:
            loaded.externs[name] = PaddedCRC32(32, extern.data_width)
            replaced += 1
    return replaced


def compare_vector(
    runner: oracle_block.BlockRunner, vector: Path, *, padded_crc32: bool = False
) -> Findings:
    """Replay a vector block by block on both sides from fresh extern state."""
    loaded = load(program_of(vector))
    if padded_crc32:
        assert with_padded_crc32(loaded), f"{vector} has no odd-byte CRC32"
    index, meta, externs = loaded.index, loaded.metadata, loaded.externs
    for decl in [*index.program.header_types, *index.program.struct_types]:
        _NAMES[decl.name] = [f.name for f in decl.fields]
    findings = Findings()
    installed: list[stf.Add | stf.SetDefault] = []
    state: Any = None
    blocks = 0
    for statement in stf.parse(vector.read_text()):
        if isinstance(statement, stf.Add | stf.SetDefault):
            installed.append(statement)
            continue
        if not isinstance(statement, stf.Packet):
            continue
        where = f"line {statement.line}"
        entries = stf.to_entries(index, installed)
        tables = loaded.entries(entries)

        # The parser, on zero metadata with the ingress port.
        m = meta.zero()
        meta.write(m, "ingress_port", statement.port)
        parsed = interp.run_parser(index, loaded.block("parser"), statement.data, m, externs)
        spec = runner.run_block(
            index,
            "parser",
            oracle_block.BlockInputs(
                packet=statement.data, metadata=m, entries=entries, state=state
            ),
        )
        state = spec.state
        findings.check(f"{where} parser", "headers", parsed.headers, spec.headers)
        findings.check(f"{where} parser", "metadata", parsed.metadata, spec.metadata)
        findings.check(f"{where} parser", "consumed bits", parsed.consumed_bits, spec.consumed_bits)
        findings.check(f"{where} parser", "accepted", parsed.accepted, spec.accepted)
        findings.check(f"{where} parser", "error", parsed.error, spec.error)
        findings.check_externs(
            f"{where} parser", observe_python(loaded), observe_spectec(spec.externs, index)
        )

        # The control, on the parser's headers and metadata with its error.
        m = copy(parsed.metadata)
        assert isinstance(m, Struct)
        meta.write(m, "parser_error", parsed.error)
        headers, m_out = interp.run_control(
            index, loaded.block("control"), parsed.headers, m, tables, externs
        )
        spec = runner.run_block(
            index,
            "control",
            oracle_block.BlockInputs(
                headers=parsed.headers, metadata=m, entries=entries, state=state
            ),
        )
        state = spec.state
        findings.check(f"{where} control", "headers", headers, spec.headers)
        findings.check(f"{where} control", "metadata", m_out, spec.metadata)
        findings.check_externs(
            f"{where} control", observe_python(loaded), observe_spectec(spec.externs, index)
        )

        # The deparser, on the control's headers.
        emitted = interp.run_deparser(index, loaded.block("deparser"), headers, externs)
        spec = runner.run_block(
            index,
            "deparser",
            oracle_block.BlockInputs(headers=headers, entries=entries, state=state),
        )
        state = spec.state
        findings.check(f"{where} deparser", "bytes", emitted.hex(), (spec.packet or b"").hex())
        findings.check_externs(
            f"{where} deparser", observe_python(loaded), observe_spectec(spec.externs, index)
        )
        blocks += 3
    assert blocks, f"{vector} runs no packet"
    return findings


class KnownDifference(Exception):
    """Every difference is one a documented classifier explains."""


# Vectors whose blocks differ only in documented ways, each named by its
# classifier. Strict: when the simulator stops differing, the XPASS fails
# and the entry must go. Anything a classifier does not explain fails.
PADDED_CRC32 = "padded-crc32"
STACK_INVALIDATION = "stack-invalidation"
KNOWN = {
    # The firewall's second Bloom filter hashes the 13-byte 5-tuple with
    # CRC32; the pipeline oracle cannot see the cell index, the block
    # comparison sees every register cell.
    "tutorial_firewall/collisions.stf": PADDED_CRC32,
    "tutorial_firewall/connection.stf": PADDED_CRC32,
    # push_front and pop_front on a stack, then the invalid elements'
    # stored fields and the popped next index, which a deparser never
    # emits and the pipeline oracle therefore never saw.
    "stacks/header-stack-ops-bmv2.stf": STACK_INVALIDATION,
}


def vector_id(vector: Path) -> str:
    return f"{vector.parent.name}/{vector.name}"


def vector_params() -> list[Any]:
    params: list[Any] = []
    for vector in VECTORS:
        known = KNOWN.get(vector_id(vector))
        marks = (
            [pytest.mark.xfail(strict=True, raises=KnownDifference, reason=known)] if known else []
        )
        params.append(pytest.param(vector, id=vector_id(vector), marks=marks))
    return params


def test_known_vectors_exist() -> None:
    assert set(KNOWN) <= {vector_id(v) for v in VECTORS}


@pytest.mark.parametrize("vector", vector_params())
def test_blocks_agree_on_spectec(runner: oracle_block.BlockRunner, vector: Path) -> None:
    findings = compare_vector(runner, vector)
    if not findings.items:
        return
    known = KNOWN.get(vector_id(vector))
    if known == STACK_INVALIDATION and not findings.untagged():
        raise KnownDifference(findings.report(vector))
    if known == PADDED_CRC32:
        modeled = compare_vector(runner, vector, padded_crc32=True)
        if not modeled.items:
            raise KnownDifference(findings.report(vector))
        pytest.fail(
            "DIVERGENCE beyond the padded-CRC32 model: "
            + modeled.report(vector)
            + "\nwithout the model: "
            + findings.report(vector)
        )
    unexplained = findings.untagged() if known == STACK_INVALIDATION else findings.items
    pytest.fail("DIVERGENCE: " + findings.report(vector, unexplained))
