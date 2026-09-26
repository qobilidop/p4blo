"""Reusable firewall body fixtures and independent expectations."""

from __future__ import annotations

from p4blo.arch import v1model
from p4blo.arch.externs.register import Register
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.interp import stmt
from p4blo.interp.env import Env
from p4blo.interp.packet import Emitter, Packet
from p4blo.interp.values import Bits, Header, Struct, Value
from tests.support.firewall import connection
from tests.support.firewall_semantics import firewall as firewall
from tests.support.forwarder import freeze


def expected_vars() -> dict[str, Value]:
    return {
        "hdr": Struct(
            "headers",
            [
                Header("ethernet_t", False, [Bits(48, 0), Bits(48, 0), Bits(16, 0)]),
                Header(
                    "ipv4_t",
                    False,
                    [Bits(w, 0) for w in [4, 4, 8, 16, 16, 3, 13, 8, 8, 16, 32, 32]],
                ),
                Header(
                    "tcp_t",
                    False,
                    [
                        Bits(w, 0)
                        for w in [16, 16, 32, 32, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 16, 16, 16]
                    ],
                ),
            ],
        ),
        "meta": Struct("metadata", [Bits(9, 0), Bits(9, 0)]),
        "reg_pos_one": Bits(32, 0),
        "reg_pos_two": Bits(32, 0),
        "reg_val_one": Bits(1, 0),
        "reg_val_two": Bits(1, 0),
        "direction": Bits(1, 0),
        "crc16_result": Bits(16, 0),
        "check_ports_hit": False,
    }


def invalid_env(
    program: apb.BlockAssembly, ev: bool, sentinel: bool, overlay: bool, dirty: bool, tcp_shape: int
) -> Env:
    loaded = v1model.load(program)
    installed = loaded.entries(connection()[0].case.entries)
    packet = Packet(bytes.fromhex("deadbeef"))
    packet.cursor = 3
    emitter = Emitter()
    emitter.value, emitter.width = 0x1234, 13
    # Deliberately arbitrary state rather than a claim of fresh initialization.
    for name, values in [("bloom_filter_1", [1, 0, 1]), ("bloom_filter_2", [0, 1])]:
        register = loaded.externs[name]
        assert isinstance(register, Register)
        register.cells[:] = [Bits(1, v) for v in values]
    sentinel_register = Register(2, 8)
    sentinel_register.cells[:] = [Bits(8, 7), Bits(8, 9)]
    loaded.externs["sentinel"] = sentinel_register
    env = Env.for_block(
        loaded.index,
        loaded.index.blocks["MyIngress"],
        loaded.externs,
        entries=installed,
        packet=packet,
        emitter=emitter,
        visits={("sentinel", "state"): 13},
    )
    tcp: Value = [
        Header("tcp_t", False, []),
        Header("tcp_t", True, [Bits(7, 83)]),
        Struct("UnusedUnknown", [True, Bits(65, 0x12345)]),
    ][tcp_shape]
    headers = Struct(
        "headers",
        [
            Header("ethernet_t", ev, [Bits(48, 0x101), Bits(48, 0x202), Bits(16, 0x0800)]),
            Header("ipv4_t", False, [True, Bits(9, 511)] if dirty else []),
            tcp,
        ],
    )
    env.vars["hdr"] = headers
    env.vars["meta"] = Struct("metadata", [Bits(9, 3), Bits(9, 511)])
    # This operational sentinel keeps the independent boolean-state boundary.
    env.vars["untouched_flag"] = sentinel
    if dirty:
        env.vars.update(
            reg_pos_one=Bits(32, 0xFFFFFFFF),
            reg_pos_two=Bits(32, 211),
            reg_val_one=Bits(1, 1),
            reg_val_two=Bits(1, 1),
            direction=Bits(1, 1),
            crc16_result=Bits(16, 0xFFFF),
            check_ports_hit=True,
        )
    env.vars["untouched"] = Struct("Unrelated", [Bits(5, 17), True])
    if overlay:
        env.vars["hdr"] = True
        env.action = "operational-overlay"
        env.action_vars = {"hdr": headers, "reg_pos_one": True, "shadow": Bits(17, 0x12345)}
    return env


def observe_body(env: Env) -> None:
    before = freeze(env)
    stmt.execute(env.block.body, env)
    assert freeze(env) == before, "invalid IPv4 changed complete firewall Env"
