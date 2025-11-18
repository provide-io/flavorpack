# Cryptography API

Ed25519 key generation and management for PSPF package signing.

!!! note "High-Level API Recommended"
    Most users should use the CLI tools or [Packaging API](packaging/) which handle cryptography automatically. This page documents the low-level key management API for advanced use cases.

## Overview

FlavorPack uses **Ed25519** digital signatures to ensure package integrity. Every PSPF package can be cryptographically signed, with the signature and public key embedded in the package index block.

**Ed25519 Benefits**:
- **Fast**: Quick signature generation and verification
- **Small**: 32-byte keys, 64-byte signatures
- **Secure**: 128-bit security level
- **Deterministic**: Same input always produces same signature
- **Simple**: No parameters to misconfigure

## Quick Start

### CLI Tool (Recommended)

```bash
# Generate a new key pair
flavor keygen --out-dir keys/

# Keys are saved as PEM files:
# - keys/flavor-private.key (Ed25519 private key)
# - keys/flavor-public.key (Ed25519 public key)

# Sign package during build
flavor pack \
  --manifest pyproject.toml \
  --private-key keys/flavor-private.key \
  --public-key keys/flavor-public.key

# Deterministic keys for CI/CD
flavor pack \
  --manifest pyproject.toml \
  --key-seed "$SECRET_SEED"

# Verify signed package
flavor verify myapp.psp
```

### Python API

```python
from pathlib import Path
from flavor.packaging.keys import generate_key_pair

# Generate and save key pair
keys_dir = Path("keys")
private_key_path, public_key_path = generate_key_pair(keys_dir)

print(f"✅ Private key: {private_key_path}")
print(f"✅ Public key: {public_key_path}")
```

## Key Generation

### Programmatic Key Generation

```python
from pathlib import Path
from flavor.packaging.keys import generate_key_pair

# Generate Ed25519 key pair and save to PEM files
keys_dir = Path("my-keys")
keys_dir.mkdir(exist_ok=True)

private_key_path, public_key_path = generate_key_pair(keys_dir)
# Creates:
# - my-keys/flavor-private.key (PEM format)
# - my-keys/flavor-public.key (PEM format)
```

**Function Signature**:
```python
def generate_key_pair(keys_dir: Path) -> tuple[Path, Path]:
    """Generate Ed25519 key pair and save to PEM files.

    Returns:
        tuple[Path, Path]: (private_key_path, public_key_path)
    """
```

### Deterministic Key Generation

For reproducible builds in CI/CD environments:

```python
from flavor.psp.format_2025.keys import generate_deterministic_keys

# Generate keys from a seed string
seed = "my-secret-seed-for-ci"
private_key_bytes, public_key_bytes = generate_deterministic_keys(seed)

# Keys are raw 32-byte values
assert len(private_key_bytes) == 32
assert len(public_key_bytes) == 32

# Same seed always produces same keys
pk2, pubk2 = generate_deterministic_keys(seed)
assert private_key_bytes == pk2
assert public_key_bytes == pubk2
```

!!! warning "Seed Security"
    The seed value should be treated as a secret. Anyone with the seed can generate the private key and sign packages. Store seeds securely in CI/CD secret management systems.

## Loading Keys

### Load from PEM Files

```python
from pathlib import Path
from flavor.packaging.keys import load_private_key_raw, load_public_key_raw

# Load keys from PEM files (returns raw 32-byte keys)
private_key = load_private_key_raw(Path("keys/flavor-private.key"))
public_key = load_public_key_raw(Path("keys/flavor-public.key"))

# Keys are raw bytes
assert len(private_key) == 32
assert len(public_key) == 32
```

### Load from Directory

```python
from pathlib import Path
from flavor.psp.format_2025.keys import load_keys_from_path

# Load both keys from a directory
keys_dir = Path("keys")
private_key, public_key = load_keys_from_path(keys_dir)
# Expects keys/flavor-private.key and keys/flavor-public.key
```

## Key Resolution

The packaging system resolves keys with the following priority:

```python
from pathlib import Path
from flavor.psp.format_2025.keys import resolve_keys, create_key_config

# Priority 1: Explicit keys (highest priority)
config = create_key_config(
    private_key=my_private_key_bytes,
    public_key=my_public_key_bytes
)
private_key, public_key = resolve_keys(config)

# Priority 2: Deterministic from seed
config = create_key_config(seed="my-seed")
private_key, public_key = resolve_keys(config)

# Priority 3: Load from filesystem
config = create_key_config(key_path=Path("keys"))
private_key, public_key = resolve_keys(config)

# Priority 4: Generate ephemeral (default)
config = create_key_config()  # No parameters
private_key, public_key = resolve_keys(config)
```

## Signing Packages

Package signing is handled automatically by the build system. The sign/verify operations use the `provide.foundation.crypto` module internally.

### Automatic Signing During Build

