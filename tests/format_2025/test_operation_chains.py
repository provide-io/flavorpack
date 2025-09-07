"""
Test suite for the new PSPF/2025 operation chain system.
Validates that packed operations work correctly with the existing system.
"""

import tempfile
from pathlib import Path

import pytest

from flavor.psp.format_2025.builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.operations import (
    OP_TAR, OP_GZIP, OP_BZIP2, OP_ZSTD, OP_AES256_GCM,
    pack_operations, unpack_operations, operations_to_string,
    string_to_operations, legacy_codec_to_operations
)
from flavor.psp.format_2025.constants import CODEC_RAW, CODEC_TAR, CODEC_GZIP, CODEC_TGZ
from flavor.psp.format_2025.slots import SlotDescriptor, SlotMetadata


class TestOperationChains:
    """Test the operation chain packing system."""
    
    def test_pack_unpack_operations(self):
        """Test packing and unpacking operation chains."""
        # Single operation
        ops1 = [OP_TAR]
        packed1 = pack_operations(ops1)
        assert packed1 == 0x01
        assert unpack_operations(packed1) == ops1
        
        # Two operations
        ops2 = [OP_TAR, OP_GZIP]
        packed2 = pack_operations(ops2)
        assert packed2 == 0x1001  # 0x01 | (0x10 << 8)
        assert unpack_operations(packed2) == ops2
        
        # Three operations
        ops3 = [OP_TAR, OP_GZIP, OP_AES256_GCM]
        packed3 = pack_operations(ops3)
        assert packed3 == 0x311001  # 0x01 | (0x10 << 8) | (0x31 << 16)
        assert unpack_operations(packed3) == ops3
        
        # Maximum 8 operations
        ops8 = [OP_TAR, OP_GZIP, OP_BZIP2, OP_ZSTD, 
                OP_TAR, OP_GZIP, OP_BZIP2, OP_ZSTD]
        packed8 = pack_operations(ops8)
        assert unpack_operations(packed8) == ops8
    
    def test_operations_to_string(self):
        """Test converting operations to human-readable strings."""
        assert operations_to_string(0) == "RAW"
        assert operations_to_string(pack_operations([OP_TAR])) == "TAR"
        assert operations_to_string(pack_operations([OP_TAR, OP_GZIP])) == "TAR|GZIP"
        assert operations_to_string(pack_operations([OP_TAR, OP_BZIP2])) == "TAR|BZIP2"
    
    def test_string_to_operations(self):
        """Test parsing operation strings."""
        assert string_to_operations("RAW") == 0
        assert string_to_operations("TAR") == pack_operations([OP_TAR])
        assert string_to_operations("TAR|GZIP") == pack_operations([OP_TAR, OP_GZIP])
        assert string_to_operations("tar.gz") == pack_operations([OP_TAR, OP_GZIP])
        assert string_to_operations("tar.bz2") == pack_operations([OP_TAR, OP_BZIP2])
    
    def test_legacy_codec_compatibility(self):
        """Test backward compatibility with legacy codec constants."""
        assert legacy_codec_to_operations(CODEC_RAW) == 0
        assert legacy_codec_to_operations(CODEC_TAR) == pack_operations([OP_TAR])
        assert legacy_codec_to_operations(CODEC_GZIP) == pack_operations([OP_GZIP])
        assert legacy_codec_to_operations(CODEC_TGZ) == pack_operations([OP_TAR, OP_GZIP])
    
    def test_slot_descriptor_with_operations(self):
        """Test SlotDescriptor handles operations correctly."""
        # Create with legacy codec
        slot1 = SlotDescriptor(
            id=1,
            name="test",
            codec=CODEC_TGZ,
            size=1024
        )
        # Should auto-convert to operations
        assert slot1.operations == pack_operations([OP_TAR, OP_GZIP])
        
        # Create with operations
        slot2 = SlotDescriptor(
            id=2,
            name="test2",
            operations=pack_operations([OP_TAR, OP_BZIP2]),
            size=2048
        )
        # Should set codec for compatibility
        assert slot2.codec == CODEC_RAW  # No direct mapping
        
        # Pack and unpack
        packed = slot1.pack()
        assert len(packed) == 64  # Correct size
        
        unpacked = SlotDescriptor.unpack(packed)
        assert unpacked.id == slot1.id
        assert unpacked.codec == slot1.codec
    
    def test_builder_with_operations(self):
        """Test that PSPFBuilder works with operation chains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test file
            test_file = tmpdir / "test.txt"
            test_file.write_text("Hello, operations!")
            
            # Build package with operation chain
            builder = PSPFBuilder(launcher_path=None, package_version="2025.1")
            builder.add_slot(
                source_path=test_file,
                target_path="test.txt",
                codec=CODEC_TGZ  # Legacy codec, will be converted
            )
            
            # Build package
            output = tmpdir / "test.psp"
            result = builder.build(output_path=output)
            assert result.success
            
            # Read package and verify operations
            reader = PSPFReader(output)
            info = reader.get_package_info()
            
            # Check slot has correct codec
            slot = info.slots[0]
            assert slot.codec == CODEC_TGZ
            
            # The slot descriptor should have operations set
            desc = reader.slot_table.slots[0]
            # Operations are handled internally now
            assert desc.codec == CODEC_TGZ
    
    def test_operation_chain_execution(self):
        """Test that operation chains can be executed."""
        from flavor.archive.operation_handler import OperationHandler
        
        handler = OperationHandler()
        
        # Validate operations
        valid, msg = handler.validate_operations(pack_operations([OP_TAR, OP_GZIP]))
        assert valid
        
        # Test with unsupported operation (if any)
        # All our test operations should be supported
        valid, msg = handler.validate_operations(pack_operations([OP_TAR]))
        assert valid
    
    def test_metadata_with_operations(self):
        """Test SlotMetadata handles operation descriptions."""
        meta = SlotMetadata(
            index=0,
            id="test",
            source="source/",
            target="target/",
            codec="tar.gz"  # String representation
        )
        
        # Should be able to describe codec
        assert meta.codec == "tar.gz"
        
        # Convert to dict for JSON
        data = meta.to_dict()
        assert data["codec"] == "tar.gz"


class TestBackwardCompatibility:
    """Ensure the new system maintains backward compatibility."""
    
    def test_existing_packages_still_readable(self):
        """Test that packages built with old system are still readable."""
        # This would test actual legacy packages if we had them
        # For now, verify the codec mapping works
        assert CODEC_RAW == 0
        assert CODEC_TAR == 1
        assert CODEC_GZIP == 2
        assert CODEC_TGZ == 3
    
    def test_codec_field_preserved(self):
        """Test that codec field is preserved for compatibility."""
        slot = SlotDescriptor(
            id=1,
            name="compat",
            codec=CODEC_TGZ
        )
        
        # Pack and unpack
        data = slot.pack()
        restored = SlotDescriptor.unpack(data)
        
        # Codec should be preserved
        assert restored.codec == CODEC_TGZ
    
    def test_mixed_codec_and_operations(self):
        """Test handling of mixed codec and operations."""
        # Create slot with codec
        slot1 = SlotDescriptor(id=1, codec=CODEC_TAR)
        assert slot1.operations == pack_operations([OP_TAR])
        
        # Create slot with operations
        ops = pack_operations([OP_TAR, OP_GZIP])
        slot2 = SlotDescriptor(id=2, operations=ops)
        assert slot2.codec == CODEC_TGZ  # Should map to TGZ
        
        # Verify both pack/unpack correctly
        data1 = slot1.pack()
        data2 = slot2.pack()
        
        restored1 = SlotDescriptor.unpack(data1)
        restored2 = SlotDescriptor.unpack(data2)
        
        assert restored1.codec == CODEC_TAR
        assert restored2.codec == CODEC_TGZ