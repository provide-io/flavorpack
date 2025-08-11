# Flavor - PSPF 2025 Development Guide

## Project Overview

Flavor is a polyglot package format and execution framework implementing the Progressive Secure Package Format (PSPF) 2025 Edition. It enables building self-contained, executable bundles that work across multiple languages (Python, Go, Rust, Node.js) and platforms.

## Current Development State

### ✅ Completed
1. **PSPF 2025 Specification** - Complete specification in `docs/SPECIFICATION_PSPF_2025.md`
2. **Mock Implementation** - Full mock implementation in `src/flavor/psp/format_2025.py`
3. **Comprehensive Test Suite** - 75 tests covering all aspects:
   - Core format tests (15 tests)
   - Slot management tests (12 tests)
   - Security tests (11 tests)
   - Execution tests (12 tests)
   - Builder tests (13 tests)
   - Compatibility tests (12 tests)
4. **BDD Test Framework** - Gherkin features with behave/pytest integration
5. **96% Code Coverage** - Mock implementation thoroughly tested

### 🚧 In Progress
1. Replacing mock implementation with production code
2. Implementing actual cryptographic signatures
3. Building real launchers for each language
4. CLI tool development
5. **Go support for PSPF 2025** - Basic structures added in `src/flavor/go/pkg/flavor/spec_2025.go`
6. **Rust support for PSPF 2025** - Basic structures added in `src/flavor/rust/flavor-launcher-rs/src/flavor_2025.rs`

## Key Design Decisions

### Format Structure
- **256-byte index block** at launcher_size offset (not at EOF)
- **Metadata-first architecture** with required `psp.json`
- **4-emoji magic sequence**: 📦[Launcher][Random]🪄
- **Slot-based design** with lifecycle policies
- **Ephemeral keys** for integrity (not persistent key management)

### Language Support
- **Launcher Emojis**:
  - 🐹 Go
  - 🦀 Rust
  - 🐍 Python
  - 🟢 Node.js
  - 📄 Generic/Unknown

### Technical Requirements
- **Python 3.11+** syntax (lowercase types, pipe unions)
- **Little-endian** binary format
- **8-byte alignment** for slots
- **CRC32** for checksums
- **SHA256** for file hashes

## Quick Start

### Running Tests
```bash
# Run all PSPF 2025 tests
pytest tests/test_pspf_2025_*.py -v

# Run with coverage
pytest tests/test_pspf_2025_*.py --cov=flavor.psp.format_2025 --cov-report=term-missing

# Run BDD tests
cd tests/bdd
behave features/

# Run specific test category
pytest tests/test_pspf_2025_core.py -v
```

### Building a Bundle (Mock Implementation)
```python
from flavor.psp.format_2025 import PSPFBuilder, SlotMetadata

builder = PSPFBuilder()
slot = SlotMetadata(
    index=0,
    name="app",
    size=1024,
    compressed_size=512,
    checksum="abc123",
    compression="gzip",
    purpose="payload",
    lifecycle="persistent",
    path=Path("app.py")
)

builder.build(
    output_path=Path("app.pspf"),
    metadata={
        "format": "PSPF/2025",
        "package": {"name": "myapp", "version": "1.0.0"}
    },
    slots=[slot],
    launcher_type="python"
)
```

### Reading a Bundle
```python
from flavor.psp.format_2025 import PSPFReader

reader = PSPFReader(Path("app.pspf"))
if reader.verify_magic():
    index = reader.read_index()
    metadata = reader.read_metadata()
    print(f"Package: {metadata['package']['name']} v{metadata['package']['version']}")
    print(f"Slots: {index.slot_count}")
```

## File Structure

```
flavor/
├── docs/
│   ├── SPECIFICATION_PSPF_2025.md    # Full format specification
│   ├── PSPF_2025_WHY.md             # Marketing/rationale document
│   ├── SPECIFICATION.md              # Old v0.1 specification
│   └── MIGRATION_TO_PSPF_2025.md    # Migration guide from v0.1
├── src/flavor/
│   ├── psp/
│   │   └── format_2025.py           # Python mock implementation
│   ├── go/pkg/flavor/
│   │   ├── spec.go                  # Old v0.1 Go implementation
│   │   ├── spec_2025.go             # PSPF 2025 Go implementation
│   │   └── errors_2025.go           # PSPF 2025 error definitions
│   └── rust/flavor-launcher-rs/src/
│       ├── flavor.rs                # Old v0.1 Rust implementation
│       └── flavor_2025.rs           # PSPF 2025 Rust implementation
├── tests/
│   ├── test_pspf_2025_core.py      # Core format tests
│   ├── test_pspf_2025_slots.py     # Slot management tests
│   ├── test_pspf_2025_security.py  # Security/crypto tests
│   ├── test_pspf_2025_execution.py # Execution tests
│   ├── test_pspf_2025_builder.py   # Builder tests
│   ├── test_pspf_2025_compatibility.py # Cross-language tests
│   ├── PSPF_2025_TEST_REPORT.md    # Test summary
│   └── bdd/
│       └── features/                # Gherkin feature files
│           ├── steps/               # Behave step definitions
│           │   ├── pytest_runner.py # Pytest integration
│           │   └── cli_steps.py     # CLI testing steps
│           ├── pspf_core.feature
│           ├── slot_management.feature
│           ├── security.feature
│           ├── execution.feature
│           ├── builder.feature
│           ├── compatibility.feature
│           └── cli_features.feature
```

## Implementation Roadmap

### Phase 1: Production Implementation (Current)
- [ ] Replace mock PSPFBuilder with real implementation
- [ ] Replace mock PSPFReader with real implementation
- [ ] Replace mock PSPFLauncher with real implementation
- [ ] Implement actual compression (gzip, zstd)
- [ ] Add real cryptographic signatures (ECDSA, Ed25519)

