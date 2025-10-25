# Cryptographic API

Python API for package signing and verification.

## Overview

FlavorPack uses Ed25519 signatures for package integrity. The Crypto API provides functions for key generation, signing, and verification.

---

## Key Generation

### generate_key_pair

Generate Ed25519 key pair and save to PEM files.

```python
from pathlib import Path
from flavor.packaging.keys import generate_key_pair

def generate_key_pair(keys_dir: Path) -> tuple[Path, Path]:
    """Generate Ed25519 key pair."""
    ...
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `keys_dir` | `Path` | Directory to save key files |

#### Returns

`tuple[Path, Path]` - (private_key_path, public_key_path)

#### Example

```python
from pathlib import Path
from flavor.packaging.keys import generate_key_pair

# Generate keys
keys_dir = Path("keys")
private_key, public_key = generate_key_pair(keys_dir)

print(f"Private key: {private_key}")  # keys/flavor-private.key
print(f"Public key: {public_key}")    # keys/flavor-public.key

# Keys are in PEM format
print(private_key.read_text())
# -----BEGIN PRIVATE KEY-----
# MC4CAQAwBQYDK2VwBCIEIE3...
# -----END PRIVATE KEY-----
```

---

## Key Loading

### load_private_key_raw

Load private key from PEM file and return raw bytes.

```python
from pathlib import Path
from flavor.packaging.keys import load_private_key_raw

def load_private_key_raw(key_path: Path) -> bytes:
    """Load private key and return raw 32-byte seed."""
    ...
```

#### Example

```python
from pathlib import Path
from flavor.packaging.keys import load_private_key_raw

# Load private key
private_key_bytes = load_private_key_raw(Path("keys/flavor-private.key"))

print(f"Private key size: {len(private_key_bytes)} bytes")  # 32 bytes
print(f"Private key (hex): {private_key_bytes.hex()[:32]}...")
```

### load_public_key_raw

Load public key from PEM file and return raw bytes.

```python
from pathlib import Path
from flavor.packaging.keys import load_public_key_raw

def load_public_key_raw(key_path: Path) -> bytes:
    """Load public key and return raw 32-byte key."""
    ...
```

#### Example

```python
from pathlib import Path
from flavor.packaging.keys import load_public_key_raw

# Load public key
public_key_bytes = load_public_key_raw(Path("keys/flavor-public.key"))

print(f"Public key size: {len(public_key_bytes)} bytes")  # 32 bytes
print(f"Public key (hex): {public_key_bytes.hex()}")
```

---

## Signing and Verification

### Sign Data

```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from flavor.packaging.keys import load_private_key_raw
from pathlib import Path

def sign_data(data: bytes, private_key_path: Path) -> bytes:
    """Sign data with Ed25519 private key."""

    # Load private key
    private_key_bytes = load_private_key_raw(private_key_path)

    # Create Ed25519 private key object
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)

    # Sign data
    signature = private_key.sign(data)

    return signature

# Example
data = b"Hello, FlavorPack!"
signature = sign_data(data, Path("keys/flavor-private.key"))

print(f"Signature size: {len(signature)} bytes")  # 64 bytes
print(f"Signature (hex): {signature.hex()[:32]}...")
```

### Verify Signature

```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from flavor.packaging.keys import load_public_key_raw
from pathlib import Path

def verify_signature(data: bytes, signature: bytes, public_key_path: Path) -> bool:
    """Verify Ed25519 signature."""

    # Load public key
    public_key_bytes = load_public_key_raw(public_key_path)

    # Create Ed25519 public key object
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)

    # Verify signature
    try:
        public_key.verify(signature, data)
        return True
    except Exception:
        return False

# Example
data = b"Hello, FlavorPack!"
is_valid = verify_signature(data, signature, Path("keys/flavor-public.key"))

if is_valid:
    print("✅ Signature valid")
else:
    print("❌ Signature invalid")
```

---

## Complete Example

### Sign and Verify Package

```python
#!/usr/bin/env python3
"""Sign and verify a PSPF package."""

from pathlib import Path
from flavor.packaging.keys import (
    generate_key_pair,
    load_private_key_raw,
    load_public_key_raw,
)
from flavor.package import build_package_from_manifest, verify_package

