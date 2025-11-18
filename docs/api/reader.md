# Reader API

The FlavorPack Reader API provides tools for reading and extracting PSPF packages.

!!! note "Low-Level API"
    This is a low-level API for advanced use cases. For package inspection, see the [CLI Reference](../guide/usage/cli/).

    The Reader API gives you programmatic access to package contents, metadata, slot extraction, and integrity verification.

## Overview

The Reader API is the low-level interface for reading and extracting PSPF/2025 packages. It handles:

- Package format validation
- Index block parsing
- Metadata deserialization
- Slot descriptor reading
- Selective slot extraction
- Signature verification
- Checksum validation

## When to Use the Reader API

**Use the Reader API when you need**:

- Programmatic package inspection
- Custom extraction logic
- Integration with analysis tools
- Selective slot extraction
- Metadata parsing in applications
- Package validation in CI/CD

**Use the CLI tools instead when**:

- Quick package inspection (`flavor inspect`)
- Verification (`flavor verify`)
- Full extraction (`flavor extract-all`)
- Manual slot extraction

## Basic Usage

### Reading Package Metadata

```python
from pathlib import Path
from flavor.psp.format_2025.reader import PSPFReader

# Open package for reading
package_path = Path("myapp.psp")
reader = PSPFReader(package_path)

# Read package metadata
metadata = reader.read_metadata()

print(f"Package: {metadata['package']['name']}")
print(f"Version: {metadata['package']['version']}")
print(f"Format: {metadata['format_version']}")
print(f"Slots: {len(metadata['slots'])}")
```

### Inspecting Slots

```python
# Get all slot descriptors
slots = reader.read_slots()

for slot in slots:
    print(f"Slot {slot.id}:")
    print(f"  Name: {slot.name}")
    print(f"  Size: {slot.size} bytes")
    print(f"  Checksum: {slot.checksum.hex()}")
    print(f"  Purpose: {slot.purpose}")
```

### Extracting a Single Slot

```python
# Extract specific slot
slot_id = 1
output_dir = Path("extracted")
output_dir.mkdir(exist_ok=True)

# Extract slot data
slot_data = reader.extract_slot(slot_id)

# Write to file
output_file = output_dir / f"slot_{slot_id}.tar.gz"
output_file.write_bytes(slot_data)

print(f"Extracted slot {slot_id} to {output_file}")
```

### Extracting All Slots

```python
# Extract all slots to directory
extraction_dir = Path("workenv")

for slot in reader.read_slots():
    slot_data = reader.extract_slot(slot.id)
    slot_file = extraction_dir / f"slot_{slot.id}_{slot.name}.tar.gz"
    slot_file.write_bytes(slot_data)
    print(f"Extracted {slot.name}")
```

## Advanced Usage

### Verifying Package Integrity

!!! note "Verification via CLI"
    Package verification is typically handled via the `flavor verify` CLI command or the high-level `verify_package()` function. The Reader API provides access to signature data, but verification logic is in `flavor.psp.security`.

    For manual verification workflows, see `src/flavor/psp/security.py` which uses `provide.foundation.crypto.Ed25519Verifier`.

```python
# Verification is typically handled via the high-level API:
from flavor import verify_package
from pathlib import Path

result = verify_package(Path("myapp.psp"))
if result["valid"]:
    print("✅ Package verification passed")
else:
    print("❌ Package verification failed")
```

### Selective Extraction Based on Purpose

```python
from flavor.psp.format_2025.slots import SlotPurpose

# Extract only application code, skip runtime
slots = reader.read_slots()

for slot in slots:
    if slot.purpose == SlotPurpose.APPLICATION_CODE:
        data = reader.extract_slot(slot.id)
        # Process application code
        print(f"Extracted application: {slot.name}")
    elif slot.purpose == SlotPurpose.PYTHON_ENVIRONMENT:
        print(f"Skipping runtime: {slot.name}")
```

### Lazy Loading with Context Manager

