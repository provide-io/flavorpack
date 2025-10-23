# FlavorPack API Reference

FlavorPack is a cross-language packaging system implementing the Progressive Secure Package Format (PSPF/2025).

## Core Modules

### Packaging System
- [`flavor.packaging`](flavor/packaging/index.md) - Build orchestration and management
- [`flavor.packaging.orchestrator`](flavor/packaging/orchestrator.md) - Main build coordinator
- [`flavor.packaging.python.packager`](flavor/packaging/python/packager.md) - Python-specific packaging

### PSPF Format Implementation
- [`flavor.psp.format_2025`](flavor/psp/format_2025/index.md) - PSPF 2025 implementation
- [`flavor.psp.format_2025.builder`](flavor/psp/format_2025/builder.md) - Package building
- [`flavor.psp.format_2025.reader`](flavor/psp/format_2025/reader.md) - Package reading
- [`flavor.psp.format_2025.constants`](flavor/psp/format_2025/constants.md) - Format constants

### Command Line Interface
- [`flavor.cli`](flavor/cli.md) - CLI framework and commands

### Operations and Handlers
- [`flavor.psp.format_2025.operations`](flavor/psp/format_2025/operations.md) - Operation chain management
- [`flavor.archive`](flavor/archive/index.md) - Archive operation handlers

## Usage Examples

### Basic Package Creation

```python
from flavor.packaging.orchestrator import Orchestrator

orchestrator = Orchestrator()
result = orchestrator.build_package(
    manifest_path="pyproject.toml",
    output_path="myapp.psp"
)
```

### PSPF Package Reading

```python
from flavor.psp.format_2025.reader import PSPFReader

with PSPFReader("myapp.psp") as reader:
    metadata = reader.read_metadata()
    slots = reader.get_slots()
```

### Operation Chains

```python
from flavor.psp.format_2025.operations import pack_operations, OperationType

# Create operation chain: TAR → GZIP
operations = pack_operations([OperationType.TAR, OperationType.GZIP])
```
