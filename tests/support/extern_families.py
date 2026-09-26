"""Shared extern families fixtures and campaign helpers."""

from p4blo.arch.builder import AssemblyBuilder
from p4blo.arch.externs import declarations as externs
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.drt.programs import bits, scalar_program
from p4blo.edsl import core


def family_program(suffix: str) -> apb.BlockAssembly:
    p = scalar_program(bits(8, 42), 8)
    declarations = AssemblyBuilder("declarations")
    register = externs.register(declarations, core.bit(8), f"register{suffix}")
    counter = externs.counter(declarations, f"counter{suffix}")
    checksum = externs.checksum16(declarations, core.bit(16), f"checksum16{suffix}")
    instances = [
        declarations.extern_instance("r", register, 2),
        declarations.extern_instance("c", counter, 2),
        declarations.extern_instance("s", checksum),
    ]
    p.extern_types.extend(t.build() for t in (register, counter, checksum))
    p.extern_instances.extend(i.build() for i in instances)
    return p
