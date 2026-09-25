"""The validator's diagnostic codes, and the two ways it reports them.

Each code is its own name as a string, so a diagnostic prints and compares
as the code; the package docstring lists what each one means, grouped as
the modules of this package are. Every diagnostic carries a protobuf-style
path to the offending element.
"""

from __future__ import annotations

from dataclasses import dataclass

NAME_EMPTY = "NAME_EMPTY"
NAME_DUPLICATE = "NAME_DUPLICATE"
ERROR_LIST = "ERROR_LIST"
REF_UNRESOLVED = "REF_UNRESOLVED"
REF_KIND = "REF_KIND"
SCOPE_VAR = "SCOPE_VAR"
SCOPE_DECL = "SCOPE_DECL"
EXPORT_DUPLICATE = "EXPORT_DUPLICATE"
EXPORT_SIGNATURE = "EXPORT_SIGNATURE"
TYPE_INVALID = "TYPE_INVALID"
LITERAL_FORMAT = "LITERAL_FORMAT"
LITERAL_RANGE = "LITERAL_RANGE"
BLOCK_KIND_SHAPE = "BLOCK_KIND_SHAPE"
PARSER_START_STATE = "PARSER_START_STATE"
BLOCK_KIND_STMT = "BLOCK_KIND_STMT"
PARSER_ONLY = "PARSER_ONLY"
NEXT_ONLY_EXTRACT = "NEXT_ONLY_EXTRACT"
PARAM_DIRECTION = "PARAM_DIRECTION"
EXPR_INVALID = "EXPR_INVALID"
STMT_INVALID = "STMT_INVALID"
TYPE_MISMATCH = "TYPE_MISMATCH"
CAST_INVALID = "CAST_INVALID"
SLICE_RANGE = "SLICE_RANGE"
LVALUE_READONLY = "LVALUE_READONLY"
STACK_COUNT = "STACK_COUNT"
ARG_COUNT = "ARG_COUNT"
ARG_DIRECTION = "ARG_DIRECTION"
ARG_TYPE = "ARG_TYPE"
CALL_KIND = "CALL_KIND"
CALL_ALIAS = "CALL_ALIAS"
CALL_CYCLE = "CALL_CYCLE"
EXTERN_RESULT = "EXTERN_RESULT"
PARSER_TRANSITION = "PARSER_TRANSITION"
SELECT_ARITY = "SELECT_ARITY"
SELECT_TYPE = "SELECT_TYPE"
KEY_NAME = "KEY_NAME"
KEY_TYPE = "KEY_TYPE"
TABLE_LPM_COUNT = "TABLE_LPM_COUNT"
TABLE_KEY_MIX = "TABLE_KEY_MIX"
TABLE_ACTIONS = "TABLE_ACTIONS"
NOACTION_RESERVED = "NOACTION_RESERVED"
ACTION_ARGS = "ACTION_ARGS"
ENTRY_SHAPE = "ENTRY_SHAPE"
ENTRY_RANGE = "ENTRY_RANGE"
ENTRY_PRIORITY = "ENTRY_PRIORITY"
ENTRY_DUPLICATE = "ENTRY_DUPLICATE"
EXTERN_ARGS = "EXTERN_ARGS"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    path: str

    def __str__(self) -> str:
        return f"{self.path}: {self.code}: {self.message}"


class ValidationError(Exception):
    """`check` found at least one problem; `diagnostics` lists them all."""

    diagnostics: list[Diagnostic]

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("\n".join(str(d) for d in diagnostics))
        self.diagnostics = diagnostics
