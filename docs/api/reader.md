# Reader API

Python API for reading and extracting PSPF packages.

## Overview

The Reader API provides functions for inspecting, verifying, and extracting PSPF packages. Use this API to programmatically access package contents.

---

## PSPFReader Class

Main class for reading PSPF packages.

```python
from pathlib import Path
from flavor.psp.format_2025.reader import PSPFReader

class PSPFReader:
    """Read PSPF bundles with backend support."""

    def __init__(
        self,
        bundle_path: Path | str,
        mode: int = ACCESS_AUTO
    ) -> None:
        """Initialize reader."""
        ...
```

### Context Manager Usage

```python
from pathlib import Path
from flavor.psp.format_2025.reader import PSPFReader

# Recommended: Use as context manager
with PSPFReader(Path("myapp.psp")) as reader:
    index = reader.read_index()
    metadata = reader.read_metadata()
    slots = reader.read_slot_descriptors()

    print(f"Package size: {index.package_size}")
    print(f"Slots: {len(slots)}")

# Reader automatically closes backend
```

---

## Reading Package Components

### read_index

Read the PSPF index block.

```python
def read_index(self) -> PSPFIndex:
    """Read and verify index block."""
    ...
```

#### Example

```python
with PSPFReader(Path("myapp.psp")) as reader:
    index = reader.read_index()

    print(f"Format version: 0x{index.format_version:08x}")
    print(f"Package size: {index.package_size:,} bytes")
    print(f"Launcher size: {index.launcher_size:,} bytes")
    print(f"Slot count: {index.slot_count}")
    print(f"Build timestamp: {index.build_timestamp}")
```

**PSPFIndex Fields:**

```python
@dataclass
class PSPFIndex:
    format_version: int          # Format version (0x2025000c)
    index_checksum: int          # Adler-32 checksum
    package_size: int            # Total package size
    launcher_size: int           # Embedded launcher size
    metadata_offset: int         # Metadata location
    metadata_size: int           # Metadata size
    metadata_checksum: bytes     # SHA-256 checksum (32 bytes)
    slot_table_offset: int       # Slot table location
    slot_count: int              # Number of slots
    build_timestamp: int         # Unix timestamp
    capabilities: int            # Capability flags
    requirements: int            # Requirement flags
```

### read_metadata

Read and parse package metadata (JSON).

```python
def read_metadata(self) -> dict[str, Any]:
    """Read and parse metadata."""
    ...
```

#### Example

```python
with PSPFReader(Path("myapp.psp")) as reader:
    metadata = reader.read_metadata()

    # Access package information
    pkg = metadata.get("package", {})
    print(f"Name: {pkg.get('name')}")
    print(f"Version: {pkg.get('version')}")

    # Access build information
    build = metadata.get("build", {})
    print(f"Builder: {build.get('builder_type')}")
    print(f"Built: {build.get('timestamp')}")

    # Access slots metadata
    slots = metadata.get("slots", [])
    for i, slot in enumerate(slots):
        print(f"Slot {i}: {slot.get('id')} - {slot.get('purpose')}")
```

**Common Metadata Structure:**

```python
{
    "package": {
        "name": str,
        "version": str,
        "description": str,
    },
    "build": {
        "timestamp": str,           # ISO 8601
        "builder_type": str,        # "flavor-rs-builder", etc.
        "builder_version": str,
        "launcher_type": str,       # "rust", "go"
        "platform": str,            # "linux_amd64", etc.
    },
    "slots": [
        {
            "id": str,              # Slot identifier
            "purpose": str,         # Human-readable purpose
            "codec": str,           # "tar.gz", "raw", etc.
        }
    ],
    "execution": {
        "command": list[str],       # Entry point command
        "environment": dict,        # Environment config
    },
}
```

### read_slot_descriptors

Read all slot descriptors.

```python
def read_slot_descriptors(self) -> list[SlotDescriptor]:
    """Read all slot descriptors."""
    ...
```

#### Example

```python
with PSPFReader(Path("myapp.psp")) as reader:
    descriptors = reader.read_slot_descriptors()

    for i, desc in enumerate(descriptors):
        print(f"\nSlot {i}:")
        print(f"  Offset: 0x{desc.offset:016x}")
        print(f"  Size: {desc.size:,} bytes")
        print(f"  Checksum: {desc.data_checksum.hex()[:16]}...")
        print(f"  Operations: 0x{desc.operations:016x}")
```

