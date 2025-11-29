#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PE header manipulation utilities."""

import struct

import pytest

from flavor.psp.format_2025.pe_utils import (
    expand_dos_stub,
    get_pe_header_offset,
    is_pe_executable,
    needs_dos_stub_expansion,
)


def create_minimal_pe(dos_stub_size: int = 0x80, num_sections: int = 2) -> bytes:
    """Create a minimal valid PE executable for testing.

    Args:
        dos_stub_size: Size of DOS stub (PE header offset)
        num_sections: Number of sections to include

    Returns:
        Minimal PE executable as bytes
    """
    data = bytearray(4096)

    # MZ header
    data[0:2] = b"MZ"
    data[0x3C:0x40] = struct.pack("<I", dos_stub_size)  # e_lfanew

    # PE signature
    data[dos_stub_size : dos_stub_size + 4] = b"PE\x00\x00"

    # COFF header
    coff_offset = dos_stub_size + 4
    data[coff_offset : coff_offset + 2] = struct.pack("<H", 0x8664)  # Machine: AMD64
    data[coff_offset + 2 : coff_offset + 4] = struct.pack("<H", num_sections)  # Number of sections
    data[coff_offset + 16 : coff_offset + 18] = struct.pack("<H", 224)  # Optional header size

    # Optional header magic (PE32+)
    opt_hdr_offset = coff_offset + 20
    data[opt_hdr_offset : opt_hdr_offset + 2] = struct.pack("<H", 0x20B)

    # Section table (after COFF + optional headers)
    section_table_offset = opt_hdr_offset + 224

    # Create sections with realistic file offsets
    for i in range(num_sections):
        section_offset = section_table_offset + (i * 40)
        # Section name
        names = [b".text\x00\x00\x00", b".data\x00\x00\x00", b".rdata\x00\x00"]
        data[section_offset : section_offset + 8] = names[i % len(names)]
        # PointerToRawData (file offset to section data)
        raw_ptr = 0x400 + (i * 0x400)  # Sections at 0x400, 0x800, etc.
        data[section_offset + 20 : section_offset + 24] = struct.pack("<I", raw_ptr)
        # SizeOfRawData
        data[section_offset + 16 : section_offset + 20] = struct.pack("<I", 0x200)

    return bytes(data)


def read_section_offsets(data: bytes) -> list[int]:
    """Read PointerToRawData values from all sections.

    Args:
        data: PE executable data

    Returns:
        List of section file offsets
    """
    pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]
    coff_offset = pe_offset + 4
    num_sections = struct.unpack("<H", data[coff_offset + 2 : coff_offset + 4])[0]
    opt_hdr_size = struct.unpack("<H", data[coff_offset + 16 : coff_offset + 18])[0]
    section_table_offset = coff_offset + 20 + opt_hdr_size

    offsets = []
    for i in range(num_sections):
        section_offset = section_table_offset + (i * 40)
        raw_ptr = struct.unpack("<I", data[section_offset + 20 : section_offset + 24])[0]
        offsets.append(raw_ptr)

    return offsets


class TestPEDetection:
    """Tests for PE executable detection."""

    def test_is_pe_executable_valid(self) -> None:
        """Test detection of valid PE executable."""
        pe_data = create_minimal_pe()
        assert is_pe_executable(pe_data)

    def test_is_pe_executable_elf(self) -> None:
        """Test rejection of ELF executable."""
        elf_data = b"\x7fELF" + b"\x00" * 100
        assert not is_pe_executable(elf_data)

    def test_is_pe_executable_too_short(self) -> None:
        """Test rejection of too-short data."""
        assert not is_pe_executable(b"M")
        assert not is_pe_executable(b"")

    def test_get_pe_header_offset(self) -> None:
        """Test reading PE header offset."""
        pe_data = create_minimal_pe(dos_stub_size=0x80)
        assert get_pe_header_offset(pe_data) == 0x80

        pe_data = create_minimal_pe(dos_stub_size=0xE8)
        assert get_pe_header_offset(pe_data) == 0xE8

    def test_needs_dos_stub_expansion_go_binary(self) -> None:
        """Test detection of Go binary (0x80 DOS stub)."""
        go_binary = create_minimal_pe(dos_stub_size=0x80)
        assert needs_dos_stub_expansion(go_binary)

    def test_needs_dos_stub_expansion_rust_binary(self) -> None:
        """Test that Rust binary (0xE8+ DOS stub) doesn't need expansion."""
        rust_binary = create_minimal_pe(dos_stub_size=0xE8)
        assert not needs_dos_stub_expansion(rust_binary)


