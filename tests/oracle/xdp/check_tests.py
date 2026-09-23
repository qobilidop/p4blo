"""Negative checks of the actual compiled object, without kernel execution."""

from __future__ import annotations

import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from check import OBJECT, inspect, inspect_elf, sections


class ObjectChecks(unittest.TestCase):
    def test_original(self) -> None:
        result = inspect(OBJECT)
        self.assertIs(result["kernel_execution"], False)
        self.assertEqual(result["bpf_syscalls"], 0)
        self.assertEqual(OBJECT.read_bytes(), OBJECT.with_suffix(".repeat.o").read_bytes())

    def test_structural_faults(self) -> None:
        data = OBJECT.read_bytes()
        for label, mutated in (
            ("empty", b""),
            ("truncated", data[:64]),
            ("endianness", data[:5] + b"\x02" + data[6:]),
            ("machine", data[:18] + b"\x3e\x00" + data[20:]),
            ("license", self.replace(data, b"GPL\0", b"MIT\0")),
        ):
            with self.subTest(label=label), self.assertRaises(ValueError):
                inspect_elf(mutated)

    @staticmethod
    def replace(data: bytes, before: bytes, after: bytes) -> bytes:
        if len(before) != len(after) or data.count(before) != 1:
            raise AssertionError("mutation anchor is not unique and length preserving")
        return data.replace(before, after, 1)

    def rejected_by_native(self, data: bytes, diagnostic: str) -> None:
        # Structural acceptance ensures this tests the independent native
        # map/BTF inspection, not merely an invalid ELF header.
        inspect_elf(data)
        with tempfile.TemporaryDirectory(prefix="xdp-negative-") as directory:
            target = Path(directory) / "mutated.o"
            target.write_bytes(data)
            with self.assertRaises(subprocess.CalledProcessError) as raised:
                inspect(target)
            self.assertEqual(raised.exception.returncode, 1)
            self.assertIn(diagnostic, raised.exception.stderr)

    def test_statistics_alias(self) -> None:
        self.rejected_by_native(
            self.replace(OBJECT.read_bytes(), b"rx_packets\0", b"rx_pacKets\0"),
            "profile: wrong statistics alias",
        )

    def test_map_capacity(self) -> None:
        data = OBJECT.read_bytes()
        btf = sections(data)[".BTF"].data
        # Parse BTF record boundaries, never search arbitrary integer bytes.
        _, _, _, header_size, type_offset, type_size, _, _ = struct.unpack_from("<HBBIIIII", btf)
        cursor, end = header_size + type_offset, header_size + type_offset + type_size
        candidates: list[int] = []
        while cursor < end:
            _, info, _ = struct.unpack_from("<III", btf, cursor)
            kind, count = (info >> 24) & 31, info & 65535
            payload = {
                1: 4,
                2: 0,
                3: 12,
                4: 12 * count,
                5: 12 * count,
                6: 8 * count,
                7: 0,
                8: 0,
                9: 0,
                10: 0,
                11: 0,
                12: 0,
                13: 8 * count,
                14: 4,
                15: 12 * count,
                16: 0,
                17: 4,
                18: 0,
                19: 12 * count,
            }[kind]
            if kind == 3 and struct.unpack_from("<I", btf, cursor + 20)[0] == 10000:
                candidates.append(cursor + 20)
            cursor += 12 + payload
        self.assertEqual(cursor, end)
        self.assertEqual(len(candidates), 1)
        offset = candidates[0]
        mutated_btf = btf[:offset] + struct.pack("<I", 9999) + btf[offset + 4 :]
        self.rejected_by_native(self.replace(data, btf, mutated_btf), "profile: wrong capacity")


if __name__ == "__main__":
    unittest.main()
