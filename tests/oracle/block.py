"""Run single p4blo blocks on P4-SpecTec's p4blo block architecture.

`run.py` compares whole pipelines: a program printed under the v1model shim
runs on the simulator's V1Model architecture, which decides everything
between blocks. This module compares blocks. The simulator, patched at
build time (`patches/`, applied by `build.sh`), has a `block` command and a
`p4blo` architecture that runs exactly one parser, control or deparser per
request on the inputs the request gives:

    parser    packet, metadata, entries, extern state
              -> headers, metadata, consumed bits, accepted, error, extern state
    control   headers, metadata, entries, extern state
              -> headers, metadata, extern state
    deparser  headers, entries, extern state -> bytes, extern state

The program is printed by `p4blo.arch.spectec_block`, which keeps each
exported block's IR signature and adds only the packet. One `p4spectec
block` process stays resident for a `BlockRunner`, so the spec is elaborated
once and a program is instantiated once, however many requests follow.

The protocol is one JSON object per line each way. A request:

    {"program": "<path of the printed .p4>",
     "block": "parser" | "control" | "deparser",
     "packet": "<hex>",                       parser only
     "headers": <value>, "metadata": <value>, as the block takes them
     "entries": "<STF add and setdefault lines>",
     "state": <extern state from an earlier reply> | null}

A reply is the block's outputs (`BlockOutputs` names them), with `state`,
the simulator's own JSON state of every extern object, to pass back
unchanged in the next request, and `externs`, a readable view of registers
and counters; or `{"error": "<the simulator's diagnostic>"}`. State belongs
to the process and the program that produced it and is refused by any
other; the simulator also refuses a value outside its type.

Values are p4blo's wire-format `Literal` in protobuf's JSON mapping for
scalars (`{"bits": {"width": 8, "value": "255"}}`, `{"boolean": true}`,
`{"error": "NoError"}`, `{"enum_member": {"enum_type": ..., "member": ...}}`)
and this protocol's own shape for compounds, fields by name in declaration
order: `{"header": {"type", "valid", "fields"}}`, `{"struct": {"type",
"fields"}}`, `{"stack": {"next_index", "elements"}}`. `to_json` and
`from_json` convert them to and from the reference interpreter's values.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import IO, Any, Self

from p4blo.arch.bindings import BoundIndex, assembly_of
from p4blo.arch.v0 import assembly_pb2 as apb

# Importable from the repository root without installing anything, as run.py;
# the root itself for `tests.oracle.run`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "impl" / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from p4blo import ir  # noqa: E402
from p4blo.arch import spectec_block  # noqa: E402
from p4blo.drt.case import Case, case_to_stf  # noqa: E402
from p4blo.interp.values import (  # noqa: E402
    Bits,
    EnumValue,
    ErrorValue,
    Header,
    Stack,
    Struct,
    Value,
)
from p4blo.v0 import p4blo_pb2 as pb  # noqa: E402
from tests.oracle import run as oracle_run  # noqa: E402

__all__ = [
    "INCLUDE_DIR",
    "BlockError",
    "BlockInputs",
    "BlockOracle",
    "BlockOutputs",
    "BlockRunner",
    "entries_to_stf",
    "find_block_oracle",
    "from_json",
    "run_block",
    "to_json",
]

# Where p4blo.p4 lives; passed to the simulator as an include directory.
INCLUDE_DIR = Path(__file__).resolve().parent / "include"
# The architecture's relations, p4blo's block contract, which the `block`
# command reads at start; tracked here rather than patched into the checkout.
WATSUP = Path(__file__).resolve().parent / "p4blo.watsup"
# The patches build.sh applies, and the stamp it writes after a build:
# "<commit> <digest of the patches>".
PATCHES_DIR = Path(__file__).resolve().parent / "patches"
STAMP = Path(".p4blo-built")


def patches_digest(patches_dir: Path = PATCHES_DIR) -> str:
    """The digest build.sh stamps: `git hash-object` of every patch's file
    name, a newline and its content, in name order."""
    data = b"".join(
        patch.name.encode() + b"\n" + patch.read_bytes()
        for patch in sorted(patches_dir.glob("*.patch"))
    )
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class BlockError(Exception):
    """The simulator could not run the block; the message is its diagnostic."""


# ---------------------------------------------------------------------------
# Locating the oracle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockOracle:
    """A P4-SpecTec checkout built with the p4blo patch."""

    oracle: oracle_run.Oracle

    @property
    def binary(self) -> Path:
        return self.oracle.binary

    @property
    def root(self) -> Path:
        return self.oracle.root

    @property
    def watsup(self) -> Path:
        return WATSUP

    def command(self, *, trace: bool = False) -> list[str]:
        """The server's command line; `trace` makes it write the spec's
        execution trace to standard error."""
        return [
            str(self.binary),
            "block",
            str(self.oracle.spec),
            str(self.watsup),
            "-i",
            str(self.oracle.include),
            "-i",
            str(INCLUDE_DIR),
            *(["-trace"] if trace else []),
        ]

    def missing(self) -> str | None:
        """Why this checkout cannot run blocks, or None when it can."""
        reason = self.oracle.missing()
        if reason is not None:
            return reason
        # A checkout built from another version of the patch would run, and
        # answer for a plugin that is not the one in this tree.
        stamp = self.root / STAMP
        built = stamp.read_text().split() if stamp.is_file() else []
        if built[1:] != [patches_digest()]:
            return (
                f"{stamp} does not name the current tests/oracle/patches: "
                "rerun tests/oracle/build.sh"
            )
        return None


def find_block_oracle(environ: dict[str, str] | None = None) -> BlockOracle | None:
    """The block oracle the environment points at, found as `run.find_oracle`."""
    found = oracle_run.find_oracle(environ)
    return None if found is None else BlockOracle(found)


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


def to_json(value: Value, index: ir.Index) -> dict[str, Any]:
    """A reference interpreter value in the protocol's shape."""
    match value:
        case Bits(width, number):
            return {"bits": {"width": width, "value": str(number)}}
        case bool():
            return {"boolean": value}
        case ErrorValue(name):
            return {"error": name}
        case EnumValue(enum_type, member):
            return {"enum_member": {"enum_type": enum_type, "member": member}}
        case Header(type_name, valid, fields):
            decl = index.header_types[type_name]
            return {
                "header": {
                    "type": type_name,
                    "valid": valid,
                    "fields": _fields(decl.fields, fields, index),
                }
            }
        case Struct(type_name, fields):
            decl = index.struct_types[type_name]
            return {"struct": {"type": type_name, "fields": _fields(decl.fields, fields, index)}}
        case Stack(_, elements, next_index):
            return {
                "stack": {
                    "next_index": next_index,
                    "elements": [to_json(e, index) for e in elements],
                }
            }


