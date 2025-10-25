# Cryptography API

The FlavorPack Cryptography API provides Ed25519 signature generation and verification for package integrity.

!!! warning "Documentation Under Revision"
    **This API documentation page is currently being updated to match the actual implementation.**

    The code examples on this page reference a simplified API (`flavor.psp.format_2025.crypto`) that doesn't exist. The actual implementation uses:

    - **Key Management**: `flavor.psp.format_2025.keys` module
    - **Signing**: `provide.foundation.crypto.Ed25519Signer`
    - **Verification**: `provide.foundation.crypto.Ed25519Verifier`

    For current usage examples, see:
    - Source: `src/flavor/psp/format_2025/keys.py`
    - Source: `src/flavor/psp/format_2025/writer.py` (signing)
    - Source: `src/flavor/psp/security.py` (verification)

    **Recommended**: Use the high-level [Packaging API](packaging.md) which handles all cryptographic operations automatically via CLI options.

!!! note "Low-Level API"
    This is a low-level API for advanced use cases. Most users should use the [Packaging API](packaging.md) which handles signing automatically.

    The Crypto API gives you direct access to Ed25519 key generation, package signing, and signature verification for custom security workflows.

## Overview

The Crypto API implements cryptographic operations for PSPF packages using **Ed25519** signatures. Ed25519 provides:

- **Fast signature generation and verification**
- **Small signatures** (64 bytes)
- **Strong security** (128-bit security level)
- **Deterministic signatures** (same input always produces same signature)
- **No side-channel vulnerabilities**

## When to Use the Crypto API

**Use the Crypto API when you need**:

- Custom key management workflows
- Integration with Hardware Security Modules (HSMs)
- Batch signing operations
- Signature verification in custom tools
- Deterministic key generation for reproducible builds
- Key rotation workflows

**Use the CLI tools instead when**:

- Generating standard key pairs (`flavor keygen`)
- Signing during package build (`flavor pack --private-key`)
- Verifying packages (`flavor verify`)

## Basic Usage

### Generating Key Pairs

```python
from pathlib import Path
from flavor.psp.format_2025.crypto import generate_keypair, save_keypair

# Generate a new Ed25519 key pair
private_key, public_key = generate_keypair()

# Save keys to PEM format files
keys_dir = Path("keys")
keys_dir.mkdir(exist_ok=True)

save_keypair(
    private_key=private_key,
    public_key=public_key,
    private_key_path=keys_dir / "flavor-private.key",
    public_key_path=keys_dir / "flavor-public.key"
)

print("✅ Key pair generated and saved")
```

### Deterministic Key Generation

```python
from flavor.psp.format_2025.crypto import generate_keypair_from_seed

# Generate keys from a seed for reproducible builds
seed = "my-secret-seed-for-ci-cd"
private_key, public_key = generate_keypair_from_seed(seed)

# Same seed always produces same keys
private_key2, public_key2 = generate_keypair_from_seed(seed)
assert private_key == private_key2
assert public_key == public_key2

print("✅ Deterministic keys generated")
```

### Signing Packages

```python
from flavor.psp.format_2025.crypto import sign_package, load_private_key

# Load private key
private_key = load_private_key(Path("keys/flavor-private.key"))

# Read package data (excluding signature)
package_path = Path("myapp.psp")
with open(package_path, "rb") as f:
    package_data = f.read()

# Sign the package
signature = sign_package(package_data, private_key)

print(f"✅ Signature: {signature.hex()[:32]}...")
print(f"   Length: {len(signature)} bytes")
```

### Verifying Signatures

```python
from flavor.psp.format_2025.crypto import verify_signature, load_public_key

# Load public key
public_key = load_public_key(Path("keys/flavor-public.key"))

# Read package and signature
with open(package_path, "rb") as f:
    package_data = f.read()

# Assume signature is embedded in package
# (In practice, extract from index block)
signature = extract_signature_from_package(package_data)

# Verify signature
is_valid = verify_signature(package_data, signature, public_key)

if is_valid:
    print("✅ Signature valid - package is authentic")
else:
    print("❌ Signature invalid - package may be tampered!")
```

