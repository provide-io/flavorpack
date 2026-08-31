#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Reading glibc requirements out of ELF objects, and enforcing them.

The regression this guards: a wheel needing a newer glibc than the bundled
interpreter builds cleanly and then fails at a user's dynamic linker. The ELF
fixtures here are synthesised rather than checked in, so the tests stay
hermetic and run on any host.
"""

from __future__ import annotations

from pathlib import Path
import struct
import zipfile

import pytest

from flavor.packaging.python.glibc import (
    glibc_versions,
    max_glibc_in_tree,
    verify_wheels_against_floor,
    wheel_glibc_requirement,
)


def make_elf(*symbols: str) -> bytes:
    """A minimal little-endian ELF64 whose .dynstr names the given symbols.

    Only the pieces the parser reads are real: the identification bytes, the
    section-header table, and two sections -- .shstrtab naming them and .dynstr
    holding the version strings.
    """
    dynstr = b"\0" + b"\0".join(s.encode() for s in symbols) + b"\0"
    shstrtab = b"\0.shstrtab\0.dynstr\0"

    header_size = 0x40
    shentsize = 0x40
    dynstr_offset = header_size
    shstrtab_offset = dynstr_offset + len(dynstr)
    shoff = shstrtab_offset + len(shstrtab)

    elf = bytearray(header_size)
    elf[0:4] = b"\x7fELF"
    elf[4] = 2  # ELFCLASS64
    elf[5] = 1  # little-endian
    struct.pack_into("<Q", elf, 0x28, shoff)
    struct.pack_into("<H", elf, 0x3A, shentsize)
    struct.pack_into("<H", elf, 0x3C, 3)  # null, .dynstr, .shstrtab
    struct.pack_into("<H", elf, 0x3E, 2)  # .shstrtab is section 2

    elf += dynstr
    elf += shstrtab

    def section(name_offset: int, offset: int, size: int) -> bytes:
        entry = bytearray(shentsize)
        struct.pack_into("<I", entry, 0x00, name_offset)
        struct.pack_into("<Q", entry, 0x18, offset)
        struct.pack_into("<Q", entry, 0x20, size)
        return bytes(entry)

    elf += section(0, 0, 0)  # SHT_NULL
    elf += section(shstrtab.index(b".dynstr"), dynstr_offset, len(dynstr))
    elf += section(shstrtab.index(b".shstrtab"), shstrtab_offset, len(shstrtab))
    return bytes(elf)


def write_wheel(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return path


class TestReadingElfObjects:
    def test_finds_every_glibc_version_named(self) -> None:
        elf = make_elf("GLIBC_2.17", "GLIBC_2.25", "malloc")
        assert glibc_versions(elf) == {(2, 17), (2, 25)}

    def test_a_non_elf_file_yields_nothing(self) -> None:
        assert glibc_versions(b"not an ELF at all") == set()

    def test_an_object_naming_no_glibc_yields_nothing(self) -> None:
        assert glibc_versions(make_elf("malloc", "free")) == set()

    def test_truncated_elf_does_not_raise(self) -> None:
        """A corrupt object should be skipped, not crash the build."""
        assert glibc_versions(make_elf("GLIBC_2.17")[:20]) == set()


class TestScanningATree:
    def test_reports_the_highest_requirement_found(self, tmp_path: Path) -> None:
        (tmp_path / "lib").mkdir()
        (tmp_path / "lib" / "a.so").write_bytes(make_elf("GLIBC_2.17"))
        (tmp_path / "lib" / "b.so").write_bytes(make_elf("GLIBC_2.28"))
        (tmp_path / "lib" / "notes.txt").write_text("ignored")

        assert max_glibc_in_tree(tmp_path) == (2, 28)

    def test_a_tree_with_no_native_objects_reports_nothing(self, tmp_path: Path) -> None:
        (tmp_path / "readme.md").write_text("no ELF here")
        assert max_glibc_in_tree(tmp_path) is None


class TestInspectingWheels:
    def test_reports_the_requirement_and_which_object_carries_it(self, tmp_path: Path) -> None:
        wheel = write_wheel(
            tmp_path / "jq-1.12.0-cp311-cp311-manylinux_2_28_x86_64.whl",
            {
                "jq.cpython-311-x86_64-linux-gnu.so": make_elf("GLIBC_2.25"),
                "jq-1.12.0.dist-info/METADATA": b"Name: jq\n",
            },
        )
        assert wheel_glibc_requirement(wheel) == ((2, 25), "jq.cpython-311-x86_64-linux-gnu.so")

    def test_a_pure_python_wheel_has_no_requirement(self, tmp_path: Path) -> None:
        wheel = write_wheel(tmp_path / "attrs-25.4.0-py3-none-any.whl", {"attr/__init__.py": b"x = 1\n"})
        assert wheel_glibc_requirement(wheel) is None

    def test_a_corrupt_wheel_is_skipped_rather_than_fatal(self, tmp_path: Path) -> None:
        broken = tmp_path / "broken-1.0-cp311-cp311-linux_x86_64.whl"
        broken.write_bytes(b"this is not a zip")
        assert wheel_glibc_requirement(broken) is None


class TestEnforcement:
    def test_wheels_within_the_floor_pass(self, tmp_path: Path) -> None:
        write_wheel(
            tmp_path / "ok-1.0-cp311-cp311-manylinux_2_17_x86_64.whl", {"ok.so": make_elf("GLIBC_2.14")}
        )
        write_wheel(tmp_path / "pure-1.0-py3-none-any.whl", {"pure/__init__.py": b""})

        verify_wheels_against_floor(tmp_path, (2, 17))  # does not raise

    def test_a_wheel_above_the_floor_fails_the_build(self, tmp_path: Path) -> None:
        """The jq case: builds clean today, dies at the user's dynamic linker."""
        write_wheel(
            tmp_path / "jq-1.12.0-cp311-cp311-manylinux_2_28_x86_64.whl",
            {"jq.cpython-311-x86_64-linux-gnu.so": make_elf("GLIBC_2.25")},
        )

        with pytest.raises(RuntimeError) as excinfo:
            verify_wheels_against_floor(tmp_path, (2, 17))

        message = str(excinfo.value)
        assert "jq-1.12.0" in message
        assert "GLIBC 2.25" in message
        assert "2.17" in message
        # It must say what to do about it, not just that it happened.
        assert "manylinux" in message

    def test_a_wheel_exactly_at_the_floor_passes(self, tmp_path: Path) -> None:
        write_wheel(
            tmp_path / "edge-1.0-cp311-cp311-manylinux_2_17_x86_64.whl", {"edge.so": make_elf("GLIBC_2.17")}
        )

        verify_wheels_against_floor(tmp_path, (2, 17))  # does not raise

    def test_every_offender_is_listed_not_just_the_first(self, tmp_path: Path) -> None:
        write_wheel(
            tmp_path / "one-1.0-cp311-cp311-manylinux_2_28_x86_64.whl", {"one.so": make_elf("GLIBC_2.28")}
        )
        write_wheel(
            tmp_path / "two-1.0-cp311-cp311-manylinux_2_34_x86_64.whl", {"two.so": make_elf("GLIBC_2.34")}
        )

        with pytest.raises(RuntimeError) as excinfo:
            verify_wheels_against_floor(tmp_path, (2, 17))

        assert "one-1.0" in str(excinfo.value)
        assert "two-1.0" in str(excinfo.value)

    def test_an_empty_wheel_directory_passes(self, tmp_path: Path) -> None:
        verify_wheels_against_floor(tmp_path, (2, 17))  # does not raise
