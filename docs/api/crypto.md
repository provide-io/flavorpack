# Crypto API

The FlavorPack Crypto API provides Ed25519 signature generation and verification for package integrity.

## Overview

FlavorPack uses Ed25519 cryptographic signatures to ensure package integrity and authenticity. The crypto module provides functions for key management and signature operations.

!!! info "Module Reference"
    This page provides usage examples for cryptographic operations. For auto-generated API details, see the source code at `src/flavor/psp/format_2025/crypto.py`

## Usage Example

### Generate Keys

```python
from flavor.psp.format_2025.crypto import generate_keypair
from pathlib import Path

# Generate Ed25519 key pair
private_key, public_key = generate_keypair()

# Save keys
Path("keys/private.pem").write_bytes(private_key)
Path("keys/public.pem").write_bytes(public_key)
```

### Sign Package

```python
from flavor.psp.format_2025.crypto import sign_package
from pathlib import Path

# Load private key
private_key = Path("keys/private.pem").read_bytes()

# Load package data
package_data = Path("myapp.psp").read_bytes()

# Generate signature
signature = sign_package(package_data, private_key)

# Signature is embedded in package metadata
```

### Verify Signature

```python
from flavor.psp.format_2025.crypto import verify_signature
from pathlib import Path

# Load package
package_data = Path("myapp.psp").read_bytes()

# Load public key
public_key = Path("keys/public.pem").read_bytes()

# Verify signature
is_valid = verify_signature(package_data, public_key)

if is_valid:
    print("✅ Signature valid - package is authentic")
else:
    print("❌ Signature invalid - package may be tampered")
```

## Deterministic Signatures

For testing purposes, generate deterministic signatures:

```python
from flavor.psp.format_2025.crypto import generate_deterministic_keypair

# Generate keys from seed (testing only!)
private_key, public_key = generate_deterministic_keypair(seed="test123")

# Always produces the same keys for the same seed
# WARNING: Not cryptographically secure - use only for testing
```

## Security Best Practices

!!! warning "Key Security"
    - Never commit private keys to version control
    - Store private keys securely (encrypted storage, HSM, key vault)
    - Use different keys for different environments
    - Rotate keys regularly

!!! tip "Production Use"
    - Always sign production packages
    - Verify signatures before deployment
    - Use hardware security modules (HSM) for private key storage
    - Implement key rotation policies

## See Also

- [Signing Guide](../guide/packaging/signing.md) - Package signing workflow
- [Security Model](../guide/concepts/security.md) - FlavorPack security architecture
- [Keygen Command](../guide/usage/cli.md#keygen) - CLI key generation
