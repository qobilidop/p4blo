"""Core library validity needs neither bindings nor unique block kinds."""

import subprocess
from pathlib import Path

import pytest

from p4blo import ir, validator
from p4blo.v0 import p4blo_pb2 as pb


def library() -> pb.BlockLibrary:
    result = pb.BlockLibrary(name="many_blocks", errors=ir.CORE_ERRORS)
    for suffix in ("first", "second"):
        parser = result.blocks.add(name=f"parse_{suffix}", kind=pb.BLOCK_KIND_PARSER)
        parser.start_state = "start"
        parser.states.add(name="start").transition.direct.accept.SetInParent()
        control = result.blocks.add(name=f"control_{suffix}", kind=pb.BLOCK_KIND_CONTROL)
        control.params.add(name="x", direction=pb.DIRECTION_INOUT, type=pb.Type(bits=8))
        result.blocks.add(name=f"emit_{suffix}", kind=pb.BLOCK_KIND_DEPARSER)
    return result


@pytest.mark.parametrize("invalid", [False, True])
def test_lean_agrees_core_block_library(lean_binary: Path, tmp_path: Path, invalid: bool) -> None:
    candidate = library()
    if invalid:
        candidate.blocks[1].body.add().assign.CopyFrom(
            pb.Assign(target=pb.LValue(var="missing"), value=pb.Expr(var="x"))
        )
    diagnostics = validator.validate(candidate)
    assert bool(diagnostics) == invalid
    source = tmp_path / "library.json"
    source.write_text(ir.dump_json(candidate))
    run = subprocess.run(
        [str(lean_binary), "check-library", str(source)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == int(invalid), run.stdout + run.stderr
    assert run.stdout.strip().startswith("reject " if invalid else "accept")
    if invalid:
        assert diagnostics[0].code in run.stdout
