#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Windows PE Executable Utilities.

Provides utilities for manipulating Windows PE (Portable Executable) files
to ensure compatibility with PSPF format when data is appended after the executable.
"""

import struct

from provide.foundation import logger

# Target DOS stub size to match Rust MSVC binaries (240 bytes / 0xF0)
TARGET_DOS_STUB_SIZE = 0xF0


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


def _update_section_offsets(data: bytearray, padding_size: int) -> None:
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


def _update_data_directories(data: bytearray, padding_size: int) -> None:
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


def _rva_to_file_offset(data: bytes, rva: int) -> int | None:
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


def _update_debug_directory(data: bytearray, padding_size: int) -> None:
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
    debug_dir_file_offset = _rva_to_file_offset(bytes(data), debug_dir_rva)
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


def _update_size_of_headers(data: bytearray, padding_size: int) -> None:
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
    _update_section_offsets(new_data, padding_size)

    # Update SizeOfHeaders to reflect expanded DOS stub size
    _update_size_of_headers(new_data, padding_size)

    # Update data directories (Certificate Table uses absolute file offsets)
    _update_data_directories(new_data, padding_size)

    # Update debug directory entries (PointerToRawData fields use absolute file offsets)
    _update_debug_directory(new_data, padding_size)

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


def get_launcher_type(launcher_data: bytes) -> str:
    """
    Detect launcher type from PE characteristics.

    Go and Rust compilers produce PE files with different characteristics:
    - Go: Minimal DOS stub (PE offset 0x80 / 128 bytes)
    - Rust: Larger DOS stub (PE offset 0xE8 / 232 bytes or more)

    Args:
        launcher_data: Launcher binary data

    Returns:
        "go", "rust", or "unknown"
    """
    if not is_pe_executable(launcher_data):
        return "unknown"

    pe_offset = get_pe_header_offset(launcher_data)
    if pe_offset is None:
        return "unknown"

    # Go binaries have PE offset 0x80, Rust has 0xE8 or larger
    if pe_offset == 0x80:
        logger.debug("Detected Go launcher", pe_offset=f"0x{pe_offset:x}")
        return "go"
    elif pe_offset >= 0xE8:
        logger.debug("Detected Rust launcher", pe_offset=f"0x{pe_offset:x}")
        return "rust"
    else:
        logger.debug("Unknown launcher type", pe_offset=f"0x{pe_offset:x}")
        return "unknown"


def process_launcher_for_pspf(launcher_data: bytes) -> bytes:
    """
    Process launcher binary for PSPF embedding compatibility.

    This is the main entry point for PE manipulation. It uses a hybrid approach:
    - Go launchers: Use PE overlay (no modifications, PSPF appended after sections)
    - Rust launchers: Use DOS stub expansion (PSPF at fixed 0xF0 offset)

    Phase 29: Go binaries are fundamentally incompatible with DOS stub expansion
    due to their PE structure (15 sections, unusual section names, missing data
    directories). The PE overlay approach is the industry standard and preserves
    100% PE structure integrity.

    Args:
        launcher_data: Original launcher binary

    Returns:
        Processed launcher binary (expanded if Rust, unchanged if Go/Unix)
    """
    if not is_pe_executable(launcher_data):
        # Not a Windows PE executable, return unchanged (Unix binary)
        logger.trace("Launcher is not a PE executable, no processing needed")
        return launcher_data

    launcher_type = get_launcher_type(launcher_data)

    if launcher_type == "go":
        # Go launcher: Use PE overlay approach (zero modifications)
        # PSPF data will be appended after all PE sections
        logger.info("Using PE overlay approach for Go launcher (no PE modifications)")
        return launcher_data
    elif launcher_type == "rust":
        # Rust launcher: Use DOS stub expansion (PSPF at fixed 0xF0 offset)
        if needs_dos_stub_expansion(launcher_data):
            logger.info("Expanding DOS stub for Rust launcher (PSPF at 0xF0)")
            return expand_dos_stub(launcher_data)
        else:
            logger.trace("Rust launcher already has adequate DOS stub")
            return launcher_data
    else:
        # Unknown launcher type: Safe default is no modification (PE overlay)
        logger.info("Unknown launcher type, using PE overlay approach")
        return launcher_data


# 🌶️📦🔚
