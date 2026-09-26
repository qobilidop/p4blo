"""Block semantics against block semantics, on P4-SpecTec.

`tests/oracles/test_oracle.py` replays every corpus vector through the v1model shim
and the simulator's V1Model architecture, so what it compares is a
pipeline: a disagreement could be in a block, in the shim or in the
architecture. Here every parser, control and deparser run the reference
interpreter makes while replaying a vector is repeated on the simulator's
p4blo block architecture (tests/oracles/block.py) with the same inputs, and
each block's outputs are compared on their own: headers, metadata, bits
consumed, acceptance and error for a parser; headers and metadata for a
control; the bytes for a deparser; and after every block the registers and
counters. Extern state is carried from request to request in the
simulator's own form, as the reference interpreter carries it in `Loaded`.

The blocks' inputs are chained as the switch chains them
(parser, ingress, deparser): the parser gets zero metadata with `ingress_port`,
the control the parser's headers and metadata with `parser_error`, the
deparser the control's headers. Unlike the switch, the harness runs all
three blocks for every packet, even one the switch would drop before its
control (a parse that ended inside a byte); both sides get the same
inputs, so this only adds block runs. That choice only picks the inputs;
nothing architectural runs on the simulator's side. Without a patched build
every test that needs the simulator skips and says so; the printer and
value tests run anyway.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from p4blo import arch, ir, stf
from p4blo.arch import entry, spectec_block, v1model
from p4blo.arch import wire as arch_wire
from p4blo.arch.bindings import BoundIndex, assembly_of
from p4blo.arch.entry import deparser as interp_deparser
from p4blo.arch.externs.crc import CRC, crc32
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.state import snapshot
from p4blo.interp import ExternResult, Externs, stmt
from p4blo.interp.expr import zero_header
from p4blo.interp.packet import Emitter
from p4blo.interp.values import Bits, Header, Stack, Struct, Value, copy, zero
from p4blo.v0 import p4blo_pb2 as pb
from tests.oracles import block as oracle_block  # noqa: E402
from tests.support.catalog import ORACLE_VECTORS as VECTORS
from tests.support.catalog import program_of

PROGRAMS = sorted({program_of(v) for v in VECTORS})


ROOT = Path(__file__).resolve().parents[2]


def load(path: Path) -> arch.Loaded:
    return v1model.load(arch_wire.load_text(path.read_text()))


@pytest.fixture(scope="module")
def runner() -> Iterator[oracle_block.BlockRunner]:
    found = oracle_block.find_block_oracle()
    if found is None:
        pytest.skip(
            "P4-SpecTec's p4spectec is not built: run tests/oracles/build.sh, "
            "or set P4BLO_ORACLE_BIN or P4BLO_ORACLE_DIR (see tests/oracles/README.md)"
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
    text = spectec_block.print_program(
        assembly_of(loaded.index.program, loaded.index.bindings), index=loaded.index
    )
    assert "#include <p4blo.p4>" in text
    assert "v1model" not in text
    assert "standard_metadata" not in text
    parts = [loaded.block(role) for role in ("parser", "ingress", "deparser")]
    assert text.rstrip().endswith(f"P4blo({', '.join(f'{p}()' for p in parts)}) main;")


def test_block_printer_supplies_missing_roles() -> None:
    loaded = load(ROOT / "tests/programs/corpus/forwarder/forwarder.txtpb")
    program = apb.BlockAssembly()
    program.CopyFrom(assembly_of(loaded.index.program, loaded.index.bindings))
    # Export only the control, and free the names the printer gives the
    # blocks it supplies.
    for block in program.blocks:
        block.name = {"MyParser": "Parse", "MyDeparser": "Deparse"}.get(block.name, block.name)
    del program.exports[:]
    program.exports.add(role="ingress", block="MyIngress")
    text = spectec_block.print_program(program)
    assert "parser MyParser(packet_in packet, out headers hdr, inout metadata meta)" in text
    assert "control MyDeparser(packet_out packet, in headers hdr)" in text
    assert "parser Parse(packet_in packet, out headers hdr, inout metadata meta)" in text
    assert text.rstrip().endswith("P4blo(MyParser(), MyIngress(), MyDeparser()) main;")


def test_block_printer_refuses_a_declared_name() -> None:
    loaded = load(ROOT / "tests/programs/corpus/forwarder/forwarder.txtpb")
    program = apb.BlockAssembly()
    program.CopyFrom(assembly_of(loaded.index.program, loaded.index.bindings))
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
    for type_ in (pb.Type(struct=index.bindings.headers), pb.Type(struct=index.bindings.metadata)):
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
    index = load(ROOT / "tests/programs/corpus/forwarder/forwarder.txtpb").index
    with pytest.raises(oracle_block.BlockError):
        oracle_block.from_json({"unknown": "{#}"}, index)
    with pytest.raises(oracle_block.BlockError):
        oracle_block.from_json(
            {"struct": {"type": "metadata", "fields": {"drop": {"boolean": True}}}}, index
        )


def _with_second_block_declaring(table: str) -> tuple[ir.Index, pb.Entries]:
    """The forwarder with an unexported control that declares a table of the
    same name as the ingress's, and one entry for the ingress's."""
    program = apb.BlockAssembly()
    original = load(ROOT / "tests/programs/corpus/forwarder/forwarder.txtpb").index
    program.CopyFrom(assembly_of(original.program, original.bindings))
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    original = next(t for t in ingress.tables if t.name == table)
    other = program.blocks.add(name="Other", kind=pb.BLOCK_KIND_CONTROL)
    other.params.extend(ingress.params)
    other.actions.extend(a for a in ingress.actions if a.name in original.actions)
    other.tables.add().CopyFrom(original)
    return BoundIndex.build(program), _entries_for("MyIngress", table)


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
    program = apb.BlockAssembly()
    original = load(ROOT / "tests/programs/corpus/forwarder/forwarder.txtpb").index
    program.CopyFrom(assembly_of(original.program, original.bindings))
    ingress = next(b for b in program.blocks if b.name == "MyIngress")
    table = ingress.tables[0]
    table.keys[0].name = "hdr.ipv4.$valid$"
    index = BoundIndex.build(program)
    entries = _entries_for("MyIngress", table.name)
    with pytest.raises(oracle_block.BlockError, match=r"\$valid\$"):
        oracle_block.entries_to_stf(index, entries)


# ---------------------------------------------------------------------------
# The simulator's own checks
# ---------------------------------------------------------------------------


@pytest.mark.spectec
def test_state_from_another_session_is_refused(runner: oracle_block.BlockRunner) -> None:
    loaded = load(ROOT / "tests/programs/corpus/stateful/stateful.txtpb")
    inputs = oracle_block.BlockInputs(
        packet=b"\x00" * 64,
        metadata=loaded.metadata.zero(),
        state={"session": "not-this-one", "objects": {}},
    )
    with pytest.raises(oracle_block.BlockError, match="session"):
        runner.run_block(loaded.index, "parser", inputs)


def _stateful_parser_state(runner: oracle_block.BlockRunner) -> Any:
    loaded = load(ROOT / "tests/programs/corpus/stateful/stateful.txtpb")
    inputs = oracle_block.BlockInputs(packet=b"\x00" * 64, metadata=loaded.metadata.zero())
    return runner.run_block(loaded.index, "parser", inputs).state


@pytest.mark.spectec
def test_state_from_another_program_is_refused(runner: oracle_block.BlockRunner) -> None:
    # stateful's register `main.c.r` is renamed nowhere: register_bounds has
    # an object of the same id, of another size and cell type.
    state = _stateful_parser_state(runner)
    loaded = load(ROOT / "tests/programs/corpus/register_bounds/register_bounds.txtpb")
    inputs = oracle_block.BlockInputs(
        packet=b"\x00" * 64, metadata=loaded.metadata.zero(), state=state
    )
    with pytest.raises(oracle_block.BlockError, match="extern state of program"):
        runner.run_block(loaded.index, "parser", inputs)


@pytest.mark.spectec
def test_state_that_does_not_parse_is_refused(runner: oracle_block.BlockRunner) -> None:
    state = _stateful_parser_state(runner)
    assert state["objects"], "stateful has extern objects"
    name = next(iter(state["objects"]))
    state["objects"][name] = {"garbage": 1}
    loaded = load(ROOT / "tests/programs/corpus/stateful/stateful.txtpb")
    inputs = oracle_block.BlockInputs(
        packet=b"\x00" * 64, metadata=loaded.metadata.zero(), state=state
    )
    with pytest.raises(oracle_block.BlockError, match=f"the state of {name} does not parse"):
        runner.run_block(loaded.index, "parser", inputs)


def _stacks_control_request(runner: oracle_block.BlockRunner, change: Any) -> dict[str, Any]:
    """A control request on the stacks program whose headers `change` edits."""
    loaded = load(ROOT / "tests/programs/corpus/stacks/stacks.txtpb")
    index = loaded.index
    headers = oracle_block.to_json(zero(pb.Type(struct=index.bindings.headers), index), index)
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
@pytest.mark.spectec
def test_values_outside_their_type_are_refused(
    runner: oracle_block.BlockRunner, change: Any, message: str
) -> None:
    request = _stacks_control_request(runner, change)
    with pytest.raises(oracle_block.BlockError, match=message):
        runner.request(request)


@pytest.mark.spectec
def test_a_struct_of_another_type_is_refused(runner: oracle_block.BlockRunner) -> None:
    request = _stacks_control_request(runner, lambda fields: None)
    request["metadata"] = json.loads(
        json.dumps(request["metadata"]).replace('"metadata"', '"bogus"')
    )
    with pytest.raises(oracle_block.BlockError, match="a value of type bogus"):
        runner.request(request)


@pytest.mark.spectec
def test_an_error_reply_leaves_the_session_usable(runner: oracle_block.BlockRunner) -> None:
    with pytest.raises(oracle_block.BlockError, match="unknown block"):
        runner.request({"program": "nowhere.p4", "block": "egress"})
    loaded = load(ROOT / "tests/programs/corpus/forwarder/forwarder.txtpb")
    inputs = oracle_block.BlockInputs(packet=bytes(14), metadata=loaded.metadata.zero())
    outputs = runner.run_block(loaded.index, "parser", inputs)
    assert outputs.accepted and outputs.consumed_bits == 112


# ---------------------------------------------------------------------------
# Every block of every vector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One block output that differs."""

    where: str
    what: str
    python: object
    spectec: object

    def __str__(self) -> str:
        return (
            f"{self.where}: {self.what}\n"
            f"    python:  {self.python!r}\n    spectec: {self.spectec!r}"
        )