def _fields(decls: Any, values: list[Value], index: ir.Index) -> dict[str, Any]:
    return {d.name: to_json(v, index) for d, v in zip(decls, values, strict=True)}


def from_json(raw: Any, index: ir.Index) -> Value:
    """A protocol value as a reference interpreter value; `BlockError` on a
    shape the protocol does not define or a field list that is not the
    declared one."""
    if not isinstance(raw, dict) or len(raw) != 1:
        raise BlockError(f"not a value: {raw!r}")
    ((kind, body),) = raw.items()
    match kind:
        case "bits":
            return Bits(int(body["width"]), int(body["value"]))
        case "boolean":
            return bool(body)
        case "error":
            return ErrorValue(str(body))
        case "enum_member":
            return EnumValue(str(body["enum_type"]), str(body["member"]))
        case "header":
            decl = index.header_types[body["type"]]
            return Header(body["type"], bool(body["valid"]), _values(decl.fields, body, index))
        case "struct":
            decl = index.struct_types[body["type"]]
            return Struct(body["type"], _values(decl.fields, body, index))
        case "stack":
            elements = [from_json(e, index) for e in body["elements"]]
            headers = [e for e in elements if isinstance(e, Header)]
            if len(headers) != len(elements) or not headers:
                raise BlockError(f"a stack of something other than headers: {raw!r}")
            return Stack(headers[0].type_name, headers, int(body["next_index"]))
        case _:
            raise BlockError(f"a value the protocol does not define: {raw!r}")


