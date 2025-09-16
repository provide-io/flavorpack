# Cryptography API

Cryptographic operations for PSPF package signing, verification, and security.

## Overview

The cryptography module provides comprehensive security features for PSPF packages including digital signatures, checksums, and encryption support.

## CryptoProvider Class

Main cryptographic operations provider.

### Constructor

```python
from flavor.psp.format_2025.crypto import CryptoProvider

provider = CryptoProvider(
    algorithm: str = "ed25519",
    hash_algorithm: str = "sha256"
)
```

**Parameters:**
- `algorithm`: Signature algorithm (ed25519, ecdsa, rsa)
- `hash_algorithm`: Hash algorithm (sha256, sha512, blake2b)

### Key Generation

```python
def generate_keypair(
    seed: bytes | str | None = None
) -> tuple[bytes, bytes]:
    """Generate cryptographic keypair.
    
    Args:
        seed: Optional seed for deterministic generation
        
    Returns:
        Tuple of (private_key, public_key)
    """
```

**Example:**
```python
# Random keypair
private_key, public_key = provider.generate_keypair()

# Deterministic keypair
private_key, public_key = provider.generate_keypair(
    seed="my-deterministic-seed"
)
```

### Signing Operations

```python
def sign(
    data: bytes,
    private_key: bytes
) -> bytes:
    """Sign data with private key.
    
    Args:
        data: Data to sign
        private_key: Private signing key
        
    Returns:
        Digital signature
    """
```

**Example:**
```python
# Sign package data
package_data = b"package contents..."
signature = provider.sign(package_data, private_key)
```

### Verification Operations

```python
def verify(
    data: bytes,
    signature: bytes,
    public_key: bytes
) -> bool:
    """Verify signature with public key.
    
    Args:
        data: Original data
        signature: Digital signature
        public_key: Public verification key
        
    Returns:
        True if valid, False otherwise
    """
```

**Example:**
```python
# Verify signature
is_valid = provider.verify(
    package_data,
    signature,
    public_key
)

if is_valid:
    print("✅ Signature verified")
else:
    print("❌ Invalid signature")
```

## Hash Functions

### SHA-256

```python
from flavor.psp.format_2025.crypto import sha256_hash

def sha256_hash(data: bytes) -> bytes:
    """Compute SHA-256 hash."""
```

### SHA-512

```python
from flavor.psp.format_2025.crypto import sha512_hash

def sha512_hash(data: bytes) -> bytes:
    """Compute SHA-512 hash."""
```

### BLAKE2b

```python
from flavor.psp.format_2025.crypto import blake2b_hash

def blake2b_hash(
    data: bytes,
    digest_size: int = 32
) -> bytes:
    """Compute BLAKE2b hash."""
```

### Multi-Hash

```python
def compute_checksums(
    data: bytes,
    algorithms: list[str] = ["sha256"]
) -> dict[str, str]:
    """Compute multiple checksums.
    
    Args:
        data: Data to hash
        algorithms: List of hash algorithms
        
    Returns:
        Dictionary of algorithm: hex_digest
    """
```

**Example:**
```python
checksums = compute_checksums(
    data,
    algorithms=["sha256", "sha512", "blake2b"]
)

for algo, digest in checksums.items():
    print(f"{algo}: {digest}")
```

## PackageSecurity Class

High-level package security operations.

### Constructor

```python
from flavor.psp.format_2025.crypto import PackageSecurity

security = PackageSecurity(
    provider: CryptoProvider | None = None
)
```

### Sign Package

```python
async def sign_package(
    package_path: Path,
    private_key: bytes,
    embed: bool = True
) -> PackageSignature:
    """Sign a PSPF package.
    
    Args:
        package_path: Path to package
        private_key: Signing key
        embed: Embed signature in package
        
    Returns:
        Package signature object
    """
```

**Example:**
```python
signature = await security.sign_package(
    Path("app.pspf"),
    private_key,
    embed=True
)

print(f"Signed by: {signature.key_id}")
print(f"Algorithm: {signature.algorithm}")
print(f"Timestamp: {signature.timestamp}")
```

### Verify Package

```python
async def verify_package(
    package_path: Path,
    public_key: bytes | None = None,
    require_signature: bool = True
) -> VerificationResult:
    """Verify package signature and integrity.
    
    Args:
        package_path: Path to package
        public_key: Verification key (or use embedded)
        require_signature: Require valid signature
        
    Returns:
        Verification result
    """
```

**Example:**
```python
result = await security.verify_package(
    Path("app.pspf"),
    public_key=public_key
)

if result.valid:
    print(f"✅ Package verified")
    print(f"   Signer: {result.signer_id}")
    print(f"   Signed: {result.timestamp}")
else:
    print(f"❌ Verification failed: {result.error}")
```

### Integrity Check

