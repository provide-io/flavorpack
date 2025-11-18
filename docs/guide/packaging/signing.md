# Signing & Verification

Secure your FlavorPack packages with Ed25519 digital signatures for authenticity and integrity.

## Overview

FlavorPack uses Ed25519 digital signatures to ensure packages haven't been tampered with and come from trusted sources. This guide covers key generation, package signing, verification, and best practices for secure distribution.

## Quick Start

### Generate Keys

```bash
# Generate a new Ed25519 key pair
flavor keygen --out-dir keys

# This creates:
# - keys/flavor-private.key (private key - keep secret!)
# - keys/flavor-public.key (public key - distribute freely)
```

### Sign Package

```bash
# Sign during build
flavor pack --manifest pyproject.toml --private-key keys/flavor-private.key --public-key keys/flavor-public.key

# Package is now signed and can be verified
```

### Verify Package

```bash
# Verify signature (uses embedded public key)
flavor verify myapp-1.0.0.psp
```

!!! info "Public Key Verification"
    The `verify` command automatically uses the public key embedded in the package. External key verification is planned for a future release.

## Key Management

### Key Generation Options

#### 1. Random Keys (Recommended for Production)

Generate cryptographically secure random keys:

```bash
# Generate with default settings (creates keys/ directory)
flavor keygen

# Specify custom output directory
flavor keygen --out-dir ~/.flavor/keys
```

#### 2. Using Existing Keys

Use existing Ed25519 key files:

```bash
# Keys must be in PEM format
flavor pack --manifest pyproject.toml \
  --private-key /path/to/flavor-private.key \
  --public-key /path/to/flavor-public.key
```

**Note**: Keys must be Ed25519 format in PEM encoding. The private key file should be 32 bytes (raw seed) or PEM-encoded Ed25519 private key.

### Key Storage Best Practices

#### Development

```bash
# Store in home directory
mkdir -p ~/.flavor/keys
chmod 700 ~/.flavor/keys
flavor keygen --out-dir ~/.flavor/keys
chmod 600 ~/.flavor/keys/flavor-private.key
```

#### Production

1. **Encrypted Storage**
   ```bash
   # Encrypt private key for storage
   openssl enc -aes-256-cbc -salt -in keys/flavor-private.key -out keys/flavor-private.key.enc

   # Decrypt when needed (in CI/CD or deployment)
   openssl enc -d -aes-256-cbc -in keys/flavor-private.key.enc -out keys/flavor-private.key
   chmod 600 keys/flavor-private.key
   ```

