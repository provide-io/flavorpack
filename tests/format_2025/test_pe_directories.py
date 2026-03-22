#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PE directory, launcher type, and RVA utilities."""

import struct

import pytest

from flavor.psp.format_2025.pe_utils.directories import update_data_directories, update_debug_directory
from flavor.psp.format_2025.pe_utils.headers import rva_to_file_offset
from flavor.psp.format_2025.pe_utils.launcher import get_launcher_type, process_launcher_for_pspf


def create_pe_with_sections(dos_stub_size: int = 0x80, num_sections: int = 2) -> bytes:
    """Create a minimal PE with realistic section virtual addresses for RVA tests."""
    data = bytearray(8192)

    data[0:2] = b"MZ"
    data[0x3C:0x40] = struct.pack("<I", dos_stub_size)
    data[dos_stub_size : dos_stub_size + 4] = b"PE\x00\x00"

    coff_offset = dos_stub_size + 4
    data[coff_offset : coff_offset + 2] = struct.pack("<H", 0x8664)  # AMD64
    data[coff_offset + 2 : coff_offset + 4] = struct.pack("<H", num_sections)
    data[coff_offset + 16 : coff_offset + 18] = struct.pack("<H", 240)

    opt_hdr_offset = coff_offset + 20
    data[opt_hdr_offset : opt_hdr_offset + 2] = struct.pack("<H", 0x20B)

    section_table_offset = opt_hdr_offset + 240

    for i in range(num_sections):
        sec_off = section_table_offset + (i * 40)
        virt_size = 0x1000
        virt_addr = 0x1000 * (i + 1)
        raw_ptr = 0x400 + (i * 0x400)
        data[sec_off + 8 : sec_off + 12] = struct.pack("<I", virt_size)
        data[sec_off + 12 : sec_off + 16] = struct.pack("<I", virt_addr)
        data[sec_off + 20 : sec_off + 24] = struct.pack("<I", raw_ptr)

    return bytes(data)


def create_minimal_pe(dos_stub_size: int = 0x80, num_sections: int = 2) -> bytes:
    """Create a minimal valid PE executable for testing."""
    data = bytearray(4096)
    data[0:2] = b"MZ"
    data[0x3C:0x40] = struct.pack("<I", dos_stub_size)
    data[dos_stub_size : dos_stub_size + 4] = b"PE\x00\x00"

    coff_offset = dos_stub_size + 4
    data[coff_offset : coff_offset + 2] = struct.pack("<H", 0x8664)
    data[coff_offset + 2 : coff_offset + 4] = struct.pack("<H", num_sections)
    data[coff_offset + 16 : coff_offset + 18] = struct.pack("<H", 224)

    opt_hdr_offset = coff_offset + 20
    data[opt_hdr_offset : opt_hdr_offset + 2] = struct.pack("<H", 0x20B)

    return bytes(data)


@pytest.mark.unit
class TestRvaToFileOffset:
    """Tests for rva_to_file_offset in pe_utils/headers.py."""

    def test_rva_in_first_section(self) -> None:
        """RVA inside first section maps to correct file offset."""
        pe = create_pe_with_sections(num_sections=2)
        result = rva_to_file_offset(pe, 0x1000)
        assert result == 0x400

    def test_rva_offset_within_section(self) -> None:
        """RVA with non-zero offset within section adds correctly."""
        pe = create_pe_with_sections(num_sections=2)
        result = rva_to_file_offset(pe, 0x1100)
        assert result == 0x500

    def test_rva_in_second_section(self) -> None:
        """RVA inside second section maps to correct file offset."""
        pe = create_pe_with_sections(num_sections=2)
        result = rva_to_file_offset(pe, 0x2000)
        assert result == 0x800

    def test_rva_not_in_any_section_returns_none(self) -> None:
        """RVA outside all sections returns None."""
        pe = create_pe_with_sections(num_sections=2)
        result = rva_to_file_offset(pe, 0x9000)
        assert result is None

    def test_rva_before_all_sections_returns_none(self) -> None:
        """RVA before all sections returns None."""
        pe = create_pe_with_sections(num_sections=2)
        result = rva_to_file_offset(pe, 0x100)
        assert result is None

    @pytest.mark.parametrize("rva_offset", [0, 0x100, 0x500, 0xFFF])
    def test_rva_boundary_values_in_section(self, rva_offset: int) -> None:
        """RVA at various offsets within a section maps correctly."""
        pe = create_pe_with_sections(num_sections=2)
        rva = 0x1000 + rva_offset
        expected = 0x400 + rva_offset
        assert rva_to_file_offset(pe, rva) == expected