def sign_and_verify_package():
    """Build, sign, and verify a package."""

    # 1. Generate keys (first time only)
    keys_dir = Path("keys")
    if not keys_dir.exists():
        print("🔑 Generating Ed25519 key pair...")
        private_key, public_key = generate_key_pair(keys_dir)
        print(f"✅ Keys generated:")
        print(f"   Private: {private_key}")
        print(f"   Public: {public_key}")
    else:
        private_key = keys_dir / "flavor-private.key"
        public_key = keys_dir / "flavor-public.key"

    # 2. Build signed package
    print("\n📦 Building package...")
    packages = build_package_from_manifest(
        manifest_path=Path("pyproject.toml"),
        private_key_path=private_key,
        public_key_path=public_key,
    )

    package = packages[0]
    print(f"✅ Package built: {package}")

    # 3. Verify signature
    print("\n🔍 Verifying package...")
    result = verify_package(package)

    if result["signature_valid"]:
        print("✅ Signature verification successful")

        # Show signature details
        from flavor.psp.format_2025.reader import PSPFReader

        with PSPFReader(package) as reader:
            metadata = reader.read_metadata()
            signature_info = metadata.get("signature", {})

            print("\n📋 Signature Details:")
            print(f"   Algorithm: Ed25519")
            print(f"   Public key (hex): {signature_info.get('public_key', 'N/A')[:32]}...")

        return True
    else:
        print("❌ Signature verification failed")
        return False

if __name__ == "__main__":
    import sys
    success = sign_and_verify_package()
    sys.exit(0 if success else 1)
```

---

## Key Format

### Ed25519 Keys

FlavorPack uses Ed25519 for all package signatures:

**Properties:**
- **Private key**: 32 bytes (256 bits)
- **Public key**: 32 bytes (256 bits)
- **Signature**: 64 bytes (512 bits)
- **Format**: PEM (PKCS#8 for private, SubjectPublicKeyInfo for public)

**Advantages:**
- Small key and signature sizes
- Fast signing and verification
- Deterministic signatures
- No parameters to misconfigure
- Strong security (equivalent to 128-bit symmetric)

### PEM Format

```
-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIE3xRm5vN7pQJ8zKqN4wXdGx0S5tFZ8yHcBqLpA3rMf=
-----END PRIVATE KEY-----

-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAm5+C7N8jQxZ6yL4kF9pT2wXdM8xHqW3vNcBrA5pLx7I=
-----END PUBLIC KEY-----
```

---

## Security Best Practices

!!! warning "Key Protection"
    - **Never commit private keys to version control**
    - Store private keys with 0600 permissions (owner read/write only)
    - Use environment variables or secret management in CI/CD
    - Rotate keys periodically

!!! tip "Key Management"
    - Generate one key pair per project
    - Keep public key with package metadata
    - Backup private keys securely
    - Use different keys for development and production

!!! tip "Signature Verification"
    - Always verify signatures before executing packages
    - Check signature validity in CI/CD pipelines
    - Reject packages with invalid signatures
    - Log verification results

---

## Error Handling

### Invalid Keys

```python
from flavor.packaging.keys import load_private_key_raw
from pathlib import Path

try:
    private_key = load_private_key_raw(Path("keys/invalid.key"))
except ValueError as e:
    print(f"❌ Invalid key: {e}")
    # Error message will indicate:
    # - Key format issues (not PEM)
    # - Key type issues (not Ed25519)
    # - File not found
```

### Signature Verification Failures

```python
from flavor.package import verify_package
from pathlib import Path

result = verify_package(Path("package.psp"))

if not result["signature_valid"]:
    print("❌ Signature verification failed")

    # Common causes:
    # - Package was tampered with
    # - Wrong public key used
    # - Package not signed
    # - Corrupted package file

    # Check if package is signed
    metadata = result.get("metadata", {})
    if "signature" not in metadata:
        print("  Package is not signed")
    else:
        print("  Signature present but invalid")
```

---

## CI/CD Integration

### GitHub Actions Example

{% raw %}
```yaml
name: Build and Sign Package

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install FlavorPack
        run: pip install flavorpack

      - name: Create signing key from secret
        run: |
          mkdir -p keys
          echo "${{ secrets.SIGNING_KEY_PRIVATE }}" > keys/flavor-private.key
          echo "${{ secrets.SIGNING_KEY_PUBLIC }}" > keys/flavor-public.key
          chmod 600 keys/flavor-private.key

      - name: Build and sign package
        run: |
          flavor pack \
            --manifest pyproject.toml \
            --output dist/myapp.psp \
            --private-key keys/flavor-private.key \
            --public-key keys/flavor-public.key

      - name: Verify package
        run: flavor verify dist/myapp.psp

      - name: Upload package
        uses: actions/upload-artifact@v3
        with:
          name: signed-package
          path: dist/myapp.psp
```
{% endraw %}

---

## See Also

- [Packaging API](packaging.md) - Build packages with signing
- [Builder API](builder.md) - Low-level package building
- [Reader API](reader.md) - Package reading and verification
- [Security Model](../guide/concepts/security.md) - Security concepts

---

**For complete API reference, see the source code:**
`src/flavor/packaging/keys.py` and `src/flavor/psp/format_2025/crypto.py`
