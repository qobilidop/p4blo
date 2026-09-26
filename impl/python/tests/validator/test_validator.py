"""One valid program, then one malformed program per rule.

`VALID` exercises every construct the validator knows; each test below takes
a fresh copy, breaks one thing, and asserts the code that names the break.
The corpus programs must validate too.
"""

from pathlib import Path

import pytest

from p4blo.arch import validator as v
from p4blo.arch import wire as arch_wire
from p4blo.arch.v0 import assembly_pb2 as apb
from tests.support import validator_scenarios as scenarios
from tests.support.validator_scenarios import CORPUS

# -- helpers --------------------------------------------------------------------


def codes(program: apb.BlockAssembly) -> list[str]:
    return [d.code for d in v.validate(program)]


# -- the valid program ---------------------------------------------------------


def test_valid_program_has_no_diagnostics() -> None:
    assert v.validate(scenarios.valid_program_has_no_diagnostics()) == []


def test_check_returns_index() -> None:
    index = v.check(scenarios.check_returns_index())
    assert set(index.blocks) == {"prs", "ing", "sub", "dep"}


def test_check_raises_with_diagnostics() -> None:
    with pytest.raises(v.ValidationError) as info:
        v.check(scenarios.check_raises_with_diagnostics())
    assert [d.code for d in info.value.diagnostics] == [v.REF_UNRESOLVED]
    assert "headers" in str(info.value)


def test_diagnostic_paths_are_protobuf_style() -> None:
    (diag,) = v.validate(scenarios.diagnostic_paths_are_protobuf_style())
    assert diag.code == v.TYPE_MISMATCH
    assert diag.path == "blocks[1].body[2].assign"
    assert str(diag).startswith("blocks[1].body[2].assign: TYPE_MISMATCH: ")


def test_nested_path() -> None:
    (diag,) = v.validate(scenarios.nested_path())
    assert diag.code == v.SELECT_TYPE
    assert diag.path == "blocks[0].states[0].transition.select.cases[1].sets[0].masked.mask"


# -- structure and names ---------------------------------------------------------


@pytest.mark.parametrize("mutate", scenarios.NAME_DUPLICATE_PARAMETERS_0)
def test_name_duplicate(mutate) -> None:
    assert v.NAME_DUPLICATE in codes(scenarios.name_duplicate(mutate))


@pytest.mark.parametrize("mutate", scenarios.NAME_EMPTY_PARAMETERS_0)
def test_name_empty(mutate) -> None:
    assert v.NAME_EMPTY in codes(scenarios.name_empty(mutate))


def test_index_failure_stops_validation() -> None:
    assert codes(scenarios.index_failure_stops_validation()) == [v.NAME_DUPLICATE]


@pytest.mark.parametrize("mutate", scenarios.ERROR_LIST_PARAMETERS_0)
def test_error_list(mutate) -> None:
    assert v.ERROR_LIST in codes(scenarios.error_list(mutate))


@pytest.mark.parametrize("mutate", scenarios.REF_UNRESOLVED_PARAMETERS_0)
def test_ref_unresolved(mutate) -> None:
    assert v.REF_UNRESOLVED in codes(scenarios.ref_unresolved(mutate))


@pytest.mark.parametrize("mutate", scenarios.REF_KIND_PARAMETERS_0)
def test_ref_kind(mutate) -> None:
    assert v.REF_KIND in codes(scenarios.ref_kind(mutate))


@pytest.mark.parametrize("mutate", scenarios.SCOPE_VAR_PARAMETERS_0)
def test_scope_var(mutate) -> None:
    assert v.SCOPE_VAR in codes(scenarios.scope_var(mutate))


@pytest.mark.parametrize("mutate", scenarios.SCOPE_DECL_PARAMETERS_0)
def test_scope_decl(mutate) -> None:
    assert v.SCOPE_DECL in codes(scenarios.scope_decl(mutate))


def test_scope_decl_state_of_another_parser() -> None:
    assert v.SCOPE_DECL in codes(scenarios.scope_decl_state_of_another_parser())


def test_export_duplicate() -> None:
    assert v.EXPORT_DUPLICATE in codes(scenarios.export_duplicate())


