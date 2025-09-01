#!/usr/bin/env python3
"""Test script to verify MagicTrailer implementation."""

import tempfile
from pathlib import Path

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader,
    SlotMetadata,
    PSPF_VERSION,
    MAGIC_TRAILER_SIZE,
    PACKAGE_EMOJI_BYTES,
    MAGIC_WAND_EMOJI_BYTES,
    build_package,
    BuildSpec,
)

def test_magic_trailer():
    """Test that MagicTrailer is properly written and detected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create build spec
        output_path = temp_path / "test.psp"
        
        # Add minimal launcher
        launcher_content = b"#!/bin/sh\necho test"
        launcher_path = temp_path / "launcher"
        launcher_path.write_bytes(launcher_content)
        
        # Build the package
        spec = BuildSpec(
            launcher_path=launcher_path,
            slots=[],
            metadata={
                "name": "test-package",
                "version": "1.0.0",
            },
            key_seed="test123",
        )
        
        result = build_package(spec, output_path)
        
        print(f"✅ Package built: {output_path}")
        print(f"   Size: {output_path.stat().st_size} bytes")
        
        # Read the last 8200 bytes (MagicTrailer)
        with open(output_path, "rb") as f:
            f.seek(-MAGIC_TRAILER_SIZE, 2)  # Seek to end - 8200
            trailer = f.read(MAGIC_TRAILER_SIZE)
        
        # Verify structure
        assert len(trailer) == MAGIC_TRAILER_SIZE, f"Trailer size mismatch: {len(trailer)} != {MAGIC_TRAILER_SIZE}"
        
        # Check for 📦 at start
        assert trailer[:4] == PACKAGE_EMOJI_BYTES, f"Missing 📦 at start: {trailer[:4].hex()}"
        print(f"✅ Found 📦 at trailer start")
        
        # Check for 🪄 at end
        assert trailer[-4:] == MAGIC_WAND_EMOJI_BYTES, f"Missing 🪄 at end: {trailer[-4:].hex()}"
        print(f"✅ Found 🪄 at trailer end")
        
        # Extract and verify index
        index_data = trailer[4:4+8192]
        assert len(index_data) == 8192, f"Index size mismatch: {len(index_data)} != 8192"
        
        # Check version at start of index (first 4 bytes should be version)
        import struct
        version = struct.unpack("<I", index_data[:4])[0]
        assert version == PSPF_VERSION, f"Version mismatch: 0x{version:08x} != 0x{PSPF_VERSION:08x}"
        print(f"✅ Index version correct: 0x{version:08x}")
        
        # Now test reading with PSPFReader
        reader = PSPFReader(output_path)
        index = reader.read_index()
        
        assert index.format_version == PSPF_VERSION
        print(f"✅ Reader successfully read index with version 0x{index.format_version:08x}")
        
        print("\n🎉 All tests passed! MagicTrailer implementation is working correctly.")
        return True

if __name__ == "__main__":
    test_magic_trailer()