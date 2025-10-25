# FlavorPack Roadmap

This document outlines the planned evolution of FlavorPack within the Provide Foundry ecosystem.

## Current Status (v0.3.x)

### ✅ Completed Features

- **PSPF/2025 Format**: Complete implementation of Progressive Secure Package Format
- **Cross-Language Support**: Python orchestrator with Go and Rust helpers
- **Ed25519 Signatures**: Cryptographic signing and verification
- **Smart Caching**: Persistent work environments with validation
- **Multi-Platform**: Linux, macOS, and Windows (beta) support
- **Static Binaries**: Portable executables with no system dependencies

### 🚧 In Progress

- **Windows Support**: Moving from beta to full support
- **Documentation**: Comprehensive docs aligned with Foundry
- **API Stability**: Finalizing public API for v1.0

## Near-Term (Next 3-6 Months)

### Enhanced Foundry Integration

**Goal**: Seamless workflow with other foundry tools

- **wrknv Deep Integration**
  - Auto-detect wrknv environments
  - One-command packaging from wrknv projects
  - Shared dependency resolution

- **Pyvider Provider Packaging**
  - Terraform provider templates
  - Multi-platform provider builds
  - Provider registry integration

- **Testing Integration**
  - Integration with provide-testkit
  - Automated cross-language testing
  - CI/CD templates

### Performance Improvements

**Goal**: Faster builds, smaller packages

- **Incremental Builds**: Only rebuild changed components
- **Compression Options**: Zstandard, Brotli support
- **Parallel Extraction**: Multi-threaded slot extraction
- **Optimized Binaries**: Reduce launcher size by 50%

### Developer Experience

**Goal**: Make packaging delightful

- **Interactive CLI**: `flavor init` with prompts
- **Better Error Messages**: Actionable suggestions
- **Progress Indicators**: Real-time build progress
- **Auto-Configuration**: Detect project type and configure automatically

## Mid-Term (6-12 Months)

### Advanced Features

**Goal**: Support complex use cases

- **Multi-Slot Orchestration**: Coordinate multiple slots
- **Dynamic Slot Loading**: Load slots on demand
- **Encrypted Slots**: Encrypt sensitive data in packages
- **Custom Launchers**: Plugin system for launchers

### Distribution & Registry

**Goal**: Easy package distribution

- **Package Registry**: Hosted registry for .psp files
- **Version Management**: Semantic versioning support
- **Dependency Resolution**: Package can depend on other packages
- **Update Mechanism**: In-place package updates

### Enterprise Features

**Goal**: Meet enterprise requirements

- **Air-Gapped Deployment**: Work without internet
- **Compliance Reporting**: Generate SBOMs and compliance docs
- **Audit Logging**: Track package usage and access
- **RBAC**: Role-based access control for packages

## Long-Term (12+ Months)

### Ecosystem Expansion

**Goal**: Become the standard Python packaging format

- **Language Support**: Package non-Python applications
- **Container Integration**: First-class Docker/Kubernetes support
- **Cloud Native**: Native AWS Lambda, Google Cloud Run support
- **Edge Deployment**: Optimize for edge computing

### Advanced Security

**Goal**: Best-in-class security

- **Hardware Security Modules**: HSM support for signing
- **Certificate Management**: X.509 certificates
- **Provenance Tracking**: Complete build provenance
- **Runtime Attestation**: Verify package at runtime

### Performance & Scale

**Goal**: Handle any workload

- **Streaming Extraction**: Extract while downloading
- **Differential Updates**: Delta updates for packages
- **CDN Integration**: Global distribution network
- **Zero-Copy Execution**: Execute without extraction

## Research & Exploration

### Under Investigation

- **WebAssembly Target**: Compile to WASM
- **GPU Acceleration**: Utilize GPU for compression/crypto
- **Distributed Builds**: Build packages across multiple machines
- **AI-Assisted Packaging**: Optimize packages with ML

## Community Priorities

We prioritize features based on:

1. **Ecosystem Value**: Benefits all foundry users
2. **User Demand**: Most requested features
3. **Technical Debt**: Improve existing features
4. **Innovation**: Explore new possibilities

## How to Influence the Roadmap

### 📢 Feature Requests

Open an issue with `[Feature Request]` in the title:
```
Title: [Feature Request] Support for XYZ
Body: Description of feature and use case
```

### 💬 Discussions

Join discussions about future features:
- [GitHub Discussions](https://github.com/provide-io/flavorpack/discussions)
- [Foundry Discord](https://discord.gg/provide-io)

### 🤝 Contributions

Implement features yourself:
1. Check roadmap for planned features
2. Open issue to discuss approach
3. Submit pull request

### ⭐ Vote on Features

Use GitHub reactions on issues:
- 👍 for "I want this"
- ❤️ for "I really want this"
- 🎉 for "I'll help implement this"

## Version Compatibility

### Semantic Versioning

FlavorPack follows [SemVer](https://semver.org/):

- **MAJOR** (v1.0.0): Breaking API changes
- **MINOR** (v0.3.0): New features, backward compatible
- **PATCH** (v0.3.1): Bug fixes, backward compatible

### Deprecation Policy

- **Minimum Notice**: 2 minor versions before removal
- **Deprecation Warnings**: Added in code and docs
- **Migration Guides**: Provided for breaking changes

### Support Policy

- **Current Major**: Full support
- **Previous Major**: Security fixes only (1 year)
- **Older Versions**: Community support only

## Feedback

This roadmap evolves based on your feedback!

- **What features are most important to you?**
- **What's missing from this roadmap?**
- **What would make FlavorPack indispensable?**

Share your thoughts:
- [Open an issue](https://github.com/provide-io/flavorpack/issues/new)
- [Start a discussion](https://github.com/provide-io/flavorpack/discussions)
- [Join our Discord](https://discord.gg/provide-io)

---

*Last updated: 2025-01-24*
*Next update: Quarterly*
