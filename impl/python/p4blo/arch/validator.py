"""Validate an architectural assembly or a library with separate bindings."""

from __future__ import annotations

from p4blo import ir
from p4blo import validator as core_validator
from p4blo.arch.bindings import BoundIndex, bindings_of, library_of, validate_bindings
from p4blo.arch.v0 import assembly_pb2 as apb
from p4blo.v0 import p4blo_pb2 as pb
from p4blo.validator.diagnostics import (
    ACTION_ARGS,
    ARG_COUNT,
    ARG_DIRECTION,
    ARG_TYPE,
    BLOCK_KIND_SHAPE,
    BLOCK_KIND_STMT,
    CALL_ALIAS,
    CALL_CYCLE,
    CALL_KIND,
    CAST_INVALID,
    ENTRY_DUPLICATE,
    ENTRY_PRIORITY,
    ENTRY_RANGE,
    ENTRY_SHAPE,
    ERROR_LIST,
    EXPORT_DUPLICATE,
    EXPORT_SIGNATURE,
    EXPR_INVALID,
    EXTERN_ARGS,
    EXTERN_RESULT,
    KEY_NAME,
    KEY_TYPE,
    LITERAL_FORMAT,
    LITERAL_RANGE,
    LVALUE_READONLY,
    NAME_DUPLICATE,
    NAME_EMPTY,
    NEXT_ONLY_EXTRACT,
    NOACTION_RESERVED,
    PARAM_DIRECTION,
    PARSER_ONLY,
    PARSER_START_STATE,
    PARSER_TRANSITION,
    REF_KIND,
    REF_UNRESOLVED,
    SCOPE_DECL,
    SCOPE_VAR,
    SELECT_ARITY,
    SELECT_TYPE,
    SLICE_RANGE,
    STACK_COUNT,
    STMT_INVALID,
    TABLE_ACTIONS,
    TABLE_KEY_MIX,
    TABLE_LPM_COUNT,
    TYPE_INVALID,
    TYPE_MISMATCH,
    Diagnostic,
    ValidationError,
)

__all__ = [
    "ACTION_ARGS",
    "ARG_COUNT",
    "ARG_DIRECTION",
    "ARG_TYPE",
    "BLOCK_KIND_SHAPE",
    "BLOCK_KIND_STMT",
    "CALL_ALIAS",
    "CALL_CYCLE",
    "CALL_KIND",
    "CAST_INVALID",
    "ENTRY_DUPLICATE",
    "ENTRY_PRIORITY",
    "ENTRY_RANGE",
    "ENTRY_SHAPE",
    "ERROR_LIST",
    "EXPORT_DUPLICATE",
    "EXPORT_SIGNATURE",
    "EXPR_INVALID",
    "EXTERN_ARGS",
    "EXTERN_RESULT",
    "KEY_NAME",
    "KEY_TYPE",
    "LITERAL_FORMAT",
    "LITERAL_RANGE",
    "LVALUE_READONLY",
    "NAME_DUPLICATE",
    "NAME_EMPTY",
    "NEXT_ONLY_EXTRACT",
    "NOACTION_RESERVED",
    "PARAM_DIRECTION",
    "PARSER_ONLY",
    "PARSER_START_STATE",
    "PARSER_TRANSITION",
    "REF_KIND",
    "REF_UNRESOLVED",
    "SCOPE_DECL",
    "SCOPE_VAR",
    "SELECT_ARITY",
    "SELECT_TYPE",
    "SLICE_RANGE",
    "STACK_COUNT",
    "STMT_INVALID",
    "TABLE_ACTIONS",
    "TABLE_KEY_MIX",
    "TABLE_LPM_COUNT",
    "TYPE_INVALID",
    "TYPE_MISMATCH",
    "Diagnostic",
    "ValidationError",
    "check",
    "validate",
]


def validate(
    source: apb.BlockAssembly | pb.BlockLibrary,
    *,
    bindings: apb.BlockBindings | None = None,
) -> list[Diagnostic]:
    """Return all core and binding diagnostics for this architecture input."""
    library, selected = _inputs(source, bindings)
    diagnostics = core_validator.validate(library)
    try:
        index = ir.Index.build(library)
    except ir.DuplicateName:
        return diagnostics
    diagnostics.extend(validate_bindings(library, index, selected))
    return diagnostics


def check(
    source: apb.BlockAssembly | pb.BlockLibrary,
    *,
    bindings: apb.BlockBindings | None = None,
) -> BoundIndex:
    """Return a validated core index or raise `ValidationError`."""
    diagnostics = validate(source, bindings=bindings)
    if diagnostics:
        raise ValidationError(diagnostics)
    return BoundIndex.build(source, bindings=bindings)


def _inputs(
    source: apb.BlockAssembly | pb.BlockLibrary,
    bindings: apb.BlockBindings | None,
) -> tuple[pb.BlockLibrary, apb.BlockBindings]:
    if isinstance(source, apb.BlockAssembly):
        if bindings is not None:
            raise TypeError("bindings must be omitted for a BlockAssembly")
        return library_of(source), bindings_of(source)
    if isinstance(source, pb.BlockLibrary):
        if bindings is None:
            raise TypeError("bindings are required for a BlockLibrary")
        return source, bindings
    raise TypeError(f"expected BlockAssembly or BlockLibrary, got {type(source).__name__}")
