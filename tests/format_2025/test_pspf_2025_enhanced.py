#!/usr/bin/env python3
# tests/test_pspf_2025_enhanced.py
# Tests for enhanced PSPF/2025 format with memory-mapped support

import pytest
import struct
from pathlib import Path

from flavor.psp.format_2025.constants import (
    PSPF_MAGIC, HEADER_SIZE, SLOT_DESCRIPTOR_SIZE,
    TRAILING_MAGIC, ACCESS_AUTO, ACCESS_MMAP, CAPABILITY_MMAP,
    CACHE_NORMAL, DEFAULT_MAX_MEMORY, DEFAULT_MIN_MEMORY
)
from flavor.psp.format_2025.index import PSPFIndex


class TestEnhancedConstants:
    """Test enhanced constants and sizes."""
    
    def test_header_size(self):
        """Header should be 8192 bytes (8KB)."""
        assert HEADER_SIZE == 8192
    
    def test_slot_descriptor_size(self):
        """Slot descriptor should be 64 bytes."""
        assert SLOT_DESCRIPTOR_SIZE == 64
    
    def test_magic_format(self):
        """Magic should be PSPF2025."""
        assert PSPF_MAGIC == b"PSPF2025"
        assert len(PSPF_MAGIC) == 8
    
    def test_trailing_magic(self):
        """Trailing magic should have both emojis."""
        assert "📦" in TRAILING_MAGIC
        assert "🪄" in TRAILING_MAGIC


class TestEnhancedIndex:
    """Test enhanced 512-byte index structure."""
    
    def test_index_size(self):
        """Index should pack to exactly 8192 bytes (8KB)."""
        index = PSPFIndex()
        packed = index.pack()
        assert len(packed) == 8192
    
    def test_index_fields(self):
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
    
    
    
    def test_pack_unpack_roundtrip(self):
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
    
    def test_checksum_validation(self):
        """Checksum should be calculated correctly."""
        index = PSPFIndex()
        packed = index.pack()
        
        # Extract checksum from packed data
        # After magic(8) + version(4) = 12
        checksum_offset = 12
        stored_checksum = struct.unpack_from('<I', packed, checksum_offset)[0]
        
        # Recalculate with checksum field zeroed
        data_copy = bytearray(packed)
        data_copy[checksum_offset:checksum_offset+4] = b'\x00\x00\x00\x00'
        
        import zlib
        calculated = zlib.adler32(bytes(data_copy))
        
        assert stored_checksum == calculated


class TestPlatformSpecific:
    """Test platform-specific features."""
    
    def test_page_size(self):
        """Page size should be set based on platform."""
        import sys
        from flavor.psp.format_2025.constants import PAGE_SIZE
        
        if sys.platform == "darwin":
            # macOS, especially Apple Silicon
            assert PAGE_SIZE == 16384
        else:
            # Linux/Windows
            assert PAGE_SIZE == 4096
    
    def test_access_modes(self):
        """Access modes should be defined."""
        from flavor.psp.format_2025.constants import (
            ACCESS_FILE, ACCESS_MMAP, ACCESS_AUTO, ACCESS_STREAM
        )
        
        # All modes should be unique
        modes = {ACCESS_FILE, ACCESS_MMAP, ACCESS_AUTO, ACCESS_STREAM}
        assert len(modes) == 4


class TestCleanup:
    """Ensure tests clean up after themselves."""
    
    @pytest.fixture(autouse=True)
    def cleanup(self, tmp_path):
        """Clean up any test artifacts."""
        yield
        # Cleanup happens automatically with tmp_path
        pass

class TestEnhancedSlots:
    """Test enhanced 64-byte slot descriptors."""
    
    def test_slot_descriptor_size(self):
        """Slot descriptor should pack to exactly 64 bytes."""
        from flavor.psp.format_2025.slots import SlotDescriptor
        
        slot = SlotDescriptor(id=12345, name="test.py")
        packed = slot.pack()
        assert len(packed) == 64
    
    def test_slot_name_hashing(self):
        """Slot names should be hashed for fast lookup."""
        from flavor.psp.format_2025.slots import SlotDescriptor, hash_name
        
        slot = SlotDescriptor(id=1, name="main.py")
        expected_hash = hash_name("main.py")
        assert slot.name_hash == expected_hash
    
    def test_slot_pack_unpack_roundtrip(self):
        """Pack and unpack should preserve slot data."""
        from flavor.psp.format_2025.slots import SlotDescriptor
        
        slot = SlotDescriptor(
            id=999,
            name="data.db",
            size=1024*1024,
            original_size=2048*1024,
            checksum=0xABCDEF00,
            compression=1,  # gzip
            lifecycle=0,  # permanent
            permissions=0o755
        )
        
        packed = slot.pack()
        unpacked = SlotDescriptor.unpack(packed)
        
        assert unpacked.id == 999
        assert unpacked.size == 1024*1024
        assert unpacked.original_size == 2048*1024
        assert unpacked.checksum == 0xABCDEF00
        assert unpacked.compression == 1
        assert unpacked.lifecycle == 0
        assert unpacked.permissions == 0o755
    
    
    
    def test_slot_view_lazy_loading(self):
        """SlotView should support lazy loading."""
        from flavor.psp.format_2025.slots import SlotDescriptor, SlotView
        
        descriptor = SlotDescriptor(id=1, name="lazy.txt")
        view = SlotView(descriptor)
        
        # Should not have data yet
        assert view._data is None
        assert view._decompressed is None

# 🧪📦🔬🪄