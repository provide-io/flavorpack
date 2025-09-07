# PSPFReader API

Low-level API for reading and extracting Progressive Secure Package Format (PSPF) packages.

## Module: `flavor.psp.format_2025.reader`

The reader module provides flexible access to PSPF packages through multiple backend strategies (file, memory-mapped, stream) and supports extraction, verification, and inspection operations.

## PSPFReader Class

### Overview

The `PSPFReader` class provides methods for reading package contents, extracting slots, and verifying integrity.

```python
from flavor.psp.format_2025.reader import PSPFReader

class PSPFReader:
    def __init__(self, bundle_path: Path | str, mode: int = ACCESS_AUTO)
    def open(self) -> None
    def close(self) -> None
    def read_index(self) -> PSPFIndex
    def read_metadata(self) -> dict[str, Any]
    def list_slots(self) -> list[SlotDescriptor]
    def extract_slot(self, slot_id: str, output_dir: Path) -> Path
    def extract_all(self, output_dir: Path) -> dict[str, Path]
    def verify_signature(self, public_key: bytes | None = None) -> bool
    def get_slot_view(self, slot_id: str) -> SlotView
```

### Constructor

```python
def __init__(self, bundle_path: Path | str, mode: int = ACCESS_AUTO) -> None
```

#### Parameters

- **bundle_path** (`Path | str`): Path to the PSPF package file
- **mode** (`int`): Backend access mode

#### Access Modes

| Mode | Value | Description | Use Case |
|------|-------|-------------|----------|
| `ACCESS_AUTO` | 0 | Auto-select based on file size | Default, recommended |
| `ACCESS_FILE` | 1 | File-based I/O | Small packages (<10MB) |
| `ACCESS_MMAP` | 2 | Memory-mapped I/O | Large packages (>100MB) |
| `ACCESS_STREAM` | 3 | Streaming I/O | Network or pipe sources |

#### Example

```python
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.constants import ACCESS_MMAP

# Auto mode (recommended)
reader = PSPFReader("package.psp")

# Memory-mapped for large files
reader = PSPFReader("large.psp", mode=ACCESS_MMAP)
```

### Context Manager Protocol

PSPFReader implements the context manager protocol for automatic resource cleanup:

```python
with PSPFReader("package.psp") as reader:
    metadata = reader.read_metadata()
    # Reader automatically closed on exit
```

### Methods

#### `open() -> None`

Open the package file with the appropriate backend.

```python
reader = PSPFReader("package.psp")
reader.open()  # Explicitly open
# ... use reader ...
reader.close()  # Must close when done
```

#### `close() -> None`

Close the backend and release resources.

```python
reader.close()
```

#### `read_index() -> PSPFIndex`

Read and parse the package index block.

##### Returns

`PSPFIndex`: Package index containing:
- **format_version** (`int`): Format version number
- **metadata_offset** (`int`): Offset to metadata
- **metadata_size** (`int`): Size of metadata
- **slot_count** (`int`): Number of slots
- **capabilities** (`int`): Package capabilities flags
- **public_key** (`bytes | None`): Embedded public key
- **signature** (`bytes | None`): Package signature

##### Example

```python
with PSPFReader("package.psp") as reader:
    index = reader.read_index()
    print(f"Format version: 0x{index.format_version:08x}")
    print(f"Slots: {index.slot_count}")
    if index.signature:
        print("Package is signed")
```

#### `read_metadata() -> dict[str, Any]`

Read and parse package metadata.

##### Returns

`dict[str, Any]`: Package metadata including:
- **name** (`str`): Package name
- **version** (`str`): Package version
- **author** (`str | None`): Package author
- **description** (`str | None`): Package description
- **platform** (`str | None`): Target platform
- **created** (`str | None`): Creation timestamp
- **entry_point** (`str | None`): Execution entry point

##### Example

```python
with PSPFReader("package.psp") as reader:
    metadata = reader.read_metadata()
    print(f"Package: {metadata['name']} v{metadata['version']}")
    print(f"Author: {metadata.get('author', 'Unknown')}")
    print(f"Description: {metadata.get('description', 'N/A')}")
```

