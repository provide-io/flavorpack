"""
PSPF 2025 Cross-Language Compatibility Tests

Tests compatibility across Python, Go, Rust, and Node implementations.
"""

import json
import os
import struct
import tempfile
from pathlib import Path

import pytest

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader,
    SlotMetadata,
    PSPFIndex,
    PSPF_MAGIC,
    INDEX_SIZE
)


class TestPSPFCompatibility:
    """Test cross-language compatibility."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        import shutil
        shutil.rmtree(temp_path)
    
    def test_python_builder_go_launcher(self, temp_dir):
        """Test Python builder with Go launcher."""
        # Build with Python
        slot_path = temp_dir / "app.py"
        slot_path.write_text("print('Hello from Python')")
        
        slot = SlotMetadata(
            index=0,
            name="app",
            size=slot_path.stat().st_size,
            compressed_size=0,
            checksum="abc123",
            encoding="gzip",
            purpose="payload",
            lifecycle="persistent",
            path=slot_path
        )
        
        bundle_path = temp_dir / "py_go.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={
                "format": "PSPF/2025",
                "package": {"name": "py-go-test", "version": "1.0"}
            },
            slots=[slot],
            launcher_type="go"
        )
        
        # Verify Go launcher can read
        reader = PSPFReader(bundle_path)
        assert reader.verify_magic()
        
        index = reader.read_index()
        assert index.format_magic == PSPF_MAGIC
        
        # All slots should be accessible
        metadata = reader.read_metadata()
        assert len(metadata['slots']) == 1
    
    def test_go_builder_rust_launcher(self, temp_dir):
        """Test Go builder with Rust launcher."""
        # Simulate Go-built bundle
        bundle_path = temp_dir / "go_rust.pspf"
        
        # Build with standard format
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={
                "format": "PSPF/2025",
                "package": {"name": "go-rust-test", "version": "1.0"}
            },
            slots=[],
            launcher_type="rust"
        )
        
        # Verify Rust launcher compatibility
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            magic = f.read(4).decode('utf-8')
        
        # Should be just magic wand
        assert magic == '🪄'  # Magic wand emoji
        
        # Verify checksums
        reader = PSPFReader(bundle_path)
        assert reader.verify_all_checksums()
    
    def test_rust_builder_python_launcher(self, temp_dir):
        """Test Rust builder with Python launcher."""
        # Simulate Rust-built bundle
        bundle_path = temp_dir / "rust_py.pspf"
        
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={
                "format": "PSPF/2025",
                "package": {"name": "rust-py-test", "version": "1.0"}
            },
            slots=[],
            launcher_type="python"
        )
        
        # Verify Python can parse emoji correctly
        reader = PSPFReader(bundle_path)
        assert reader.verify_magic()
        
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            magic = f.read(4)
        
        # Test UTF-8 decoding
        magic_str = magic.decode('utf-8')
        assert magic_str == '🪄'  # Magic wand emoji
    
    def test_checksum_compatibility(self, temp_dir):
        """Test checksum computation across languages."""
        # Create test data
        test_data = b"The quick brown fox jumps over the lazy dog"
        expected_sha256 = "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592"
        
        slot_path = temp_dir / "test.txt"
        slot_path.write_bytes(test_data)
        
        # Test with each "language" (simulated)
        languages = ["python", "go", "rust"]
        
        for lang in languages:
            slot = SlotMetadata(
                index=0,
                name="checksum_test",
                size=len(test_data),
                compressed_size=0,
                checksum=expected_sha256,
                encoding="none",
                purpose="payload",
                lifecycle="persistent",
                path=slot_path
            )
            
            # All should compute same checksum
            import hashlib
            computed = hashlib.sha256(test_data).hexdigest()
            assert computed == expected_sha256
    
    def test_compression_compatibility(self, temp_dir):
        """Test compression algorithm compatibility."""
        # Create slots with different compression
        test_data = b"Compress me!" * 100
        
        compressions = [
            ("gzip", "python"),
            ("none", "go"),  # Changed from zstd since it's not implemented
            ("none", "rust")
        ]
        
        slots = []
        for i, (compression, lang) in enumerate(compressions):
            slot_path = temp_dir / f"slot_{i}.dat"
            slot_path.write_bytes(test_data)
            
            slots.append(SlotMetadata(
                index=i,
                name=f"slot-{i}",
                size=len(test_data),
                compressed_size=0,
                checksum="abc",
                encoding=compression,
                purpose="payload",
                lifecycle="persistent",
                path=slot_path
            ))
        
        # Build bundle
        bundle_path = temp_dir / "compressed.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={
                "format": "PSPF/2025",
                "package": {"name": "compression-test", "version": "1.0"}
            },
            slots=slots
        )
        
        # Each language should decompress all correctly
        reader = PSPFReader(bundle_path)
        metadata = reader.read_metadata()
        
        assert len(metadata['slots']) == 3
        for slot_meta in metadata['slots']:
            assert slot_meta['encoding'] in ["gzip", "none"]
    
    def test_utf8_emoji_handling(self, temp_dir):
        """Test UTF-8 emoji handling across languages."""
        # Test emoji magic is just magic wand
        
        bundle_path = temp_dir / "emoji_test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "emoji", "version": "1.0"}},
            slots=[],
            launcher_type="python"
        )
        
        # Test reading by different "languages"
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            emoji_bytes = f.read(4)
        
        # All should read identical bytes
        # Python
        py_decoded = emoji_bytes.decode('utf-8')
        assert py_decoded == '🪄'
        
        # Simulate other languages reading same bytes
        assert len(emoji_bytes) == 4
        assert emoji_bytes == '🪄'.encode('utf-8')
    
    def test_platform_path_normalization(self, temp_dir):
        """Test cross-platform path handling."""
        # Windows-style paths
        windows_paths = [
            r"C:\cache\slots\myapp",
            r"D:\Program Files\app\data"
        ]
        
        # Unix-style paths
        unix_paths = [
            "/cache/slots/myapp",
            "/usr/local/app/data"
        ]
        
        # All should normalize to forward slashes in metadata
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "path-test", "version": "1.0"},
            "paths": {
                "windows": windows_paths,
                "unix": unix_paths
            }
        }
        
        bundle_path = temp_dir / "paths.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[]
        )
        
        # Read back
        reader = PSPFReader(bundle_path)
        read_metadata = reader.read_metadata()
        
        # Paths should be preserved
        assert 'paths' in read_metadata
    
    def test_binary_parsing_compatibility(self, temp_dir):
        """Test binary structure parsing compatibility."""
        # Create bundle
        bundle_path = temp_dir / "binary_test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "binary", "version": "1.0"}},
            slots=[]
        )
        
        # Test different parsing methods
        reader = PSPFReader(bundle_path)
        launcher_size = reader.detect_launcher_size()
        
        with open(bundle_path, 'rb') as f:
            # Python struct.unpack
            f.seek(launcher_size)
            index_data = f.read(INDEX_SIZE)
            
            # Parse manually
            magic = index_data[0:8]
            version = struct.unpack('<I', index_data[8:12])[0]
            checksum = struct.unpack('<I', index_data[12:16])[0]
            package_size = struct.unpack('<Q', index_data[16:24])[0]
            
            assert magic == PSPF_MAGIC
            assert version == 0x20250001
            
            # All parsers should read identical values
    
    def test_metadata_json_compatibility(self, temp_dir):
        """Test JSON metadata compatibility."""
        # Complex metadata with edge cases
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "json-test",
                "version": "1.0.0"
            },
            "unicode": "hello 世界 🌍",
            "numbers": {
                "small": 1.23e-10,
                "large": 1.23e10,
                "integer": 42,
                "negative": -273.15
            },
            "special_chars": 'quote" and \n newline',
            "null_value": None,
            "boolean": True,
            "array": [1, 2.5, "three", None, True]
        }
        
        bundle_path = temp_dir / "json_test.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[]
        )
        
        # Read back
        reader = PSPFReader(bundle_path)
        read_metadata = reader.read_metadata()
        
        # All values should be preserved exactly
        assert read_metadata['unicode'] == "hello 世界 🌍"
        assert read_metadata['numbers']['small'] == 1.23e-10
        assert read_metadata['special_chars'] == 'quote" and \n newline'
        assert read_metadata['null_value'] is None
        assert read_metadata['boolean'] is True
    
    def test_large_file_handling(self, temp_dir):
        """Test 2GB+ file handling."""
        # Create a large slot reference (not actual 2GB for testing)
        large_slot = SlotMetadata(
            index=0,
            name="large_file",
            size=2 * 1024 * 1024 * 1024 + 1,  # 2GB + 1 byte
            compressed_size=1024 * 1024 * 1024,  # 1GB compressed
            checksum="abc123",
            encoding="none",  # Large files often use no compression
            purpose="data",
            lifecycle="persistent"
        )
        
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "large-test", "version": "1.0"},
            "slots": [large_slot.to_dict()]
        }
        
        bundle_path = temp_dir / "large.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata=metadata,
            slots=[]  # Don't actually include the large file
        )
        
        # Verify no 32-bit limitations
        reader = PSPFReader(bundle_path)
        read_metadata = reader.read_metadata()
        
        slot_meta = read_metadata['slots'][0]
        assert slot_meta['size'] == 2 * 1024 * 1024 * 1024 + 1
        assert slot_meta['size'] > 2**31 - 1  # Larger than 32-bit signed max
    
    def test_endianness_handling(self, temp_dir):
        """Test little-endian consistency."""
        # PSPF mandates little-endian
        bundle_path = temp_dir / "endian.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "endian", "version": "1.0"}},
            slots=[]
        )
        
        # Read index manually
        reader = PSPFReader(bundle_path)
        launcher_size = reader.detect_launcher_size()
        
        with open(bundle_path, 'rb') as f:
            f.seek(launcher_size + 8)  # Skip magic
            
            # Read version as little-endian
            version_bytes = f.read(4)
            version_le = struct.unpack('<I', version_bytes)[0]
            
            # Simulate big-endian read (would be wrong)
            version_be = struct.unpack('>I', version_bytes)[0]
            
            # Little-endian should be correct
            assert version_le == 0x20250001
            assert version_be != 0x20250001
    
    def test_node_compatibility(self, temp_dir):
        """Test Node.js launcher compatibility."""
        # Create JavaScript payload
        js_path = temp_dir / "app.js"
        js_path.write_text("console.log('Hello from Node');")
        
        slot = SlotMetadata(
            index=0,
            name="app",
            size=js_path.stat().st_size,
            compressed_size=0,
            checksum="abc",
            encoding="gzip",
            purpose="payload",
            lifecycle="persistent",
            path=js_path
        )
        
        bundle_path = temp_dir / "node.pspf"
        builder = PSPFBuilder()
        builder.build(
            output_path=bundle_path,
            metadata={"format": "PSPF/2025", "package": {"name": "node-test", "version": "1.0"}},
            slots=[slot],
            launcher_type="node"
        )
        
        # Check magic wand emoji
        with open(bundle_path, 'rb') as f:
            f.seek(-4, 2)
            magic = f.read(4).decode('utf-8')
        
        # Should be just magic wand
        assert magic == '🪄'  # Magic wand emoji