```python
async def check_integrity(
    package_path: Path
) -> IntegrityResult:
    """Check package integrity without signature.
    
    Args:
        package_path: Path to package
        
    Returns:
        Integrity check result
    """
```

## Signature Formats

### Ed25519 Signatures

Fast, secure, and compact signatures.

```python
from flavor.psp.format_2025.crypto import Ed25519Provider

provider = Ed25519Provider()

# Generate 32-byte keys
private_key, public_key = provider.generate_keypair()

# Create 64-byte signature
signature = provider.sign(data, private_key)
```

### ECDSA Signatures

Standard elliptic curve signatures.

```python
from flavor.psp.format_2025.crypto import ECDSAProvider

provider = ECDSAProvider(curve="P-256")

# Supports curves: P-256, P-384, P-521
private_key, public_key = provider.generate_keypair()
signature = provider.sign(data, private_key)
```

### RSA Signatures

Traditional RSA signatures.

```python
from flavor.psp.format_2025.crypto import RSAProvider

provider = RSAProvider(key_size=4096)

# Key sizes: 2048, 3072, 4096
private_key, public_key = provider.generate_keypair()
signature = provider.sign(data, private_key)
```

## Key Formats

### PEM Encoding

```python
from flavor.psp.format_2025.crypto import (
    encode_private_key_pem,
    encode_public_key_pem,
    decode_private_key_pem,
    decode_public_key_pem
)

# Encode keys to PEM
private_pem = encode_private_key_pem(
    private_key,
    algorithm="ed25519",
    password=b"optional-password"
)

public_pem = encode_public_key_pem(
    public_key,
    algorithm="ed25519"
)

# Decode PEM keys
private_key = decode_private_key_pem(
    private_pem,
    password=b"optional-password"
)

public_key = decode_public_key_pem(public_pem)
```

### DER Encoding

```python
from flavor.psp.format_2025.crypto import (
    encode_key_der,
    decode_key_der
)

# Binary DER format
der_key = encode_key_der(public_key, "ed25519")
public_key = decode_key_der(der_key, "ed25519")
```

### JWK Format

```python
from flavor.psp.format_2025.crypto import (
    key_to_jwk,
    jwk_to_key
)

# JSON Web Key format
jwk = key_to_jwk(public_key, algorithm="ed25519")
public_key = jwk_to_key(jwk)
```

## Checksums and Verification

### File Checksums

```python
from flavor.psp.format_2025.crypto import file_checksum

async def file_checksum(
    path: Path,
    algorithm: str = "sha256",
    chunk_size: int = 8192
) -> str:
    """Compute file checksum.
    
    Args:
        path: File path
        algorithm: Hash algorithm
        chunk_size: Read chunk size
        
    Returns:
        Hex digest string
    """
```

**Example:**
```python
checksum = await file_checksum(
    Path("large-file.bin"),
    algorithm="sha256"
)
print(f"SHA-256: {checksum}")
```

### Directory Tree Hash

```python
from flavor.psp.format_2025.crypto import tree_hash

async def tree_hash(
    directory: Path,
    algorithm: str = "sha256"
) -> str:
    """Compute hash of directory tree.
    
    Includes file contents and structure.
    """
```

### Merkle Tree

```python
from flavor.psp.format_2025.crypto import MerkleTree

tree = MerkleTree(algorithm="sha256")

# Add data blocks
tree.add(b"block1")
tree.add(b"block2")
tree.add(b"block3")

# Get root hash
root = tree.root_hash()

# Generate proof
proof = tree.get_proof(1)  # Proof for block2

# Verify proof
valid = tree.verify_proof(b"block2", proof, root)
```

## Encryption (Future)

### Symmetric Encryption

```python
from flavor.psp.format_2025.crypto import SymmetricCrypto

crypto = SymmetricCrypto(algorithm="AES-256-GCM")

# Generate key
key = crypto.generate_key()

# Encrypt data
ciphertext, nonce, tag = crypto.encrypt(
    plaintext=data,
    key=key,
    associated_data=b"metadata"
)

# Decrypt data
plaintext = crypto.decrypt(
    ciphertext=ciphertext,
    key=key,
    nonce=nonce,
    tag=tag,
    associated_data=b"metadata"
)
```

### Key Derivation

```python
from flavor.psp.format_2025.crypto import derive_key

# Derive key from password
key = derive_key(
    password="strong-password",
    salt=b"random-salt",
    iterations=100000,
    algorithm="pbkdf2-sha256"
)

# Derive key from master key
subkey = derive_key(
    master_key=master,
    info=b"encryption-key",
    algorithm="hkdf-sha256"
)
```

## Security Best Practices

### Key Management