2. **Secret Management**
   - Store private key in secret manager (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Retrieve at build time via environment variables or secret injection
   - Never commit private keys to version control

#### CI/CD

{% raw %}
```yaml
# GitHub Actions with secrets
- name: Sign package
  env:
    FLAVOR_KEY_SEED: ${{ secrets.SIGNING_SEED }}
  run: |
    flavor pack --manifest pyproject.toml --key-seed "$FLAVOR_KEY_SEED"
```
{% endraw %}

```yaml
# GitLab CI with protected variables
sign:
  script:
    - flavor pack --manifest pyproject.toml --key-seed "$CI_SIGNING_SEED"
  only:
    - tags
```

### Key Rotation

Implement regular key rotation by rebuilding packages with new keys:

```bash
# Generate new key
flavor keygen --out-dir keys/2024-01

# Rebuild packages with new key
for manifest in projects/*/pyproject.toml; do
  flavor pack --manifest "$manifest" \
    --private-key keys/2024-01/flavor-private.key \
    --public-key keys/2024-01/flavor-public.key
done

# Archive old key
mv keys/2023-12 keys/archive/
```

## Signing Process

### How Signing Works

1. **Metadata Hash**: Package metadata is serialized and hashed with SHA-256
2. **Digital Signature**: Hash is signed with Ed25519 private key
3. **Embedding**: Public key and signature are embedded in package index block
4. **Verification**: Signature can be verified using embedded or external public key

### Build-Time Signing

All signing happens during package build with `flavor pack`:

```bash
# Basic signing with key files
flavor pack --manifest pyproject.toml \
  --private-key keys/flavor-private.key \
  --public-key keys/flavor-public.key

# With deterministic seed (for reproducible builds)
flavor pack --manifest pyproject.toml --key-seed "secret-seed"

# Signing is automatic - no separate sign command needed
```

!!! note "No Post-Build Signing"
    FlavorPack does not support signing packages after they've been built. Signing happens only during `flavor pack`. To re-sign a package, rebuild it with new keys.

### Batch Building with Signing

Build and sign multiple packages:

```bash
#!/bin/bash
# build-and-sign-all.sh

PRIVATE_KEY="$1"
PUBLIC_KEY="$2"

for manifest in projects/*/pyproject.toml; do
  echo "Building and signing $manifest..."
  flavor pack --manifest "$manifest" \
    --private-key "$PRIVATE_KEY" \
    --public-key "$PUBLIC_KEY"
done
```

## Verification

### Automatic Verification

Packages are automatically verified when executed:

```bash
# Launcher verifies signature before extraction
./myapp.psp

# Disable verification (DANGEROUS - development only!)
FLAVOR_VALIDATION=none ./myapp.psp
```

### Manual Verification

#### Basic Verification

```bash
# Verify with embedded public key
flavor verify package.psp

# Output:
# ✅ Signature valid
# Package: myapp v1.0.0
# Signed by: SHA256:abc123...
```

#### Deep Verification

> **Planned Feature**: Advanced verification modes are planned for a future release. Currently, the `verify` command performs comprehensive verification of all components.

```bash
# Verify all components (standard verification)
flavor verify package.psp

# Output:
# ✅ Index block valid
# ✅ Metadata signature valid
# ✅ All slot checksums valid
# ✅ Package integrity confirmed
```

#### Verification with External Key

!!! info "📋 Planned Feature"
    External key verification is planned for a future release. Currently, verification uses the public key embedded in the package.

**Current verification:**
```bash
# Verify with embedded public key
flavor verify package.psp
```

**Planned verification (future release):**
```bash
# Verify against external trusted key (not yet implemented)
flavor verify package.psp --public-key trusted.pub
flavor verify package.psp --trusted-keys keys/trusted/
```

### Programmatic Verification

```python
from pathlib import Path
from flavor.package import verify_package

# Verify package
result = verify_package(Path("package.psp"))

if result["signature_valid"]:
    print("✅ Package signature verified")
else:
    print("❌ Invalid signature!")
```

## Trust Models

### 1. Self-Signed (Default)

Package contains its own public key:

```toml
[tool.flavor.security]
trust_model = "self-signed"
```

**Use Cases**:
- Internal distribution
- Development packages
- Personal projects

**Verification**:
```bash
# Verifies integrity only
flavor verify package.psp
```

### 2. Pre-Shared Keys

!!! info "📋 Planned Feature"
    Pre-shared key verification with external key management is planned for a future release.

Distribute public keys separately:

```toml
# Planned configuration format
[tool.flavor.security]
trust_model = "pre-shared"
require_known_key = true
```

**Planned Distribution Methods**:
```bash
# Via secure channel
scp public.pem user@server:/etc/flavor/trusted-keys/

# Via configuration management
ansible-playbook deploy-keys.yml

# Via package manager
apt-get install myapp-signing-keys
```

**Current Verification**:
```bash
# Currently: Verify with embedded public key
flavor verify package.psp
```

**Planned Verification**:
```bash
# Future: Verify against trusted keys
# flavor verify package.psp --trusted-keys /etc/flavor/trusted-keys/
```

### 3. Web of Trust (Future)

!!! info "Planned Feature"
    Multiple signatures from trusted parties is planned for a future release.

    **Planned workflow:**
    ```bash
    # Sign with multiple keys (not yet implemented)
    flavor pack --manifest pyproject.toml --private-key key1.pem
    flavor cosign package.psp --private-key key2.pem
    flavor cosign package.psp --private-key key3.pem

    # Verify requires threshold
    flavor verify package.psp --min-signatures 2
    ```

### 4. Certificate Authority (Future)

X.509 certificate chains:

```toml
[tool.flavor.security]
trust_model = "pki"
ca_bundle = "/etc/ssl/certs/ca-certificates.crt"
```

## Key Distribution

### Public Key Format

FlavorPack generates keys in PEM format:

```bash
# Generate keys
flavor keygen --out-dir keys

# Public key is in PEM format
cat keys/flavor-public.key
# -----BEGIN PUBLIC KEY-----
# ...
# -----END PUBLIC KEY-----
```

!!! info "Key Format Conversion"
    For other formats (SSH, JWK, etc.), use standard tools like `ssh-keygen` or `openssl` to convert the PEM-formatted public key.

### Distribution Channels

#### 1. Package Metadata

The public key is automatically embedded in every signed package's index block. Recipients can extract it for verification:

```bash
# Inspect package to see embedded public key
flavor inspect package.psp
```

#### 2. Key Servers

```bash
# Upload to key server
curl -X POST https://keys.example.com/upload \
  -F "key=@public.pem" \
  -F "email=team@example.com"
```

#### 3. DNS Records

```bash
# TXT record with public key
_flavor.example.com. IN TXT "ed25519-key:BASE64_PUBLIC_KEY"
```

#### 4. Version Control

```bash
# Commit public keys (never private!)
git add keys/public/*.pem
git commit -m "Add signing public keys"
```

## Security Best Practices

### Do's ✅

1. **Generate keys on secure systems**
   ```bash
   # Use air-gapped machine for production keys
   flavor keygen --out-dir /secure/usb/prod-keys
   ```

2. **Use unique keys per environment**
   ```bash
   ~/.flavor/keys/
   ├── dev.pem       # Development
   ├── staging.pem   # Staging
   └── prod.pem      # Production
   ```

3. **Rotate keys regularly**
   ```bash
   # Quarterly rotation for production
   flavor keygen --out-dir "keys/$(date +%Y-Q%q)"
   ```

4. **Verify packages before distribution**
   ```bash
   # CI/CD verification step
   flavor verify dist/*.psp || exit 1
   ```

5. **Log signature verification**
   ```python
   import logging
   
   logger.info("Package verified", 
               package=package_path,
               key_fingerprint=fingerprint)
   ```

### Don'ts ❌

1. **Never commit private keys**
   ```bash
   # .gitignore
   *.pem
   !*.pem.pub
   ```

2. **Never share private keys**
   ```bash
   # Wrong: Shared key
   team-key.pem
   
   # Right: Individual keys
   alice-key.pem
   bob-key.pem
   ```

3. **Never use weak seeds**
   ```bash
   # Bad seeds:
   "password123"
   "company-name"
   
   # Good seeds:
   "$(openssl rand -hex 32)"
   ```

4. **Never ignore verification failures**
   ```python
   # Wrong:
   try:
       verify_package(package)
   except:
       pass  # Never do this!
   
   # Right:
   if not verify_package(package):
       raise SecurityError("Invalid signature")
   ```

## Troubleshooting

### Common Issues

#### "Private key not found"

```bash
# Check file exists and permissions
ls -la private.pem
# Should show: -rw------- (600)

# Fix permissions
chmod 600 private.pem
```

#### "Invalid signature"

```bash
# Verify package
flavor verify package.psp

# Check package integrity with checksum
sha256sum package.psp

# If corrupted, rebuild the package with correct keys
flavor pack --manifest pyproject.toml \
  --private-key keys/flavor-private.key \
  --public-key keys/flavor-public.key
```

#### "Key format not recognized"

```bash
# Convert to PEM format
openssl pkey -in key.der -inform DER -out key.pem

# Verify key type
openssl pkey -in key.pem -text | head -1
# Should show: "ED25519 Private-Key"
```

### Debugging

```bash
# Verbose verification
FOUNDATION_LOG_LEVEL=debug flavor verify package.psp

# Inspect signature details
flavor inspect package.psp

# The inspect command shows:
# - Package signature status
# - Embedded public key (first 16 bytes)
# - Format version and metadata
```

## Advanced Topics (Future Features)

The following features are planned for future releases:

### Multi-Signature Packages (Planned)

!!! info "Future Feature"
    Support for multiple signatures per package is under development.

    **Planned API:**
    ```python
    # Sign with multiple keys (not yet implemented)
    from flavor.signing import multi_sign

    multi_sign("package.psp", [
        "key1.pem",
        "key2.pem",
        "key3.pem"
    ])
    ```

### Threshold Signatures (Planned)

!!! info "Future Feature"
    Threshold signature schemes (N-of-M signatures required) are planned.

    **Planned manifest format:**
    ```toml
    [tool.flavor.security.multisig]
    required_signatures = 2
    total_signers = 3
    ```

### Hardware Token Integration (Planned)

!!! info "Future Feature"
    PKCS#11 hardware token support (YubiKey, HSM, etc.) is planned.

    **Planned workflow:**
    ```bash
    # YubiKey signing (not yet implemented)
    flavor pack --manifest pyproject.toml --pkcs11-module /usr/lib/opensc-pkcs11.so
    ```

### Notarization (Platform-Specific)

!!! info "Platform-Specific"
    For macOS code signing and notarization, use Apple's standard tools after building:

    ```bash
    # Build package
    flavor pack --manifest pyproject.toml --output myapp.psp

    # Sign with codesign (macOS only)
    codesign --sign "Developer ID" myapp.psp

    # Notarize with Apple (macOS only)
    xcrun notarytool submit myapp.psp \
      --apple-id "developer@example.com" \
      --team-id "TEAMID"
    ```

## Related Documentation

- [Cryptographic Specification](../../reference/spec/pspf-2025/) - Technical details
- [Security Model](../concepts/security/) - Security architecture
- [Package Verification](../../api/index/) - API reference
- [Troubleshooting](../../troubleshooting/index/#signature-and-security) - Common issues
