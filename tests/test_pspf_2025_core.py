"""
Core PSPF 2025 Format Tests

Tests the fundamental PSPF format structure, reading, and writing.
"""

import hashlib
import json
import os
import struct
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List
import zlib

import pytest

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader,
    PSPFIndex,
    SlotMetadata,
    ephemeral_key_pair,
    PSPF_MAGIC,
    PSPF_VERSION,
    INDEX_SIZE,
    EMOJI_MAGIC_SIZE,
    SLOT_ALIGNMENT,
    LAUNCHER_EMOJIS,
    align_offset
)


class TestPSPFCore:
    """Test core PSPF format functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        import shutil
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def simple_payload(self, temp_dir):
        """Create a simple test payload."""
        payload_path = temp_dir / "hello.sh"
        payload_path.write_text("#!/bin/sh\necho 'Hello PSPF!'")
        return payload_path
    
    @pytest.fixture
    def simple_metadata(self):
        """Create simple metadata."""
        return {
            "format": "PSPF/2025",
            "package": {
                "name": "test-bundle",
                "version": "1.0.0"
            },
            "execution": {
                "primary_slot": 0,
                "command": "{slot:0}/hello.sh"
            },
            "verification": {
                "integrity_seal": {
                    "required": True,
                    "algorithm": "ecdsa-p256"
                }
            }
        }
    
    def test_pspf_specification_implemented(self):
        """Test that PSPF 2025 specification is implemented."""
        assert PSPFBuilder is not None
        assert PSPFReader is not None
        assert PSPFIndex is not None
    
    def test_ephemeral_keys_available(self):
        """Test ephemeral key generation."""
        private_key, public_key = ephemeral_key_pair()
        assert private_key is not None
        assert public_key is not None
        assert len(private_key) == 32
        assert len(public_key) == 32
        assert private_key != public_key
    
    def test_build_minimal_bundle(self, temp_dir, simple_payload, simple_metadata):
        """Test building a minimal PSPF bundle."""
        # Create slot
        slot = SlotMetadata(
            index=0,
            name="hello",
            size=simple_payload.stat().st_size,
            compressed_size=0,
            checksum=hashlib.sha256(simple_payload.read_bytes()).hexdigest(),
            compression="gzip",
            purpose="payload",
            lifecycle="persistent",
            path=simple_payload
        )
        
        # Build bundle
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=[slot],
            launcher_type="go"
        )
        
        # Verify bundle exists
        assert bundle_path.exists()
        assert bundle_path.stat().st_size > 0
    
    def test_emoji_magic_format(self, temp_dir, simple_payload, simple_metadata):
        """Test emoji magic ends with 📦??🪄."""
        # Build bundle
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=[],
            launcher_type="python"
        )
        
        # Check emoji magic
        with open(bundle_path, 'rb') as f:
            f.seek(-16, 2)
            magic = f.read(16)
        
        magic_str = magic.decode('utf-8').strip('\x00')
        assert len(magic_str) == 4
        assert magic_str[0] == '📦'
        assert magic_str[1] == '🐍'  # Python launcher
        assert magic_str[3] == '🪄'
    
    def test_launcher_emoji_mapping(self, temp_dir, simple_metadata):
        """Test launcher language emoji mapping."""
        test_cases = [
            ("go", "🐹"),
            ("rust", "🦀"),
            ("python", "🐍"),
            ("node", "🟢"),
            ("unknown", "📄")
        ]
        
        for launcher_type, expected_emoji in test_cases:
            bundle_path = temp_dir / f"test_{launcher_type}.pspf"
            builder = PSPFBuilder()
            builder.build(
                output_path=bundle_path,
                metadata=simple_metadata,
                slots=[],
                launcher_type=launcher_type
            )
            
            # Check emoji
            with open(bundle_path, 'rb') as f:
                f.seek(-16, 2)
                magic = f.read(16)
            
            magic_str = magic.decode('utf-8')
            # Split into individual emojis (they're multi-byte)
            emojis = [c for c in magic_str.strip('\x00')]
            assert len(emojis) == 4
            assert emojis[1] == expected_emoji
    
    def test_index_block_location(self, temp_dir, simple_metadata):
        """Test index block is at launcher_size offset."""
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=[],
            launcher_type="go"
        )
        
        # Read bundle
        reader = PSPFReader(bundle_path)
        launcher_size = reader.detect_launcher_size()
        
        # Check index magic at correct position
        with open(bundle_path, 'rb') as f:
            f.seek(launcher_size)
            index_magic = f.read(8)
        
        assert index_magic == PSPF_MAGIC
    
    def test_index_block_size(self):
        """Test index block is exactly 256 bytes."""
        assert struct.calcsize(PSPFIndex.FORMAT) == INDEX_SIZE
        
        # Also test packing
        index = PSPFIndex()
        packed = index.pack()
        assert len(packed) == INDEX_SIZE
    
    def test_index_checksum(self, temp_dir, simple_metadata):
        """Test index block checksum validation."""
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=[]
        )
        
        # Read and verify checksum
        reader = PSPFReader(bundle_path)
        index = reader.read_index()  # Should not raise
        assert index.format_magic == PSPF_MAGIC
        assert index.format_version == PSPF_VERSION
    
    def test_metadata_archive_structure(self, temp_dir, simple_metadata):
        """Test metadata.tgz structure."""
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=[]
        )
        
        # Read index to get metadata location
        reader = PSPFReader(bundle_path)
        index = reader.read_index()
        
        # Extract metadata archive
        with open(bundle_path, 'rb') as f:
            f.seek(index.metadata_offset)
            archive_data = f.read(index.metadata_size)
        
        # Verify it's a valid tar.gz
        import io
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode='r:gz') as tar:
            names = tar.getnames()
            assert 'psp.json' in names
            assert 'integrity/seal.sig' in names
            assert 'integrity/seal.pem' in names
    
    def test_metadata_psp_json_required(self, temp_dir, simple_metadata):
        """Test psp.json is required in metadata."""
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=[]
        )
        
        # Read metadata
        reader = PSPFReader(bundle_path)
        metadata = reader.read_metadata()
        
        # Verify required fields
        assert metadata['format'] == 'PSPF/2025'
        assert 'package' in metadata
        assert 'verification' in metadata
    
    def test_slot_alignment(self, temp_dir, simple_metadata):
        """Test slots are aligned to 8-byte boundaries."""
        # Create multiple slots
        slots = []
        for i in range(3):
            slot_path = temp_dir / f"slot{i}.dat"
            # Create slots with non-aligned sizes
            slot_path.write_bytes(b"X" * (100 + i * 7))
            
            slots.append(SlotMetadata(
                index=i,
                name=f"slot{i}",
                size=slot_path.stat().st_size,
                compressed_size=0,
                checksum=hashlib.sha256(slot_path.read_bytes()).hexdigest(),
                compression="none",
                purpose="payload",
                lifecycle="persistent",
                path=slot_path
            ))
        
        # Build bundle
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=slots
        )
        
        # Read and verify alignment
        reader = PSPFReader(bundle_path)
        index = reader.read_index()
        
        with open(bundle_path, 'rb') as f:
            f.seek(index.slot_table_offset)
            for i in range(index.slot_count):
                offset = struct.unpack('<Q', f.read(8))[0]
                size = struct.unpack('<Q', f.read(8))[0]
                checksum = struct.unpack('<I', f.read(4))[0]
                
                # Verify alignment
                assert offset % SLOT_ALIGNMENT == 0, f"Slot {i} not aligned"
    
    def test_align_offset_function(self):
        """Test offset alignment function."""
        # Test various offsets
        assert align_offset(0) == 0
        assert align_offset(1) == 8
        assert align_offset(7) == 8
        assert align_offset(8) == 8
        assert align_offset(9) == 16
        assert align_offset(100) == 104
        assert align_offset(104) == 104
    
    def test_reader_verify_magic(self, temp_dir, simple_metadata):
        """Test magic verification."""
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=[]
        )
        
        reader = PSPFReader(bundle_path)
        assert reader.verify_magic()
        
        # Test corrupted magic
        with open(bundle_path, 'r+b') as f:
            f.seek(-16, 2)
            f.write(b"BADMAGIC" * 2)
        
        reader2 = PSPFReader(bundle_path)
        assert not reader2.verify_magic()
    
    def test_launcher_size_detection(self, temp_dir, simple_metadata):
        """Test launcher size detection."""
        bundle_path = temp_dir / "test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=simple_metadata,
            slots=[]
        )
        
        reader = PSPFReader(bundle_path)
        launcher_size = reader.detect_launcher_size()
        
        # Verify index is at detected position
        with open(bundle_path, 'rb') as f:
            f.seek(launcher_size)
            magic = f.read(8)
        
        assert magic == PSPF_MAGIC
    
    def test_empty_bundle(self, temp_dir):
        """Test building bundle with no slots."""
        bundle_path = temp_dir / "empty.pspf"
        builder = PSPFBuilder()
        
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "empty",
                "version": "1.0.0"
            }
        }
        
        builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[]
        )
        
        # Verify structure
        reader = PSPFReader(bundle_path)
        assert reader.verify_magic()
        index = reader.read_index()
        assert index.slot_count == 0
        
        metadata = reader.read_metadata()
        assert metadata['package']['name'] == 'empty'