def _values(decls: Any, body: dict[str, Any], index: ir.Index) -> list[Value]:
    fields = body["fields"]
    names = [d.name for d in decls]
    if list(fields) != names:
        raise BlockError(f"{body['type']} has fields {names}, got {list(fields)}")
    return [from_json(fields[name], index) for name in names]


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


def entries_to_stf(index: ir.Index, entries: pb.Entries) -> str:
    """Host entries as the STF lines the simulator installs, rendered by
    `p4blo.drt.case` and translated by `run.translate` exactly as the
    pipeline oracle renders them (lpm prefixes as full-width wildcards with
    their length as priority).

    The simulator resolves an entry's table by its unqualified name, and
    this architecture does not apply V1Model's STF rewrites (block names
    and `$valid$` in key names), so entries for a table name two blocks
    declare, or for a table with a `$valid$` key name, would mean something
    else here than in the pipeline; `BlockError` refuses them instead."""
    for installed in entries.tables:
        declared = sorted(
            block for block, scope in index.scopes.items() if installed.table in scope.tables
        )
        if len(declared) > 1:
            raise BlockError(
                f"table {installed.table!r} is declared in {', '.join(declared)}; "
                "the block runner finds tables by their unqualified name"
            )
        scope = index.scopes.get(installed.block)
        table = scope.tables.get(installed.table) if scope is not None else None
        for key in table.keys if table is not None else []:
            name = ir.key_name(key) or ""
            if "$valid$" in name:
                raise BlockError(
                    f"table {installed.table!r} has a key named {name!r}; the block "
                    "runner does not rewrite $valid$ as V1Model's STF runner does"
                )
    text = case_to_stf(index, Case(entries, 0, b"\x00"))
    lines = [line for line in text.splitlines() if line.startswith(("add ", "setdefault "))]
    if not lines:
        return ""
    translated, _ = oracle_run.translate("\n".join(lines) + "\n", index)
    return translated


@dataclass
class BlockInputs:
    """What one block receives. `packet` is the parser's; `headers` the
    control's and the deparser's; `metadata` the parser's and the control's.
    `state` is the `state` of an earlier reply from the same runner, or None
    for every extern's initial state."""

    packet: bytes = b""
    headers: Struct | None = None
    metadata: Struct | None = None
    entries: pb.Entries = field(default_factory=pb.Entries)
    state: Any = None


@dataclass
class BlockOutputs:
    """What one block left. Fields a block does not produce stay None:
    `consumed_bits`, `accepted` and `error` are the parser's, `packet` and
    `bits` the deparser's (the bytes zero-padded to a whole byte, `bits` the
    exact number emitted)."""

    state: Any
    externs: dict[str, Any]
    headers: Struct | None = None
    metadata: Struct | None = None
    consumed_bits: int | None = None
    accepted: bool | None = None
    error: ErrorValue | None = None
    packet: bytes | None = None
    bits: int | None = None


