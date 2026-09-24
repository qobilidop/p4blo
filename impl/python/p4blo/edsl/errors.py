# pyright: strict
"""Errors that say where the mistake was made.

Every `EdslError` the typed surface raises ends with `(defined at
file:line)`: the nearest frame outside this package and the standard
library, which is the user's declaration or statement. Errors the core
builder raises are re-raised here with the same provenance, taken from
the traceback when the user's frame is below the catch point (a state or
action method being run) and from the stack otherwise (a direct call such
as `self.assign` into the core). The run-time checks the core makes stay
authoritative; this module only adds where.
"""

from __future__ import annotations

import os
import sys
import sysconfig
from collections.abc import Generator
from contextlib import contextmanager
from types import TracebackType
from typing import Any

from p4blo.edsl.core.types import EdslError as _CoreEdslError

_PACKAGE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # impl/python/p4blo
_STDLIB = sysconfig.get_paths()["stdlib"]
_SITE = sysconfig.get_paths()["purelib"]


class EdslError(_CoreEdslError):
    """A mistake visible at build time, with the file and line it was made at.

    Subclasses the core builder's `EdslError`, so `except` clauses written
    for the dynamic API catch both.
    """

    def __init__(self, message: str, *, location: str | None = None) -> None:
        if location is None:
            location = caller_location()
        self.location = location
        super().__init__(f"{message} (defined at {location})" if location else message)


def _is_user_frame(filename: str) -> bool:
    return not (
        filename.startswith(_PACKAGE)
        or filename.startswith(_STDLIB)
        or filename.startswith(_SITE)
        or filename.startswith("<")
    )


def caller_location() -> str | None:
    """`file:line` of the nearest frame on the stack outside this package."""
    frame = sys._getframe(1)  # pyright: ignore[reportPrivateUsage]
    while frame is not None:
        if _is_user_frame(frame.f_code.co_filename):
            return f"{frame.f_code.co_filename}:{frame.f_lineno}"
        frame = frame.f_back
    return None


def user_globals() -> dict[str, Any]:
    """The globals of the nearest frame on the stack outside this package,
    where a declaration being processed was written."""
    frame = sys._getframe(1)  # pyright: ignore[reportPrivateUsage]
    while frame is not None:
        if _is_user_frame(frame.f_code.co_filename):
            return frame.f_globals
        frame = frame.f_back
    return {}


def traceback_location(tb: TracebackType | None) -> str | None:
    """`file:line` of the innermost frame of a traceback outside this package."""
    location: str | None = None
    while tb is not None:
        if _is_user_frame(tb.tb_frame.f_code.co_filename):
            location = f"{tb.tb_frame.f_code.co_filename}:{tb.tb_lineno}"
        tb = tb.tb_next
    return location


@contextmanager
def provenance() -> Generator[None]:
    """Re-raise a core `EdslError` raised inside as an `EdslError` with a location."""
    try:
        yield
    except EdslError:
        raise
    except _CoreEdslError as e:
        location = traceback_location(e.__traceback__) or caller_location()
        raise EdslError(str(e), location=location) from None


__all__ = ["EdslError", "caller_location", "provenance", "traceback_location", "user_globals"]