class TestDOSStubExpansion:
    """Tests for DOS stub expansion logic."""

    def test_expand_dos_stub_updates_e_lfanew(self) -> None:
        """Test that e_lfanew pointer is updated correctly."""
        original = create_minimal_pe(dos_stub_size=0x80)
        expanded = expand_dos_stub(original)

        # Verify e_lfanew was updated
        new_pe_offset = get_pe_header_offset(expanded)
        assert new_pe_offset == 0xF0, f"Expected PE offset 0xF0, got 0x{new_pe_offset:x}"

    def test_expand_dos_stub_preserves_pe_signature(self) -> None:
        """Test that PE signature is preserved at new location."""
        original = create_minimal_pe(dos_stub_size=0x80)
        expanded = expand_dos_stub(original)

        pe_offset = get_pe_header_offset(expanded)
        pe_sig = expanded[pe_offset : pe_offset + 4]
        assert pe_sig == b"PE\x00\x00"

    def test_expand_dos_stub_updates_section_offsets(self) -> None:
        """Test that section PointerToRawData values are updated.

        This is the CRITICAL test that catches the bug where section offsets
        weren't being updated, causing Windows to read section data from
        wrong file offsets.
        """
        original = create_minimal_pe(dos_stub_size=0x80, num_sections=3)
        original_offsets = read_section_offsets(original)

        # Expand DOS stub
        expanded = expand_dos_stub(original)
        expanded_offsets = read_section_offsets(expanded)

        # Verify all section offsets were shifted by padding size (0x70)
        padding_size = 0xF0 - 0x80
        for i, (orig, exp) in enumerate(zip(original_offsets, expanded_offsets, strict=False)):
            expected = orig + padding_size
            assert exp == expected, (
                f"Section {i}: expected offset 0x{expected:x}, got 0x{exp:x} (original was 0x{orig:x})"
            )

    def test_expand_dos_stub_increases_file_size(self) -> None:
        """Test that expanded file is larger by padding size."""
        original = create_minimal_pe(dos_stub_size=0x80)
        expanded = expand_dos_stub(original)

        padding_size = 0xF0 - 0x80  # 112 bytes
        assert len(expanded) == len(original) + padding_size

    def test_expand_dos_stub_no_op_for_adequate_stub(self) -> None:
        """Test that binaries with adequate DOS stub are unchanged."""
        # Create binary with DOS stub >= target size (0xF0)
        rust_binary = create_minimal_pe(dos_stub_size=0x100)  # 256 bytes, > 0xF0
        result = expand_dos_stub(rust_binary)

        # Should return unchanged
        assert result == rust_binary

    def test_expand_dos_stub_invalid_pe(self) -> None:
        """Test that invalid PE raises ValueError."""
        not_pe = b"Not a PE file"
        with pytest.raises(ValueError, match="not a Windows PE executable"):
            expand_dos_stub(not_pe)


class TestSectionOffsetCorrection:
    """Specific tests for section offset correction - the critical bug fix."""

    def test_section_data_remains_accessible(self) -> None:
        """Test that section data can still be read at correct offset after expansion."""
        # Create PE with known data in sections
        original = create_minimal_pe(dos_stub_size=0x80, num_sections=2)

        # Write marker data at first section location (0x400)
        original_bytes = bytearray(original)
        marker = b"SECTION_DATA_MARKER"
        original_bytes[0x400 : 0x400 + len(marker)] = marker

        # Expand
        expanded = expand_dos_stub(bytes(original_bytes))

        # Read section offset from expanded file
        section_offsets = read_section_offsets(expanded)
        first_section_offset = section_offsets[0]

        # Verify marker data is at the NEW section offset
        read_marker = expanded[first_section_offset : first_section_offset + len(marker)]
        assert read_marker == marker, f"Section data not found at offset 0x{first_section_offset:x}"

    def test_all_sections_shifted_consistently(self) -> None:
        """Test that all sections are shifted by the same amount."""
        original = create_minimal_pe(dos_stub_size=0x80, num_sections=5)
        original_offsets = read_section_offsets(original)

        expanded = expand_dos_stub(original)
        expanded_offsets = read_section_offsets(expanded)

        # Calculate shifts for each section
        shifts = [exp - orig for orig, exp in zip(original_offsets, expanded_offsets, strict=False)]

        # All shifts should be identical (0x70)
        assert all(shift == shifts[0] for shift in shifts), f"Inconsistent shifts: {[hex(s) for s in shifts]}"
        assert shifts[0] == 0x70, f"Expected shift of 0x70, got {hex(shifts[0])}"
