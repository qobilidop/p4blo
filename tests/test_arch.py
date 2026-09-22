"""The two architectures and the metadata contract (docs/design.md, claim 3).

The forwarder replays under both architectures unchanged; the rules every
architecture shares (metadata initialization, the control after a parser
rejection, byte-aligned parsing, the payload) and the switch's fates are
checked on tiny programs written in text format below.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from p4blo import arch, ir, stf
from p4blo.arch import CONTRACT, Architecture, ContractError, Filter, Switch, stf_driver
from p4blo.v0 import p4blo_pb2 as pb

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "forwarder"
VECTORS = sorted(CORPUS.glob("*.stf"))

# ---------------------------------------------------------------------------
# A tiny program: one-byte header h, two-byte header g, parser, control,
# deparser. The pieces a test varies are the metadata fields, the parser
# state's body, the control's locals and body, and extra declarations.
# ---------------------------------------------------------------------------

CORE_ERRORS = "".join(f'errors: "{e}"\n' for e in ir.CORE_ERRORS)
HDR_H = 'member { base { var: "hdr" } field: "h" }'
HDR_G = 'member { base { var: "hdr" } field: "g" }'
H_F = f'member {{ base {{ {HDR_H} }} field: "f" }}'
EXTRACT_H = f"body {{ extract {{ target {{ {HDR_H} }} }} }}"
EXTRACT_G = f"body {{ extract {{ target {{ {HDR_G} }} }} }}"


def meta(field: str) -> str:
    return f'member {{ base {{ var: "meta" }} field: "{field}" }}'


def assign(target: str, value: str) -> str:
    return f"body {{ assign {{ target {{ {target} }} value {{ {value} }} }} }}"


def bits(width: int, value: int) -> str:
    return f'literal {{ bits {{ width: {width} value: "{value}" }} }}'


def program(
    *,
    metadata: str,
    h_width: int = 8,
    parser_body: str = EXTRACT_H,
    locals: str = "",
    control: str = "",
    extra: str = "",
) -> pb.Program:
    return ir.load_text(f"""
        name: "tiny"
        {CORE_ERRORS}
        header_types {{ name: "h_t" fields {{ name: "f" type {{ bits: {h_width} }} }} }}
        header_types {{ name: "g_t" fields {{ name: "f" type {{ bits: 16 }} }} }}
        struct_types {{
          name: "H"
          fields {{ name: "h" type {{ header: "h_t" }} }}
          fields {{ name: "g" type {{ header: "g_t" }} }}
        }}
        struct_types {{ name: "M" {metadata} }}
        headers: "H"
        metadata: "M"
        {extra}
        blocks {{
          name: "P" kind: BLOCK_KIND_PARSER
          params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_OUT }}
          params {{ name: "meta" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
          start_state: "start"
          states {{ name: "start" {parser_body} transition {{ direct {{ accept {{}} }} }} }}
        }}
        blocks {{
          name: "C" kind: BLOCK_KIND_CONTROL
          params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_INOUT }}
          params {{ name: "meta" type {{ struct: "M" }} direction: DIRECTION_INOUT }}
          {locals}
          {control}
        }}
        blocks {{
          name: "D" kind: BLOCK_KIND_DEPARSER
          params {{ name: "hdr" type {{ struct: "H" }} direction: DIRECTION_IN }}
          body {{ emit {{ value {{ {HDR_H} }} }} }}
          body {{ emit {{ value {{ {HDR_G} }} }} }}
        }}
        exports {{ role: "parser" block: "P" }}
        exports {{ role: "control" block: "C" }}
        exports {{ role: "deparser" block: "D" }}
        """)


DROP = 'fields { name: "drop" type { boolean {} } }'
FLOOD = 'fields { name: "flood" type { boolean {} } }'
EGRESS = 'fields { name: "egress_port" type { bits: 9 } }'
INGRESS = 'fields { name: "ingress_port" type { bits: 9 } }'
PARSER_ERROR = 'fields { name: "parser_error" type { error {} } }'


@pytest.fixture(scope="module")
def forwarder() -> arch.Loaded:
    return arch.load(ir.load_text(CORPUS / "forwarder.txtpb"))


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


def test_the_forwarder_declares_three_contract_fields(forwarder: arch.Loaded) -> None:
    assert CONTRACT.present(forwarder.index) == {"ingress_port", "egress_port", "drop"}


def test_a_program_may_declare_no_contract_field() -> None:
    loaded = arch.load(program(metadata='fields { name: "color" type { bits: 3 } }'))
    assert CONTRACT.present(loaded.index) == set()
    # Undeclared fields read as their zero value and swallow writes.
    m = loaded.metadata.zero()
    loaded.metadata.write(m, "ingress_port", 3)
    assert loaded.metadata.number(m, "egress_port") == 0
    assert loaded.metadata.flag(m, "drop") is False
    assert loaded.metadata.error(m, "parser_error").name == "NoError"


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ('fields { name: "drop" type { bits: 1 } }', "M.drop must be bool, got bit<1>"),
        ('fields { name: "egress_port" type { bits: 8 } }', "M.egress_port must be bit<9>"),
        ('fields { name: "parser_error" type { bits: 3 } }', "M.parser_error must be error"),
    ],
)
def test_a_contract_field_of_the_wrong_type_refuses_to_load(field: str, message: str) -> None:
    with pytest.raises(ContractError, match=message):
        arch.load(program(metadata=field))


def test_a_missing_role_is_refused_at_load() -> None:
    """The validator does not know which roles an architecture needs, so
    the loader resolves them: a program without them never reaches a packet."""
    full = program(metadata=EGRESS)
    without = pb.Program()
    without.CopyFrom(full)
    del without.exports[:]
    with pytest.raises(arch.LoadError, match="exports no 'parser' block"):
        arch.load(without)
    without.exports.add(role="parser", block="P")
    without.exports.add(role="control", block="C")
    with pytest.raises(arch.LoadError, match="exports no 'deparser' block"):
        arch.load(without)
    # The filter runs without a deparser when asked for only what it needs.
    loaded = arch.load(without, roles=("parser", "control"))
    assert dict(loaded.blocks) == {"parser": "P", "control": "C"}
    assert Filter().run(loaded, loaded.entries(), 0, b"\x01") == [(0, b"\x01")]
    assert dict(arch.load(full).blocks) == {"parser": "P", "control": "C", "deparser": "D"}


def test_the_contract_is_the_design_table() -> None:
    table = {(f.name, f.provided) for f in CONTRACT.fields}
    assert table == {
        ("ingress_port", True),
        ("parser_error", True),
        ("egress_port", False),
        ("drop", False),
        ("flood", False),
    }


# ---------------------------------------------------------------------------
# The forwarder under both architectures, on the same vectors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
def test_forwarder_under_the_switch(forwarder: arch.Loaded, vector: Path) -> None:
    statements = stf.parse(vector.read_text())
    stf.assert_replay(forwarder.index, statements, stf_driver(Switch(ports=4), forwarder))


def as_the_filter_sees_it(text: str) -> str:
    """The vector with every `expect` carrying its packet's own bytes.

    The filter has no deparser, so the control's rewrites never reach the
    wire: the forwarder's new MAC addresses and decremented TTL in
    forward.stf and lpm_precedence.stf are invisible, and only the port
    decision remains. The other three vectors expect the input bytes
    already, so this leaves them as they are.
    """
    lines: list[str] = []
    data = ""
    for line in text.splitlines():
        words = line.split()
        if words[:1] == ["packet"]:
            data = " ".join(words[2:])
        elif words[:1] == ["expect"]:
            line = f"expect {words[1]} {data}"
        lines.append(line)
    return "\n".join(lines)


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
def test_forwarder_under_the_filter(forwarder: arch.Loaded, vector: Path) -> None:
    statements = stf.parse(as_the_filter_sees_it(vector.read_text()))
    stf.assert_replay(forwarder.index, statements, stf_driver(Filter(), forwarder))


def test_the_filter_does_not_rewrite(forwarder: arch.Loaded) -> None:
    """forward.stf as written fails under the filter: right port, old bytes."""
    statements = stf.parse((CORPUS / "forward.stf").read_text())
    failures = stf.replay(forwarder.index, statements, stf_driver(Filter(), forwarder))
    assert len(failures) == 1
    assert "expected 000000000202" in str(failures[0])
    assert "got 000000000101" in str(failures[0])


def test_the_filter_forwards_the_original_bytes(forwarder: arch.Loaded) -> None:
    packet = bytes.fromhex(
        "000000000101 000000000001 0800 4500001a0001000040110000 0a000101 0a000202 deadbeefcafe"
    )
    run = stf_driver(Filter(), forwarder)
    host = stf_entries(
        forwarder.index,
        "add ipv4_lpm hdr.ipv4.dstAddr:0x0a000200/24 ipv4_forward(dstAddr:0x000000000202, port:2)",
    )
    assert run(host, 0, packet) == [(2, packet)]


def stf_entries(index: ir.Index, text: str) -> pb.Entries:
    """The `pb.Entries` an STF `add` line installs, via the runner itself."""
    seen: list[pb.Entries] = []

    def capture(entries: pb.Entries, port: int, packet: bytes) -> list[tuple[int, bytes]]:
        seen.append(entries)
        return []

    stf.replay(index, stf.parse(text + "\npacket 0 00\n"), capture)
    return seen[0]


# ---------------------------------------------------------------------------
# The switch's fates
# ---------------------------------------------------------------------------


def test_flood_sends_to_every_port_but_the_ingress_one() -> None:
    loaded = arch.load(
        program(metadata=FLOOD, control=assign(meta("flood"), "literal { boolean: true }"))
    )
    switch = Switch(ports=4)
    packet = b"\x0a\xbb"
    assert switch.run(loaded, loaded.entries(), 1, packet) == [
        (0, packet),
        (2, packet),
        (3, packet),
    ]
    assert switch.run(loaded, loaded.entries(), 3, packet) == [
        (0, packet),
        (1, packet),
        (2, packet),
    ]


def test_drop_wins_over_flood() -> None:
    loaded = arch.load(
        program(
            metadata=DROP + FLOOD + EGRESS,
            control=assign(meta("flood"), "literal { boolean: true }")
            + assign(meta("egress_port"), bits(9, 2))
            + assign(meta("drop"), "literal { boolean: true }"),
        )
    )
    assert Switch(ports=4).run(loaded, loaded.entries(), 1, b"\x00") == []
    assert Filter().run(loaded, loaded.entries(), 1, b"\x00") == []


def test_unicast_goes_to_egress_port_with_the_payload_appended() -> None:
    loaded = arch.load(
        program(
            metadata=EGRESS + INGRESS,
            # egress_port = ingress_port + 1; hdr.h.f = 0x42
            control=assign(
                meta("egress_port"),
                f"binary {{ op: BINARY_OP_ADD left {{ {meta('ingress_port')} }} "
                f"right {{ {bits(9, 1)} }} }}",
            )
            + assign(H_F, bits(8, 0x42)),
        )
    )
    assert Switch(ports=4).run(loaded, loaded.entries(), 2, b"\x01payload") == [(3, b"\x42payload")]
    # The filter takes the same decision but leaves the bytes alone.
    assert Filter().run(loaded, loaded.entries(), 2, b"\x01payload") == [(3, b"\x01payload")]


def egress_to(port: int) -> pb.Program:
    return program(metadata=EGRESS, control=assign(meta("egress_port"), bits(9, port)))


@pytest.mark.parametrize("port", [4, 511])
def test_an_egress_port_the_switch_does_not_have_drops_with_a_diagnostic(port: int) -> None:
    """The filter has no port count and passes any bit<9> port through;
    511, BMv2's drop port, is just an out-of-range port here."""
    loaded = arch.load(egress_to(port))
    switch = Switch(ports=4)
    assert switch.run(loaded, loaded.entries(), 0, b"\x01") == []
    assert switch.diagnostics == [f"egress_port {port} is not a port of this switch"]
    assert Filter().run(loaded, loaded.entries(), 0, b"\x01") == [(port, b"\x01")]


