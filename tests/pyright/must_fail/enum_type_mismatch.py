# expect: reportCallIssue line 42
# expect: reportArgumentType line 42
"""A member of one enum assigned to a place of another.

`assign` is overloaded over the kinds of target, so the failure shows as
both the failed overload resolution and the argument that caused it.
"""

from __future__ import annotations

from p4blo.edsl import Bool, Control, Enum, Header, Struct, Transition, bit8, state
from p4blo.arch import assemble
from p4blo.edsl import Deparser, Parser, BlockLibrary


class Color(Enum):
    RED: Color
    GREEN: Color


class Shape(Enum):
    ROUND: Shape
    FLAT: Shape


class h_t(Header):
    f: bit8


class headers(Struct):
    h: h_t


class metadata(Struct):
    c: Color
    drop: Bool


class MyIngress(Control[headers, metadata]):
    def apply(self) -> None:
        self.assign(self.meta.c, Color.RED)
        self.assign(self.meta.c, Shape.FLAT)  # error: a Shape into a Color place


class MyParser(Parser[headers, metadata]):
    @state(start=True)
    def start(self) -> Transition:
        self.extract(self.hdr.h)
        return self.accept


class MyDeparser(Deparser[headers]):
    def apply(self) -> None:
        self.emit(self.hdr.h)


program = assemble(BlockLibrary(MyParser, MyIngress, MyDeparser), name="enums", headers=headers, metadata=metadata, exports={"parser": MyParser, "control": MyIngress, "deparser": MyDeparser})