## Advanced Usage

### Custom Key Storage

```python
from cryptography.hazmat.primitives import serialization
from flavor.psp.format_2025.crypto import generate_keypair

# Generate keys
private_key, public_key = generate_keypair()

# Custom serialization (e.g., for HSM integration)
private_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption()
)

public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)

# Store in custom backend (database, HSM, etc.)
store_in_hsm(private_bytes, key_id="flavorpack-signing-key")
print("✅ Keys stored in HSM")
```

### Batch Signing

```python
from concurrent.futures import ThreadPoolExecutor
from flavor.psp.format_2025.crypto import sign_package, load_private_key

def sign_package_file(package_path, private_key):
    """Sign a single package file."""
    with open(package_path, "rb") as f:
        data = f.read()

    signature = sign_package(data, private_key)

    # Write signature to separate file or embed in package
    sig_path = package_path.with_suffix(".psp.sig")
    sig_path.write_bytes(signature)

    return package_path, signature

# Load signing key once
private_key = load_private_key(Path("keys/flavor-private.key"))

# Sign multiple packages in parallel
packages = list(Path("dist").glob("*.psp"))

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(
        lambda p: sign_package_file(p, private_key),
        packages
    ))

print(f"✅ Signed {len(results)} packages")
```

### Signature Verification with Timing

```python
import time
from flavor.psp.format_2025.crypto import verify_signature, load_public_key

def verify_with_timing(package_path, public_key):
    """Verify signature and measure time."""
    with open(package_path, "rb") as f:
        package_data = f.read()

    signature = extract_signature_from_package(package_data)

    start = time.perf_counter()
    is_valid = verify_signature(package_data, signature, public_key)
    elapsed = time.perf_counter() - start

    return {
        "path": package_path,
        "valid": is_valid,
        "verification_time_ms": elapsed * 1000,
        "size_mb": len(package_data) / 1024 / 1024
    }

# Verify and benchmark
public_key = load_public_key(Path("keys/flavor-public.key"))
result = verify_with_timing(Path("myapp.psp"), public_key)

print(f"Package: {result['path']}")
print(f"Valid: {result['valid']}")
print(f"Size: {result['size_mb']:.2f} MB")
print(f"Verification: {result['verification_time_ms']:.2f} ms")
```

### Key Rotation

```python
from datetime import datetime
from flavor.psp.format_2025.crypto import generate_keypair, save_keypair

def rotate_keys(keys_dir, reason="scheduled_rotation"):
    """Rotate signing keys with backup."""
    keys_dir = Path(keys_dir)

    # Backup old keys
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = keys_dir / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup existing keys
    old_private = keys_dir / "flavor-private.key"
    old_public = keys_dir / "flavor-public.key"

    if old_private.exists():
        old_private.rename(backup_dir / "flavor-private.key")
        old_public.rename(backup_dir / "flavor-public.key")

        # Save rotation metadata
        (backup_dir / "rotation.txt").write_text(
            f"Rotated: {timestamp}\nReason: {reason}\n"
        )

    # Generate new keys
    private_key, public_key = generate_keypair()
    save_keypair(
        private_key=private_key,
        public_key=public_key,
        private_key_path=old_private,
        public_key_path=old_public
    )

    print(f"✅ Keys rotated - backup in {backup_dir}")
    return private_key, public_key

# Rotate keys
new_private, new_public = rotate_keys(Path("keys"), reason="annual_rotation")
```

## Common Patterns

### CI/CD Signing Workflow

