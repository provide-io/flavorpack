#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PE executable validation utilities.

Provides functions to validate and analyze Windows PE (Portable Executable) files.
"""

import struct

from provide.foundation import logger


def is_pe_executable(data: bytes) -> bool:
    """
    Check if data starts with a valid Windows PE executable header.

    Args:
        data: Binary data to check

    Returns:
        True if data starts with "MZ" signature (PE executable)
    """
    return len(data) >= 2 and data[0:2] == b"MZ"


def get_pe_header_offset(data: bytes) -> int | None:
    """
    Read the PE header offset from the DOS header.

    The offset is stored at position 0x3C (e_lfanew field) as a 4-byte
    little-endian integer.

    Args:
        data: PE executable data

    Returns:
        PE header offset, or None if invalid
    """
    if len(data) < 0x40:
        return None

    # Read e_lfanew field at offset 0x3C
    pe_offset: int = struct.unpack("<I", data[0x3C:0x40])[0]

    # Validate PE signature at that offset
    if len(data) < pe_offset + 4:
        return None

    pe_signature = data[pe_offset : pe_offset + 4]
    if pe_signature != b"PE\x00\x00":
        logger.warning(
            "Invalid PE signature",
            expected="PE\\x00\\x00",
            actual=pe_signature.hex(),
            offset=f"0x{pe_offset:x}",
        )
        return None

    return pe_offset


def needs_dos_stub_expansion(data: bytes) -> bool:
    """
    Check if a PE executable needs DOS stub expansion.

    Go binaries use minimal DOS stub (128 bytes / 0x80) which is incompatible
    with Windows PE loader when PSPF data is appended. This function detects
    such binaries.

    Args:
        data: PE executable data

    Returns:
        True if DOS stub needs expansion (Go binary with 0x80 stub)
    """
    if not is_pe_executable(data):
        return False

    pe_offset = get_pe_header_offset(data)
    if pe_offset is None:
        return False

    # Check if this is a Go binary with minimal DOS stub (0x80 = 128 bytes)
    # Rust/MSVC binaries typically use 0xE8-0xF0 (232-240 bytes)
    if pe_offset == 0x80:
        logger.debug(
            "Detected Go binary with minimal DOS stub",
            pe_offset=f"0x{pe_offset:x}",
            dos_stub_size=pe_offset,
        )
        return True

    logger.trace(
        "PE binary has adequate DOS stub size",
        pe_offset=f"0x{pe_offset:x}",
        dos_stub_size=pe_offset,
    )
    return False
