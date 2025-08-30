#!/usr/bin/env python3
"""Test to verify mock launcher creates proper MagicTrailer."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from flavor.psp.format_2025.builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.constants import (
    MAGIC_TRAILER_SIZE,
    PACKAGE_EMOJI_BYTES,
    MAGIC_WAND_EMOJI_BYTES,
)

# Mock launcher data - same as in conftest.py
MOCK_LAUNCHER_SIZE = 124
MOCK_LAUNCHER_DATA = b"FAKE_LAUNCHER_FOR_TEST" + b"\x00" * (MOCK_LAUNCHER_SIZE - 22)


def mock_load_launcher(launcher_type):
    """Mock launcher loader."""
    return MOCK_LAUNCHER_DATA


def test_mock_creates_valid_magic_trailer():
    """Test that packages built with mock launcher have valid MagicTrailer."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "test.psp"
        
        # Patch the launcher loading
        with patch("flavor.psp.format_2025.metadata.assembly.load_launcher_binary", mock_load_launcher):
            # Build a minimal package
            builder = PSPFBuilder.create().with_keys(seed="test")
            result = builder.metadata(
                format="PSPF/2025",
                package={"name": "test", "version": "1.0.0"},
                allow_empty=True,
            ).build(output)
            
            if not result.success:
                print(f"❌ Build failed: {result.errors}")
                return False
            
            print(f"✅ Build succeeded")
            print(f"Package size: {output.stat().st_size} bytes")
            
            # Check the structure
            with open(output, "rb") as f:
                # Read entire file to understand structure
                data = f.read()
                
                # Look for MagicTrailer components
                package_emoji_pos = data.find(PACKAGE_EMOJI_BYTES)
                wand_emoji_pos = data.find(MAGIC_WAND_EMOJI_BYTES)
                
                print(f"Package emoji (📦) found at: {package_emoji_pos}")
                print(f"Magic wand emoji (🪄) found at: {wand_emoji_pos}")
                
                # Check if MagicTrailer is at the end
                expected_trailer_start = len(data) - MAGIC_TRAILER_SIZE
                print(f"Expected MagicTrailer start: {expected_trailer_start}")
                
                # Read last 8200 bytes
                f.seek(-MAGIC_TRAILER_SIZE, 2)
                trailer = f.read(MAGIC_TRAILER_SIZE)
                
                print(f"Trailer first 4 bytes: {trailer[:4].hex()} (should be f09f93a6)")
                print(f"Trailer last 4 bytes: {trailer[-4:].hex()} (should be f09faa84)")
                
                # Test with reader
                reader = PSPFReader(output)
                magic_ok = reader.verify_magic_trailer()
                print(f"verify_magic_trailer(): {magic_ok}")
                
                if not magic_ok:
                    print("\n❌ MagicTrailer verification failed!")
                    print("Debugging info:")
                    print(f"  File size: {len(data)}")
                    print(f"  Mock launcher size: {MOCK_LAUNCHER_SIZE}")
                    print(f"  First 30 bytes of file: {data[:30].hex()}")
                    print(f"  Last 30 bytes of file: {data[-30:].hex()}")
                    
                    # Find where the actual trailer is
                    if package_emoji_pos >= 0 and wand_emoji_pos >= 0:
                        if wand_emoji_pos == package_emoji_pos + 8196:
                            print(f"  ✓ MagicTrailer found at offset {package_emoji_pos}")
                            print(f"  Problem: Reader expects it at {expected_trailer_start}")
                            print(f"  Difference: {package_emoji_pos - expected_trailer_start} bytes")
                else:
                    print("\n✅ MagicTrailer verification succeeded!")
                    
                return magic_ok


if __name__ == "__main__":
    success = test_mock_creates_valid_magic_trailer()
    exit(0 if success else 1)