@pytest.mark.parametrize("mutate", scenarios.EXPORT_SIGNATURE_PARAMETERS_0)
def test_export_signature(mutate) -> None:
    assert v.EXPORT_SIGNATURE in codes(scenarios.export_signature(mutate))


def test_unexported_block_may_have_any_signature() -> None:
    assert codes(scenarios.unexported_block_may_have_any_signature()) == []


# -- types and literals ----------------------------------------------------------


@pytest.mark.parametrize("mutate", scenarios.TYPE_INVALID_PARAMETERS_0)
def test_type_invalid(mutate) -> None:
    assert v.TYPE_INVALID in codes(scenarios.type_invalid(mutate))


def test_struct_cycle_through_another_struct() -> None:
    (diag,) = v.validate(scenarios.struct_cycle_through_another_struct())
    assert diag.code == v.TYPE_INVALID
    assert "A -> B -> A" in diag.message


@pytest.mark.parametrize("mutate", scenarios.LITERAL_FORMAT_PARAMETERS_0)
def test_literal_format(mutate) -> None:
    assert v.LITERAL_FORMAT in codes(scenarios.literal_format(mutate))


@pytest.mark.parametrize("mutate", scenarios.LITERAL_RANGE_PARAMETERS_0)
def test_literal_range(mutate) -> None:
    assert v.LITERAL_RANGE in codes(scenarios.literal_range(mutate))


# -- blocks ------------------------------------------------------------------------


@pytest.mark.parametrize("mutate", scenarios.BLOCK_KIND_SHAPE_PARAMETERS_0)
def test_block_kind_shape(mutate) -> None:
    assert v.BLOCK_KIND_SHAPE in codes(scenarios.block_kind_shape(mutate))


@pytest.mark.parametrize("start", scenarios.PARSER_START_STATE_PARAMETERS_0)
def test_parser_start_state(start: str) -> None:
    assert v.PARSER_START_STATE in codes(scenarios.parser_start_state(start))


@pytest.mark.parametrize(
    "block, text", scenarios.BLOCK_KIND_STMT_IN_CONTROL_OR_DEPARSER_PARAMETERS_0
)
def test_block_kind_stmt_in_control_or_deparser(block: int, text: str) -> None:
    assert v.BLOCK_KIND_STMT in codes(scenarios.block_kind_stmt_in_control_or_deparser(block, text))


@pytest.mark.parametrize("text", scenarios.BLOCK_KIND_STMT_IN_PARSER_PARAMETERS_0)
def test_block_kind_stmt_in_parser(text: str) -> None:
    assert v.BLOCK_KIND_STMT in codes(scenarios.block_kind_stmt_in_parser(text))


@pytest.mark.parametrize("text", scenarios.BLOCK_KIND_STMT_IN_ACTION_PARAMETERS_0)
def test_block_kind_stmt_in_action(text: str) -> None:
    assert v.BLOCK_KIND_STMT in codes(scenarios.block_kind_stmt_in_action(text))


@pytest.mark.parametrize("block, text", scenarios.PARSER_ONLY_PARAMETERS_0)
def test_parser_only(block: int, text: str) -> None:
    assert v.PARSER_ONLY in codes(scenarios.parser_only(block, text))


def test_last_index_in_an_action_is_parser_only() -> None:
    assert v.PARSER_ONLY in codes(scenarios.last_index_in_an_action_is_parser_only())


def test_last_index_in_a_parser_is_fine() -> None:
    assert codes(scenarios.last_index_in_a_parser_is_fine()) == []


@pytest.mark.parametrize("text", scenarios.NEXT_ONLY_EXTRACT_IN_A_PARSER_PARAMETERS_0)
def test_next_only_extract_in_a_parser(text: str) -> None:
    assert v.NEXT_ONLY_EXTRACT in codes(scenarios.next_only_extract_in_a_parser(text))


def test_next_only_extract_in_a_control() -> None:
    assert codes(scenarios.next_only_extract_in_a_control()) == [v.NEXT_ONLY_EXTRACT]


