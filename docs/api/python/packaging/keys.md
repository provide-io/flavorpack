# Key Management API

Package signing and verification key management for FlavorPack.

## Overview

The key management system handles cryptographic keys for package signing and verification, ensuring package integrity and authenticity.

## KeyManager Class

Main class for managing signing and verification keys.

### Constructor

```python
from flavor.packaging.keys import KeyManager

manager = KeyManager(
    key_dir: Path | None = None,
    auto_generate: bool = True
)
```

**Parameters:**
- `key_dir`: Directory for storing keys (default: `~/.flavor/keys`)
- `auto_generate`: Auto-generate keys if missing

### Key Generation

```python
async def generate_keypair(
    name: str,
    algorithm: str = "ed25519",
    key_size: int | None = None
) -> KeyPair:
    """Generate new signing keypair.
    
    Args:
        name: Key identifier
        algorithm: Signing algorithm
        key_size: Key size in bits
        
    Returns:
        Generated keypair
    """
```

**Example:**
```python
# Generate Ed25519 keypair
keypair = await manager.generate_keypair("my-app")

# Generate RSA keypair
keypair = await manager.generate_keypair(
    "my-app-rsa",
    algorithm="rsa",
    key_size=4096
)
```

### Key Storage

```python
async def save_keypair(
    keypair: KeyPair,
    password: str | None = None
) -> None:
    """Save keypair to disk.
    
    Args:
        keypair: Keypair to save
        password: Optional encryption password
    """

async def load_keypair(
    name: str,
    password: str | None = None
) -> KeyPair:
    """Load keypair from disk.
    
    Args:
        name: Key identifier
        password: Decryption password if encrypted
        
    Returns:
        Loaded keypair
    """
```

### Key Operations

```python
async def list_keys() -> list[KeyInfo]:
    """List all available keys."""

async def delete_key(name: str) -> None:
    """Delete a keypair."""

async def export_public_key(
    name: str,
    format: str = "pem"
) -> bytes:
    """Export public key for distribution."""

async def import_public_key(
    data: bytes,
    name: str,
    format: str = "pem"  
) -> None:
    """Import public key for verification."""
```

## PackageSigner Class

Signs packages with private keys.

### Constructor

```python
from flavor.packaging.keys import PackageSigner

signer = PackageSigner(
    key_manager: KeyManager,
    default_key: str | None = None
)
```

### Signing Operations

```python
async def sign_package(
    package_path: Path,
    key_name: str | None = None,
    metadata: dict[str, Any] | None = None
) -> Signature:
    """Sign a package file.
    
    Args:
        package_path: Path to package
        key_name: Signing key (or use default)
        metadata: Additional signature metadata
        
    Returns:
        Package signature
    """
```

**Example:**
```python
# Sign package
signature = await signer.sign_package(
    Path("my-app.pspf"),
    key_name="my-app",
    metadata={"version": "1.0.0"}
)

# Embed signature in package
await signer.embed_signature(
    package_path=Path("my-app.pspf"),
    signature=signature
)
```

### Signature Formats

```python
async def create_detached_signature(
    package_path: Path,
    output_path: Path | None = None
) -> Path:
    """Create detached signature file."""

async def create_inline_signature(
    package_path: Path
) -> None:
    """Embed signature in package."""
```

## PackageVerifier Class

Verifies package signatures.

### Constructor

```python
from flavor.packaging.keys import PackageVerifier

verifier = PackageVerifier(
    key_manager: KeyManager,
    trusted_keys: list[str] | None = None
)
```

### Verification Operations

```python
async def verify_package(
    package_path: Path,
    signature: Signature | None = None
) -> VerificationResult:
    """Verify package signature.
    
    Args:
        package_path: Package to verify
        signature: External signature (if detached)
        
    Returns:
        Verification result with status
    """
```

**Example:**
```python
# Verify package
result = await verifier.verify_package(
    Path("my-app.pspf")
)

if result.valid:
    print(f"Package signed by: {result.signer}")
    print(f"Signed at: {result.timestamp}")
else:
    print(f"Verification failed: {result.error}")
```

### Trust Management

```python
async def add_trusted_key(
    name: str,
    public_key: bytes | None = None
) -> None:
    """Add key to trusted list."""

async def remove_trusted_key(name: str) -> None:
    """Remove key from trusted list."""

async def list_trusted_keys() -> list[str]:
    """List all trusted key names."""
```

## Data Classes

### KeyPair

```python
@dataclass
class KeyPair:
    """Cryptographic keypair."""
    name: str
    algorithm: str
    private_key: bytes
    public_key: bytes
    created_at: datetime
    fingerprint: str
```

### KeyInfo

```python
@dataclass
class KeyInfo:
    """Key metadata."""
    name: str
    algorithm: str
    fingerprint: str
    created_at: datetime
    has_private: bool
    trusted: bool
```

