# expect: reportCallIssue line 49
# expect: reportArgumentType line 53
"""A const entry value of the wrong width: a 16-bit value for an 8-bit key.

`keys=(...)` as a tuple selects `Table`'s typed overloads, which type the
entries by the key widths; `keys=[...]` as a list is the untyped form,
kept for generated programs, and its entries are checked at run time.
`Table.__init__` is overloaded over the key arity, so the mismatch is
reported twice: once as the failed overload resolution on the `Table(`
call, once as the argument that made it fail.
"""

from __future__ import annotations

from p4blo.edsl import (
    Bool,
    Control,
    Header,
    Struct,
    Table,
    action,
    bit8,
    bit9,
    bit16,
    entry,
    exact,
)


class h_t(Header):
    f8: bit8
    f16: bit16


class headers(Struct):
    h: h_t


class metadata(Struct):
    egress_port: bit9
    drop: Bool


class MyIngress(Control[headers, metadata]):
    @action
    def drop(self) -> None:
        self.assign(self.meta.drop, True)

    t = Table(
        keys=(exact(headers.h.f8),),
        actions=[drop],
        default=drop(),
        entries=[entry(bit8(1), drop()), entry(bit16(2), drop())],  # the key is 8 bits
    )

    def apply(self) -> None:
        self.apply_table(self.t)
