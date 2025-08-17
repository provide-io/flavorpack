"""
PSPF 2025 Slot Management Tests

Tests slot lifecycle, compression, and management functionality.
"""

import hashlib
import os
import struct
import tempfile
from pathlib import Path
import zlib

import pytest

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader,
    PSPFLauncher,
    SlotMetadata,
    SLOT_ALIGNMENT
)
from flavor.psp.format_2025.constants import SLOT_DESCRIPTOR_SIZE


class TestPSPFSlots:
    """Test PSPF slot management."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        import shutil
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def test_slots(self, temp_dir, test_builder):
        """Create test slots with different properties."""
        slots = []
        
        # Text file (compressible)
        text_path = temp_dir / "text.json"
        text_data = '{"key": "value"}' * 100
        text_path.write_text(text_data)
        
        slots.append(SlotMetadata(
            index=0,
            name="config",
            size=len(text_data),
            checksum=hashlib.sha256(text_data.encode()).hexdigest(),
            encoding="gzip",
            purpose="config",
            lifecycle="persistent",
            path=text_path
        ))
        
        # Binary file (less compressible)
        binary_path = temp_dir / "binary.so"
        binary_data = os.urandom(1024)
        binary_path.write_bytes(binary_data)
        
        slots.append(SlotMetadata(
            index=1,
            name="library",
            size=len(binary_data),
            checksum=hashlib.sha256(binary_data).hexdigest(),
            encoding="none",  # Binary files often don't compress well
            purpose="library",
            lifecycle="volatile",
            path=binary_path
        ))
        
        # Temporary file
        temp_path = temp_dir / "temp.whl"
        temp_data = b"WHEEL_DATA" * 50
        temp_path.write_bytes(temp_data)
        
        slots.append(SlotMetadata(
            index=2,
            name="wheel",
            size=len(temp_data),
            checksum=hashlib.sha256(temp_data).hexdigest(),
            encoding="none",
            purpose="payload",
            lifecycle="temporary",
            path=temp_path
        ))
        
        return slots
    
    def test_slot_lifecycle_persistent(self, temp_dir, test_builder):
        """Test persistent slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            name="test-persistent",
            size=1024,
            checksum="abc123",
            encoding="gzip",
            purpose="payload",
            lifecycle="persistent"
        )
        
        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict['lifecycle'] == 'persistent'
        assert slot_dict['name'] == 'test-persistent'
        # Persistent slots should remain after first use
    
    def test_slot_lifecycle_volatile(self, temp_dir, test_builder):
        """Test volatile slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            name="test-volatile",
            size=1024,
            checksum="abc123",
            encoding="gzip",
            purpose="payload",
            lifecycle="volatile"
        )
        
        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict['lifecycle'] == 'volatile'
        assert slot_dict['name'] == 'test-volatile'
        # Volatile slots removed on process exit
    
    def test_slot_lifecycle_temporary(self, temp_dir, test_builder):
        """Test temporary slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            name="test-temporary",
            size=1024,
            checksum="abc123",
            encoding="gzip",
            purpose="payload",
            lifecycle="temporary"
        )
        
        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict['lifecycle'] == 'temporary'
        assert slot_dict['name'] == 'test-temporary'
        # Temporary slots removed after first use
    
    def test_slot_lifecycle_install(self, temp_dir, test_builder):
        """Test install slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            name="test-install",
            size=1024,
            checksum="abc123",
            encoding="gzip",
            purpose="installer",
            lifecycle="install"
        )
        
        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict['lifecycle'] == 'install'
        assert slot_dict['purpose'] == 'installer'
        # Install slots run once then entire bundle removed
    
    def test_multiple_slots(self, temp_dir, test_slots, test_builder):
        """Test bundle with multiple slots."""
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "multi-slot",
                "version": "1.0.0"
            },
            "slots": [slot.to_dict() for slot in test_slots]
        }
        
        bundle_path = temp_dir / "multi.psp"
        # Use test_builder from fixture
        test_builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=test_slots
        )
        
        # Verify all slots
        reader = PSPFReader(bundle_path)
        index = reader.read_index()
        assert index.slot_count == len(test_slots)
        
        # Read metadata
        metadata_read = reader.read_metadata()
        assert len(metadata_read['slots']) == len(test_slots)
        
        # Verify slot properties preserved
        for i, slot in enumerate(test_slots):
            slot_meta = metadata_read['slots'][i]
            assert slot_meta['name'] == slot.name
            assert slot_meta['lifecycle'] == slot.lifecycle
            assert slot_meta['purpose'] == slot.purpose
    
    def test_slot_compression_gzip(self, temp_dir, test_builder):
        """Test gzip compression."""
        # Create highly compressible data
        data = b"REPEAT" * 1000
        slot_path = temp_dir / "compress.txt"
        slot_path.write_bytes(data)
        
        slot = SlotMetadata(
            index=0,
            name="compressed",
            size=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            encoding="gzip",
            purpose="payload",
            lifecycle="persistent",
            path=slot_path
        )
        
        # Use test_builder from fixture
        from flavor.psp.format_2025.constants import COMPRESSION_GZIP
        compressed_data, compression_type = test_builder._compress_data(data, "gzip")
        
        # Verify compression worked
        assert len(compressed_data) < len(data)
        assert compression_type == COMPRESSION_GZIP
        
        # Verify decompression  
        import gzip
        decompressed = gzip.decompress(compressed_data)
        assert decompressed == data
    
    def test_slot_compression_none(self, temp_dir, test_builder):
        """Test no compression."""
        data = b"NOCOMPRESS" * 100
        slot_path = temp_dir / "nocompress.bin"
        slot_path.write_bytes(data)
        
        slot = SlotMetadata(
            index=0,
            name="uncompressed",
            size=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            encoding="none",
            purpose="payload",
            lifecycle="persistent",
            path=slot_path
        )
        
        # Use test_builder from fixture
        from flavor.psp.format_2025.constants import COMPRESSION_NONE
        stored_data, compression_type = test_builder._compress_data(data, "none")
        
        # Verify no compression
        assert stored_data == data
        assert compression_type == COMPRESSION_NONE
    
    def test_slot_checksum_verification(self, temp_dir, test_builder):
        """Test slot checksum verification."""
        # Create slot with known checksum
        data = b"CHECKSUM_TEST"
        expected_checksum = hashlib.sha256(data).hexdigest()
        
        slot_path = temp_dir / "checksum.dat"
        slot_path.write_bytes(data)
        
        slot = SlotMetadata(
            index=0,
            name="checksum_test",
            size=len(data),
            checksum=expected_checksum,
            encoding="none",
            purpose="payload",
            lifecycle="persistent",
            path=slot_path
        )
        
        # Build bundle
        bundle_path = temp_dir / "checksum.psp"
        # Use test_builder from fixture
        test_builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "test", "version": "1.0"}},
            slots=[slot]
        )
        
        # Verify checksum
        reader = PSPFReader(bundle_path)
        assert reader.verify_all_checksums()
    
    def test_slot_table_structure(self, temp_dir, test_slots, test_builder):
        """Test slot table binary structure."""
        bundle_path = temp_dir / "table.psp"
        # Use test_builder from fixture
        test_builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "test", "version": "1.0"}},
            slots=test_slots
        )
        
        reader = PSPFReader(bundle_path)
        index = reader.read_index()
        
        # Read slot table - NEW FORMAT uses 64-byte descriptors
        from flavor.psp.format_2025.slots import SlotDescriptor
        
        with open(bundle_path, 'rb') as f:
            f.seek(index.slot_table_offset)
            
            for i in range(index.slot_count):
                # Each entry is now 64 bytes (SlotDescriptor)
                entry = f.read(SLOT_DESCRIPTOR_SIZE)
                assert len(entry) == SLOT_DESCRIPTOR_SIZE
                
                # Use SlotDescriptor to unpack
                descriptor = SlotDescriptor.unpack(entry)
                
                # Verify descriptor fields
                assert descriptor.offset > 0
                assert descriptor.offset % SLOT_ALIGNMENT == 0
                assert descriptor.size > 0
                assert descriptor.checksum != 0
    
    def test_slot_extraction_caching(self, temp_dir, test_builder):
        """Test slot caching metadata."""
        # Create a bundle with a cacheable slot
        slot_path = temp_dir / "cached.txt"
        slot_path.write_text("Cached content")
        
        slot = SlotMetadata(
            index=0,
            name="cached_slot",
            size=slot_path.stat().st_size,
            checksum=hashlib.sha256(slot_path.read_bytes()).hexdigest(),
            encoding="gzip",
            purpose="payload",
            lifecycle="persistent",
            path=slot_path
        )
        
        # Build bundle
        bundle_path = temp_dir / "cached.psp"
        # Use test_builder from fixture
        test_builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "cached", "version": "1.0"}},
            slots=[slot]
        )
        
        # Verify slot metadata includes caching info
        reader = PSPFReader(bundle_path)
        metadata = reader.read_metadata()
        slot_meta = metadata['slots'][0]
        assert slot_meta['lifecycle'] == 'persistent'  # Persistent slots can be cached
    
    def test_slot_metadata_serialization(self, test_builder):
        """Test SlotMetadata to_dict serialization."""
        slot = SlotMetadata(
            index=5,
            name="test_slot",
            size=2048,
            checksum="deadbeef",
            encoding="none",  # Binary files often don't compress well
            purpose="library",
            lifecycle="volatile",
            path=Path("/tmp/test")
        )
        
        # Serialize
        slot_dict = slot.to_dict()
        
        # Verify all fields
        assert slot_dict['index'] == 5
        assert slot_dict['name'] == "test_slot"
        assert slot_dict['size'] == 2048
        assert slot_dict['checksum'] == "deadbeef"
        assert slot_dict['encoding'] == "none"
        assert slot_dict['purpose'] == "library"
        assert slot_dict['lifecycle'] == "volatile"
        # Path should not be included in serialized metadata
        assert 'path' not in slot_dict
    
    def test_large_slot_handling(self, temp_dir, test_builder):
        """Test handling of large slots."""
        # Create a 10MB slot
        large_data = os.urandom(10 * 1024 * 1024)
        large_path = temp_dir / "large.bin"
        large_path.write_bytes(large_data)
        
        slot = SlotMetadata(
            index=0,
            name="large_slot",
            size=len(large_data),
            checksum=hashlib.sha256(large_data).hexdigest(),
            encoding="none",
            purpose="payload",
            lifecycle="persistent",
            path=large_path
        )
        
        # Build bundle
        bundle_path = temp_dir / "large.psp"
        # Use test_builder from fixture
        test_builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "large", "version": "1.0"}},
            slots=[slot]
        )
        
        # Verify
        assert bundle_path.exists()
        assert bundle_path.stat().st_size > 10 * 1024 * 1024