#### `list_slots() -> list[SlotDescriptor]`

List all slots in the package.

##### Returns

`list[SlotDescriptor]`: List of slot descriptors containing:
- **id** (`str`): Slot identifier
- **offset** (`int`): Offset in package
- **size** (`int`): Compressed size
- **uncompressed_size** (`int`): Uncompressed size
- **checksum** (`bytes`): SHA-256 checksum
- **codec** (`int`): Compression codec
- **lifecycle** (`int`): Loading lifecycle
- **purpose** (`int`): Slot purpose

##### Example

```python
with PSPFReader("package.psp") as reader:
    slots = reader.list_slots()
    for slot in slots:
        print(f"Slot: {slot.id}")
        print(f"  Size: {slot.size:,} bytes")
        print(f"  Uncompressed: {slot.uncompressed_size:,} bytes")
        print(f"  Codec: {slot.codec}")
```

#### `extract_slot(slot_id: str, output_dir: Path) -> Path`

Extract a specific slot to disk.

##### Parameters

- **slot_id** (`str`): Identifier of slot to extract
- **output_dir** (`Path`): Directory for extraction

##### Returns

`Path`: Path to extracted content

##### Raises

- **KeyError**: Slot not found
- **IOError**: Extraction failed

##### Example

```python
with PSPFReader("package.psp") as reader:
    # Extract single slot
    extracted = reader.extract_slot("application", Path("/tmp/extracted"))
    print(f"Extracted to: {extracted}")
```

#### `extract_all(output_dir: Path) -> dict[str, Path]`

Extract all slots to disk.

##### Parameters

- **output_dir** (`Path`): Base directory for extraction

##### Returns

`dict[str, Path]`: Mapping of slot IDs to extracted paths

##### Example

```python
with PSPFReader("package.psp") as reader:
    extracted = reader.extract_all(Path("/tmp/package"))
    for slot_id, path in extracted.items():
        print(f"{slot_id}: {path}")
```

#### `verify_signature(public_key: bytes | None = None) -> bool`

Verify package signature.

##### Parameters

- **public_key** (`bytes | None`): Public key for verification. If None, uses embedded key

##### Returns

`bool`: True if signature is valid, False otherwise

##### Example

```python
with PSPFReader("package.psp") as reader:
    # Verify with embedded key
    if reader.verify_signature():
        print("✅ Signature valid")
    else:
        print("❌ Signature invalid")
    
    # Verify with external key
    with open("public.pem", "rb") as f:
        public_key = f.read()
    if reader.verify_signature(public_key):
        print("✅ Verified with external key")
```

#### `get_slot_view(slot_id: str) -> SlotView`

Get a view of slot data without extraction.

##### Parameters

- **slot_id** (`str`): Slot identifier

##### Returns

`SlotView`: View object providing access to slot data

##### Example

```python
with PSPFReader("package.psp") as reader:
    view = reader.get_slot_view("config")
    
    # Read as bytes
    data = view.read()
    
    # Read as text
    text = view.read_text()
    
    # Get decompressed size
    size = view.uncompressed_size
```

### Additional Methods

#### `verify_magic_trailer() -> bool`

Verify the package has valid magic trailer bytes.

```python
with PSPFReader("package.psp") as reader:
    if reader.verify_magic_trailer():
        print("✅ Valid PSPF package")
```

#### `extraction_lock(extract_dir: Path, timeout: float = 30.0)`

Context manager for extraction locking to prevent concurrent extraction.

```python
with PSPFReader("package.psp") as reader:
    extract_dir = Path("/tmp/extract")
    with reader.extraction_lock(extract_dir):
        reader.extract_all(extract_dir)
```

## Backend System

### Backend Classes

The reader uses different backend strategies based on file size and access patterns:

```python
from flavor.psp.format_2025.backends import (
    Backend,           # Abstract base
    FileBackend,       # File I/O
    MmapBackend,       # Memory-mapped
    StreamBackend,     # Streaming
    create_backend     # Factory function
)
```

### Creating Custom Backends

```python
from flavor.psp.format_2025.backends import Backend

class CustomBackend(Backend):
    def open(self, source: Any) -> None:
        # Open the source
        pass
    
    def read_at(self, offset: int, size: int) -> bytes:
        # Read bytes at offset
        pass
    
    def close(self) -> None:
        # Close and cleanup
        pass

# Use custom backend
backend = CustomBackend()
backend.open(my_source)
# Reader can use this backend
```

## SlotView Class

Provides lazy access to slot data without full extraction.

```python
class SlotView:
    @property
    def id(self) -> str
    @property
    def size(self) -> int
    @property
    def uncompressed_size(self) -> int
    @property
    def checksum(self) -> bytes
    @property
    def codec(self) -> int
    
    def read(self) -> bytes
    def read_text(self, encoding: str = "utf-8") -> str
    def extract_to(self, path: Path) -> Path
    def verify_checksum(self) -> bool
```

### Example

```python
with PSPFReader("package.psp") as reader:
    view = reader.get_slot_view("readme")
    
    # Get properties without reading data
    print(f"Size: {view.size}")
    print(f"Uncompressed: {view.uncompressed_size}")
    
    # Read as text
    readme = view.read_text()
    print(readme)
    
    # Verify integrity
    if view.verify_checksum():
        print("✅ Checksum valid")
```

## PSPFIndex Class

Package index structure.

```python
@attrs.define(frozen=True)
class PSPFIndex:
    format_version: int
    metadata_offset: int
    metadata_size: int
    slot_count: int
    launcher_size: int
    capabilities: int
    min_memory: int
    max_memory: int
    public_key: bytes | None = None
    signature: bytes | None = None
```

### Capability Flags

```python
from flavor.psp.format_2025.constants import (
    CAPABILITY_SIGNED,        # Package is signed
    CAPABILITY_COMPRESSED,    # Uses compression
    CAPABILITY_ENCRYPTED,     # Encrypted (future)
    CAPABILITY_MMAP,         # Supports memory mapping
    CAPABILITY_PAGE_ALIGNED,  # Slots are page-aligned
)

# Check capabilities
if index.capabilities & CAPABILITY_SIGNED:
    print("Package is signed")
if index.capabilities & CAPABILITY_COMPRESSED:
    print("Package uses compression")
```

## Error Handling

The reader may raise the following exceptions:

```python
from flavor.exceptions import (
    VerificationError,  # Signature verification failed
    ValidationError,    # Invalid package format
    PackagingError,     # Extraction errors
)

try:
    with PSPFReader("package.psp") as reader:
        metadata = reader.read_metadata()
except VerificationError as e:
    print(f"Verification failed: {e}")
except ValidationError as e:
    print(f"Invalid package: {e}")
except PackagingError as e:
    print(f"Extraction error: {e}")
```

## Performance Optimization

### Backend Selection

```python
from pathlib import Path
from flavor.psp.format_2025.constants import ACCESS_FILE, ACCESS_MMAP

def optimal_backend(package_path: Path) -> int:
    """Select optimal backend based on file size."""
    size = package_path.stat().st_size
    
    if size < 10 * 1024 * 1024:  # < 10MB
        return ACCESS_FILE
    elif size > 100 * 1024 * 1024:  # > 100MB
        return ACCESS_MMAP
    else:
        return ACCESS_AUTO

reader = PSPFReader(package_path, mode=optimal_backend(package_path))
```

### Lazy Extraction

```python
def extract_on_demand(reader: PSPFReader, slot_id: str) -> bytes:
    """Extract slot only when needed."""
    cache_dir = Path("~/.cache/myapp").expanduser()
    cache_file = cache_dir / f"{slot_id}.dat"
    
    if cache_file.exists():
        # Use cached version
        return cache_file.read_bytes()
    
    # Extract and cache
    view = reader.get_slot_view(slot_id)
    data = view.read()
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(data)
    
    return data
```

### Parallel Extraction

```python
import concurrent.futures
from pathlib import Path

def parallel_extract(package_path: Path, output_dir: Path):
    """Extract slots in parallel."""
    with PSPFReader(package_path) as reader:
        slots = reader.list_slots()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for slot in slots:
                future = executor.submit(
                    reader.extract_slot, slot.id, output_dir
                )
                futures.append((slot.id, future))
            
            for slot_id, future in futures:
                path = future.result()
                print(f"Extracted {slot_id}: {path}")
```

## Complete Example

```python
from pathlib import Path
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.constants import ACCESS_MMAP

def analyze_package(package_path: Path):
    """Complete package analysis example."""
    
    # Open package with memory mapping for large files
    with PSPFReader(package_path, mode=ACCESS_MMAP) as reader:
        # Verify package integrity
        if not reader.verify_magic_trailer():
            raise ValueError("Invalid PSPF package")
        
        # Read index
        index = reader.read_index()
        print(f"Format: PSPF/{index.format_version >> 16:04x}")
        print(f"Capabilities: 0x{index.capabilities:08x}")
        
        # Read metadata
        metadata = reader.read_metadata()
        print(f"\nPackage: {metadata['name']} v{metadata['version']}")
        print(f"Author: {metadata.get('author', 'Unknown')}")
        print(f"Platform: {metadata.get('platform', 'Any')}")
        
        # Verify signature
        if index.signature:
            if reader.verify_signature():
                print("✅ Signature verified")
            else:
                print("❌ Signature verification failed")
        else:
            print("⚠️ Package is not signed")
        
        # List slots
        print(f"\nSlots ({index.slot_count}):")
        slots = reader.list_slots()
        total_size = 0
        total_uncompressed = 0
        
        for slot in slots:
            ratio = 100 * (1 - slot.size / slot.uncompressed_size)
            print(f"  {slot.id}:")
            print(f"    Size: {slot.size:,} bytes")
            print(f"    Uncompressed: {slot.uncompressed_size:,} bytes")
            print(f"    Compression: {ratio:.1f}%")
            print(f"    Lifecycle: {slot.lifecycle}")
            
            total_size += slot.size
            total_uncompressed += slot.uncompressed_size
        
        # Summary
        print(f"\nTotal compressed: {total_size:,} bytes")
        print(f"Total uncompressed: {total_uncompressed:,} bytes")
        ratio = 100 * (1 - total_size / total_uncompressed)
        print(f"Overall compression: {ratio:.1f}%")
        
        # Extract if requested
        if input("\nExtract package? (y/n): ").lower() == 'y':
            output_dir = Path("extracted") / metadata['name']
            output_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\nExtracting to {output_dir}...")
            extracted = reader.extract_all(output_dir)
            
            for slot_id, path in extracted.items():
                size = path.stat().st_size if path.is_file() else 0
                print(f"  ✅ {slot_id}: {size:,} bytes")
            
            print(f"\nExtraction complete: {output_dir}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python analyze.py package.psp")
        sys.exit(1)
    
    analyze_package(Path(sys.argv[1]))
```

## Thread Safety

The `PSPFReader` class is thread-safe for read operations. Multiple threads can safely read from the same reader instance:

```python
import threading

def read_slot(reader: PSPFReader, slot_id: str):
    view = reader.get_slot_view(slot_id)
    data = view.read()
    print(f"Thread {threading.current_thread().name}: Read {len(data)} bytes")

with PSPFReader("package.psp") as reader:
    threads = []
    for slot in reader.list_slots():
        thread = threading.Thread(target=read_slot, args=(reader, slot.id))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
```

## Related Documentation

- [PSPFBuilder](builder.md) - Building packages
- [Slot Management](slots.md) - Slot specifications
- [Package Format](index.md) - Package format overview
- [Format Specification](../../../spec/pspf-2025.md) - PSPF format details
- [Core API](../api.md) - High-level API functions