```python
from pathlib import Path
from flavor import build_package_from_manifest

# Sign with explicit keys
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    private_key_path=Path("keys/flavor-private.key"),
    public_key_path=Path("keys/flavor-public.key"),
)

# Sign with deterministic seed (CI/CD)
packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    key_seed="my-secret-seed",
)
```

### Verification

```bash
# Verify package signature (automatic)
flavor verify myapp.psp
```

Verification happens automatically when a package is executed. The launcher:
1. Reads the index block to get the public key and signature
2. Calculates the package checksum
3. Verifies the signature using the embedded public key
4. Fails if verification fails (unless `FLAVOR_VALIDATION=none`)

## Key Storage Best Practices

### File Permissions

Keys are automatically saved with restrictive permissions:

```python
from pathlib import Path
from flavor.packaging.keys import generate_key_pair

keys_dir = Path("keys")
private_key_path, public_key_path = generate_key_pair(keys_dir)

# Private key is saved with 0o600 permissions (owner read/write only)
# Directory is created with 0o700 permissions (owner only)
```

### Secure Storage Locations

```bash
# Development (local)
keys/
├── flavor-private.key  # Never commit to git!
└── flavor-public.key

# Production (CI/CD)
# Store seed in secrets manager:
# - GitHub Secrets: FLAVOR_KEY_SEED
# - GitLab CI/CD Variables: FLAVOR_KEY_SEED
# - AWS Secrets Manager
# - HashiCorp Vault
```

### .gitignore

Always exclude private keys from version control:

```gitignore
# FlavorPack keys
keys/flavor-private.key
*.key
!*-public.key  # Allow public keys
```

## Common Workflows

### CI/CD Pipeline

{% raw %}
```yaml
# .github/workflows/build.yml
name: Build Package

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and sign package
        env:
          FLAVOR_KEY_SEED: ${{ secrets.FLAVOR_KEY_SEED }}
        run: |
          flavor pack \
            --manifest pyproject.toml \
            --key-seed "$FLAVOR_KEY_SEED" \
            --output myapp.psp

      - name: Verify package
        run: flavor verify myapp.psp
```
{% endraw %}

### Key Rotation

```python
from pathlib import Path
from datetime import datetime
from flavor.packaging.keys import generate_key_pair

def rotate_keys(keys_dir: Path) -> tuple[Path, Path]:
    """Rotate keys with backup."""

    # Backup old keys
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = keys_dir / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    old_private = keys_dir / "flavor-private.key"
    old_public = keys_dir / "flavor-public.key"

    if old_private.exists():
        old_private.rename(backup_dir / "flavor-private.key")
        old_public.rename(backup_dir / "flavor-public.key")

        with open(backup_dir / "rotation.txt", "w") as f:
            f.write(f"Rotated: {timestamp}\nReason: scheduled_rotation\n")

    # Generate new keys
    return generate_key_pair(keys_dir)

# Rotate keys
new_private, new_public = rotate_keys(Path("keys"))
print(f"✅ Keys rotated. Old keys backed up.")
```

### Multi-Environment Keys

```python
from pathlib import Path
from flavor import build_package_from_manifest

# Development environment
dev_packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    key_seed="dev-seed-123",  # Fixed seed for dev
    output_path=Path("dist/myapp-dev.psp"),
)

# Staging environment
staging_packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    private_key_path=Path("keys/staging/flavor-private.key"),
    public_key_path=Path("keys/staging/flavor-public.key"),
    output_path=Path("dist/myapp-staging.psp"),
)

# Production environment
import os
prod_seed = os.environ["PROD_KEY_SEED"]  # From secrets manager
prod_packages = build_package_from_manifest(
    manifest_path=Path("pyproject.toml"),
    key_seed=prod_seed,
    output_path=Path("dist/myapp-prod.psp"),
)
```

## API Reference

### Key Generation Functions

#### `generate_key_pair(keys_dir: Path) -> tuple[Path, Path]`

Generate Ed25519 key pair and save to PEM files.

- **Module**: `flavor.packaging.keys`
- **Args**: `keys_dir` - Directory to save keys
- **Returns**: `(private_key_path, public_key_path)`
- **Creates**:
  - `keys_dir/flavor-private.key` (PEM format, 0o600 permissions)
  - `keys_dir/flavor-public.key` (PEM format)

#### `generate_deterministic_keys(seed: str) -> tuple[bytes, bytes]`

Generate deterministic Ed25519 keys from a seed string.

- **Module**: `flavor.psp.format_2025.keys`
- **Args**: `seed` - Seed string for deterministic generation
- **Returns**: `(private_key_bytes, public_key_bytes)` - Raw 32-byte keys

#### `generate_ephemeral_keys() -> tuple[bytes, bytes]`

Generate new ephemeral Ed25519 keys.

- **Module**: `flavor.psp.format_2025.keys`
- **Returns**: `(private_key_bytes, public_key_bytes)` - Raw 32-byte keys

### Key Loading Functions

#### `load_private_key_raw(key_path: Path) -> bytes`