def test_the_last_port_is_a_port() -> None:
    loaded = arch.load(egress_to(3))
    switch = Switch(ports=4)
    assert switch.run(loaded, loaded.entries(), 0, b"\x01") == [(3, b"\x01")]
    assert switch.diagnostics == []


def test_an_ingress_port_the_switch_does_not_have_is_the_callers_error() -> None:
    loaded = arch.load(counting_program())
    switch = Switch(ports=4)
    with pytest.raises(ValueError, match="ingress_port 4 is not a port of this switch"):
        switch.run(loaded, loaded.entries(), 4, b"\x00")
    with pytest.raises(ValueError, match="ingress_port 600 is not a port of this switch"):
        switch.run(loaded, loaded.entries(), 600, b"\x00")
    # Before anything runs: the register was never touched.
    assert switch.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x01")]


def test_an_ingress_port_wider_than_bit9_is_the_callers_error_under_the_filter() -> None:
    loaded = arch.load(counting_program())
    with pytest.raises(ValueError, match="ingress_port 512 does not fit in bit<9>"):
        Filter().run(loaded, loaded.entries(), 512, b"\x00")
    assert Filter().run(loaded, loaded.entries(), 511, b"\x00") == [(0, b"\x00")]


# ---------------------------------------------------------------------------
# Rules every architecture shares
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("make", [Filter, lambda: Switch(ports=2)], ids=["filter", "switch"])
def test_a_misaligned_parse_drops_with_a_diagnostic(make: Callable[[], Architecture]) -> None:
    loaded = arch.load(program(metadata=EGRESS, h_width=4))
    architecture = make()
    assert architecture.run(loaded, loaded.entries(), 0, b"\x12") == []
    assert architecture.diagnostics == ["parser consumed 4 bits, not whole bytes; packet dropped"]


