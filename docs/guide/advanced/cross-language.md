# Cross-Language Support

Understanding FlavorPack's Go and Rust helper integration.

## Coming Soon

This page is under development. In the meantime, see:

- **[Architecture](../../development/architecture.md)** - System design
- **[Building Helpers](../../development/helpers.md)** - Build Go/Rust helpers

## Overview

FlavorPack uses a polyglot architecture:

- **Python** - Orchestration and high-level logic
- **Go** - Cross-platform builder and launcher
- **Rust** - High-performance builder and launcher

All implementations produce identical PSPF/2025 format packages.

## Topics to be Covered

- Go helper architecture
- Rust helper architecture
- Format compatibility
- Cross-language testing
- Performance comparison
- When to use which helper

---

**See also:** [Architecture](../../development/architecture.md) | [Testing](../../development/testing/cross-language.md)
