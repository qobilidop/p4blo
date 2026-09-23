"""Offline validation of one pinned BPF build profile, never kernel execution."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

PROFILE = "xdp-filter-ethernet-allow-v1"
OBJECT = Path("/opt/artifacts/xdpfilt_alw_eth.o")


def metadata_json(text: str) -> dict[str, object]:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            require(key not in result, "duplicate inspector key")
            result[key] = value
        return result

    result = json.loads(text, object_pairs_hook=unique)
    expected = {"programs": 1, "maps": 2, "priority": 10, "chain_pass": 1, "loaded": False}
    require(isinstance(result, dict) and result.keys() == expected.keys(), "wrong inspector keys")
    require(
        all(
            type(result[key]) is type(value) and result[key] == value
            for key, value in expected.items()
        ),
        "unexpected inspector response",
    )
    return result


@dataclass(frozen=True)
class Section:
    index: int
    kind: int
    flags: int
    data: bytes
    link: int
    info: int
    entry_size: int


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def cstring(data: bytes, offset: int) -> str:
    require(0 <= offset < len(data), "invalid ELF string offset")
    end = data.find(b"\0", offset)
    require(end >= 0, "unterminated ELF string")
    return data[offset:end].decode("ascii")


def sections(data: bytes) -> dict[str, Section]:
    """A deliberately restricted ELF64/BPF reader, not a general ELF validator."""
    require(
        len(data) >= 64 and data[:16] == b"\x7fELF\x02\x01\x01" + bytes(9), "wrong ELF identity"
    )
    kind, machine, version, entry, phoff, shoff, flags, ehsize, _, phnum, shsize, count, strings = (
        struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    )
    require(
        (kind, machine, version, entry, flags, ehsize) == (1, 247, 1, 0, 0, 64), "wrong ELF header"
    )
    require(phoff == phnum == 0 and shsize == 64 and 0 < strings < count <= 128, "wrong ELF layout")
    require(64 <= shoff and shoff + count * shsize <= len(data), "truncated section table")
    headers = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + n * shsize) for n in range(count)]
    _, string_kind, _, _, start, size, *_ = headers[strings]
    require(string_kind == 3 and start + size <= len(data), "invalid section names")
    names = data[start : start + size]
    result: dict[str, Section] = {}
    for index, (name, kind, flags, _, start, size, link, info, _, entry_size) in enumerate(headers):
        require(start + size <= len(data), "truncated section")
        name = cstring(names, name)
        require(name not in result, "duplicate section")
        result[name] = Section(
            index, kind, flags, data[start : start + size], link, info, entry_size
        )
    return result


def inspect_elf(data: bytes) -> dict[str, Section]:
    found = sections(data)
    required = {
        "xdp",
        "license",
        "features",
        ".maps",
        ".xdp_run_config",
        ".BTF",
        ".BTF.ext",
        ".symtab",
        ".strtab",
        ".relxdp",
    }
    require(required <= found.keys(), "missing profile section")
    require(found["license"].data == b"GPL\0", "wrong program license")
    require(found["features"].data == struct.pack("<I", 0x30), "wrong feature profile")
    code = found["xdp"]
    require(
        code.kind == 1 and code.flags == 6 and len(code.data) > 0 and len(code.data) % 8 == 0,
        "invalid XDP code section",
    )
    require(
        found[".BTF"].data[:4] == b"\x9f\xeb\x01\0"
        and found[".BTF.ext"].data[:4] == b"\x9f\xeb\x01\0",
        "invalid BTF header",
    )
    symbols = found[".symtab"]
    require(
        symbols.kind == 2 and symbols.entry_size == 24 and len(symbols.data) % 24 == 0,
        "invalid symbol table",
    )
    require(symbols.link == found[".strtab"].index, "wrong symbol strings")
    names: list[str] = []
    functions: list[tuple[str, int, int, int]] = []
    for offset in range(0, len(symbols.data), 24):
        name, info, _, section, value, size = struct.unpack_from("<IBBHQQ", symbols.data, offset)
        name = cstring(found[".strtab"].data, name)
        require(section != 0 or name == "", "unexpected undefined symbol")
        names.append(name)
        if info & 15 == 2:
            functions.append((name, section, value, size))
    require(
        functions == [("xdpfilt_alw_eth", code.index, 0, len(code.data))], "wrong function profile"
    )
    relocations = found[".relxdp"]
    require(
        relocations.kind == 9
        and relocations.link == symbols.index
        and relocations.info == code.index
        and relocations.entry_size == 16
        and len(relocations.data) % 16 == 0,
        "invalid code relocations",
    )
    referenced: list[str] = []
    for offset in range(0, len(relocations.data), 16):
        target, info = struct.unpack_from("<QQ", relocations.data, offset)
        symbol = info >> 32
        require(
            info & 0xFFFFFFFF == 1
            and symbol < len(names)
            and target % 8 == 0
            and target + 16 <= len(code.data),
            "invalid map relocation",
        )
        require(code.data[target] == 0x18, "map relocation is not a wide immediate")
        referenced.append(names[symbol])
    require(
        sorted(referenced) == ["filter_ethernet", "filter_ethernet", "xdp_stats_map"],
        "wrong map references",
    )
    return found


def inspect(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    found = inspect_elf(data)
    with tempfile.TemporaryDirectory(prefix="xdp-offline-") as directory:
        trace = Path(directory) / "bpf-syscalls.txt"
        result = subprocess.run(
            ["strace", "-f", "-qq", "-e", "trace=bpf", "-o", str(trace), "/opt/inspect", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        require(trace.read_bytes() == b"", "offline inspector attempted a BPF syscall")
        result.check_returncode()
    expected_stderr = "".join(
        f"libbpf: elf: skipping unrecognized data section({found[name].index}) {name}\n"
        for name in ("features", ".xdp_run_config")
    )
    require(result.stderr == expected_stderr, "unexpected libbpf diagnostic")
    metadata = metadata_json(result.stdout)
    subprocess.run(
        ["llvm-objdump-18", "--disassemble", str(path)], capture_output=True, timeout=30, check=True
    )
    return {
        "profile": PROFILE,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "instruction_slots": len(found["xdp"].data) // 8,
        "metadata": metadata,
        "bpf_syscalls": 0,
        "kernel_execution": False,
    }


def main() -> None:
    require(len(sys.argv) <= 2, "expected at most one object path")
    print(json.dumps(inspect(Path(sys.argv[1]) if len(sys.argv) == 2 else OBJECT), sort_keys=True))


if __name__ == "__main__":
    main()
