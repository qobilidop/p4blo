"""The v1model metadata contract and packet behavior.

Replay the canonical forwarder and pin initialization, parser-error
continuation, payload alignment, port diagnostics and persistent state.
The six-stage composition and profile boundaries have additional witnesses
in test_v1model.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from p4blo import arch, ir, stf
from p4blo.arch import CONTRACT, ContractError, stf_driver, v1model
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb

CORPUS = Path(__file__).resolve().parents[4] / "tests/programs/corpus/forwarder"
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
) -> apb.BlockAssembly:
    return arch_wire.load_text(f"""
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
        exports {{ role: "ingress" block: "C" }}
        exports {{ role: "deparser" block: "D" }}
        """)


EGRESS = 'fields { name: "egress_spec" type { bits: 9 } }'
INGRESS = 'fields { name: "ingress_port" type { bits: 9 } }'
PARSER_ERROR = 'fields { name: "parser_error" type { error {} } }'


@pytest.fixture(scope="module")
def forwarder() -> arch.Loaded:
    return v1model.load(arch_wire.load_text(CORPUS / "forwarder.txtpb"))


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


def test_the_forwarder_declares_two_contract_fields(forwarder: arch.Loaded) -> None:
    assert CONTRACT.present(forwarder.index) == {"ingress_port", "egress_spec"}


def test_a_program_may_declare_no_contract_field() -> None:
    loaded = v1model.load(program(metadata='fields { name: "color" type { bits: 3 } }'))
    assert CONTRACT.present(loaded.index) == set()
    # Undeclared fields read as their zero value and swallow writes.
    m = loaded.metadata.zero()
    loaded.metadata.write(m, "ingress_port", 3)
    assert loaded.metadata.number(m, "egress_port") == 0
    assert loaded.metadata.number(m, "egress_spec") == 0
    assert loaded.metadata.error(m, "parser_error").name == "NoError"


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ('fields { name: "egress_spec" type { bits: 1 } }', "M.egress_spec must be bit<9>"),
        ('fields { name: "egress_port" type { bits: 8 } }', "M.egress_port must be bit<9>"),
        ('fields { name: "parser_error" type { bits: 3 } }', "M.parser_error must be error"),
    ],
)
def test_a_contract_field_of_the_wrong_type_refuses_to_load(field: str, message: str) -> None:
    with pytest.raises(ContractError, match=message):
        v1model.load(program(metadata=field))


def test_a_missing_role_is_refused_at_load() -> None:
    """The validator does not know which roles an architecture needs, so
    the loader resolves them: a program without them never reaches a packet."""
    full = program(metadata=EGRESS)
    without = apb.BlockAssembly()
    without.CopyFrom(full)
    del without.exports[:]
    with pytest.raises(arch.LoadError, match="missing v1model roles: deparser, ingress, parser"):
        v1model.load(without)
    without.exports.add(role="parser", block="P")
    without.exports.add(role="ingress", block="C")
    with pytest.raises(arch.LoadError, match="missing v1model roles: deparser"):
        v1model.load(without)
    assert dict(v1model.load(full).blocks) == {
        "parser": "P",
        "ingress": "C",
        "deparser": "D",
    }


def test_the_contract_is_the_design_table() -> None:
    table = {(f.name, f.provided) for f in CONTRACT.fields}
    assert table == {
        ("ingress_port", True),
        ("parser_error", True),
        ("egress_spec", False),
        ("egress_port", True),
    }


# ---------------------------------------------------------------------------
# The forwarder under v1model, on the canonical vectors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vector", VECTORS, ids=lambda path: path.stem)
def test_forwarder_under_v1model(forwarder: arch.Loaded, vector: Path) -> None:
    statements = stf.parse(vector.read_text())
    stf.assert_replay(forwarder.index, statements, stf_driver(v1model.V1Model(ports=4), forwarder))


# ---------------------------------------------------------------------------
# v1model packet fate
# ---------------------------------------------------------------------------


def test_unicast_goes_to_egress_spec_with_the_payload_appended() -> None:
    loaded = v1model.load(
        program(
            metadata=EGRESS + INGRESS,
            # egress_spec = ingress_port + 1; hdr.h.f = 0x42
            control=assign(
                meta("egress_spec"),
                f"binary {{ op: BINARY_OP_ADD left {{ {meta('ingress_port')} }} "
                f"right {{ {bits(9, 1)} }} }}",
            )
            + assign(H_F, bits(8, 0x42)),
        )
    )
    assert v1model.V1Model(ports=4).run(loaded, loaded.entries(), 2, b"\x01payload") == [
        (3, b"\x42payload")
    ]


def egress_to(port: int) -> apb.BlockAssembly:
    return program(metadata=EGRESS, control=assign(meta("egress_spec"), bits(9, port)))


def test_an_unconfigured_egress_spec_drops_with_a_diagnostic() -> None:
    loaded = v1model.load(egress_to(4))
    pipeline = v1model.V1Model(ports=4)
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x01") == []
    assert pipeline.diagnostics == ["egress_spec 4 is not a configured v1model port"]


def test_egress_spec_511_drops_without_a_diagnostic() -> None:
    loaded = v1model.load(egress_to(511))
    pipeline = v1model.V1Model(ports=4)
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x01") == []
    assert pipeline.diagnostics == []


def test_the_last_port_is_a_port() -> None:
    loaded = v1model.load(egress_to(3))
    pipeline = v1model.V1Model(ports=4)
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x01") == [(3, b"\x01")]
    assert pipeline.diagnostics == []


def test_an_unconfigured_ingress_port_is_the_callers_error() -> None:
    loaded = v1model.load(counting_program())
    pipeline = v1model.V1Model(ports=4)
    with pytest.raises(ValueError, match="ingress_port 4 is not a configured v1model port"):
        pipeline.run(loaded, loaded.entries(), 4, b"\x00")
    with pytest.raises(ValueError, match="ingress_port 600 is not a configured v1model port"):
        pipeline.run(loaded, loaded.entries(), 600, b"\x00")
    # Before anything runs: the register was never touched.
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x01")]


def test_an_ingress_port_outside_the_supported_range_is_the_callers_error() -> None:
    loaded = v1model.load(counting_program())
    pipeline = v1model.V1Model(ports=511)
    for port in (511, 512):
        with pytest.raises(
            ValueError, match=f"ingress_port {port} is not a configured v1model port"
        ):
            pipeline.run(loaded, loaded.entries(), port, b"\x00")
    # The maximum configured port works, and invalid requests did not execute.
    assert pipeline.run(loaded, loaded.entries(), 510, b"\x00") == [(0, b"\x01")]


# ---------------------------------------------------------------------------
# Parser outcomes and payloads
# ---------------------------------------------------------------------------


def test_a_misaligned_parse_drops_with_a_diagnostic() -> None:
    loaded = v1model.load(program(metadata=EGRESS, h_width=4))
    pipeline = v1model.V1Model(ports=2)
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x12") == []
    assert pipeline.diagnostics == ["parser consumed 4 bits, not whole bytes; packet dropped"]


PARSER_ERROR_IS_TOO_SHORT = (
    f"binary {{ op: BINARY_OP_EQ left {{ {meta('parser_error')} }} "
    f'right {{ literal {{ error: "PacketTooShort" }} }} }}'
)


def test_parser_error_reaches_the_control_and_the_wire() -> None:
    """The parser fails on g; the control writes the error into h; v1model
    emits h and the byte g could not take as payload."""
    loaded = v1model.load(
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
    pipeline = v1model.V1Model(ports=2)
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x01\x02") == [(0, b"\xff\x02")]
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x01\x02\x03") == [(0, b"\x01\x02\x03")]
    assert pipeline.diagnostics == []


def test_ingress_can_drop_on_parser_error() -> None:
    loaded = v1model.load(
        program(
            metadata=PARSER_ERROR + EGRESS,
            parser_body=EXTRACT_H + EXTRACT_G,
            control=(
                f"body {{ conditional {{ condition {{ {PARSER_ERROR_IS_TOO_SHORT} }} "
                f"then {{ assign {{ target {{ {meta('egress_spec')} }} "
                f"value {{ {bits(9, 511)} }} }} }} }} }}"
            ),
        )
    )
    pipeline = v1model.V1Model(ports=4)
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x01\x02") == []
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x01\x02\x03") == [(0, b"\x01\x02\x03")]


def test_without_parser_error_the_control_still_runs_after_a_rejection() -> None:
    loaded = v1model.load(
        program(
            metadata=EGRESS,
            parser_body=EXTRACT_H + EXTRACT_G,
            control=assign(meta("egress_spec"), bits(9, 1)),
        )
    )
    assert v1model.V1Model(ports=2).run(loaded, loaded.entries(), 0, b"\x01\x02") == [
        (1, b"\x01\x02")
    ]


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


def counting_program() -> apb.BlockAssembly:
    return program(
        metadata=EGRESS,
        extra=REGISTER,
        locals='locals { name: "t" type { bits: 8 } }',
        control=COUNT,
    )


def test_a_register_counts_across_packets() -> None:
    loaded = v1model.load(counting_program())
    pipeline = v1model.V1Model(ports=2)
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x01")]
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x02")]
    # A fresh pipeline instance shares the loaded program's existing state.
    assert v1model.V1Model(ports=2).run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x03")]
    assert pipeline.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x04")]


def test_loading_again_starts_the_register_over() -> None:
    pipeline = v1model.V1Model(ports=2)
    for _ in range(2):
        loaded = v1model.load(counting_program())
        assert pipeline.run(loaded, loaded.entries(), 0, b"\x00") == [(0, b"\x01")]
