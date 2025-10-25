# API Reference

Python API reference documentation for FlavorPack.

## Coming Soon

Comprehensive API documentation is under development.

## Quick Reference

### Main Classes

```python
from flavor import Packager, Package
from flavor.psp import Builder, Reader
```

### Common Operations

```python
# Package creation
packager = Packager(manifest="pyproject.toml")
package = packager.build(output="myapp.psp")

# Package reading
package = Package.open("myapp.psp")
metadata = package.metadata()
package.verify()

# Package extraction
package.extract(output_dir="extracted/")
```

## Modules

- `flavor.packaging` - High-level packaging API
- `flavor.psp.format_2025` - PSPF/2025 implementation
- `flavor.psp.builder` - Package building
- `flavor.psp.reader` - Package reading
- `flavor.psp.crypto` - Cryptographic operations

## Documentation Format

API documentation will include:

- Class and function signatures
- Parameter descriptions
- Return types
- Usage examples
- Related functions

---

**In the meantime, see:** [User Guide](../guide/) | [Cookbook](../cookbook/)

**For source code:** [GitHub Repository](https://github.com/provide-io/flavorpack)
