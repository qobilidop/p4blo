"""P4 source into p4blo IR, through P4-SpecTec's typing and instantiation.

`p4blo.frontend.export` runs P4-SpecTec's `il-export` command on a P4 file;
`p4blo.frontend.il` reads what it prints; `p4blo.frontend.spectec_il`
translates the typed, instantiated IL into IR, performing the elaborations
docs/p4-spec-coverage.md names; `p4blo.frontend.v1model` binds a V1Switch
program's architecture layer to the IR's roles and metadata contract; and
`p4blo.frontend.normalize` puts two programs in a canonical form so that a
translation can be compared with a golden written by hand.

The bridge needs a P4-SpecTec checkout built by tests/oracle/build.sh. It is
not a verified frontend: it is checked on the corpus (tests/external/test_frontend_spectec.py).
"""

from p4blo.frontend.spectec_il import (
    Excluded,
    FrontendError,
    NotTranslated,
    Translation,
    translate,
    translate_source,
)

__all__ = [
    "Excluded",
    "FrontendError",
    "NotTranslated",
    "Translation",
    "translate",
    "translate_source",
]
