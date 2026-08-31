#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Check that no bundled wheel needs a newer glibc than the bundled interpreter.

A packaged build assembles two things that carry a glibc requirement and know
nothing about each other: the interpreter, whose floor comes from whichever
python-build-standalone release uv resolves, and the wheels, whose floor comes
from the manylinux tags pip was allowed to see. When the wheel side drifts
above the interpreter side the build still succeeds -- the mismatch surfaces on
a user's machine as the dynamic linker refusing to load an extension module,
which is the worst possible place to learn about it.

The requirement is read from the ELF objects themselves rather than from
manylinux tags, because the tags overstate it. jq 1.12.0 publishes a wheel
tagged `manylinux_2_26.manylinux_2_28` whose `.so` in fact requires only
GLIBC 2.25: auditwheel stamps the glibc of the build image, not the minimum the
code needs. Checking tags would reject wheels that would have run.
"""

from __future__ import annotations

from pathlib import Path
import re
import struct
import zipfile

from provide.foundation import logger

#: Version strings the dynamic linker records, e.g. `GLIBC_2.28`.
_GLIBC_SYMBOL = re.compile(rb"GLIBC_(\d+)\.(\d+)")

_ELF_MAGIC = b"\x7fELF"

#: Only these carry native code; everything else in an interpreter tree or a
#: wheel is data we would waste time reading.
_NATIVE_SUFFIXES = (".so", ".so.1.0")

GlibcVersion = tuple[int, int]


def _section_offsets(data: bytes) -> dict[str, tuple[int, int]]:
    """Map section name to (offset, size) for a little-endian ELF64 object."""
    # A truncated or foreign object is skipped, never fatal: one unreadable
    # file in a tree must not be able to fail a build.
    if len(data) < 0x40 or data[4] != 2 or data[5] != 1:  # 64-bit, little-endian
        return {}

    try:
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        e_shstrndx = struct.unpack_from("<H", data, 0x3E)[0]
    except struct.error:
        return {}
    if not e_shoff or not e_shnum or e_shstrndx >= e_shnum or e_shoff >= len(data):
        return {}

    def header(index: int) -> tuple[int, int, int]:
        base = e_shoff + index * e_shentsize
        name = struct.unpack_from("<I", data, base)[0]
        offset = struct.unpack_from("<Q", data, base + 0x18)[0]
        size = struct.unpack_from("<Q", data, base + 0x20)[0]
        return name, offset, size

    try:
        _, strtab_offset, _ = header(e_shstrndx)
        sections: dict[str, tuple[int, int]] = {}
        for index in range(e_shnum):
            name_offset, offset, size = header(index)
            start = strtab_offset + name_offset
            end = data.index(b"\0", start)
            sections[data[start:end].decode("utf-8", "replace")] = (offset, size)
        return sections
    except (struct.error, ValueError, IndexError):
        return {}


def glibc_versions(data: bytes) -> set[GlibcVersion]:
    """Every GLIBC_x.y version an ELF object names.

    The versions live in `.dynstr`, referenced from `.gnu.version_r`. Reading
    the string table directly finds all of them without walking the version
    records, and a non-ELF or unreadable object simply yields nothing.
    """
    if not data.startswith(_ELF_MAGIC):
        return set()

    sections = _section_offsets(data)
    dynstr = sections.get(".dynstr")
    if dynstr is None:
        return set()

    offset, size = dynstr
    blob = data[offset : offset + size]
    return {(int(major), int(minor)) for major, minor in _GLIBC_SYMBOL.findall(blob)}


def max_glibc_in_tree(root: Path) -> GlibcVersion | None:
    """The highest glibc any native object under `root` requires."""
    highest: GlibcVersion | None = None
    for path in root.rglob("*"):
        if not path.is_file() or not path.name.endswith(_NATIVE_SUFFIXES):
            continue
        try:
            versions = glibc_versions(path.read_bytes())
        except OSError:
            continue
        if versions and (highest is None or max(versions) > highest):
            highest = max(versions)
    return highest


def wheel_glibc_requirement(wheel: Path) -> tuple[GlibcVersion, str] | None:
    """The highest glibc any extension module in a wheel requires, and which one.

    Returns None for a wheel with no native code, which is most of them.
    """
    highest: GlibcVersion | None = None
    culprit = ""
    try:
        with zipfile.ZipFile(wheel) as archive:
            for name in archive.namelist():
                if not name.endswith(_NATIVE_SUFFIXES):
                    continue
                versions = glibc_versions(archive.read(name))
                if versions and (highest is None or max(versions) > highest):
                    highest = max(versions)
                    culprit = name
    except (zipfile.BadZipFile, OSError) as exc:
        logger.debug(f"Could not inspect {wheel.name} for glibc requirements: {exc}")
        return None
    return (highest, culprit) if highest else None


def verify_wheels_against_floor(wheels_dir: Path, floor: GlibcVersion) -> None:
    """Fail the build when a wheel needs a newer glibc than the interpreter.

    Raises:
        RuntimeError: if any bundled wheel requires more than `floor`.
    """
    violations: list[str] = []
    inspected = 0

    for wheel in sorted(wheels_dir.glob("*.whl")):
        requirement = wheel_glibc_requirement(wheel)
        if requirement is None:
            continue
        inspected += 1
        needed, culprit = requirement
        if needed > floor:
            violations.append(f"{wheel.name} needs GLIBC {needed[0]}.{needed[1]} ({culprit})")

    if violations:
        listed = "\n  ".join(violations)
        raise RuntimeError(
            f"Bundled wheels require a newer glibc than the bundled interpreter, "
            f"which supports {floor[0]}.{floor[1]}:\n  {listed}\n\n"
            "This package would build cleanly and then fail to start on any system "
            "the interpreter itself supports, because the dynamic linker refuses to "
            "load these extension modules. Pin the offending packages to versions "
            "built against an older glibc, or state a newer baseline with "
            "`manylinux` under [tool.flavor.build] and accept the narrower support."
        )

    logger.info(
        "✅ Bundled wheels are within the interpreter's glibc floor",
        floor=f"{floor[0]}.{floor[1]}",
        native_wheels=inspected,
    )
