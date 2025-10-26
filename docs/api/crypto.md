# Cryptography API

The FlavorPack Cryptography API provides Ed25519 signature generation and verification for package integrity.

!!! note "Low-Level API"
    This is a low-level API for advanced use cases. Most users should use the [Packaging API](packaging.md) which handles signing automatically.

## Security Module

::: flavor.psp.security
    options:
      show_root_heading: false
      show_source: true
      members: true
      show_if_no_docstring: false
      heading_level: 3
      filters:
        - "!^_"

## See Also

- [Packaging API](packaging.md) - High-level packaging with automatic signing
- [Signing Guide](../guide/packaging/signing.md) - Package signing workflow
- [Security Model](../guide/concepts/security.md) - FlavorPack security architecture
- [Keygen Command](../guide/usage/cli.md#keygen) - CLI key generation
