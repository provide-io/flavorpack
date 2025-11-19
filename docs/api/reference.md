# Auto-Generated API Reference

This page provides auto-generated API documentation directly from the FlavorPack source code.

!!! tip "Complete Documentation"
    For detailed usage examples and explanations, see the manually-written API guides:

    - [Packaging API](packaging.md) - Build and verify packages
    - [Builder API](builder.md) - Low-level package building
    - [Reader API](reader.md) - Package inspection and extraction
    - [Cryptography API](crypto.md) - Signing and verification

---

## Core API

### Package Building and Verification

::: flavor.package.build_package_from_manifest
    options:
      show_source: true
      heading_level: 4

::: flavor.package.verify_package
    options:
      show_source: false
      heading_level: 4

::: flavor.package.clean_cache
    options:
      show_source: false
      heading_level: 4

::: flavor.package.generate_keys
    options:
      show_source: false
      heading_level: 4

---

## Exceptions

::: flavor.exceptions.BuildError
    options:
      show_source: false
      heading_level: 3

::: flavor.exceptions.VerificationError
    options:
      show_source: false
      heading_level: 3

---

## Packaging Modules

### PackagingOrchestrator

High-level orchestrator for the entire package build process.

::: flavor.packaging.orchestrator.PackagingOrchestrator
    options:
      members: true
      show_source: false
      heading_level: 4
      show_root_heading: false

---

## PSPF Format 2025

### PSPFReader

Read and inspect PSPF package files.

::: flavor.psp.format_2025.reader.PSPFReader
    options:
      members: true
      show_source: false
      heading_level: 4
      show_root_heading: false

### WorkEnvManager

Manage package work environment caching.

::: flavor.psp.format_2025.workenv.WorkEnvManager
    options:
      members: true
      show_source: false
      heading_level: 4
      show_root_heading: false

---

## Related Documentation

- [Main API Index](index.md) - Overview and quick reference
- [User Guide](../guide/index.md) - Learn how to use FlavorPack
- [CLI Reference](../guide/usage/cli.md) - Command-line interface
