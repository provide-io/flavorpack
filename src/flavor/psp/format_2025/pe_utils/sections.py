#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PE section table utilities.

Provides utilities for updating PE section offsets and header sizes.
"""

import struct

from provide.foundation import logger


def update_section_offsets(data: bytearray, padding_size: int) -> None:
    """
    Update section PointerToRawData values after DOS stub expansion.

    When expanding the DOS stub, all content after the DOS stub shifts forward
    by padding_size bytes. This includes all section data. The section table
    contains PointerToRawData fields (absolute file offsets) that must be
    updated to point to the new section locations.

    Args:
        data: PE executable data (modified in-place)
        padding_size: Number of bytes added to DOS stub
    """
    # Get PE header location
    pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]

    # COFF header starts after PE signature
    coff_offset = pe_offset + 4

    # Read number of sections
    num_sections = struct.unpack("<H", data[coff_offset + 2 : coff_offset + 4])[0]

    # Read optional header size
    opt_hdr_size = struct.unpack("<H", data[coff_offset + 16 : coff_offset + 18])[0]

    # Section table starts after COFF header (20 bytes) + optional header
    section_table_offset = coff_offset + 20 + opt_hdr_size

    logger.debug(
        "Updating section offsets",
        num_sections=num_sections,
        section_table_offset=f"0x{section_table_offset:x}",
        padding_size=padding_size,
    )

    # Update each section's PointerToRawData
    # Section structure is 40 bytes, PointerToRawData is at offset +20
    updated_count = 0
    for i in range(num_sections):
        section_offset = section_table_offset + (i * 40)
        ptr_to_raw_data_offset = section_offset + 20

        # Read current PointerToRawData
        current_ptr = struct.unpack("<I", data[ptr_to_raw_data_offset : ptr_to_raw_data_offset + 4])[0]

        # Only update if pointer is non-zero (sections with no data have ptr=0)
        if current_ptr > 0:
            new_ptr = current_ptr + padding_size
            struct.pack_into("<I", data, ptr_to_raw_data_offset, new_ptr)
            logger.trace(
                f"Updated section {i} offset",
                old_offset=f"0x{current_ptr:x}",
                new_offset=f"0x{new_ptr:x}",
            )
            updated_count += 1

    logger.debug(f"Updated {updated_count}/{num_sections} section offset(s)")


def update_size_of_headers(data: bytearray, padding_size: int) -> None:
    """
    Update SizeOfHeaders field in the Optional Header after DOS stub expansion.

    The SizeOfHeaders field specifies the combined size of the DOS stub, PE headers,
    and section table, rounded to the file alignment. When the DOS stub expands,
    this field must be updated to match the new total header size.

    Windows PE loader validates that sections start at or after SizeOfHeaders.
    A mismatch causes loader rejection, especially on ARM64 (exit code 126).

    Args:
        data: PE executable data (modified in-place)
        padding_size: Number of bytes added to DOS stub
    """
    # Get PE header location
    pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]
    coff_offset = pe_offset + 4

    # SizeOfHeaders is at optional header + 60 bytes
    # Optional header starts at COFF header + 20
    size_of_headers_offset = coff_offset + 20 + 60

    # Read current SizeOfHeaders value
    current_size = struct.unpack("<I", data[size_of_headers_offset : size_of_headers_offset + 4])[0]

    # Update to reflect expanded DOS stub
    new_size = current_size + padding_size
    struct.pack_into("<I", data, size_of_headers_offset, new_size)

    logger.debug(
        "Updated SizeOfHeaders field",
        old_size=f"0x{current_size:x}",
        new_size=f"0x{new_size:x}",
        padding=padding_size,
    )
