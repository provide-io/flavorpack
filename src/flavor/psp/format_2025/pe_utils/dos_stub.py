#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""DOS stub expansion utilities.

Provides utilities for expanding PE DOS stubs to ensure Windows compatibility.
"""

import struct

from provide.foundation import logger

from .directories import update_data_directories, update_debug_directory
from .sections import update_section_offsets, update_size_of_headers
from .validation import get_pe_header_offset, is_pe_executable

# Target DOS stub size to match Rust MSVC binaries (240 bytes / 0xF0)
TARGET_DOS_STUB_SIZE = 0xF0


def expand_dos_stub(data: bytes) -> bytes:
    """
    Expand the DOS stub of a PE executable to match Rust/MSVC binary size.

    This fixes Windows PE loader rejection of Go binaries when PSPF data
    is appended. The DOS stub is expanded from 128 bytes (0x80) to 240 bytes
    (0xF0) to match Rust binaries.

    Process:
    1. Extract MZ header (first 64 bytes)
    2. Extract DOS stub code (bytes 64 to current PE offset)
    3. Extract PE header and remainder
    4. Insert padding to expand stub to target size
    5. Update e_lfanew pointer to new PE offset

    Args:
        data: Original PE executable data

    Returns:
        Modified PE executable with expanded DOS stub

    Raises:
        ValueError: If data is not a valid PE executable
    """
    if not is_pe_executable(data):
        raise ValueError("Data is not a Windows PE executable")

    current_pe_offset = get_pe_header_offset(data)
    if current_pe_offset is None:
        raise ValueError("Invalid PE header offset")

    if current_pe_offset >= TARGET_DOS_STUB_SIZE:
        logger.debug(
            "DOS stub already adequate size",
            current=f"0x{current_pe_offset:x}",
            target=f"0x{TARGET_DOS_STUB_SIZE:x}",
        )
        return data

    # Calculate padding needed
    padding_size = TARGET_DOS_STUB_SIZE - current_pe_offset

    logger.info(
        "Expanding DOS stub for Windows compatibility",
        current_pe_offset=f"0x{current_pe_offset:x}",
        target_pe_offset=f"0x{TARGET_DOS_STUB_SIZE:x}",
        padding_bytes=padding_size,
    )

    # Build new executable:
    # 1. MZ header + DOS stub (up to current PE offset)
    # 2. Padding (zeros to expand stub)
    # 3. PE header and remainder
    mz_and_dos_stub = data[0:current_pe_offset]
    pe_header_and_remainder = data[current_pe_offset:]
    padding = b"\x00" * padding_size

    new_data = bytearray(mz_and_dos_stub + padding + pe_header_and_remainder)

    # Update e_lfanew pointer at offset 0x3C to point to new PE header location
    struct.pack_into("<I", new_data, 0x3C, TARGET_DOS_STUB_SIZE)

    # CRITICAL: Update all section PointerToRawData values
    # When we shift the file content forward, section data moves but the section
    # table entries still point to old offsets. We must update them.
    update_section_offsets(new_data, padding_size)

    # Update SizeOfHeaders to reflect expanded DOS stub size
    update_size_of_headers(new_data, padding_size)

    # Update data directories (Certificate Table uses absolute file offsets)
    update_data_directories(new_data, padding_size)

    # Update debug directory entries (PointerToRawData fields use absolute file offsets)
    update_debug_directory(new_data, padding_size)

    # Verify the modification
    new_pe_offset = get_pe_header_offset(bytes(new_data))
    if new_pe_offset != TARGET_DOS_STUB_SIZE:
        raise ValueError(
            f"Failed to update PE offset: expected 0x{TARGET_DOS_STUB_SIZE:x}, got 0x{new_pe_offset:x}"
        )

    logger.debug(
        "DOS stub expansion complete",
        original_size=len(data),
        new_size=len(new_data),
        bytes_added=padding_size,
        new_pe_offset=f"0x{new_pe_offset:x}",
    )

    return bytes(new_data)
