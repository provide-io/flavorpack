#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PE data directory utilities.

Provides utilities for updating PE data directory offsets, including certificate
and debug directories.
"""

import struct

from provide.foundation import logger

from .headers import rva_to_file_offset


def update_data_directories(data: bytearray, padding_size: int) -> None:
    """
    Update data directory file offsets after DOS stub expansion.

    The Certificate Table (data directory entry #4) is special: it uses absolute
    file offsets instead of RVAs. When the DOS stub expands, this offset must
    be updated. Other data directories use RVAs (relative to image base) and
    don't need updating.

    Args:
        data: PE executable data (modified in-place)
        padding_size: Number of bytes added to DOS stub
    """
    # Get PE header location
    pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]

    # COFF header starts after PE signature
    coff_offset = pe_offset + 4

    # Read optional header size to determine PE32 vs PE32+
    struct.unpack("<H", data[coff_offset + 16 : coff_offset + 18])[0]

    # Read magic number to identify PE32 vs PE32+
    magic = struct.unpack("<H", data[coff_offset + 20 : coff_offset + 22])[0]
    is_pe32_plus = magic == 0x20B

    # Data directory offset in optional header
    # PE32: starts at optional header + 96
    # PE32+: starts at optional header + 112
    data_dir_offset = coff_offset + 20 + 112 if is_pe32_plus else coff_offset + 20 + 96

    # Certificate Table is the 5th entry (index 4) in data directory array
    # Each entry is 8 bytes (4 bytes RVA/offset + 4 bytes size)
    cert_entry_offset = data_dir_offset + (4 * 8)

    if cert_entry_offset + 8 > len(data):
        logger.trace(
            "Certificate table entry beyond file bounds, skipping update",
            entry_offset=f"0x{cert_entry_offset:x}",
            file_size=len(data),
        )
        return

    # Read certificate table entry
    cert_file_offset = struct.unpack("<I", data[cert_entry_offset : cert_entry_offset + 4])[0]
    cert_size = struct.unpack("<I", data[cert_entry_offset + 4 : cert_entry_offset + 8])[0]

    logger.trace(
        "Checked certificate table",
        offset=f"0x{cert_file_offset:x}",
        size=cert_size,
    )

    # Update certificate table offset if it exists (non-zero) and is after the DOS stub
    if cert_file_offset > 0 and cert_file_offset >= 0x80:
        new_cert_offset = cert_file_offset + padding_size
        struct.pack_into("<I", data, cert_entry_offset, new_cert_offset)
        logger.debug(
            "Updated certificate table offset",
            old_offset=f"0x{cert_file_offset:x}",
            new_offset=f"0x{new_cert_offset:x}",
        )

    # Zero out PE checksum (not validated for executable files, only for drivers/DLLs)
    # CheckSum field is at optional header + 64
    checksum_offset = coff_offset + 20 + 64
    struct.pack_into("<I", data, checksum_offset, 0)
    logger.trace("Zeroed PE checksum (not required for executables)")


def update_debug_directory(data: bytearray, padding_size: int) -> None:
    """
    Update debug directory entries' PointerToRawData values after DOS stub expansion.

    The Debug Directory (data directory entry #6) contains an array of IMAGE_DEBUG_DIRECTORY
    structures. Each structure has both AddressOfRawData (RVA) and PointerToRawData (absolute
    file offset). The PointerToRawData field MUST be updated when the DOS stub expands.

    Args:
        data: PE executable data (modified in-place)
        padding_size: Number of bytes added to DOS stub
    """
    # Get PE header location
    pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]
    coff_offset = pe_offset + 4

    # Read magic number to identify PE32 vs PE32+
    magic = struct.unpack("<H", data[coff_offset + 20 : coff_offset + 22])[0]
    is_pe32_plus = magic == 0x20B

    # Data directory offset in optional header
    data_dir_offset = coff_offset + 20 + 112 if is_pe32_plus else coff_offset + 20 + 96

    # Debug Directory is the 7th entry (index 6) in data directory array
    debug_dir_entry_offset = data_dir_offset + (6 * 8)

    if debug_dir_entry_offset + 8 > len(data):
        logger.trace(
            "Debug directory entry beyond file bounds, skipping",
            entry_offset=f"0x{debug_dir_entry_offset:x}",
        )
        return

    # Read debug directory entry (RVA and size)
    debug_dir_rva = struct.unpack("<I", data[debug_dir_entry_offset : debug_dir_entry_offset + 4])[0]
    debug_dir_size = struct.unpack("<I", data[debug_dir_entry_offset + 4 : debug_dir_entry_offset + 8])[0]

    # If no debug directory, skip
    if debug_dir_rva == 0 or debug_dir_size == 0:
        logger.trace("No debug directory present (RVA or size is 0)")
        return

    # Map debug directory RVA to file offset
    debug_dir_file_offset = rva_to_file_offset(bytes(data), debug_dir_rva)
    if debug_dir_file_offset is None:
        logger.trace(
            "Unable to map debug directory RVA to file offset, skipping",
            debug_dir_rva=f"0x{debug_dir_rva:x}",
        )
        return

    logger.debug(
        "Found debug directory",
        rva=f"0x{debug_dir_rva:x}",
        file_offset=f"0x{debug_dir_file_offset:x}",
        size=debug_dir_size,
    )

    # Calculate number of debug directory entries (each is 28 bytes)
    num_debug_entries = debug_dir_size // 28
    logger.debug(f"Debug directory entry count: {num_debug_entries}")

    # Update each debug directory entry's PointerToRawData field
    # IMAGE_DEBUG_DIRECTORY structure:
    #   offset 0: Characteristics (4 bytes)
    #   offset 4: TimeDateStamp (4 bytes)
    #   offset 8: MajorVersion (2 bytes)
    #   offset 10: MinorVersion (2 bytes)
    #   offset 12: Type (4 bytes)
    #   offset 16: SizeOfData (4 bytes)
    #   offset 20: AddressOfRawData (4 bytes, RVA)
    #   offset 24: PointerToRawData (4 bytes, FILE OFFSET) ← THIS NEEDS UPDATE

    updated_count = 0
    for i in range(num_debug_entries):
        entry_offset = debug_dir_file_offset + (i * 28)

        # PointerToRawData is at offset 24 within the debug directory entry
        ptr_raw_data_offset = entry_offset + 24

        if ptr_raw_data_offset + 4 > len(data):
            logger.trace(
                f"Debug entry {i} PointerToRawData beyond file bounds",
                offset=f"0x{ptr_raw_data_offset:x}",
            )
            continue

        # Read current PointerToRawData
        current_ptr = struct.unpack("<I", data[ptr_raw_data_offset : ptr_raw_data_offset + 4])[0]

        # Update if non-zero and >= 0x80 (after DOS stub start)
        if current_ptr > 0 and current_ptr >= 0x80:
            new_ptr = current_ptr + padding_size
            struct.pack_into("<I", data, ptr_raw_data_offset, new_ptr)

            logger.trace(
                f"Updated debug entry {i} PointerToRawData",
                old_offset=f"0x{current_ptr:x}",
                new_offset=f"0x{new_ptr:x}",
            )
            updated_count += 1

    if updated_count > 0:
        logger.debug(f"Updated {updated_count}/{num_debug_entries} debug directory entries")