```python
import os
import sys
from pathlib import Path
from flavor.psp.format_2025.crypto import (
    generate_keypair_from_seed,
    sign_package,
    save_public_key
)

def ci_sign_package(package_path):
    """Sign package in CI environment using secret seed."""
    # Get seed from environment (stored in CI secrets)
    seed = os.environ.get("SIGNING_KEY_SEED")
    if not seed:
        print("❌ SIGNING_KEY_SEED not set", file=sys.stderr)
        return False

    # Generate deterministic keys
    private_key, public_key = generate_keypair_from_seed(seed)

    # Read package
    with open(package_path, "rb") as f:
        package_data = f.read()

    # Sign package
    signature = sign_package(package_data, private_key)

    # Embed signature in package
    # (Implementation depends on package format)
    embed_signature_in_package(package_path, signature)

    # Save public key for distribution
    save_public_key(public_key, Path("dist/public-key.pem"))

    print(f"✅ Package signed: {package_path}")
    return True

# Usage in CI
if __name__ == "__main__":
    package = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/app.psp")
    success = ci_sign_package(package)
    sys.exit(0 if success else 1)
```

### Multi-Signature Verification

```python
from flavor.psp.format_2025.crypto import verify_signature, load_public_key

def verify_multi_signature(package_path, trusted_keys_dir):
    """Verify package is signed by at least one trusted key."""
    # Load all trusted public keys
    trusted_keys = []
    for key_file in Path(trusted_keys_dir).glob("*.pem"):
        trusted_keys.append(load_public_key(key_file))

    if not trusted_keys:
        print("❌ No trusted keys found")
        return False

    # Read package
    with open(package_path, "rb") as f:
        package_data = f.read()

    signature = extract_signature_from_package(package_data)

    # Try each trusted key
    for i, public_key in enumerate(trusted_keys):
        if verify_signature(package_data, signature, public_key):
            print(f"✅ Valid signature from trusted key {i+1}")
            return True

    print("❌ No valid signature from trusted keys")
    return False

# Verify with multiple trusted keys
is_trusted = verify_multi_signature(
    Path("myapp.psp"),
    Path("trusted-keys")
)
```

### Signature Chain of Trust

```python
from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class SignatureChain:
    """Chain of signatures for auditing."""
    package_name: str
    signatures: List[dict]

def build_signature_chain(package_path, key_history):
    """Build chain of trust with historical signatures."""
    chain = SignatureChain(
        package_name=package_path.name,
        signatures=[]
    )

    with open(package_path, "rb") as f:
        package_data = f.read()

    # Verify against each historical key
    for entry in key_history:
        public_key = load_public_key(entry["key_path"])
        signature = extract_signature_for_key(package_data, entry["key_id"])

        is_valid = verify_signature(package_data, signature, public_key)

        chain.signatures.append({
            "key_id": entry["key_id"],
            "valid_from": entry["valid_from"],
            "valid_until": entry.get("valid_until"),
            "is_valid": is_valid,
            "verified_at": datetime.now().isoformat()
        })

    return chain

# Build and verify chain
key_history = [
    {"key_id": "key-2024", "key_path": "keys/2024.pem", "valid_from": "2024-01-01"},
    {"key_id": "key-2025", "key_path": "keys/2025.pem", "valid_from": "2025-01-01"},
]
chain = build_signature_chain(Path("myapp.psp"), key_history)

for sig in chain.signatures:
    status = "✅" if sig["is_valid"] else "❌"
    print(f"{status} {sig['key_id']}: {sig['verified_at']}")
```

### Offline Signing

```python
from flavor.psp.format_2025.crypto import sign_package, load_private_key
import json

def prepare_for_offline_signing(package_path):
    """Prepare package hash for offline signing."""
    with open(package_path, "rb") as f:
        package_data = f.read()

    # Calculate hash for signing
    from hashlib import sha256
    package_hash = sha256(package_data).hexdigest()

    # Create signing request
    request = {
        "package_path": str(package_path),
        "package_hash": package_hash,
        "size": len(package_data),
    }

    request_file = package_path.with_suffix(".signing-request.json")
    request_file.write_text(json.dumps(request, indent=2))

    print(f"✅ Signing request saved: {request_file}")
    return request_file

def apply_offline_signature(package_path, signature_file):
    """Apply signature from offline signing."""
    # Read signature
    signature = Path(signature_file).read_bytes()

    # Embed in package
    embed_signature_in_package(package_path, signature)

    print(f"✅ Signature applied to {package_path}")

# Offline workflow
# 1. On online machine
request = prepare_for_offline_signing(Path("sensitive-app.psp"))

# 2. Transfer request to offline signing machine
# 3. On offline machine: sign and return signature
# 4. Back on online machine
apply_offline_signature(Path("sensitive-app.psp"), Path("signature.bin"))
```