**SlotDescriptor Fields:**

```python
@dataclass
class SlotDescriptor:
    offset: int                  # Offset in package
    size: int                    # Compressed size
    original_size: int           # Uncompressed size
    data_checksum: bytes         # SHA-256 checksum (32 bytes)
    operations: int              # Operation chain (64-bit)
```

### read_slot_data

Read raw slot data.

```python
def read_slot_data(self, slot_index: int) -> bytes:
    """Read raw slot data (compressed)."""
    ...
```

#### Example

```python
with PSPFReader(Path("myapp.psp")) as reader:
    # Read raw compressed data for slot 0
    slot_data = reader.read_slot_data(0)

    print(f"Slot 0 data size: {len(slot_data):,} bytes")

    # Write to file
    Path("slot_0.tar.gz").write_bytes(slot_data)
```

---

## Extraction

### extract_slot

Extract a single slot to a directory.

```python
def extract_slot(self, slot_index: int, output_dir: Path) -> None:
    """Extract slot to directory."""
    ...
```

#### Example

```python
from pathlib import Path
from flavor.psp.format_2025.reader import PSPFReader

# Extract slot 0 (runtime) to directory
with PSPFReader(Path("myapp.psp")) as reader:
    output = Path("extracted/runtime")
    output.mkdir(parents=True, exist_ok=True)

    reader.extract_slot(0, output)

    print(f"Extracted to: {output}")
    print("Contents:")
    for file in output.rglob("*"):
        if file.is_file():
            print(f"  {file.relative_to(output)}")
```

### extract_all_slots

Extract all slots to a directory.

```python
def extract_all_slots(self, output_dir: Path) -> None:
    """Extract all slots to directory."""
    ...
```

#### Example

```python
with PSPFReader(Path("myapp.psp")) as reader:
    output = Path("extracted")
    reader.extract_all_slots(output)

    # Directory structure:
    # extracted/
    # ├── slot_0/  (runtime)
    # ├── slot_1/  (app code)
    # └── metadata.json
```

---

## Verification

### verify_magic_trailer

Verify package format magic bytes.

```python
def verify_magic_trailer(self) -> bool:
    """Verify MagicTrailer emoji bookends."""
    ...
```

#### Example

```python
with PSPFReader(Path("myapp.psp")) as reader:
    if reader.verify_magic_trailer():
        print("✅ Valid PSPF package")
    else:
        print("❌ Invalid package format")
```

### Verify Checksums

```python
def verify_checksums(reader: PSPFReader) -> bool:
    """Verify all checksums in package."""
    import hashlib

    # Verify index checksum (done automatically in read_index)
    try:
        index = reader.read_index()
    except ValueError as e:
        print(f"❌ Index checksum failed: {e}")
        return False

    # Verify metadata checksum (done automatically in read_metadata)
    try:
        metadata = reader.read_metadata()
    except ValueError as e:
        print(f"❌ Metadata checksum failed: {e}")
        return False

    # Verify slot checksums
    descriptors = reader.read_slot_descriptors()
    for i, desc in enumerate(descriptors):
        slot_data = reader.read_slot_data(i)
        actual_checksum = hashlib.sha256(slot_data).digest()

        if actual_checksum != desc.data_checksum:
            print(f"❌ Slot {i} checksum failed")
            return False

    print("✅ All checksums valid")
    return True

# Use
with PSPFReader(Path("myapp.psp")) as reader:
    verify_checksums(reader)
```

---

## Complete Examples

### Inspect Package

