# TofuSoup Integration Refactor: `pyvider-builder` → `soup package`

## Overview

This document outlines the refactoring plan to integrate `pyvider-builder` into TofuSoup as the `soup package` command group, creating a unified developer experience for Flavor (Pyvider Secure Package Format) operations within the broader OpenTofu ecosystem.

## Design Goals

1. **Unified CLI Experience**: All Flavor operations accessible via `soup package <subcommand>`
2. **Cross-Language Testing**: Built-in compatibility testing for Go/Python/Rust implementations
3. **Modular Architecture**: Clean separation between CLI, business logic, and cross-language harnesses
4. **Developer Experience**: Rich terminal output, comprehensive error handling, unified configuration
5. **Future-Proofing**: Architecture ready for Rust and other language implementations

## Architectural Design

### Current State
```
pyvider-builder/
├── src/pyvider/builder/
│   ├── cli.py (Click-based CLI)
│   ├── models.py (Flavor models)
│   ├── compiler.py (Go binary management)
│   ├── packaging/ (Python packaging logic)
│   └── go/ (Go Flavor implementation)
└── tests/ (50 tests, all passing)
```

### Target State
```
tofusoup/
├── src/tofusoup/
│   └── package/  # New module
│       ├── cli.py (soup package commands)
│       ├── logic.py (business logic)
│       ├── models.py (Flavor models)
│       └── harness/ (cross-language harness management)
├── conformance/
│   └── package/ # New conformance tests
│       ├── test_cross_language_pspf.py
│       └── test_pspf_compatibility.py
└── src/tofusoup/harness/
    ├── go/flavor-packager/ (moved from pyvider-builder)
    └── rust/flavor-packager/ (future)
```

## Detailed Implementation Checklist

### Phase 1: Preparation & Analysis
- [ ] **1.1** Analyze current pyvider-builder test coverage (✅ 50/50 tests passing)
- [ ] **1.2** Document all existing CLI commands and their functionality
- [ ] **1.3** Identify cross-language compatibility test patterns
- [ ] **1.4** Map current Go harness integration points
- [ ] **1.5** Review TofuSoup's lazy loading and CLI architecture

### Phase 2: TofuSoup Module Creation
- [ ] **2.1** Create `src/tofusoup/package/` module structure
  - [ ] **2.1.1** `__init__.py` with module exports
  - [ ] **2.1.2** `cli.py` with Click commands integrated into TofuSoup's LazyGroup
  - [ ] **2.1.3** `logic.py` with core business logic abstracted from CLI
  - [ ] **2.1.4** `models.py` with Flavor data models (migrated from pyvider.builder.models)
- [ ] **2.2** Integrate into TofuSoup's main CLI
  - [ ] **2.2.1** Add `"package": ("tofusoup.package.cli", "package_cli")` to LAZY_COMMANDS
  - [ ] **2.2.2** Update `pyproject.toml` dependencies
  - [ ] **2.2.3** Test lazy loading functionality

### Phase 3: Go Harness Migration
- [ ] **3.1** Move Go Flavor implementation to TofuSoup harness structure
  - [ ] **3.1.1** Copy `src/pyvider/builder/go/` → `src/tofusoup/harness/go/flavor-packager/`
  - [ ] **3.1.2** Update Go module paths and imports
  - [ ] **3.1.3** Integrate with TofuSoup's harness build system
- [ ] **3.2** Update TofuSoup harness management
  - [ ] **3.2.1** Add flavor-packager to `soup harness list`
  - [ ] **3.2.2** Add build support via `soup harness build flavor-packager`
  - [ ] **3.2.3** Add verification via `soup harness verify-cli flavor-packager`
- [ ] **3.3** Configuration integration
  - [ ] **3.3.1** Add Flavor harness config to `soup.toml`
  - [ ] **3.3.2** Support for harness-specific build flags and environment variables

### Phase 4: CLI Command Implementation
- [ ] **4.1** `soup package build` command
  - [ ] **4.1.1** Migrate build orchestration logic
  - [ ] **4.1.2** Integration with TofuSoup's rich output system
  - [ ] **4.1.3** Support for `--manifest` and target platform selection
  - [ ] **4.1.4** Error handling with TofuSoup's exception hierarchy
- [ ] **4.2** `soup package verify` command
  - [ ] **4.2.1** Migrate verification logic
  - [ ] **4.2.2** Rich output for package information display
  - [ ] **4.2.3** Integration with Go harness for cryptographic verification
- [ ] **4.3** `soup package keygen` command
  - [ ] **4.3.1** Migrate key generation logic
  - [ ] **4.3.2** Support for different key formats and algorithms
- [ ] **4.4** `soup package init` command
  - [ ] **4.4.1** Migrate project scaffolding logic
  - [ ] **4.4.2** Template system integration
- [ ] **4.5** `soup package clean` command
  - [ ] **4.5.1** Migrate cache cleanup logic

### Phase 5: Cross-Language Testing Integration
- [ ] **5.1** Create conformance test structure
  - [ ] **5.1.1** `conformance/package/test_pspf_cross_language.py`
  - [ ] **5.1.2** `conformance/package/test_pspf_binary_compatibility.py`
  - [ ] **5.1.3** `conformance/package/conftest.py` with Flavor fixtures