@pytest.mark.parametrize("mutate", scenarios.PARAM_DIRECTION_PARAMETERS_0)
def test_param_direction(mutate) -> None:
    assert v.PARAM_DIRECTION in codes(scenarios.param_direction(mutate))


def test_action_with_directed_params_is_fine_when_only_called() -> None:
    assert codes(scenarios.action_with_directed_params_is_fine_when_only_called()) == []


# -- expressions, lvalues and statements -----------------------------------------


@pytest.mark.parametrize("text", scenarios.EXPR_INVALID_PARAMETERS_0)
def test_expr_invalid(text: str) -> None:
    assert v.EXPR_INVALID in codes(scenarios.expr_invalid(text))


def test_stmt_invalid() -> None:
    assert v.STMT_INVALID in codes(scenarios.stmt_invalid())


@pytest.mark.parametrize("text", scenarios.TYPE_MISMATCH_IN_CONTROL_PARAMETERS_0)
def test_type_mismatch_in_control(text: str) -> None:
    assert v.TYPE_MISMATCH in codes(scenarios.type_mismatch_in_control(text))


@pytest.mark.parametrize("text", scenarios.TYPE_MISMATCH_IN_PARSER_PARAMETERS_0)
def test_type_mismatch_in_parser(text: str) -> None:
    assert v.TYPE_MISMATCH in codes(scenarios.type_mismatch_in_parser(text))


def test_lookahead_of_bits_boolean_and_header_is_fine() -> None:
    assert codes(scenarios.lookahead_of_bits_boolean_and_header_is_fine()) == []


@pytest.mark.parametrize("text", scenarios.TYPE_MISMATCH_IN_DEPARSER_PARAMETERS_0)
def test_type_mismatch_in_deparser(text: str) -> None:
    assert v.TYPE_MISMATCH in codes(scenarios.type_mismatch_in_deparser(text))


def test_emit_of_struct_with_scalar_field_is_rejected() -> None:
    assert codes(scenarios.emit_of_struct_with_scalar_field_is_rejected()) == [v.TYPE_MISMATCH]


def test_emit_of_headers_struct_is_fine() -> None:
    assert codes(scenarios.emit_of_headers_struct_is_fine()) == []


@pytest.mark.parametrize("text", scenarios.CAST_INVALID_PARAMETERS_0)
def test_cast_invalid(text: str) -> None:
    assert v.CAST_INVALID in codes(scenarios.cast_invalid(text))


def test_bit1_and_boolean_casts_are_fine() -> None:
    assert codes(scenarios.bit1_and_boolean_casts_are_fine()) == []


@pytest.mark.parametrize("hi, lo", scenarios.SLICE_RANGE_PARAMETERS_0)
def test_slice_range(hi: int, lo: int) -> None:
    assert v.SLICE_RANGE in codes(scenarios.slice_range(hi, lo))


def test_slice_width() -> None:
    assert codes(scenarios.slice_width()) == []


@pytest.mark.parametrize("mutate", scenarios.LVALUE_READONLY_PARAMETERS_0)
def test_lvalue_readonly(mutate) -> None:
    assert v.LVALUE_READONLY in codes(scenarios.lvalue_readonly(mutate))


@pytest.mark.parametrize("text", scenarios.STACK_COUNT_PARAMETERS_0)
def test_stack_count(text: str) -> None:
    assert v.STACK_COUNT in codes(scenarios.stack_count(text))


@pytest.mark.parametrize("text", scenarios.ARG_COUNT_PARAMETERS_0)
def test_arg_count(text: str) -> None:
    assert v.ARG_COUNT in codes(scenarios.arg_count(text))


@pytest.mark.parametrize("text", scenarios.ARG_DIRECTION_PARAMETERS_0)
def test_arg_direction(text: str) -> None:
    assert v.ARG_DIRECTION in codes(scenarios.arg_direction(text))


@pytest.mark.parametrize("text", scenarios.ARG_TYPE_PARAMETERS_0)
def test_arg_type(text: str) -> None:
    assert v.ARG_TYPE in codes(scenarios.arg_type(text))


