# FlavorPack API Reference

FlavorPack is a cross-language packaging system implementing the Progressive Secure Package Format (PSPF/2025).

## Core Modules

### Packaging System
- [`flavor.packaging`](reference/flavor/packaging/index.md) - Build orchestration and management
- [`flavor.packaging.orchestrator`](reference/flavor/packaging/orchestrator.md) - Main build coordinator
- [`flavor.packaging.python_packager`](reference/flavor/packaging/python_packager.md) - Python-specific packaging

### PSPF Format Implementation
- [`flavor.psp.format_2025`](reference/flavor/psp/format_2025/index.md) - PSPF 2025 implementation
- [`flavor.psp.format_2025.builder`](reference/flavor/psp/format_2025/builder.md) - Package building
- [`flavor.psp.format_2025.reader`](reference/flavor/psp/format_2025/reader.md) - Package reading
- [`flavor.psp.format_2025.crypto`](reference/flavor/psp/format_2025/crypto.md) - Cryptographic operations

### Command Line Interface
- [`flavor.cli`](reference/flavor/cli/index.md) - CLI framework and commands

### Operations and Handlers
- [`flavor.psp.format_2025.operations`](reference/flavor/psp/format_2025/operations.md) - Operation chain management
- [`flavor.archive`](reference/flavor/archive/index.md) - Archive operation handlers

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