FieldNames = dict[str, list[str]]


def field_names(index: ir.Index) -> FieldNames:
    """Every header and struct type's field names, for reporting paths."""
    return {
        decl.name: [f.name for f in decl.fields]
        for decl in [*index.program.header_types, *index.program.struct_types]
    }


def differences(
    ours: Value, theirs: Value, names: FieldNames, path: str = ""
) -> Iterator[tuple[str, object, object]]:
    """Every leaf, validity bit and stack index where two values differ, by
    path (`.ipv4.ttl`, `.hs[1].valid`, `.hs.next_index`)."""

    def named(value: Header | Struct) -> list[str]:
        return names.get(value.type_name) or [str(i) for i in range(len(value.fields))]

    match ours, theirs:
        case Struct(_, fs), Struct(_, gs) if len(fs) == len(gs):
            for name, f, g in zip(named(ours), fs, gs, strict=True):
                yield from differences(f, g, names, f"{path}.{name}")
        case Header(_, va, fs), Header(_, vb, gs) if len(fs) == len(gs):
            if va != vb:
                yield f"{path}.valid", va, vb
            for name, f, g in zip(named(ours), fs, gs, strict=True):
                if f != g:
                    yield f"{path}.{name}", f, g
        case Stack(_, es, na), Stack(_, fs, nb) if len(es) == len(fs):
            if na != nb:
                yield f"{path}.next_index", na, nb
            for i, (e, f) in enumerate(zip(es, fs, strict=True)):
                yield from differences(e, f, names, f"{path}[{i}]")
        case _:
            if ours != theirs:
                yield path, ours, theirs