```python
from flavor.psp.format_2025.crypto import SecureKeyStore

# Secure key storage
store = SecureKeyStore(
    path=Path("~/.flavor/keys"),
    encryption_key=master_key
)

# Save key securely
await store.save_key(
    name="signing-key",
    key_data=private_key,
    metadata={"algorithm": "ed25519"}
)

# Load key securely
key_data = await store.load_key(
    name="signing-key",
    password="key-password"
)
```

### Secure Random

```python
from flavor.psp.format_2025.crypto import secure_random

# Cryptographically secure random
random_bytes = secure_random(32)  # 32 random bytes
random_hex = secure_random_hex(16)  # 16 random hex chars
random_id = secure_random_id()  # Random UUID
```

### Constant-Time Operations

```python
from flavor.psp.format_2025.crypto import constant_time_compare

# Prevent timing attacks
def verify_token(provided: bytes, expected: bytes) -> bool:
    """Verify token in constant time."""
    return constant_time_compare(provided, expected)
```

## Performance Optimization

### Parallel Hashing

```python
async def parallel_hash_files(
    files: list[Path],
    algorithm: str = "sha256"
) -> dict[Path, str]:
    """Hash multiple files in parallel."""
    
    import asyncio
    
    tasks = [
        file_checksum(f, algorithm)
        for f in files
    ]
    
    results = await asyncio.gather(*tasks)
    return dict(zip(files, results))
```

### Streaming Operations

```python
from flavor.psp.format_2025.crypto import StreamHasher

async def hash_stream(stream):
    """Hash streaming data."""
    hasher = StreamHasher("sha256")
    
    async for chunk in stream:
        hasher.update(chunk)
    
    return hasher.finalize()
```

### Hardware Acceleration

```python
from flavor.psp.format_2025.crypto import get_crypto_capabilities

caps = get_crypto_capabilities()

if caps.has_aes_ni:
    print("AES-NI hardware acceleration available")

if caps.has_sha_extensions:
    print("SHA hardware extensions available")

# Auto-select best implementation
provider = CryptoProvider(
    algorithm="ed25519",
    use_hardware=True  # Use hardware if available
)
```

## Error Handling

```python
from flavor.psp.format_2025.crypto import (
    CryptoError,
    InvalidSignatureError,
    InvalidKeyError,
    UnsupportedAlgorithmError
)

try:
    provider = CryptoProvider(algorithm="unknown")
except UnsupportedAlgorithmError as e:
    print(f"Algorithm not supported: {e}")

try:
    provider.verify(data, signature, public_key)
except InvalidSignatureError as e:
    print(f"Signature verification failed: {e}")

try:
    provider.sign(data, invalid_key)
except InvalidKeyError as e:
    print(f"Invalid key format: {e}")
```

## CLI Integration

```bash
# Generate keypair
flavor crypto generate --algorithm ed25519

# Sign file
flavor crypto sign file.bin --key private.pem

# Verify signature
flavor crypto verify file.bin file.sig --key public.pem

# Compute checksums
flavor crypto hash file.bin --algorithms sha256,blake2b
```

## Complete Example

```python
from pathlib import Path
from flavor.psp.format_2025.crypto import (
    CryptoProvider,
    PackageSecurity,
    file_checksum
)

async def secure_package_workflow():
    """Complete security workflow."""
    
    # Initialize crypto
    provider = CryptoProvider(algorithm="ed25519")
    security = PackageSecurity(provider)
    
    # Generate keys
    private_key, public_key = provider.generate_keypair()
    
    # Save keys
    Path("private.pem").write_bytes(
        encode_private_key_pem(private_key, "ed25519")
    )
    Path("public.pem").write_bytes(
        encode_public_key_pem(public_key, "ed25519")
    )
    
    # Build package (assumed to exist)
    package_path = Path("app.pspf")
    
    # Compute checksum
    checksum = await file_checksum(package_path)
    print(f"Package checksum: {checksum}")
    
    # Sign package
    signature = await security.sign_package(
        package_path,
        private_key,
        embed=True
    )
    print(f"Package signed: {signature.signature_hex[:16]}...")
    
    # Verify package
    result = await security.verify_package(
        package_path,
        public_key
    )
    
    if result.valid:
        print("✅ Package verified successfully")
        print(f"   Signer: {result.signer_id}")
        print(f"   Algorithm: {result.algorithm}")
        print(f"   Timestamp: {result.timestamp}")
    else:
        print(f"❌ Verification failed: {result.error}")

# Run workflow
import asyncio
asyncio.run(secure_package_workflow())
```

## Related Documentation

- [Key Management](../packaging/keys.md) - Key management API
- [Package Signing](../../../guide/packaging/signing.md) - Signing guide
- [Security Model](../../../guide/concepts/security.md) - Security architecture
- [PSPFBuilder](builder.md) - Building signed packages
- [PSPFReader](reader.md) - Verifying packages