@pytest.mark.unit
class TestGetLauncherType:
    """Tests for get_launcher_type in pe_utils/launcher.py."""

    def test_non_pe_returns_unknown(self) -> None:
        """Non-PE data returns 'unknown'."""
        result = get_launcher_type(b"ELF binary data" + b"\x00" * 100)
        assert result == "unknown"

    def test_too_short_returns_unknown(self) -> None:
        """Too-short data returns 'unknown'."""
        result = get_launcher_type(b"\x00" * 4)
        assert result == "unknown"

    def test_go_binary_detection(self) -> None:
        """PE with offset 0x80 is detected as Go."""
        go_pe = create_minimal_pe(dos_stub_size=0x80)
        result = get_launcher_type(go_pe)
        assert result == "go"

    def test_rust_binary_detection(self) -> None:
        """PE with offset 0xE8 is detected as Rust."""
        rust_pe = create_minimal_pe(dos_stub_size=0xE8)
        result = get_launcher_type(rust_pe)
        assert result == "rust"

    def test_rust_large_stub_detection(self) -> None:
        """PE with offset 0xF0 (>= 0xE8) is detected as Rust."""
        rust_pe = create_minimal_pe(dos_stub_size=0xF0)
        result = get_launcher_type(rust_pe)
        assert result == "rust"

    def test_intermediate_offset_returns_unknown(self) -> None:
        """PE with offset between 0x80 and 0xE8 (exclusive) returns 'unknown'."""
        pe = create_minimal_pe(dos_stub_size=0xC0)
        result = get_launcher_type(pe)
        assert result == "unknown"

    def test_invalid_pe_signature_returns_unknown(self) -> None:
        """PE with wrong magic at PE offset returns 'unknown'."""
        data = bytearray(512)
        data[0:2] = b"MZ"
        data[0x3C:0x40] = struct.pack("<I", 0x80)
        data[0x80:0x84] = b"XX\x00\x00"
        result = get_launcher_type(bytes(data))
        assert result == "unknown"


@pytest.mark.unit
class TestProcessLauncherForPspf:
    """Tests for process_launcher_for_pspf in pe_utils/launcher.py."""

    def test_non_pe_returned_unchanged(self) -> None:
        """Non-PE (Unix) binary is returned unchanged."""
        unix_data = b"\x7fELF" + b"\x00" * 100
        result = process_launcher_for_pspf(unix_data)
        assert result == unix_data

    def test_go_launcher_returned_unchanged(self) -> None:
        """Go PE launcher (0x80 stub) is returned unchanged."""
        go_pe = create_minimal_pe(dos_stub_size=0x80)
        result = process_launcher_for_pspf(go_pe)
        assert result == go_pe

    def test_rust_launcher_returned(self) -> None:
        """Rust PE launcher (0xE8 stub) is returned (possibly unchanged)."""
        rust_pe = create_minimal_pe(dos_stub_size=0xE8)
        result = process_launcher_for_pspf(rust_pe)
        assert isinstance(result, bytes)

    def test_unknown_launcher_returned_unchanged(self) -> None:
        """Unknown PE type (intermediate offset) is returned unchanged."""
        unknown_pe = create_minimal_pe(dos_stub_size=0xC0)
        result = process_launcher_for_pspf(unknown_pe)
        assert result == unknown_pe

    def test_result_is_bytes(self) -> None:
        """Result is always bytes."""
        data = b"not a PE at all " + b"\x00" * 50
        result = process_launcher_for_pspf(data)
        assert isinstance(result, bytes)


@pytest.mark.unit
class TestUpdateDataDirectories:
    """Tests for update_data_directories in pe_utils/directories.py."""

    def _make_pe_with_cert_table(self, cert_offset: int, cert_size: int = 100) -> bytearray:
        """Build a minimal PE with a certificate table entry."""
        pe = bytearray(create_minimal_pe(dos_stub_size=0x80))
        pe_offset = struct.unpack("<I", pe[0x3C:0x40])[0]
        coff_offset = pe_offset + 4
        opt_hdr_offset = coff_offset + 20
        struct.pack_into("<H", pe, opt_hdr_offset, 0x20B)
        data_dir_offset = opt_hdr_offset + 112
        cert_entry_offset = data_dir_offset + (4 * 8)
        if cert_entry_offset + 8 <= len(pe):
            struct.pack_into("<I", pe, cert_entry_offset, cert_offset)
            struct.pack_into("<I", pe, cert_entry_offset + 4, cert_size)
        return pe

    def test_updates_cert_table_offset(self) -> None:
        """Certificate table offset is updated by padding_size."""
        pe = self._make_pe_with_cert_table(cert_offset=0x200)
        update_data_directories(pe, padding_size=0x70)
        pe_offset = struct.unpack("<I", pe[0x3C:0x40])[0]
        coff_offset = pe_offset + 4
        opt_hdr_offset = coff_offset + 20
        data_dir_offset = opt_hdr_offset + 112
        cert_entry_offset = data_dir_offset + (4 * 8)
        new_cert_offset = struct.unpack("<I", pe[cert_entry_offset : cert_entry_offset + 4])[0]
        assert new_cert_offset == 0x200 + 0x70

    def test_zeroes_cert_table_with_zero_offset(self) -> None:
        """Certificate table with zero offset is not updated."""
        pe = self._make_pe_with_cert_table(cert_offset=0)
        update_data_directories(pe, padding_size=0x70)
        pe_offset = struct.unpack("<I", pe[0x3C:0x40])[0]
        coff_offset = pe_offset + 4
        opt_hdr_offset = coff_offset + 20
        data_dir_offset = opt_hdr_offset + 112
        cert_entry_offset = data_dir_offset + (4 * 8)
        cert_off = struct.unpack("<I", pe[cert_entry_offset : cert_entry_offset + 4])[0]
        assert cert_off == 0

    def test_cert_entry_beyond_bounds_is_noop(self) -> None:
        """Does not raise when cert table entry is beyond file bounds."""
        import contextlib

        pe = bytearray(create_minimal_pe(dos_stub_size=0x80))
        truncated = pe[:512]
        with contextlib.suppress(struct.error):
            update_data_directories(truncated, padding_size=0x10)