class Findings:
    """Disagreements, each with where it happened; empty means agreement."""

    def __init__(self, names: FieldNames) -> None:
        self.names = names
        self.items: list[Finding] = []

    def check(self, where: str, what: str, python: object, spectec: object) -> None:
        if python == spectec:
            return
        if isinstance(python, Struct) and isinstance(spectec, Struct):
            for path, ours, theirs in differences(python, spectec, self.names):
                self.items.append(Finding(where, f"{what}{path}", ours, theirs))
            return
        self.items.append(Finding(where, what, python, spectec))

    def check_externs(
        self, where: str, python: dict[str, tuple[int, ...]], spectec: dict[str, tuple[int, ...]]
    ) -> None:
        """Registers and counters, reported by the cells that differ, since
        whole arrays are too long to read. The simulator's instances are
        matched to the reference interpreter's by their last name part."""
        spectec = by_ir_name(spectec)
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

    def report(self, vector: Path, items: list[Finding] | None = None) -> str:
        items = self.items if items is None else items
        listed = "\n".join(str(f) for f in items[:40])
        more = f"\n... and {len(items) - 40} more" if len(items) > 40 else ""
        return f"{len(items)} block output(s) differ on {vector.relative_to(ROOT)}\n{listed}{more}"


def observe_spectec(externs: dict[str, Any], index: ir.Index) -> dict[str, tuple[int, ...]]:
    """The simulator's registers and counters by their full object id,
    qualified by where the printer instantiated them (`main.c.r` inside an
    exported block, `r` at top level)."""
    observed: dict[str, tuple[int, ...]] = {}
    for name, extern in externs.items():
        values: list[int] = []
        for raw in extern["values"]:
            if extern["kind"] == "register":
                value = oracle_block.from_json(raw, index)
                if not isinstance(value, Bits):
                    raise oracle_block.BlockError(f"register {name} holds {value!r}")
                values.append(value.value)
            else:
                values.append(int(raw))
        observed[name] = tuple(values)
    return observed