### Phase 2: Language Launchers
- [ ] Go launcher implementation
- [ ] Rust launcher implementation
- [ ] Python launcher implementation
- [ ] Node.js launcher implementation

### Phase 3: CLI Tools
- [ ] `flavor build` - Build PSPF bundles
- [ ] `flavor inspect` - Inspect bundle contents
- [ ] `flavor verify` - Verify signatures
- [ ] `flavor extract` - Extract slots
- [ ] `flavor execute` - Run bundles

### Phase 4: Advanced Features
- [ ] Incremental builds
- [ ] Cross-platform building
- [ ] Reproducible builds
- [ ] Size optimization
- [ ] Performance benchmarks

## Testing Strategy

### Unit Tests (pytest)
- Primary test framework (100%)
- Comprehensive coverage of all components
- Fast execution for development

### BDD Tests (behave)
- Wrapper around pytest for specification validation
- CLI integration testing across languages
- Cached test results for efficiency

### Cross-Language Testing
- All 16 builder/launcher combinations tested
- Compatibility verification across formats
- Binary parsing consistency

## Common Development Tasks

### Adding a New Launcher
1. Add emoji mapping in `LAUNCHER_EMOJIS`
2. Implement launcher binary generation
3. Add launcher detection logic
4. Update compatibility tests

### Adding a New Compression Algorithm
1. Add to compression options in SlotMetadata
2. Implement compression in `_compress_slot`
3. Implement decompression in reader
4. Add compression tests

### Adding a New Slot Lifecycle
1. Add to valid lifecycles list
2. Implement lifecycle behavior in launcher
3. Update slot management tests
4. Document lifecycle semantics

## Debugging Tips

### Verifying Bundle Structure
```bash
# Check emoji magic
xxd -s -16 bundle.pspf | tail -1

# Find index block
xxd bundle.pspf | grep "PSPF2025"

# Extract metadata archive
python -c "
from flavor.psp.format_2025 import PSPFReader
r = PSPFReader('bundle.pspf')
idx = r.read_index()
print(f'Metadata at offset {idx.metadata_offset}, size {idx.metadata_size}')
"
```

### Common Issues
1. **Index checksum mismatch** - Ensure checksum calculated with field set to 0
2. **Emoji encoding issues** - Use UTF-8 and strip null padding
3. **Slot alignment** - All slots must be 8-byte aligned
4. **Tarfile creation** - Use BytesIO instead of SpooledTemporaryFile

## Contributing

### Code Style
- Python 3.11+ syntax required
- Use lowercase types: `str`, `int`, `list`
- Use pipe unions: `str | None`
- No future imports
- Follow existing patterns

### Test Requirements
- All new features need tests
- Maintain >95% code coverage
- Add both pytest and behave tests
- Test cross-language compatibility

### Documentation
- Update SPECIFICATION_PSPF_2025.md for format changes
- Add examples to this file
- Update test report with new tests
- Document CLI commands

## Key Concepts

### Ephemeral Keys
- Generated per-bundle for integrity
- No key management required
- Public key stored in index block
- Private key discarded after signing

### Slot Lifecycles
- **persistent** - Permanent installation
- **volatile** - Deleted after execution
- **temporary** - Deleted on system cleanup
- **install** - One-time installation

### Metadata Archive Structure
```
metadata.tgz/
├── psp.json              # Required package metadata
├── integrity/
│   ├── seal.sig         # Ephemeral signature
│   └── seal.pem         # Ephemeral public key
└── trust/               # Optional persistent signatures
    ├── developer.sig
    └── developer.pem
```

## Security Considerations

1. **Integrity Sealing** - Every bundle has ephemeral signature
2. **Trust Signatures** - Optional persistent signatures
3. **Checksum Verification** - CRC32 for index, SHA256 for files
4. **Tamper Detection** - Any modification invalidates bundle
5. **Platform Isolation** - Slots extracted to isolated cache

## Performance Guidelines

1. **Lazy Loading** - Only extract slots when needed
2. **Compression** - Choose algorithm based on content
3. **Alignment** - 8-byte alignment for efficient access
4. **Caching** - Reuse extracted slots across runs
5. **Parallel Extraction** - Extract multiple slots concurrently

## Frequently Asked Questions

**Q: Why dated specification (2025) instead of version numbers?**
A: Following Rust's edition model for clarity and avoiding confusion with package versions.

**Q: Why emoji magic instead of traditional signatures?**
A: Visual identification, fun factor, and still provides format validation.

**Q: Why ephemeral keys for every bundle?**
A: Eliminates key management complexity while providing integrity verification.

**Q: Why metadata-first architecture?**
A: Enables quick inspection without parsing entire bundle, better for tools.

**Q: Why 256-byte index block?**
A: Sufficient for current needs with room for future expansion, easy to parse.

## Contact

For questions or issues:
- GitHub Issues: https://github.com/anthropics/claude-code/issues
- Documentation: https://docs.anthropic.com/en/docs/claude-code

## Commands to Run

```bash
# Verify all tests pass
pytest tests/test_pspf_2025_*.py -v

# Run linting
ruff check src/flavor/psp/format_2025.py

# Run type checking
mypy src/flavor/psp/format_2025.py

# Build a test bundle
python -c "
from pathlib import Path
from flavor.psp.format_2025 import PSPFBuilder
builder = PSPFBuilder()
builder.build(
    output_path=Path('test.pspf'),
    metadata={'format': 'PSPF/2025', 'package': {'name': 'test', 'version': '1.0'}},
    slots=[]
)
print('Bundle created: test.pspf')
"
```