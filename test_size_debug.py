#!/usr/bin/env python3
"""Debug the package size issue."""

import tempfile
from pathlib import Path
import hashlib

from flavor.psp.format_2025 import PSPFBuilder, PSPFReader, SlotMetadata

# Create test payload
with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir = Path(tmpdir)
    
    # Create a simple payload
    payload_path = tmpdir / "test.txt"
    payload_path.write_text("Hello, world!")
    
    # Create slot
    slot = SlotMetadata(
        index=0,
        name="test",
        size=payload_path.stat().st_size,
        checksum=hashlib.sha256(payload_path.read_bytes()).hexdigest(),
        encoding="gzip",
        purpose="payload",
        lifecycle="persistent",
        path=payload_path
    )
    
    # Build package
    bundle_path = tmpdir / "test.pspf"
    builder = PSPFBuilder()
    
    metadata = {
        "format": "PSPF/2025",
        "package": {
            "name": "test",
            "version": "1.0.0"
        }
    }
    
    builder.build(
        output_path=bundle_path,
        metadata=metadata,
        slots=[slot],
        launcher_type="rust"
    )
    
    # Read index
    with PSPFReader(bundle_path) as reader:
        index = reader.read_index()
        actual_size = bundle_path.stat().st_size
        
        print(f"Package size in index: {index.package_size}")
        print(f"Actual file size: {actual_size}")
        print(f"Difference: {actual_size - index.package_size}")
        
        # Check what's at the end of the file and at package_size
        with open(bundle_path, 'rb') as f:
            # Check at package_size position
            f.seek(index.package_size - 20)
            around_size = f.read(40)
            print(f"Around package_size position ({index.package_size}):")
            print(f"  {around_size.hex()}")
            
            # Check actual end
            f.seek(-20, 2)
            last_bytes = f.read()
            print(f"Last 20 bytes of file: {last_bytes.hex()}")
            
            # Check for emoji magic
            emoji_magic = '📦🪄'.encode('utf-8')
            print(f"Emoji magic bytes: {emoji_magic.hex()}")
            
            # Find all occurrences of emoji magic
            f.seek(0)
            content = f.read()
            positions = []
            pos = 0
            while True:
                pos = content.find(emoji_magic, pos)
                if pos == -1:
                    break
                positions.append(pos)
                pos += 1
            print(f"Emoji magic found at positions: {positions}")