def by_ir_name(observed: dict[str, tuple[int, ...]]) -> dict[str, tuple[int, ...]]:
    """The simulator's instances by the IR name, their id's last part, which
    is unique because the IR's instance names are; two ids that share it
    would be a printer change this harness does not know about."""
    named: dict[str, str] = {}
    for qualified in observed:
        simple = qualified.rsplit(".", 1)[-1]
        if simple in named:
            raise AssertionError(f"{named[simple]} and {qualified} are both {simple!r}")
        named[simple] = qualified
    return {simple: observed[qualified] for simple, qualified in named.items()}


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
            # The binding itself is still checked: only the padding is the
            # simulator's, so a wrong binding cannot hide behind the model.
            expected = Bits(32, crc32(payload))
            assert result.returns == expected, (
                f"the CRC32 binding gives {result.returns!r} on {payload.hex()}, not {expected!r}"
            )
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


@contextlib.contextmanager
def spectec_stack_ops() -> Iterator[None]:
    """`push_front` and `pop_front` as the pinned simulator runs them, the
    ledger's *deviates* entry (docs/ir-semantics.md, `push_front(n)`): after
    a push the first `n` elements keep their own old fields; a pop rotates
    the first `n` elements to the back, where they keep their fields, and
    sets `nextIndex` to `S - n`. Each wraps the reference interpreter's own
    operation, checks that it did what P4 says, and then changes only those
    things, so a wrong push or pop cannot hide behind the model."""
    push, pop = stmt.push_front, stmt.pop_front

    def vacated(stack: Stack, i: int, index: ir.Index) -> None:
        element = stack.elements[i]
        assert element == zero_header(stack.header_type, index), (
            f"element {i} left by push or pop is {element!r}, not an invalid zero header"
        )

    def push_front(stack: Stack, n: int, index: ir.Index) -> None:
        before = [[copy(f) for f in e.fields] for e in stack.elements]
        push(stack, n, index)
        for i in range(min(n, len(before))):
            vacated(stack, i, index)
            stack.elements[i].fields = before[i]

    def pop_front(stack: Stack, n: int, index: ir.Index) -> None:
        before = [[copy(f) for f in e.fields] for e in stack.elements]
        next_index = stack.next_index
        pop(stack, n, index)
        size, n = len(before), min(n, len(before))
        assert stack.next_index == max(next_index - n, 0), (
            f"pop_front({n}) from {next_index} gives next_index {stack.next_index}"
        )
        for j in range(n):
            vacated(stack, size - n + j, index)
            stack.elements[size - n + j].fields = before[j]
        stack.next_index = size - n

    stmt.push_front, stmt.pop_front = push_front, pop_front
    try:
        yield
    finally:
        stmt.push_front, stmt.pop_front = push, pop


def run_deparser(
    index: ir.Index, block: str, headers: Struct, externs: Externs
) -> tuple[bytes, int]:
    """The reference deparser's bytes and the exact number of bits it
    emitted, which `entry.run_deparser` pads away; read from its emitter."""
    made: list[Emitter] = []

    class Counted(Emitter):
        __slots__ = ()

        def __init__(self) -> None:
            super().__init__()
            made.append(self)

    with mock.patch.object(interp_deparser, "Emitter", Counted):
        emitted = entry.run_deparser(index, block, headers, externs)
    (emitter,) = made
    return emitted, emitter.width


def compare_vector(
    runner: oracle_block.BlockRunner, vector: Path, *, model: str | None = None
) -> Findings:
    """Replay a vector block by block on both sides from fresh extern state,
    with the reference interpreter changed by `model` (one of the
    classifiers below) when one is given."""
    loaded = load(program_of(vector))
    with contextlib.ExitStack() as scope:
        if model == PADDED_CRC32:
            assert with_padded_crc32(loaded), f"{vector} has no odd-byte CRC32"
        elif model == STACK_INVALIDATION:
            scope.enter_context(spectec_stack_ops())
        else:
            assert model is None, model
        return _compare(runner, vector, loaded)