## Security Best Practices

### Secure Key Storage

```python
import stat
from pathlib import Path

def save_key_securely(key_data, key_path):
    """Save key with restricted permissions."""
    key_path = Path(key_path)

    # Write key
    key_path.write_bytes(key_data)

    # Set restrictive permissions (owner read/write only)
    key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600

    print(f"✅ Key saved with restricted permissions: {key_path}")
    print(f"   Permissions: {oct(key_path.stat().st_mode)[-3:]}")

# Usage
from flavor.psp.format_2025.crypto import generate_keypair
private_key, public_key = generate_keypair()

from cryptography.hazmat.primitives import serialization
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

save_key_securely(private_pem, Path("keys/flavor-private.key"))
```

### Key Validation

```python
from flavor.psp.format_2025.crypto import load_private_key, load_public_key

def validate_keypair(private_key_path, public_key_path):
    """Validate that private and public keys match."""
    try:
        private_key = load_private_key(private_key_path)
        public_key = load_public_key(public_key_path)

        # Generate test signature
        test_data = b"test message"
        signature = sign_package(test_data, private_key)

        # Verify with public key
        is_valid = verify_signature(test_data, signature, public_key)

        if is_valid:
            print("✅ Key pair is valid and matches")
            return True
        else:
            print("❌ Key pair does not match")
            return False

    except Exception as e:
        print(f"❌ Key validation failed: {e}")
        return False

# Validate keys
validate_keypair(
    Path("keys/flavor-private.key"),
    Path("keys/flavor-public.key")
)
```

## Error Handling

```python
from flavor.psp.format_2025.crypto import (
    CryptoError,
    InvalidSignatureError,
    KeyError,
    load_private_key,
    sign_package
)

def safe_sign_package(package_path, key_path):
    """Safely sign package with comprehensive error handling."""
    try:
        # Load key
        private_key = load_private_key(key_path)

        # Read package
        with open(package_path, "rb") as f:
            data = f.read()

        # Sign
        signature = sign_package(data, private_key)
        return signature

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return None

    except KeyError as e:
        print(f"❌ Invalid or corrupted key: {e}")
        return None

    except CryptoError as e:
        print(f"❌ Cryptographic operation failed: {e}")
        return None

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

# Safe signing
signature = safe_sign_package(
    Path("myapp.psp"),
    Path("keys/flavor-private.key")
)

if signature:
    print("✅ Package signed successfully")
```

## API Reference

!!! warning "Auto-Generated API Documentation Disabled"
    The auto-generated API reference has been temporarily disabled while the documentation is updated to match the actual implementation.

    For now, refer to the source code:

    - **Key Management**: `src/flavor/psp/format_2025/keys.py`
    - **Signing**: `src/flavor/psp/format_2025/writer.py`
    - **Verification**: `src/flavor/psp/security.py`

    Or use the high-level API documented in [Packaging API](packaging.md).

## See Also

- **[Packaging API](packaging.md)** - High-level packaging with automatic signing
- **[Builder API](builder.md)** - Package creation with signing
- **[Signing Guide](../guide/packaging/signing.md)** - Package signing workflow
- **[Security Model](../guide/concepts/security.md)** - FlavorPack security architecture
- **[Keygen Command](../guide/usage/cli.md#keygen)** - CLI key generation
- **[PSPF Security Specification](../reference/spec/fep-0001-core-format-and-operation-chains.md#7-security-model)** - Security model details
