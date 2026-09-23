"""Unambiguous JSON syntax for differential harness envelopes, not an IR codec."""

from __future__ import annotations

import json
from typing import NoReturn


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _non_json_constant(value: str) -> NoReturn:
    raise ValueError(f"nonstandard JSON constant {value!r}")


def loads(text: str) -> object:
    """Reject information-losing duplicate keys and Python's numeric extensions."""
    try:
        return json.loads(text, object_pairs_hook=_unique_fields, parse_constant=_non_json_constant)
    except RecursionError as error:
        raise ValueError("JSON nesting exceeds the decoder limit") from error