- [ ] **5.2** Migrate existing cross-language tests
  - [ ] **5.2.1** `test_python_and_go_checksum_match` → TofuSoup conformance
  - [ ] **5.2.2** `test_python_signature_verifies_in_go` → TofuSoup conformance
  - [ ] **5.2.3** Flavor model consistency tests
- [ ] **5.3** Test runner integration
  - [ ] **5.3.1** Add `soup test package` command
  - [ ] **5.3.2** Integration with `soup test all`
  - [ ] **5.3.3** Test configuration in `soup.toml`

### Phase 6: Documentation & Developer Experience
- [ ] **6.1** Update TofuSoup documentation
  - [ ] **6.1.1** Add package commands to main README
  - [ ] **6.1.2** Create package-specific documentation
  - [ ] **6.1.3** Update architecture documentation
- [ ] **6.2** Configuration documentation
  - [ ] **6.2.1** Document package-specific `soup.toml` settings
  - [ ] **6.2.2** Provide example configurations for common use cases
- [ ] **6.3** Developer workflow documentation
  - [ ] **6.3.1** Provider development workflow with `soup package`
  - [ ] **6.3.2** Cross-language testing procedures
  - [ ] **6.3.3** Integration with existing TofuSoup workflows

### Phase 7: Backward Compatibility & Migration
- [ ] **7.1** Provide migration path from `pyvbuild` CLI
  - [ ] **7.1.1** Deprecation warnings in pyvider-builder
  - [ ] **7.1.2** Migration guide documentation
  - [ ] **7.1.3** Compatibility shim (optional)
- [ ] **7.2** Handle existing projects and workflows
  - [ ] **7.2.1** Support for existing pyproject.toml configurations
  - [ ] **7.2.2** Migration tooling for existing projects

### Phase 8: Testing & Validation
- [ ] **8.1** Comprehensive test migration
  - [ ] **8.1.1** Migrate all 50 existing tests to new structure
  - [ ] **8.1.2** Ensure 100% test pass rate
  - [ ] **8.1.3** Add additional integration tests for TofuSoup integration
- [ ] **8.2** Cross-language compatibility validation
  - [ ] **8.2.1** Verify Go/Python checksum compatibility maintained
  - [ ] **8.2.2** Test ECDSA signature cross-verification
  - [ ] **8.2.3** Validate Flavor binary format consistency
- [ ] **8.3** Performance validation
  - [ ] **8.3.1** CLI startup time testing (lazy loading)
  - [ ] **8.3.2** Build performance benchmarking
  - [ ] **8.3.3** Memory usage validation

### Phase 9: Future-Proofing for Rust
- [ ] **9.1** Architecture preparation
  - [ ] **9.1.1** Design harness interface for Rust Flavor implementation
  - [ ] **9.1.2** Test matrix framework for three-way compatibility (Go/Python/Rust)
  - [ ] **9.1.3** Build system hooks for Cargo integration
- [ ] **9.2** Test framework extension
  - [ ] **9.2.1** Parameterized tests for multiple language implementations
  - [ ] **9.2.2** Cross-language checksum validation matrix
  - [ ] **9.2.3** Performance comparison framework

### Phase 10: Cleanup & Finalization
- [ ] **10.1** Remove redundant code
  - [ ] **10.1.1** Clean up migrated pyvider-builder code
  - [ ] **10.1.2** Update import statements throughout codebase
  - [ ] **10.1.3** Remove deprecated functionality
- [ ] **10.2** Final validation
  - [ ] **10.2.1** End-to-end workflow testing
  - [ ] **10.2.2** Documentation review and updates
  - [ ] **10.2.3** Performance and compatibility final validation

## Success Criteria

1. **✅ All Commands Migrated**: Every `pyvbuild` command available as `soup package <cmd>`
2. **✅ Test Compatibility**: All 50 existing tests pass in new structure
3. **✅ Cross-Language Compatibility**: Go/Python checksum verification maintains identical results
4. **✅ Rich UX**: All commands use TofuSoup's rich terminal output
5. **✅ Unified Configuration**: Single `soup.toml` configuration for all operations
6. **✅ Future-Ready**: Architecture supports easy addition of Rust implementation
7. **✅ Performance**: CLI startup time < 500ms (lazy loading working)
8. **✅ Documentation**: Complete documentation for all new functionality

## Risk Mitigation

1. **Test Coverage**: Maintain 100% existing test pass rate throughout migration
2. **Cross-Language Compatibility**: Validate checksum compatibility at each step
3. **Performance**: Monitor CLI startup time to ensure lazy loading effectiveness
4. **Developer Experience**: Gather feedback on new CLI interface early in process
5. **Rollback Plan**: Keep pyvider-builder functional until migration is complete and validated

## Timeline Estimate

- **Phases 1-3**: 2-3 days (Analysis and basic structure)
- **Phases 4-5**: 3-4 days (Core CLI and testing)
- **Phases 6-8**: 2-3 days (Documentation and validation)
- **Phases 9-10**: 1-2 days (Future-proofing and cleanup)

**Total Estimated Time**: 8-12 days

## Dependencies

1. **TofuSoup Environment**: Must be properly set up with `env.sh`
2. **Go Toolchain**: For building flavor-packager harness
3. **All Tests Passing**: Current pyvider-builder test suite must be green
4. **Cross-Language Verification**: Existing Go/Python compatibility must be validated

This refactor will create a unified, powerful development environment that positions TofuSoup as the definitive toolchain for OpenTofu provider development with built-in cross-language compatibility validation.