def _compare(runner: oracle_block.BlockRunner, vector: Path, loaded: arch.Loaded) -> Findings:
    index, meta, externs = loaded.index, loaded.metadata, loaded.externs
    findings = Findings(field_names(index))
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
        parsed = entry.run_parser(index, loaded.block("parser"), statement.data, m, externs)
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
        headers, m_out = entry.run_control(
            index, loaded.block("ingress"), parsed.headers, m, tables, externs
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
        emitted, bits = run_deparser(index, loaded.block("deparser"), headers, externs)
        spec = runner.run_block(
            index,
            "deparser",
            oracle_block.BlockInputs(headers=headers, entries=entries, state=state),
        )
        state = spec.state
        findings.check(f"{where} deparser", "bytes", emitted.hex(), (spec.packet or b"").hex())
        findings.check(f"{where} deparser", "bits", bits, spec.bits)
        findings.check_externs(
            f"{where} deparser", observe_python(loaded), observe_spectec(spec.externs, index)
        )
        blocks += 3
    assert blocks, f"{vector} runs no packet"
    return findings


class KnownDifference(Exception):
    """Every difference is one a documented classifier explains."""


# Vectors whose blocks differ only in documented ways, each named by its
# classifier: a model of the simulator's behavior applied to the reference
# interpreter, under which the vector is run again and every difference
# must vanish. Strict: when the simulator stops differing, the XPASS fails
# and the entry must go. Anything a model does not explain fails.
PADDED_CRC32 = "padded-CRC32"
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


def vector_named(name: str) -> Path:
    (found,) = [v for v in VECTORS if vector_id(v) == name]
    return found


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


def judge(runner: oracle_block.BlockRunner, vector: Path) -> None:
    """Return on agreement, raise `KnownDifference` when the vector's
    classifier explains every difference, and fail otherwise."""
    findings = compare_vector(runner, vector)
    if not findings.items:
        return
    known = KNOWN.get(vector_id(vector))
    if known is None:
        pytest.fail("DIVERGENCE: " + findings.report(vector))
    modeled = compare_vector(runner, vector, model=known)
    if not modeled.items:
        raise KnownDifference(findings.report(vector))
    pytest.fail(
        f"DIVERGENCE beyond the {known} model: "
        + modeled.report(vector)
        + "\nwithout the model: "
        + findings.report(vector)
    )


@pytest.mark.parametrize("vector", vector_params())
@pytest.mark.spectec
def test_blocks_agree_on_spectec(runner: oracle_block.BlockRunner, vector: Path) -> None:
    judge(runner, vector)


# ---------------------------------------------------------------------------
# The classifiers cannot hide a bug in what they model
# ---------------------------------------------------------------------------


@pytest.mark.spectec
def test_a_push_front_that_keeps_next_index_is_caught(
    runner: oracle_block.BlockRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The review's mutant: nextIndex is P4's `min(nextIndex + n, S)` on
    # both sides, so the stack model leaves it alone and the difference
    # remains.
    def push_front(stack: Stack, n: int, index: ir.Index) -> None:
        size = len(stack.elements)
        n = min(n, size)
        fresh = [zero_header(stack.header_type, index) for _ in range(n)]
        stack.elements = fresh + stack.elements[: size - n]

    monkeypatch.setattr(stmt, "push_front", push_front)
    with pytest.raises(pytest.fail.Exception, match="beyond the stack-invalidation model"):
        judge(runner, vector_named("stacks/header-stack-ops-bmv2.stf"))


@pytest.mark.spectec
def test_an_odd_byte_crc32_binding_on_the_wrong_bytes_is_caught(
    runner: oracle_block.BlockRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The review's mutant: the binding hashes the reversed payload. The
    # padding model replaces its result, so only the model's check of
    # that result can see it.
    call = CRC.call

    def reversed_call(self: CRC, method: str, args: list[Value]) -> ExternResult:
        result = call(self, method, args)
        (data,) = args
        width = self.data_width // 8
        if self.output_width == 32 and width % 2 and isinstance(data, Bits):
            return ExternResult(returns=Bits(32, crc32(data.value.to_bytes(width, "big")[::-1])))
        return result

    monkeypatch.setattr(CRC, "call", reversed_call)
    with pytest.raises(AssertionError, match="the CRC32 binding gives"):
        judge(runner, vector_named("tutorial_firewall/collisions.stf"))