PARSER_ERROR_IS_TOO_SHORT = (
    f"binary {{ op: BINARY_OP_EQ left {{ {meta('parser_error')} }} "
    f'right {{ literal {{ error: "PacketTooShort" }} }} }}'
)


def test_parser_error_reaches_the_control_and_the_wire() -> None:
    """The parser fails on g; the control writes the error into h; the
    switch emits h and the byte g could not take as payload."""
    loaded = arch.load(
        program(
            metadata=PARSER_ERROR,
            parser_body=EXTRACT_H + EXTRACT_G,
            control=assign(
                H_F,
                f"mux {{ condition {{ {PARSER_ERROR_IS_TOO_SHORT} }} "
                f"then {{ {bits(8, 0xFF)} }} otherwise {{ {H_F} }} }}",
            ),
        )
    )
    switch = Switch(ports=2)
    assert switch.run(loaded, loaded.entries(), 0, b"\x01\x02") == [(0, b"\xff\x02")]
    assert switch.run(loaded, loaded.entries(), 0, b"\x01\x02\x03") == [(0, b"\x01\x02\x03")]
    assert switch.diagnostics == []


def test_the_filter_can_drop_on_parser_error() -> None:
    loaded = arch.load(
        program(
            metadata=PARSER_ERROR + DROP,
            parser_body=EXTRACT_H + EXTRACT_G,
            control=(
                f"body {{ conditional {{ condition {{ {PARSER_ERROR_IS_TOO_SHORT} }} "
                f"then {{ assign {{ target {{ {meta('drop')} }} "
                f"value {{ literal {{ boolean: true }} }} }} }} }} }}"
            ),
        )
    )
    filter = Filter()
    assert filter.run(loaded, loaded.entries(), 0, b"\x01\x02") == []
    assert filter.run(loaded, loaded.entries(), 0, b"\x01\x02\x03") == [(0, b"\x01\x02\x03")]


