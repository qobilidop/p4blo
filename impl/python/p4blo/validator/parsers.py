"""Parser states: their bodies, transitions and select expressions."""

from __future__ import annotations

from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    PARSER_TRANSITION,
    SELECT_ARITY,
    SELECT_TYPE,
)
from p4blo.validator.names import (
    Scope,
)
from p4blo.validator.statements import StatementChecks
from p4blo.validator.types import (
    SCALAR_KINDS,
    describe,
    is_bits,
    kind_of,
    same_type,
)


class ParserChecks(StatementChecks):
    """Parser states, transitions and key sets."""

    def check_state(self, state: pb.State, scope: Scope, path: str) -> None:
        self.check_stmts(state.body, scope, f"{path}.body")
        tpath = f"{path}.transition"
        match state.transition.WhichOneof("kind"):
            case "direct":
                self.check_target(state.transition.direct, scope, f"{tpath}.direct")
            case "select":
                self.check_select(state.transition.select, scope, f"{tpath}.select")
            case _:
                self.report(PARSER_TRANSITION, "state has no transition", tpath)

    def check_target(self, target: pb.Target, scope: Scope, path: str) -> None:
        match target.WhichOneof("kind"):
            case "state":
                self.resolve_local(
                    target.state, scope.names.states, "state", scope, f"{path}.state"
                )
            case "accept" | "reject":
                pass
            case _:
                self.report(PARSER_TRANSITION, "target has no kind", path)

    def check_select(self, select: pb.Select, scope: Scope, path: str) -> None:
        if not select.keys:
            self.report(SELECT_ARITY, "select has no keys", path)
        key_types: list[pb.Type | None] = []
        for i, key in enumerate(select.keys):
            t = self.type_of(key, scope, f"{path}.keys[{i}]")
            if t is not None and kind_of(t) not in SCALAR_KINDS:
                self.report(
                    SELECT_TYPE,
                    f"select key must be a scalar, got {describe(t)}",
                    f"{path}.keys[{i}]",
                )
                t = None
            key_types.append(t)
        for i, case in enumerate(select.cases):
            cpath = f"{path}.cases[{i}]"
            if len(case.sets) != len(select.keys):
                self.report(
                    SELECT_ARITY,
                    f"case has {len(case.sets)} sets for {len(select.keys)} keys",
                    f"{cpath}.sets",
                )
            else:
                for j, (key_set, key_type) in enumerate(zip(case.sets, key_types, strict=True)):
                    self.check_key_set(key_set, key_type, f"{cpath}.sets[{j}]")
            self.check_target(case.target, scope, f"{cpath}.target")

    def check_key_set(self, key_set: pb.KeySet, key: pb.Type | None, path: str) -> None:
        def literal_of_key(lit: pb.Literal, lpath: str) -> None:
            t = self.type_of_literal(lit, lpath)
            if key is not None and t is not None and not same_type(t, key):
                self.report(SELECT_TYPE, f"key is {describe(key)}, literal is {describe(t)}", lpath)

        def bits_key(what: str) -> bool:
            if key is not None and not is_bits(key):
                self.report(SELECT_TYPE, f"{what} needs a bits key, got {describe(key)}", path)
                return False
            return True

        match key_set.WhichOneof("kind"):
            case "exact":
                literal_of_key(key_set.exact, f"{path}.exact")
            case "masked":
                if bits_key("masked"):
                    literal_of_key(key_set.masked.value, f"{path}.masked.value")
                    literal_of_key(key_set.masked.mask, f"{path}.masked.mask")
            case "range":
                if bits_key("range"):
                    literal_of_key(key_set.range.lo, f"{path}.range.lo")
                    literal_of_key(key_set.range.hi, f"{path}.range.hi")
            case "dont_care":
                pass
            case _:
                self.report(SELECT_TYPE, "key set has no kind", path)
