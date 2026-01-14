# Cross-Language Support

Understanding FlavorPack's Go and Rust helper integration.

## Overview

FlavorPack uses a polyglot architecture where Python orchestrates native Go and Rust helpers to create high-performance, cross-platform packages.

```mermaid
graph TB
    subgraph "Python Layer"
        Orch[Orchestrator<br/>Manifest Processing]
        PyPkg[Python Packager<br/>Dependency Resolution]
    end

    subgraph "Native Helpers - Go"
        GoBuilder[flavor-go-builder<br/>Package Assembly]
        GoLauncher[flavor-go-launcher<br/>Embedded in .psp]
    end

    subgraph "Native Helpers - Rust"
        RsBuilder[flavor-rs-builder<br/>Package Assembly]
        RsLauncher[flavor-rs-launcher<br/>Embedded in .psp]
    end

    subgraph "PSPF Package"
        Package[myapp.psp<br/>Identical format]
    end

    Orch --> PyPkg
    PyPkg --> GoBuilder
    PyPkg --> RsBuilder

    GoBuilder --> Package
    RsBuilder --> Package

    GoLauncher -.embedded in.-> Package
    RsLauncher -.embedded in.-> Package

    style Package fill:#e8f5e9
    style GoBuilder fill:#e3f2fd
    style RsBuilder fill:#fce4ec
```

### Language Roles

| Component | Language | Purpose |
|-----------|----------|---------|
| **Orchestrator** | Python | High-level packaging logic, manifest parsing |
| **Builder** | Go/Rust | PSPF package assembly, compression, signing |
| **Launcher** | Go/Rust | Package extraction, verification, execution |
| **Runtime** | Python | Packaged application execution |

All helpers produce **identical PSPF/2025 format** packages with full cross-compatibility.

## Topics to be Covered

- Go helper architecture
- Rust helper architecture
- Format compatibility
- Cross-language testing
- Performance comparison
- When to use which helper

---

**See also:** [Architecture](../../development/architecture/) | [Testing](../../development/testing/cross-language/)