### Signature

```python
@dataclass
class Signature:
    """Package signature."""
    signer: str
    algorithm: str
    signature: bytes
    timestamp: datetime
    metadata: dict[str, Any]
```

### VerificationResult

```python
@dataclass
class VerificationResult:
    """Signature verification result."""
    valid: bool
    signer: str | None
    timestamp: datetime | None
    error: str | None
    metadata: dict[str, Any]
```

## Algorithms

### Supported Algorithms

| Algorithm | Key Size | Security | Performance |
|-----------|----------|----------|-------------|
| `ed25519` | 256 bits | High | Fast |
| `ecdsa` | 256-521 bits | High | Moderate |
| `rsa` | 2048-4096 bits | High | Slow |

### Algorithm Selection

```python
# Ed25519 (recommended)
keypair = await manager.generate_keypair(
    "app-key",
    algorithm="ed25519"
)

# ECDSA P-256
keypair = await manager.generate_keypair(
    "app-key",
    algorithm="ecdsa",
    curve="P-256"
)

# RSA-4096
keypair = await manager.generate_keypair(
    "app-key",
    algorithm="rsa",
    key_size=4096
)
```

## Key Formats

### PEM Format

```python
# Export as PEM
pem_key = await manager.export_public_key(
    "my-key",
    format="pem"
)

# Import PEM
await manager.import_public_key(
    pem_data,
    "their-key",
    format="pem"
)
```

### DER Format

```python
# Export as DER
der_key = await manager.export_public_key(
    "my-key",
    format="der"
)
```

### JWK Format

```python
# Export as JWK
jwk_key = await manager.export_public_key(
    "my-key",
    format="jwk"
)
```

## Security Features

### Key Encryption

```python
# Save with encryption
await manager.save_keypair(
    keypair,
    password="strong-password"
)

# Load with decryption
keypair = await manager.load_keypair(
    "my-key",
    password="strong-password"
)
```

### Key Rotation

```python
async def rotate_key(
    old_name: str,
    new_name: str | None = None
) -> KeyPair:
    """Rotate signing key.
    
    Creates new key and archives old one.
    """
```

### Secure Storage

```python
# Use hardware security module
manager = KeyManager(
    key_store="hsm",
    hsm_config={
        "module": "pkcs11",
        "slot": 0
    }
)

# Use system keychain
manager = KeyManager(
    key_store="keychain"
)
```

## CLI Integration

### Key Commands

```bash
# Generate key
flavor key generate my-app

# List keys
flavor key list

# Export public key
flavor key export my-app > my-app.pub

# Import public key
flavor key import their-app < their-app.pub

# Sign package
flavor sign my-app.pspf --key my-app

# Verify package
flavor verify my-app.pspf
```

## Examples

### Complete Signing Workflow

```python
from flavor.packaging.keys import (
    KeyManager,
    PackageSigner,
    PackageVerifier
)

async def signing_workflow():
    # Initialize
    manager = KeyManager()
    signer = PackageSigner(manager)
    verifier = PackageVerifier(manager)
    
    # Generate key
    keypair = await manager.generate_keypair("release-key")
    await manager.save_keypair(keypair)
    
    # Sign package
    signature = await signer.sign_package(
        Path("app.pspf"),
        key_name="release-key"
    )
    
    # Verify package
    result = await verifier.verify_package(
        Path("app.pspf")
    )
    
    if result.valid:
        print(f"Package verified: {result.signer}")
```

### Key Distribution

```python
async def distribute_public_key():
    manager = KeyManager()
    
    # Export public key
    public_key = await manager.export_public_key(
        "release-key",
        format="pem"
    )
    
    # Save to file
    Path("release-key.pub").write_bytes(public_key)
    
    # On verifier side
    verifier_manager = KeyManager()
    public_data = Path("release-key.pub").read_bytes()
    
    await verifier_manager.import_public_key(
        public_data,
        "vendor-key",
        format="pem"
    )
```

## Best Practices

1. **Use Ed25519** for new applications (fast, secure, small keys)
2. **Protect private keys** with encryption and secure storage
3. **Rotate keys regularly** to limit exposure
4. **Verify signatures** before running packages
5. **Distribute public keys** through secure channels

## Error Handling

```python
from flavor.packaging.keys import (
    KeyNotFoundError,
    InvalidSignatureError,
    KeyGenerationError
)

try:
    keypair = await manager.load_keypair("missing")
except KeyNotFoundError:
    # Generate new key
    keypair = await manager.generate_keypair("missing")

try:
    result = await verifier.verify_package(package)
except InvalidSignatureError as e:
    print(f"Invalid signature: {e}")
```

## Related Documentation

- [Package Signing](../../../guide/packaging/signing.md)
- [Security Model](../../../guide/concepts/security.md)
- [Orchestrator](orchestrator.md)
- [Cryptography](../psp/crypto.md)