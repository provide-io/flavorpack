# Reader API

The FlavorPack Reader API provides tools for reading and extracting PSPF packages.

## PSPFReader

::: flavor.psp.format_2025.reader.PSPFReader
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - read_package
        - get_metadata
        - get_slot
        - extract_slot
        - extract_all
        - verify

## Usage Example

```python
from flavor.psp.format_2025.reader import PSPFReader
from pathlib import Path

# Open and read a package
reader = PSPFReader(Path("myapp.psp"))
package_info = reader.read_package()

# Get metadata
metadata = reader.get_metadata()
print(f"Package: {metadata['package']['name']} v{metadata['package']['version']}")

# Extract a specific slot
slot_data = reader.extract_slot(slot_id=0)
Path("extracted_slot_0.tar.gz").write_bytes(slot_data)

# Extract all slots
reader.extract_all(output_dir=Path("extracted/"))

# Verify package integrity
is_valid = reader.verify()
print(f"Package valid: {is_valid}")
```

## Package Information

Access package details:

```python
reader = PSPFReader(Path("myapp.psp"))
info = reader.read_package()

print(f"Format version: {info['format_version']}")
print(f"Launcher size: {info['launcher_size']} bytes")
print(f"Slot count: {info['slot_count']}")

for slot in info['slots']:
    print(f"Slot {slot['id']}: {slot['name']} ({slot['size']} bytes)")
```

## See Also

- [Builder API](builder.md) - Creating packages
- [Inspection Guide](../guide/usage/inspection.md) - CLI inspection tools
- [Package Structure](../guide/concepts/package-structure.md) - PSPF format details