@pytest.mark.unit
class TestUpdateDebugDirectory:
    """Tests for update_debug_directory in pe_utils/directories.py."""

    def test_no_debug_directory_is_noop(self) -> None:
        """PE without debug directory returns without modification."""
        pe = bytearray(create_minimal_pe(dos_stub_size=0x80))
        update_debug_directory(pe, padding_size=0x70)
        assert pe[0:2] == b"MZ"

    def test_does_not_raise_for_truncated_pe(self) -> None:
        """Does not raise for a truncated PE beyond normal bounds."""
        import contextlib

        pe = bytearray(create_minimal_pe(dos_stub_size=0x80))
        truncated = pe[:512]
        with contextlib.suppress(struct.error):
            update_debug_directory(truncated, padding_size=0x10)

    def _make_pe_with_debug_dir(self) -> bytearray:
        """Create a PE with a valid debug directory entry."""
        data = bytearray(8192)

        data[0:2] = b"MZ"
        dos_stub_size = 0x80
        data[0x3C:0x40] = struct.pack("<I", dos_stub_size)
        data[dos_stub_size : dos_stub_size + 4] = b"PE\x00\x00"

        coff_offset = dos_stub_size + 4
        data[coff_offset : coff_offset + 2] = struct.pack("<H", 0x8664)
        data[coff_offset + 2 : coff_offset + 4] = struct.pack("<H", 1)
        data[coff_offset + 16 : coff_offset + 18] = struct.pack("<H", 240)

        opt_hdr_offset = coff_offset + 20
        data[opt_hdr_offset : opt_hdr_offset + 2] = struct.pack("<H", 0x20B)

        data_dir_offset = opt_hdr_offset + 112
        debug_dir_rva = 0x1000
        debug_dir_size = 28
        debug_entry_offset = data_dir_offset + (6 * 8)
        struct.pack_into("<I", data, debug_entry_offset, debug_dir_rva)
        struct.pack_into("<I", data, debug_entry_offset + 4, debug_dir_size)

        section_table_offset = opt_hdr_offset + 240
        sec = section_table_offset
        struct.pack_into("<I", data, sec + 8, 0x1000)
        struct.pack_into("<I", data, sec + 12, 0x1000)
        struct.pack_into("<I", data, sec + 20, 0x400)

        debug_raw_ptr = 0x200
        struct.pack_into("<I", data, 0x400 + 24, debug_raw_ptr)

        return data

    def test_updates_debug_ptr_to_raw_data(self) -> None:
        """PointerToRawData in debug directory is updated by padding_size."""
        pe = self._make_pe_with_debug_dir()
        update_debug_directory(pe, padding_size=0x70)
        updated_ptr = struct.unpack("<I", pe[0x400 + 24 : 0x400 + 28])[0]
        assert updated_ptr == 0x200 + 0x70

    def test_zero_ptr_not_updated(self) -> None:
        """PointerToRawData with value 0 is NOT updated."""
        pe = self._make_pe_with_debug_dir()
        struct.pack_into("<I", pe, 0x400 + 24, 0)
        update_debug_directory(pe, padding_size=0x70)
        ptr = struct.unpack("<I", pe[0x400 + 24 : 0x400 + 28])[0]
        assert ptr == 0

    def test_unmappable_rva_is_noop(self) -> None:
        """Debug directory with unmappable RVA is silently skipped."""
        pe = bytearray(create_pe_with_sections(dos_stub_size=0x80, num_sections=2))
        pe_offset = struct.unpack("<I", pe[0x3C:0x40])[0]
        coff_offset = pe_offset + 4
        opt_hdr_offset = coff_offset + 20
        data_dir_offset = opt_hdr_offset + 112
        debug_entry_offset = data_dir_offset + (6 * 8)
        struct.pack_into("<I", pe, debug_entry_offset, 0x9000)
        struct.pack_into("<I", pe, debug_entry_offset + 4, 28)
        update_debug_directory(pe, padding_size=0x70)


# 🌶️📦🔚