class BlockRunner:
    """One resident `p4spectec block` process and the programs printed for it."""

    def __init__(
        self, oracle: BlockOracle, workdir: Path | None = None, *, trace: bool = False
    ) -> None:
        """`trace` writes the spec's execution trace to the process's
        standard error, `p4spectec-block.stderr` in `workdir`."""
        self.oracle = oracle
        self._tmp = (
            None if workdir is not None else tempfile.TemporaryDirectory(prefix="p4blo-block-")
        )
        self.workdir = workdir if workdir is not None else Path(self._tmp.name)  # type: ignore[union-attr]
        self._stderr: IO[str] = (self.workdir / "p4spectec-block.stderr").open("w")
        self._process = subprocess.Popen(
            oracle.command(trace=trace),
            cwd=oracle.root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr,
            text=True,
            bufsize=1,
        )
        self._printed: dict[str, Path] = {}

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self._process.stdin is not None:
            self._process.stdin.close()
        try:
            self._process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        if self._process.stdout is not None:
            self._process.stdout.close()
        self._stderr.close()
        if self._tmp is not None:
            self._tmp.cleanup()

    def program_path(self, index: BoundIndex) -> Path:
        """The program printed for the block architecture, once per content."""
        text = spectec_block.print_program(assembly_of(index.program, index.bindings), index=index)
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]
        path = self._printed.get(digest)
        if path is None:
            path = self.workdir / f"{index.program.name or 'program'}-{digest}.p4"
            path.write_text(text)
            self._printed[digest] = path
        return path

    def request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send one request and return its reply; `BlockError` on an error
        reply, `RuntimeError` when the process is gone."""
        stdin, stdout = self._process.stdin, self._process.stdout
        assert stdin is not None and stdout is not None
        try:
            stdin.write(json.dumps(request) + "\n")
            stdin.flush()
        except BrokenPipeError as e:
            raise RuntimeError(self._died()) from e
        line = stdout.readline()
        if not line:
            raise RuntimeError(self._died())
        reply = json.loads(line)
        if not isinstance(reply, dict):
            raise RuntimeError(f"a reply that is not an object: {line!r}")
        if "error" in reply and isinstance(reply["error"], str) and len(reply) == 1:
            raise BlockError(reply["error"])
        return reply

    def _died(self) -> str:
        self._stderr.flush()
        err = (self.workdir / "p4spectec-block.stderr").read_text()
        return f"p4spectec block exited with {self._process.poll()}:\n{err}"

    def run_block(self, index: BoundIndex, role: str, inputs: BlockInputs) -> BlockOutputs:
        """Run the block `index`'s program exports as `role` on `inputs`."""
        request: dict[str, Any] = {
            "program": str(self.program_path(index)),
            "block": role,
            "entries": entries_to_stf(index, inputs.entries),
            "state": inputs.state,
        }
        if role == "parser":
            request["packet"] = inputs.packet.hex()
        if role in ("control", "deparser"):
            if inputs.headers is None:
                raise ValueError(f"a {role} needs headers")
            request["headers"] = to_json(inputs.headers, index)
        if role in ("parser", "control"):
            if inputs.metadata is None:
                raise ValueError(f"a {role} needs metadata")
            request["metadata"] = to_json(inputs.metadata, index)
        reply = self.request(request)
        outputs = BlockOutputs(state=reply["state"], externs=reply["externs"])
        if "headers" in reply:
            outputs.headers = _struct(from_json(reply["headers"], index))
        if "metadata" in reply:
            outputs.metadata = _struct(from_json(reply["metadata"], index))
        if role == "parser":
            outputs.consumed_bits = int(reply["consumed_bits"])
            outputs.accepted = bool(reply["accepted"])
            outputs.error = ErrorValue(str(reply["error"]))
        if role == "deparser":
            outputs.packet = bytes.fromhex(reply["packet"])
            outputs.bits = int(reply["bits"])
        return outputs


def _struct(value: Value) -> Struct:
    if not isinstance(value, Struct):
        raise BlockError(f"expected a struct, got {value!r}")
    return value


def run_block(
    program: apb.BlockAssembly, block: str, inputs: BlockInputs, oracle: BlockOracle | None = None
) -> BlockOutputs:
    """One block on a fresh runner: convenient, and slow, since the spec is
    elaborated again. Keep a `BlockRunner` for more than one request, and to
    carry extern state from one to the next."""
    if oracle is None:
        oracle = find_block_oracle()
        if oracle is None:
            raise RuntimeError("no p4spectec binary: run tests/oracle/build.sh")
    with BlockRunner(oracle) as runner:
        return runner.run_block(BoundIndex.build(program), block, inputs)
