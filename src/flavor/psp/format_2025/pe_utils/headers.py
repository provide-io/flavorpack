#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PE header utilities.

Provides utilities for working with PE file headers and offset calculations.
"""

import struct

from provide.foundation import logger


def rva_to_file_offset(data: bytes, rva: int) -> int | None:
    """
    Map a Relative Virtual Address (RVA) to a file offset.

    Walks the section table to find which section contains the RVA and
    calculates the corresponding file offset.

    Args:
        data: PE executable data
        rva: Relative Virtual Address to map

    Returns:
        File offset if mapping succeeded, None otherwise
    """
    # Get PE header location
    pe_offset: int = struct.unpack("<I", data[0x3C:0x40])[0]
    coff_offset = pe_offset + 4

    # Read number of sections
    num_sections: int = struct.unpack("<H", data[coff_offset + 2 : coff_offset + 4])[0]

    # Read optional header size
    opt_hdr_size: int = struct.unpack("<H", data[coff_offset + 16 : coff_offset + 18])[0]

    # Section table offset
    section_table_offset = coff_offset + 20 + opt_hdr_size

    # Walk section table to find which section contains this RVA
    for i in range(num_sections):
        section_offset = section_table_offset + (i * 40)

        # Read section header fields
        # VirtualAddress is at offset 12 in section header
        # VirtualSize is at offset 8 in section header
        # PointerToRawData is at offset 20 in section header

        virtual_addr: int = struct.unpack("<I", data[section_offset + 12 : section_offset + 16])[0]
        virtual_size: int = struct.unpack("<I", data[section_offset + 8 : section_offset + 12])[0]
        pointer_to_raw_data: int = struct.unpack("<I", data[section_offset + 20 : section_offset + 24])[0]

        # Check if RVA falls within this section
        if rva >= virtual_addr and rva < virtual_addr + virtual_size:
            offset_within_section = rva - virtual_addr
            file_offset: int = pointer_to_raw_data + offset_within_section
            logger.trace(
                "Mapped RVA to file offset",
                rva=f"0x{rva:x}",
                section=i,
                section_va=f"0x{virtual_addr:x}",
                file_offset=f"0x{file_offset:x}",
            )
            return file_offset

    logger.trace("RVA not found in any section", rva=f"0x{rva:x}")
    return None
