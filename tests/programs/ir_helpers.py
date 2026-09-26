"""Small literal IR constructors shared by runtime observation tests."""

from p4blo.v0 import p4blo_pb2 as pb


def target(*names: str) -> pb.LValue:
    value = pb.LValue(var=names[0])
    for name in names[1:]:
        value = pb.LValue(member=pb.LMember(base=value, field=name))
    return value