```python
# Use context manager for automatic cleanup
with PSPFReader(package_path) as reader:
    # Read metadata
    meta = reader.read_metadata()

    # Extract only what's needed
    if meta['slots'][0]['size'] < 1_000_000:  # < 1MB
        data = reader.extract_slot(0)
        # Process small slot
    else:
        print("Slot too large, skipping")

# Reader automatically closed here
```

### Streaming Large Slots

```python
# Stream slot data for large files
def stream_slot(reader, slot_id, chunk_size=8192):
    """Stream slot data in chunks."""
    slot = reader.read_slots()[slot_id]
    offset = slot.offset

    with open(reader.package_path, "rb") as f:
        f.seek(offset)
        remaining = slot.size

        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk:
                break
            yield chunk
            remaining -= len(chunk)

# Use streaming extraction
output_file = Path("large_slot.tar.gz")
with output_file.open("wb") as f:
    for chunk in stream_slot(reader, slot_id=2):
        f.write(chunk)
```

### Validating Checksums

```python
from hashlib import sha256

def validate_slot_checksums(reader):
    """Validate all slot checksums."""
    slots = reader.read_slots()
    results = []

    for slot in slots:
        # Extract slot data
        data = reader.extract_slot(slot.id)

        # Calculate checksum
        calculated = sha256(data).digest()[:8]  # First 8 bytes

        # Compare with stored checksum
        is_valid = calculated == slot.checksum

        results.append({
            "slot_id": slot.id,
            "name": slot.name,
            "valid": is_valid,
        })

    return results

# Validate all checksums
results = validate_slot_checksums(reader)
for result in results:
    status = "✅" if result["valid"] else "❌"
    print(f"{status} Slot {result['slot_id']}: {result['name']}")
```

## Common Patterns

### Package Analysis Tool

```python
def analyze_package(package_path):
    """Comprehensive package analysis."""
    reader = PSPFReader(package_path)

    # Basic info
    metadata = reader.read_metadata()
    slots = reader.read_slots()

    analysis = {
        "package_name": metadata["package"]["name"],
        "version": metadata["package"]["version"],
        "format_version": metadata["format_version"],
        "total_size": package_path.stat().st_size,
        "slot_count": len(slots),
        "slots": []
    }

    # Analyze each slot
    total_slot_size = 0
    for slot in slots:
        slot_info = {
            "id": slot.id,
            "name": slot.name,
            "size": slot.size,
            "original_size": slot.original_size,
            "compression_ratio": slot.original_size / slot.size if slot.size > 0 else 1.0,
            "purpose": str(slot.purpose),
        }
        analysis["slots"].append(slot_info)
        total_slot_size += slot.size

    analysis["data_size"] = total_slot_size
    analysis["overhead"] = analysis["total_size"] - total_slot_size

    return analysis

# Analyze and report
import json
analysis = analyze_package(Path("myapp.psp"))
print(json.dumps(analysis, indent=2))
```

### Dependency Scanner

```python
def scan_dependencies(package_path):
    """Scan package for Python dependencies."""
    reader = PSPFReader(package_path)
    metadata = reader.read_metadata()

    # Check for dependency information in metadata
    if "dependencies" in metadata.get("package", {}):
        return metadata["package"]["dependencies"]

    # Alternative: Extract and scan Python code
    slots = reader.read_slots()
    dependencies = set()

    for slot in slots:
        if slot.purpose == SlotPurpose.APPLICATION_CODE:
            # Extract and analyze (simplified)
            data = reader.extract_slot(slot.id)
            # Parse requirements or imports
            # ...

    return list(dependencies)

deps = scan_dependencies(Path("myapp.psp"))
print("Dependencies:", deps)
```

### CI/CD Validation