@pytest.mark.parametrize("mutate", scenarios.CALL_KIND_PARAMETERS_0)
def test_call_kind(mutate) -> None:
    assert v.CALL_KIND in codes(scenarios.call_kind(mutate))


def test_deparser_may_call_a_deparser() -> None:
    assert codes(scenarios.deparser_may_call_a_deparser()) == []


@pytest.mark.parametrize("text", scenarios.CALL_ALIAS_PARAMETERS_0)
def test_call_alias(text: str) -> None:
    assert v.CALL_ALIAS in codes(scenarios.call_alias(text))


@pytest.mark.parametrize("text", scenarios.NO_ALIAS_PARAMETERS_0)
def test_no_alias(text: str) -> None:
    assert codes(scenarios.no_alias(text)) == []


@pytest.mark.parametrize("mutate", scenarios.CALL_CYCLE_PARAMETERS_0)
def test_call_cycle(mutate) -> None:
    assert v.CALL_CYCLE in codes(scenarios.call_cycle(mutate))


def test_call_cycle_message_and_path() -> None:
    (diag,) = v.validate(scenarios.call_cycle_message_and_path())
    assert diag.code == v.CALL_CYCLE
    assert "ing -> sub -> ing" in diag.message
    assert diag.path == "blocks[2].body[1].call_block"


def test_action_call_cycle() -> None:
    assert v.CALL_CYCLE in codes(scenarios.action_call_cycle())


def test_mutual_action_call_cycle_message_and_path() -> None:
    (diag,) = v.validate(scenarios.mutual_action_call_cycle_message_and_path())
    assert diag.code == v.CALL_CYCLE
    assert "drop -> fwd -> drop" in diag.message
    assert diag.path == "blocks[1].actions[1].body[2].call_action"


def test_actions_may_call_actions_without_a_cycle() -> None:
    assert codes(scenarios.actions_may_call_actions_without_a_cycle()) == []


@pytest.mark.parametrize("text", scenarios.EXTERN_RESULT_PARAMETERS_0)
def test_extern_result(text: str) -> None:
    assert v.EXTERN_RESULT in codes(scenarios.extern_result(text))


# -- parsers -----------------------------------------------------------------------


@pytest.mark.parametrize("mutate", scenarios.PARSER_TRANSITION_PARAMETERS_0)
def test_parser_transition(mutate) -> None:
    assert v.PARSER_TRANSITION in codes(scenarios.parser_transition(mutate))


@pytest.mark.parametrize("mutate", scenarios.SELECT_ARITY_PARAMETERS_0)
def test_select_arity(mutate) -> None:
    assert v.SELECT_ARITY in codes(scenarios.select_arity(mutate))


@pytest.mark.parametrize("mutate", scenarios.SELECT_TYPE_PARAMETERS_0)
def test_select_type(mutate) -> None:
    assert v.SELECT_TYPE in codes(scenarios.select_type(mutate))


def test_select_on_boolean_and_enum_keys() -> None:
    assert codes(scenarios.select_on_boolean_and_enum_keys()) == []


# -- tables ------------------------------------------------------------------------


def test_ternary_table_is_valid() -> None:
    assert codes(scenarios.ternary_table_is_valid()) == []


def test_key_name() -> None:
    assert v.KEY_NAME in codes(scenarios.key_name())


@pytest.mark.parametrize("mutate", scenarios.KEY_TYPE_PARAMETERS_0)
def test_key_type(mutate) -> None:
    assert v.KEY_TYPE in codes(scenarios.key_type(mutate))


def test_table_lpm_count() -> None:
    assert v.TABLE_LPM_COUNT in codes(scenarios.table_lpm_count())


def test_table_key_mix() -> None:
    assert v.TABLE_KEY_MIX in codes(scenarios.table_key_mix())


@pytest.mark.parametrize("mutate", scenarios.TABLE_ACTIONS_PARAMETERS_0)
def test_table_actions(mutate) -> None:
    assert v.TABLE_ACTIONS in codes(scenarios.table_actions(mutate))


@pytest.mark.parametrize("mutate", scenarios.NOACTION_RESERVED_PARAMETERS_0)
def test_noaction_reserved(mutate) -> None:
    assert v.NOACTION_RESERVED in codes(scenarios.noaction_reserved(mutate))


def test_an_empty_noaction_may_be_declared() -> None:
    assert codes(scenarios.an_empty_noaction_may_be_declared()) == []


@pytest.mark.parametrize("mutate", scenarios.ACTION_ARGS_PARAMETERS_0)
def test_action_args(mutate) -> None:
    assert v.ACTION_ARGS in codes(scenarios.action_args(mutate))


@pytest.mark.parametrize("mutate", scenarios.ENTRY_SHAPE_PARAMETERS_0)
def test_entry_shape(mutate) -> None:
    assert v.ENTRY_SHAPE in codes(scenarios.entry_shape(mutate))


@pytest.mark.parametrize("entries", scenarios.ENTRY_SHAPE_TERNARY_AND_EXACT_PARAMETERS_0)
def test_entry_shape_ternary_and_exact(entries: str) -> None:
    assert v.ENTRY_SHAPE in codes(scenarios.entry_shape_ternary_and_exact(entries))


@pytest.mark.parametrize("mutate", scenarios.ENTRY_RANGE_PARAMETERS_0)
def test_entry_range(mutate) -> None:
    assert v.ENTRY_RANGE in codes(scenarios.entry_range(mutate))


@pytest.mark.parametrize("entries", scenarios.ENTRY_RANGE_TERNARY_AND_EXACT_PARAMETERS_0)
def test_entry_range_ternary_and_exact(entries: str) -> None:
    assert v.ENTRY_RANGE in codes(scenarios.entry_range_ternary_and_exact(entries))


def test_entry_priority_on_non_ternary_table() -> None:
    assert v.ENTRY_PRIORITY in codes(scenarios.entry_priority_on_non_ternary_table())


@pytest.mark.parametrize("entries", scenarios.ENTRY_PRIORITY_OVERLAP_PARAMETERS_0)
def test_entry_priority_overlap(entries: str) -> None:
    assert codes(scenarios.entry_priority_overlap(entries)) == [v.ENTRY_PRIORITY]


@pytest.mark.parametrize("entries", scenarios.ENTRY_PRIORITY_NO_OVERLAP_PARAMETERS_0)
def test_entry_priority_no_overlap(entries: str) -> None:
    assert codes(scenarios.entry_priority_no_overlap(entries)) == []


def test_entry_duplicate() -> None:
    assert v.ENTRY_DUPLICATE in codes(scenarios.entry_duplicate())


def test_lpm_entry_must_be_canonical() -> None:
    assert v.ENTRY_RANGE in codes(scenarios.lpm_entry_must_be_canonical())


def test_ternary_entry_must_be_canonical() -> None:
    assert v.ENTRY_RANGE in codes(scenarios.ternary_entry_must_be_canonical())


def test_lpm_entries_with_different_prefixes_are_fine() -> None:
    assert codes(scenarios.lpm_entries_with_different_prefixes_are_fine()) == []


@pytest.mark.parametrize("key", scenarios.TABLE_KEYS_ARE_BITS_ONLY_PARAMETERS_0)
def test_table_keys_are_bits_only(key: str) -> None:
    assert v.KEY_TYPE in codes(scenarios.table_keys_are_bits_only(key))


def test_apply_inside_an_action_is_rejected() -> None:
    assert v.BLOCK_KIND_STMT in codes(scenarios.apply_inside_an_action_is_rejected())


def test_derived_key_names_collide() -> None:
    assert v.KEY_NAME in codes(scenarios.derived_key_names_collide())


# -- externs -----------------------------------------------------------------------


@pytest.mark.parametrize("mutate", scenarios.EXTERN_ARGS_PARAMETERS_0)
def test_extern_args(mutate) -> None:
    assert v.EXTERN_ARGS in codes(scenarios.extern_args(mutate))


# -- the corpus ------------------------------------------------------------------


@pytest.mark.parametrize("program", sorted(CORPUS.glob("*/*.txtpb")), ids=lambda p: p.stem)
def test_corpus_programs_validate(program: Path) -> None:
    assert v.validate(arch_wire.load_text(program)) == []