Load private key from PEM file and return raw 32-byte seed.

- **Module**: `flavor.packaging.keys`
- **Args**: `key_path` - Path to PEM-encoded private key
- **Returns**: Raw 32-byte private key seed
- **Raises**: `ValueError` if key is not Ed25519

#### `load_public_key_raw(key_path: Path) -> bytes`

Load public key from PEM file and return raw 32-byte key.

- **Module**: `flavor.packaging.keys`
- **Args**: `key_path` - Path to PEM-encoded public key
- **Returns**: Raw 32-byte public key
- **Raises**: `ValueError` if key is not Ed25519

#### `load_keys_from_path(key_path: Path) -> tuple[bytes, bytes]`

Load Ed25519 keys from filesystem directory.

- **Module**: `flavor.psp.format_2025.keys`
- **Args**: `key_path` - Directory containing key files
- **Returns**: `(private_key, public_key)` as raw bytes
- **Expects**:
  - `key_path/flavor-private.key` (raw 32-byte format)
  - `key_path/flavor-public.key` (raw 32-byte format)

### Key Persistence Functions

#### `save_keys_to_path(private_key: bytes, public_key: bytes, key_path: Path) -> None`

Save Ed25519 keys to filesystem directory.

- **Module**: `flavor.psp.format_2025.keys`
- **Args**:
  - `private_key` - 32-byte private key
  - `public_key` - 32-byte public key
  - `key_path` - Directory to save keys in
- **Creates**:
  - `key_path/flavor-private.key` (raw 32-byte, 0o600 permissions)
  - `key_path/flavor-public.key` (raw 32-byte)

### Key Resolution Functions

#### `create_key_config(...) -> KeyConfig`

Create a validated key configuration.

- **Module**: `flavor.psp.format_2025.keys`
- **Args** (all optional, mutually exclusive):
  - `seed: str | None` - Seed for deterministic generation
  - `private_key: bytes | None` - Explicit private key bytes
  - `public_key: bytes | None` - Explicit public key bytes
  - `key_path: Path | None` - Path to load keys from
- **Returns**: `KeyConfig` instance
- **Raises**: `ValueError` if configuration is invalid

#### `resolve_keys(config: KeyConfig) -> tuple[bytes, bytes]`

Resolve keys based on configuration priority.

- **Module**: `flavor.psp.format_2025.keys`
- **Args**: `config` - Key configuration
- **Returns**: `(private_key, public_key)` as raw bytes
- **Priority Order**:
  1. Explicit keys (if both provided)
  2. Deterministic from seed
  3. Load from filesystem path
  4. Generate ephemeral (default)

## Security Considerations

### Key Format

- **PEM Files**: Used for persistent storage (CLI-generated keys)
- **Raw Bytes**: Used internally (32 bytes private, 32 bytes public)
- **Ed25519 Only**: Other key types (RSA, ECDSA) are rejected with helpful error messages

### Key Validation

```python
from pathlib import Path
from flavor.packaging.keys import load_private_key_raw

try:
    private_key = load_private_key_raw(Path("keys/flavor-private.key"))
except ValueError as e:
    # Helpful error if wrong key type
    print(e)
    # "Incompatible key type: Found RSA key, but Ed25519 is required."
```

### Seed Security

Deterministic seeds should be treated as secrets:

```python
import os

# ✅ GOOD: Load from environment
seed = os.environ.get("FLAVOR_KEY_SEED")

# ❌ BAD: Hardcode in source
seed = "my-hardcoded-seed"  # Don't do this!

# ✅ GOOD: Use secrets manager
from my_secrets import get_secret
seed = get_secret("flavor-key-seed")
```

## Troubleshooting

### Wrong Key Type

```python
# Error: "Found RSA key, but Ed25519 is required"
# Solution: Generate new Ed25519 keys
from pathlib import Path
from flavor.packaging.keys import generate_key_pair

# Delete old keys
Path("keys/flavor-private.key").unlink(missing_ok=True)
Path("keys/flavor-public.key").unlink(missing_ok=True)

# Generate new Ed25519 keys
generate_key_pair(Path("keys"))
```

### Invalid Key Size

```python
# Error: "Invalid private key size: expected 32 bytes, got 64"
# This happens when using PEM format where raw format expected
# Solution: Use the appropriate loader

from flavor.packaging.keys import load_private_key_raw  # For PEM files
from flavor.psp.format_2025.keys import load_keys_from_path  # For raw files
```

## Related Documentation

- **[Packaging API](packaging/)** - High-level package building with automatic signing
- **[Security Model](../guide/concepts/security/)** - FlavorPack security architecture
- **[Signing Guide](../guide/packaging/signing/)** - Package signing workflow
- **[CLI Reference](../guide/usage/cli/#keygen)** - CLI key generation
- **[PSPF Security Specification](../reference/spec/fep-0001-core-format-and-operation-chains/#7-security-model)** - Format security details
