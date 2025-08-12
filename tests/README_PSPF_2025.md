# PSPF 2025 Test Structure

## Overview

The PSPF 2025 tests are organized in two complementary ways:

1. **Primary Tests (pytest)** - Comprehensive unit and integration tests
2. **BDD Tests (behave)** - High-level feature specifications that call pytest

## Test Organization

```
tests/
├── test_pspf_2025_core.py          # Core format tests
├── test_pspf_2025_slots.py         # Slot management tests  
├── test_pspf_2025_security.py      # Security and integrity tests
├── test_pspf_2025_execution.py     # Bundle execution tests
├── test_pspf_2025_builder.py       # Builder functionality tests
├── test_pspf_2025_compatibility.py # Cross-language compatibility tests
│
└── bdd/                            # Behavior-driven tests
    ├── features/
    │   ├── pspf_core.feature
    │   ├── slot_management.feature
    │   ├── security.feature
    │   ├── execution.feature
    │   ├── builder.feature
    │   └── compatibility.feature
    │
    ├── features/steps/
    │   ├── pspf_steps.py           # Original BDD step definitions
    │   └── pytest_runner.py        # Pytest integration layer
    │
    └── run_tests.py                # Script to run tests

```

## Running Tests

### Run all pytest tests directly:
```bash
pytest tests/test_pspf_2025_*.py -v
```

### Run specific test module:
```bash
pytest tests/test_pspf_2025_core.py -v
```

### Run specific test:
```bash
pytest tests/test_pspf_2025_core.py::TestPSPFCore::test_emoji_magic_format -v
```

### Run BDD tests (calls pytest):
```bash
cd tests/bdd
behave features/pspf_core.feature
```

### Run all tests via BDD runner:
```bash
python tests/bdd/run_tests.py
```

## Test Coverage

The tests cover all aspects of PSPF 2025:

- **Core Format**: Magic validation, index structure, metadata handling
- **Slot Management**: Lifecycles, compression, alignment, caching
- **Security**: Ephemeral keys, integrity sealing, tamper detection
- **Execution**: Command substitution, environment handling, signal propagation
- **Builder**: Manifest parsing, compression selection, reproducible builds
- **Compatibility**: Cross-language parsing, checksum algorithms, endianness

## Implementation Status

✅ Pytest tests are 100% complete and primary
✅ BDD feature files describe high-level behavior
✅ BDD can run pytest tests or check cached results
✅ Mock PSPF 2025 format implementation for testing

## Next Steps

1. Implement actual PSPF 2025 format based on tests
2. Replace mock implementations with real code
3. Add performance benchmarks
4. Create language-specific implementations (Go, Rust)