```python
#!/usr/bin/env python3
"""Inspect a PSPF package programmatically."""

from pathlib import Path
from flavor.psp.format_2025.reader import PSPFReader

def inspect_package(package_path: Path):
    """Inspect package and print details."""

    with PSPFReader(package_path) as reader:
        # Verify format
        if not reader.verify_magic_trailer():
            print("❌ Invalid PSPF package")
            return

        # Read components
        index = reader.read_index()
        metadata = reader.read_metadata()
        slots = reader.read_slot_descriptors()

        # Print summary
        print(f"\n📦 Package: {package_path.name}")
        print(f"{'=' * 60}")

        # Format info
        print(f"\n📋 Format:")
        print(f"  Version: 0x{index.format_version:08x}")
        print(f"  Size: {index.package_size / 1024 / 1024:.1f} MB")
        print(f"  Launcher: {index.launcher_size / 1024 / 1024:.1f} MB")

        # Package info
        pkg = metadata.get("package", {})
        print(f"\n📦 Package:")
        print(f"  Name: {pkg.get('name', 'Unknown')}")
        print(f"  Version: {pkg.get('version', 'Unknown')}")

        # Build info
        build = metadata.get("build", {})
        print(f"\n🔨 Build:")
        print(f"  Builder: {build.get('builder_type', 'Unknown')}")
        print(f"  Timestamp: {build.get('timestamp', 'Unknown')}")

        # Slots
        print(f"\n🎰 Slots ({len(slots)}):")
        slot_metadata = metadata.get("slots", [])
        for i, desc in enumerate(slots):
            slot_meta = slot_metadata[i] if i < len(slot_metadata) else {}
            slot_id = slot_meta.get("id", f"slot_{i}")
            purpose = slot_meta.get("purpose", "Unknown")

            print(f"  [{i}] {slot_id}")
            print(f"      Purpose: {purpose}")
            print(f"      Size: {desc.size / 1024 / 1024:.1f} MB")
            print(f"      Original: {desc.original_size / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: inspect.py <package.psp>")
        sys.exit(1)

    inspect_package(Path(sys.argv[1]))
```

### Extract Package Contents

```python
#!/usr/bin/env python3
"""Extract PSPF package contents."""

from pathlib import Path
from flavor.psp.format_2025.reader import PSPFReader
import json

def extract_package(package_path: Path, output_dir: Path):
    """Extract package to directory."""

    print(f"Extracting {package_path} to {output_dir}...")

    with PSPFReader(package_path) as reader:
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract metadata
        metadata = reader.read_metadata()
        metadata_file = output_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
        print(f"✅ Metadata: {metadata_file}")

        # Extract index
        index = reader.read_index()
        index_file = output_dir / "index.json"
        index_data = {
            "format_version": f"0x{index.format_version:08x}",
            "package_size": index.package_size,
            "launcher_size": index.launcher_size,
            "slot_count": index.slot_count,
            "build_timestamp": index.build_timestamp,
        }
        index_file.write_text(json.dumps(index_data, indent=2))
        print(f"✅ Index: {index_file}")

        # Extract slots
        slots = reader.read_slot_descriptors()
        for i in range(len(slots)):
            slot_file = output_dir / f"slot_{i}.tar.gz"
            slot_data = reader.read_slot_data(i)
            slot_file.write_bytes(slot_data)
            print(f"✅ Slot {i}: {slot_file} ({len(slot_data) / 1024 / 1024:.1f} MB)")

        print(f"\n✅ Extraction complete: {output_dir}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: extract.py <package.psp> <output_dir>")
        sys.exit(1)

    extract_package(Path(sys.argv[1]), Path(sys.argv[2]))
```

---

## Best Practices

!!! tip "Context Managers"
    Always use PSPFReader as a context manager to ensure proper cleanup:
    ```python
    with PSPFReader(path) as reader:
        # Work with reader
        ...
    # Automatically closed
    ```

!!! tip "Error Handling"
    Handle checksumfailures and corrupted packages:
    ```python
    try:
        with PSPFReader(path) as reader:
            index = reader.read_index()
            metadata = reader.read_metadata()
    except ValueError as e:
        print(f"Package corrupted: {e}")
    ```

!!! tip "Performance"
    Read components only once and cache results:
    ```python
    with PSPFReader(path) as reader:
        index = reader.read_index()
        # index is cached, subsequent calls are fast
        index2 = reader.read_index()  # Returns cached
    ```

---

## See Also

- [Packaging API](packaging.md) - Build packages
- [Builder API](builder.md) - Low-level building
- [Crypto API](crypto.md) - Cryptographic operations
- [Inspection Guide](../guide/usage/inspection.md) - Inspection workflows

---

**For complete API reference, see the source code:**
`src/flavor/psp/format_2025/reader.py`
