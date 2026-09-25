import p4blo
from p4blo.v0 import p4blo_pb2


def test_version() -> None:
    assert p4blo.__version__ == "0.0.0"


def test_generated_schema_loads() -> None:
    program = p4blo_pb2.BlockLibrary(name="smoke")
    assert program.name == "smoke"
    assert p4blo_pb2.DESCRIPTOR.package == "p4blo.v0"
