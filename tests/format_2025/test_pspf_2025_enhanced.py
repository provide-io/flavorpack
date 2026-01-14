#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for enhanced PSPF/2025 format with memory-mapped support."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import struct

import pytest

from flavor.config.defaults import (
    ACCESS_AUTO,
    ACCESS_FILE,
    ACCESS_MMAP,
    CACHE_NORMAL,
    CAPABILITY_MMAP,
)
from flavor.psp.format_2025.constants import (
    DEFAULT_HEADER_SIZE,
    DEFAULT_MAGIC_TRAILER_SIZE,
    DEFAULT_MAX_MEMORY,
    DEFAULT_MIN_MEMORY,
    PSPF_VERSION,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
)
from flavor.psp.format_2025.index import PSPFIndex


class TestEnhancedConstants:
    """Test enhanced constants and sizes."""

    def test_header_size(self) -> None:
        """Header should be 8192 bytes (8KB)."""
        assert DEFAULT_HEADER_SIZE == 8192

    def test_version_format(self) -> None:
        """Version should be 0x20250001."""
        assert PSPF_VERSION == 0x20250001

    def test_magic_trailer_emojis(self) -> None:
        """MagicTrailer should have both emojis."""
        assert DEFAULT_MAGIC_TRAILER_SIZE == 8200  # 4 + 8192 + 4
        assert len(TRAILER_START_MAGIC + TRAILER_END_MAGIC) == 8  # Both emojis = 8 bytes


class TestEnhancedIndex:
    """Test enhanced 512-byte index structure."""

    def test_index_size(self) -> None:
        """Index should pack to exactly 8192 bytes (8KB)."""
        index = PSPFIndex()
        packed = index.pack()
        assert len(packed) == 8192

    def test_index_fields(self) -> None:
        """Test new index fields."""
        index = PSPFIndex()

        # New fields should exist
        assert index.access_mode == ACCESS_AUTO
        assert index.cache_strategy == CACHE_NORMAL
        assert index.max_memory == DEFAULT_MAX_MEMORY
        assert index.min_memory == DEFAULT_MIN_MEMORY
        assert index.capabilities & CAPABILITY_MMAP
        # SLOT_DESCRIPTOR_SIZE is a constant (64), not an index field
        assert index.page_size == 4096

    def test_pack_unpack_roundtrip(self) -> None:
        """Pack and unpack should preserve data."""
        index = PSPFIndex()
        index.package_size = 1234567
        index.slot_count = 10
        index.max_memory = 256 * 1024 * 1024

        packed = index.pack()
        unpacked = PSPFIndex.unpack(packed)

        assert unpacked.package_size == 1234567
        assert unpacked.slot_count == 10
        assert unpacked.max_memory == 256 * 1024 * 1024
        assert unpacked.index_checksum != 0  # Should have checksum

    def test_checksum_validation(self) -> None:
        """Checksum should be calculated correctly."""
        index = PSPFIndex()
        packed = index.pack()

        # Extract checksum from packed data
        # Checksum is at offset 4 (after format_version at offset 0)
        checksum_offset = 4
        stored_checksum = struct.unpack_from("<I", packed, checksum_offset)[0]

        # Recalculate with checksum field zeroed
        data_copy = bytearray(packed)
        data_copy[checksum_offset : checksum_offset + 4] = b"\x00\x00\x00\x00"

        import zlib

        calculated = zlib.adler32(bytes(data_copy))

        assert stored_checksum == calculated


class TestPlatformSpecific:
    """Test platform-specific features."""

    def test_page_size(self) -> None:
        """Page size should be set based on platform."""
        import sys

        from flavor.config.defaults import DEFAULT_PAGE_SIZE

        if sys.platform == "darwin":
            # macOS, especially Apple Silicon
            assert DEFAULT_PAGE_SIZE == 16384
        else:
            # Linux/Windows
            assert DEFAULT_PAGE_SIZE == 4096

    def test_access_modes(self) -> None:
        """Access modes should be defined."""
        from flavor.config.defaults import (
            ACCESS_AUTO,
            ACCESS_STREAM,
        )

        # All modes should be unique
        modes = {ACCESS_FILE, ACCESS_MMAP, ACCESS_AUTO, ACCESS_STREAM}
        assert len(modes) == 4


class TestCleanup:
    """Ensure tests clean up after themselves."""

    @pytest.fixture(autouse=True)
    def cleanup(self, tmp_path: Path) -> Iterator[None]:
        """Clean up any test artifacts."""
        yield
        # Cleanup happens automatically with tmp_path
        pass


class TestEnhancedSlots:
    """Test enhanced 64-byte slot descriptors."""

    def test_slot_descriptor_size(self) -> None:
        """Slot descriptor should pack to exactly 64 bytes."""
        from flavor.psp.format_2025.slots import SlotDescriptor

        slot = SlotDescriptor(id=12345, name="test.py")
        packed = slot.pack()
        assert len(packed) == 64

    def test_slot_name_hashing(self) -> None:
        """Slot names should be hashed for fast lookup."""
        from flavor.psp.format_2025.slots import SlotDescriptor, hash_name

        slot = SlotDescriptor(id=1, name="main.py")
        expected_hash = hash_name("main.py")
        assert slot.name_hash == expected_hash

    def test_slot_pack_unpack_roundtrip(self) -> None:
        """Pack and unpack should preserve slot data."""
        from flavor.psp.format_2025.slots import SlotDescriptor

        slot = SlotDescriptor(
            id=999,
            name="data.db",
            size=1024 * 1024,
            checksum=0xABCDEF00,
            operations=1,  # gzip
            lifecycle=0,  # permanent
            permissions=0o755 & 0xFF,  # Low byte
            permissions_high=(0o755 >> 8) & 0xFF,  # High byte
        )

        packed = slot.pack()
        unpacked = SlotDescriptor.unpack(packed)

        assert unpacked.id == 999
        assert unpacked.size == 1024 * 1024
        assert unpacked.checksum == 0xABCDEF00
        assert unpacked.operations == 1
        assert unpacked.lifecycle == 0
        assert unpacked.permissions == 0o755 & 0xFF
        assert unpacked.permissions_high == (0o755 >> 8) & 0xFF

    def test_slot_view_lazy_loading(self) -> None:
        """SlotView should support lazy loading."""
        from flavor.psp.format_2025.slots import SlotDescriptor, SlotView

        descriptor = SlotDescriptor(id=1, name="lazy.txt")
        view = SlotView(descriptor)

        # Should not have data yet
        assert view._data is None
        assert view._decompressed is None


# 🌶️📦🔚
