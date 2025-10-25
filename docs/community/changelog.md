# Changelog

All notable changes to FlavorPack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Professional MkDocs documentation with Material theme
- Auto-generated API documentation using mkdocstrings
- Cross-language packaging system with Go and Rust launchers
- Progressive Secure Package Format (PSPF) 2025 specification
- Ed25519 signature verification for package integrity
- Smart caching with work environment management
- Platform-specific static binaries for Linux (musl libc)
- Comprehensive test suite with 299+ tests
- CI/CD pipeline with 8 GitHub Actions workflows
- Support for multiple platforms (Linux, macOS, Windows*)

### Changed
- Documentation structure aligned with high-profile Python projects
- Visual theme integrated with provide.io design language
- Improved API organization and navigation
- Refactored packaging orchestrator for better modularity

### Security
- Implemented secure package signing and verification
- Added runtime security model (FEP-0003)
- Deterministic key generation with seed support

### Fixed
- UV binary extraction path issues
- Cross-language compatibility between builders and launchers
- Platform-specific path handling

## [0.3.0] - 2024-08-30

### Added
- Go and Rust helper implementations
- Cross-language testing with pretaster
- Platform matrix builds for multiple architectures
- Artifact management in CI/CD

### Changed
- Migrated from single-language to multi-language architecture
- Improved builder and launcher separation

## [0.2.0] - 2024-07-01

### Added
- Work environment management
- Slot lifecycle support
- Metadata compression with gzip

### Changed
- Package format to PSPF/2025
- Improved caching strategy

## [0.1.0] - 2024-01-01

### Added
- Initial release of FlavorPack
- Basic PSPF format implementation
- Python packaging support
- CLI tool (`flavor` command)
- Go and Rust launcher implementations

---

For detailed release notes, see the [GitHub Releases](https://github.com/provide-io/flavorpack/releases) page.