def test_without_parser_error_the_control_still_runs_after_a_rejection() -> None:
    loaded = arch.load(
        program(
            metadata=EGRESS,
            parser_body=EXTRACT_H + EXTRACT_G,
            control=assign(meta("egress_port"), bits(9, 1)),
        )
    )
    assert Switch(ports=2).run(loaded, loaded.entries(), 0, b"\x01\x02") == [(1, b"\x01\x02")]


# ---------------------------------------------------------------------------
# Extern state persists across packets
# ---------------------------------------------------------------------------

REGISTER = """
    extern_types {
      name: "register"
      constructor_params { name: "size" type { bits: 32 } direction: DIRECTION_IN }
      methods {
        name: "read"
        params { name: "result" type { bits: 8 } direction: DIRECTION_OUT }
        params { name: "index" type { bits: 32 } direction: DIRECTION_IN }
      }
      methods {
        name: "write"
        params { name: "index" type { bits: 32 } direction: DIRECTION_IN }
        params { name: "value" type { bits: 8 } direction: DIRECTION_IN }
      }
    }
    extern_instances { name: "r" extern_type: "register" args { bits { width: 32 value: "4" } } }
"""

# t = r.read(0); t = t + 1; r.write(0, t); hdr.h.f = t
COUNT = (
    f'body {{ call_extern {{ instance: "r" method: "read" '
    f'args {{ lvalue {{ var: "t" }} }} args {{ expr {{ {bits(32, 0)} }} }} }} }}'
    + assign(
        'var: "t"',
        f'binary {{ op: BINARY_OP_ADD left {{ var: "t" }} right {{ {bits(8, 1)} }} }}',
    )
    + f'body {{ call_extern {{ instance: "r" method: "write" '
    f'args {{ expr {{ {bits(32, 0)} }} }} args {{ expr {{ var: "t" }} }} }} }}'
    + assign(H_F, 'var: "t"')
)


def counting_program() -> pb.Program:
    return program(
        metadata=EGRESS,
        extra=REGISTER,
        locals='locals { name: "t" type { bits: 8 } }',
        control=COUNT,
    )


def test_a_register_counts_across_packets() -> None:
    loaded = arch.load(counting_program())
    switch = Switch(ports=2)
    assert switch.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x01")]
    assert switch.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x02")]
    # The state is the loaded program's, not the architecture's.
    assert Filter().run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x00")]
    assert switch.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x04")]


def test_loading_again_starts_the_register_over() -> None:
    switch = Switch(ports=2)
    for _ in range(2):
        loaded = arch.load(counting_program())
        assert switch.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x01")]
