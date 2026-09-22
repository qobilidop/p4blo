import pytest

from p4blo import externs, ir
from p4blo.externs.checksum import internet_checksum
from p4blo.interp.values import Bits


def register_decl(*, name: str = "register", value_width: int = 16, extra: str = "") -> str:
    return f"""
    extern_types {{
      name: "{name}"
      constructor_params {{ name: "size" type {{ bits: 32 }} direction: DIRECTION_IN }}
      methods {{
        name: "read"
        params {{ name: "result" type {{ bits: 16 }} direction: DIRECTION_OUT }}
        params {{ name: "index" type {{ bits: 32 }} direction: DIRECTION_IN }}
      }}
      methods {{
        name: "write"
        params {{ name: "index" type {{ bits: 32 }} direction: DIRECTION_IN }}
        params {{ name: "value" type {{ bits: {value_width} }} direction: DIRECTION_IN }}
      }}
      {extra}
    }}
    """


def instance(*, extern_type: str = "register", arg_width: int = 32) -> str:
    return f"""
    extern_instances {{
      name: "r" extern_type: "{extern_type}"
      args {{ bits {{ width: {arg_width} value: "4" }} }}
    }}
    """


def program(extern_types: str, instances: str) -> ir.Index:
    return ir.Index.build(
        ir.load_text(
            f"""
            errors: "NoError"
            struct_types {{ name: "H" }}
            struct_types {{ name: "M" }}
            headers: "H"
            metadata: "M"
            {extern_types}
            {instances}
            """
        )
    )


def test_register_binds_and_runs() -> None:
    bound = externs.default_registry().bind(program(register_decl(), instance()))
    r = bound["r"]
    assert r.call("read", [Bits(16, 0), Bits(32, 1)]).outs == (Bits(16, 0),)
    r.call("write", [Bits(32, 1), Bits(16, 0xABCD)])
    assert r.call("read", [Bits(16, 0), Bits(32, 1)]).outs == (Bits(16, 0xABCD),)
    # Out of range: read zero, write ignored.
    assert r.call("read", [Bits(16, 0), Bits(32, 9)]).outs == (Bits(16, 0),)
    r.call("write", [Bits(32, 9), Bits(16, 1)])


def test_extra_method_refuses_to_bind() -> None:
    decl = register_decl(extra='methods { name: "clear" }')
    with pytest.raises(externs.BindError, match="methods"):
        externs.default_registry().bind(program(decl, instance()))


def test_inconsistent_width_variable_refuses_to_bind() -> None:
    decl = register_decl(value_width=8)
    with pytest.raises(externs.BindError, match="T is bit<16> elsewhere"):
        externs.default_registry().bind(program(decl, instance()))


def test_unknown_extern_refuses_to_bind() -> None:
    decl = register_decl(name="mystery")
    with pytest.raises(externs.BindError, match="no implementation"):
        externs.default_registry().bind(program(decl, instance(extern_type="mystery")))


def test_constructor_arg_must_fit() -> None:
    with pytest.raises(externs.BindError, match="does not fit"):
        externs.default_registry().bind(program(register_decl(), instance(arg_width=8)))


def test_internet_checksum_rfc1071_example() -> None:
    # The worked example from RFC 1071 section 3.
    data = bytes([0x00, 0x01, 0xF2, 0x03, 0xF4, 0xF5, 0xF6, 0xF7])
    assert internet_checksum(data) == (~0xDDF2) & 0xFFFF


def test_checksum_validates_ipv4_header() -> None:
    header = bytes.fromhex("450000730000400040110000c0a80001c0a800c7")
    checksum = internet_checksum(header)
    with_checksum = header[:10] + checksum.to_bytes(2, "big") + header[12:]
    assert internet_checksum(with_checksum) == 0
    assert checksum == 0xB861
