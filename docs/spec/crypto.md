# Cryptographic Security

The PSPF/2025 format uses Ed25519 digital signatures to ensure package integrity and authenticity.

## Overview

Every FlavorPack package is cryptographically signed to provide:

1. **Integrity**: Detect any tampering or corruption
2. **Authenticity**: Verify the package creator
3. **Non-repudiation**: Prove who created the package
4. **Determinism**: Support reproducible builds

## Ed25519 Algorithm

FlavorPack uses Ed25519, a modern elliptic curve signature scheme that provides:

- **128-bit security level**
- **Fast signature generation and verification**
- **Small key and signature sizes**
- **Resistance to timing attacks**
- **No random number generator required for signing**

### Key Sizes

| Component | Size | Description |
|-----------|------|-------------|
| Private Key | 32 bytes | Secret key for signing |
| Public Key | 32 bytes | Public key for verification |
| Signature | 64 bytes | Digital signature |
| Seed | Variable | Optional deterministic seed |

## Key Generation

### Random Key Generation

Generate a new random key pair:

```python
from cryptography.hazmat.primitives.asymmetric import ed25519

# Generate random key pair
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Export keys
private_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption()
)
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
)
```

### Deterministic Key Generation

Generate reproducible keys from a seed:

```python
import hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519

def generate_key_pair(seed: str) -> tuple[bytes, bytes]:
    """Generate deterministic Ed25519 key pair from seed."""
    # Derive 32-byte seed from input
    seed_bytes = hashlib.sha256(seed.encode('utf-8')).digest()
    
    # Generate key pair from seed
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)
    public_key = private_key.public_key()
    
    return private_key, public_key
```

### Key Storage

Keys are typically stored in PEM format:

```python
from cryptography.hazmat.primitives import serialization

# Save private key
with open('private.pem', 'wb') as f:
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    f.write(pem)

# Save public key
with open('public.pem', 'wb') as f:
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    f.write(pem)
```

## Package Signing Process

### 1. Prepare Metadata

The metadata JSON is the primary signed content:

```python
import json
import gzip

metadata = {
    "package": {"name": "myapp", "version": "1.0.0"},
    "slots": [...],
    "execution": {...}
}

# Serialize and compress
metadata_json = json.dumps(metadata, separators=(',', ':'), sort_keys=True)
metadata_compressed = gzip.compress(metadata_json.encode('utf-8'))
```

### 2. Calculate Hash

Create a SHA-256 hash of the metadata:

```python
import hashlib

metadata_hash = hashlib.sha256(metadata_compressed).digest()
```

### 3. Generate Signature

Sign the hash with the private key:

```python
signature = private_key.sign(metadata_hash)
```

### 4. Embed in Package

Store the public key and signature in the index block:

```python
import struct

# Write to index block at appropriate offsets
index_data[36:68] = public_key_bytes  # 32 bytes at offset 36
index_data[68:132] = signature        # 64 bytes at offset 68
```

## Verification Process

### 1. Extract Components

Read from the package index block:

```python
# Read index block
with open('package.psp', 'rb') as f:
    f.seek(launcher_size)  # Skip launcher
    index_data = f.read(8192)

# Extract crypto fields
public_key_bytes = index_data[36:68]
signature = index_data[68:132]
```

### 2. Read Metadata

Load and hash the metadata:

```python
# Read metadata
metadata_offset = struct.unpack('<Q', index_data[8:16])[0]
metadata_size = struct.unpack('<Q', index_data[16:24])[0]

with open('package.psp', 'rb') as f:
    f.seek(metadata_offset)
    metadata_compressed = f.read(metadata_size)

# Calculate hash
metadata_hash = hashlib.sha256(metadata_compressed).digest()
```

### 3. Verify Signature

Verify using the public key:

```python
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

# Load public key
public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)

# Verify signature
try:
    public_key.verify(signature, metadata_hash)
    print("✅ Signature valid")
except InvalidSignature:
    print("❌ Signature invalid")
    raise
```

## Security Considerations

### Key Management

1. **Private Key Protection**
   - Never commit private keys to version control
   - Store securely (HSM, secure storage, encrypted)
   - Use different keys for different environments

2. **Public Key Distribution**
   - Embed in packages for self-verification
   - Distribute separately for third-party verification
   - Consider key rotation strategies

### Deterministic Builds

Using seed-based keys enables:

```bash
# CI/CD with consistent signatures
flavor pack --key-seed "$CI_SECRET_SEED"

# Development with test keys
flavor pack --key-seed "dev-test-key"

# Production with secure keys
flavor pack --private-key /secure/private.pem
```

### Trust Models

1. **Self-Signed** (Default)
   - Package contains its own public key
   - Verifies integrity, not trust
   - Suitable for internal distribution

2. **Pre-Shared Keys**
   - Public key distributed separately
   - Verifies both integrity and authenticity
   - Suitable for controlled environments

3. **PKI Integration** (Future)
   - Certificate-based trust chains
   - Third-party certificate authorities
   - Enterprise deployment scenarios

## Implementation Notes

### Launcher Verification

Both Go and Rust launchers implement verification:

```go
// Go launcher
func verifySignature(publicKey, signature, hash []byte) error {
    return ed25519.Verify(publicKey, hash, signature)
}
```

```rust
// Rust launcher
fn verify_signature(public_key: &[u8], signature: &[u8], hash: &[u8]) -> Result<()> {
    let key = Ed25519PublicKey::from_bytes(public_key)?;
    let sig = Ed25519Signature::from_bytes(signature)?;
    key.verify(hash, &sig)
}
```

### Performance

- Key generation: ~1ms
- Signing: ~0.5ms
- Verification: ~1ms
- Hash calculation: Depends on metadata size

### Compatibility

The Ed25519 implementation is compatible across:
- Python (cryptography library)
- Go (crypto/ed25519)
- Rust (ed25519-dalek)
- OpenSSL 1.1.1+

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid signature | Package tampered or corrupted | Re-download or rebuild |
| Missing public key | Index block corrupted | Package invalid |
| Key format error | Incompatible key encoding | Check key format |
| Verification timeout | Large metadata | Increase timeout |

### Insecure Mode

For development/testing only:

```bash
# Skip verification (NEVER in production!)
FLAVOR_INSECURE=1 ./package.psp
```

## Best Practices

1. **Always sign packages** for production use
2. **Use deterministic seeds** for CI/CD pipelines
3. **Rotate keys periodically** for long-term projects
4. **Verify packages** before execution
5. **Keep private keys secure** and never share
6. **Log verification failures** for security monitoring
7. **Test signature verification** in your test suite

## Future Enhancements

- **X.509 certificate support** for enterprise PKI
- **Multiple signature support** for multi-party signing
- **Timestamp signatures** for time-based validity
- **Revocation lists** for compromised keys
- **Hardware security module** (HSM) integration

## Related Documentation

- [Binary Layout](binary-layout.md) - Where signatures are stored
- [Metadata Structure](metadata.md) - What gets signed
- [Package Format](pspf-2025.md) - Overall format specification
- [Security Model](../guide/concepts/security.md) - Security architecture