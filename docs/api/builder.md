# Builder API

The FlavorPack Builder API provides tools for creating PSPF packages programmatically.

## PSPFBuilder

::: flavor.psp.format_2025.pspf_builder.PSPFBuilder
    options:
      show_root_heading: true
      show_source: false
      members:
        - __init__
        - add_launcher
        - add_metadata
        - add_slot
        - build
        - write

## Usage Example

```python
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from pathlib import Path

# Create a new package builder
builder = PSPFBuilder()

# Add launcher binary
launcher_data = Path("dist/bin/flavor-rs-launcher").read_bytes()
builder.add_launcher(launcher_data)

# Add metadata
metadata = {
    "package": {"name": "myapp", "version": "1.0.0"},
    "execution": {"command": "python {workenv}/bin/myapp"}
}
builder.add_metadata(metadata)

# Add a slot
slot_data = Path("app.tar.gz").read_bytes()
builder.add_slot(
    slot_id=0,
    data=slot_data,
    operations=0x1001,  # tar + gzip
    name="app-code"
)

# Build and write package
package_data = builder.build()
Path("myapp.psp").write_bytes(package_data)
```

## See Also

- [Reader API](reader.md) - Reading and extracting packages
- [Crypto API](crypto.md) - Signature generation and verification
- [Packaging Guide](../guide/packaging/index.md) - High-level packaging workflow