```python
import sys

def validate_package_for_ci(package_path):
    """Validate package in CI pipeline."""
    try:
        reader = PSPFReader(package_path)

        # 1. Validate format
        metadata = reader.read_metadata()
        if metadata["format_version"] != "2025.1":
            print(f"❌ Unsupported format: {metadata['format_version']}")
            return False

        # 2. Validate signature
        if not reader.verify_signature():
            print("❌ Invalid signature")
            return False

        # 3. Validate checksums
        slots = reader.read_slots()
        for slot in slots:
            data = reader.extract_slot(slot.id)
            if sha256(data).digest()[:8] != slot.checksum:
                print(f"❌ Checksum mismatch: slot {slot.id}")
                return False

        # 4. Check metadata
        required_fields = ["package.name", "package.version"]
        for field in required_fields:
            if not _get_nested(metadata, field):
                print(f"❌ Missing field: {field}")
                return False

        print("✅ Package validation passed")
        return True

    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def _get_nested(data, path):
    """Get nested dict value by dot path."""
    keys = path.split(".")
    value = data
    for key in keys:
        value = value.get(key, {})
    return value

# Run validation
if __name__ == "__main__":
    package = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("myapp.psp")
    success = validate_package_for_ci(package)
    sys.exit(0 if success else 1)
```

### Package Comparison

```python
def compare_packages(path1, path2):
    """Compare two package versions."""
    reader1 = PSPFReader(path1)
    reader2 = PSPFReader(path2)

    meta1 = reader1.read_metadata()
    meta2 = reader2.read_metadata()

    comparison = {
        "version_change": f"{meta1['package']['version']} → {meta2['package']['version']}",
        "size_change": path2.stat().st_size - path1.stat().st_size,
        "slot_changes": [],
    }

    slots1 = {s.name: s for s in reader1.read_slots()}
    slots2 = {s.name: s for s in reader2.read_slots()}

    # Check for added/removed/changed slots
    all_names = set(slots1.keys()) | set(slots2.keys())

    for name in all_names:
        if name not in slots1:
            comparison["slot_changes"].append(f"+ Added: {name}")
        elif name not in slots2:
            comparison["slot_changes"].append(f"- Removed: {name}")
        else:
            size_diff = slots2[name].size - slots1[name].size
            if size_diff != 0:
                comparison["slot_changes"].append(
                    f"~ Modified: {name} ({size_diff:+d} bytes)"
                )

    return comparison

# Compare versions
diff = compare_packages(Path("myapp-1.0.0.psp"), Path("myapp-1.0.1.psp"))
for change in diff["slot_changes"]:
    print(change)
```

### Extract to Memory (No Disk I/O)

```python
import io
import tarfile

def extract_slot_to_memory(reader, slot_id):
    """Extract and decompress slot entirely in memory."""
    # Get slot data
    slot_data = reader.extract_slot(slot_id)

    # Decompress tar.gz in memory
    with io.BytesIO(slot_data) as compressed:
        with tarfile.open(fileobj=compressed, mode='r:gz') as tar:
            # Extract to dict
            files = {}
            for member in tar.getmembers():
                if member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        files[member.name] = f.read()
            return files

# Use in-memory extraction
files = extract_slot_to_memory(reader, slot_id=1)
for filename, content in files.items():
    print(f"{filename}: {len(content)} bytes")
```

## Error Handling

```python
from flavor.psp.format_2025.reader import ReadError, InvalidPackageError

def safe_read_package(package_path):
    """Safely read package with comprehensive error handling."""
    try:
        reader = PSPFReader(package_path)
        return reader.read_metadata()

    except FileNotFoundError:
        print(f"❌ Package not found: {package_path}")
        return None

    except InvalidPackageError as e:
        print(f"❌ Invalid package format: {e}")
        return None

    except ReadError as e:
        print(f"❌ Read error: {e}")
        print(f"   Context: {e.context}")
        return None

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

# Safe reading
metadata = safe_read_package(Path("myapp.psp"))
if metadata:
    print("Package is valid")
```

## API Reference

The complete PSPFReader class reference with all methods, parameters, and return types:
