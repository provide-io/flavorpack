# Signing & Verification

Secure your FlavorPack packages with Ed25519 digital signatures for authenticity and integrity.

## Overview

FlavorPack uses Ed25519 digital signatures to ensure packages haven't been tampered with and come from trusted sources. This guide covers key generation, package signing, verification, and best practices for secure distribution.

## Quick Start

### Generate Keys

```bash
# Generate a new Ed25519 key pair
flavor keygen --output private.pem

# This creates:
# - private.pem (private key - keep secret!)
# - private.pem.pub (public key - distribute freely)
```

### Sign Package

```bash
# Sign during build
flavor pack pyproject.toml --private-key private.pem

# Package is now signed and can be verified
```

### Verify Package

```bash
# Verify signature (uses embedded public key)
flavor verify myapp-1.0.0.psp

# Verify with specific public key
flavor verify myapp-1.0.0.psp --public-key private.pem.pub
```

## Key Management

### Key Generation Options

#### 1. Random Keys (Recommended for Production)

Generate cryptographically secure random keys:

```bash
# Generate with default settings
flavor keygen

# Specify output file
flavor keygen --output mykey.pem

# Generate with metadata
flavor keygen --output prod.pem --comment "Production signing key"
```

#### 2. Deterministic Keys (For CI/CD)

Generate reproducible keys from a seed:

```bash
# Use seed for deterministic generation
flavor keygen --seed "my-secret-seed" --output ci.pem

# Or use environment variable
export FLAVOR_KEY_SEED="my-secret-seed"
flavor pack pyproject.toml
```

⚠️ **Warning**: Deterministic keys are only as secure as their seed. Use strong, unique seeds and keep them secret.

#### 3. Existing Keys

Import existing Ed25519 keys:

```bash
# Convert from OpenSSH format
ssh-keygen -f ~/.ssh/id_ed25519 -e -m PEM > private.pem

# Use existing PEM key
flavor pack pyproject.toml --private-key existing.pem
```

### Key Storage Best Practices

#### Development

```bash
# Store in home directory
mkdir -p ~/.flavor/keys
chmod 700 ~/.flavor/keys
flavor keygen --output ~/.flavor/keys/dev.pem
chmod 600 ~/.flavor/keys/dev.pem
```

#### Production

1. **Hardware Security Module (HSM)**
   ```bash
   # Use PKCS#11 interface
   flavor pack pyproject.toml --hsm-slot 0 --hsm-pin $PIN
   ```

2. **Key Management Service (KMS)**
   ```bash
   # AWS KMS example
   flavor pack pyproject.toml --kms-key-id "arn:aws:kms:..."
   ```

3. **Encrypted Storage**
   ```bash
   # Encrypt private key
   openssl enc -aes-256-cbc -salt -in private.pem -out private.pem.enc
   
   # Decrypt when needed
   openssl enc -d -aes-256-cbc -in private.pem.enc -out private.pem
   ```

#### CI/CD

```yaml
# GitHub Actions with secrets
- name: Sign package
  env:
    FLAVOR_KEY_SEED: ${{ secrets.SIGNING_SEED }}
  run: |
    flavor pack pyproject.toml --key-seed "$FLAVOR_KEY_SEED"

# GitLab CI with protected variables
sign:
  script:
    - flavor pack pyproject.toml --key-seed "$CI_SIGNING_SEED"
  only:
    - tags
```

### Key Rotation

Implement regular key rotation:

```bash
# Generate new key
flavor keygen --output keys/2024-01.pem

# Re-sign existing packages
for package in dist/*.psp; do
  flavor resign "$package" --private-key keys/2024-01.pem
done

# Archive old key
mv keys/2023-12.pem keys/archive/
```

## Signing Process

### How Signing Works

1. **Metadata Hash**: Package metadata is serialized and hashed with SHA-256
2. **Digital Signature**: Hash is signed with Ed25519 private key
3. **Embedding**: Public key and signature are embedded in package index block
4. **Verification**: Signature can be verified using embedded or external public key

### Build-Time Signing

Sign packages during build:

```bash
# Basic signing
flavor pack pyproject.toml --private-key private.pem

# With deterministic seed
flavor pack pyproject.toml --key-seed "secret-seed"

# With key from environment
export FLAVOR_PRIVATE_KEY_PATH=~/.flavor/keys/prod.pem
flavor pack pyproject.toml
```

### Post-Build Signing

Sign existing unsigned packages:

```bash
# Sign unsigned package
flavor sign unsigned.psp --private-key private.pem --output signed.psp

# Re-sign with new key
flavor resign signed.psp --private-key new-key.pem
```

### Batch Signing

Sign multiple packages:

```bash
#!/bin/bash
# sign-all.sh

KEY_FILE="$1"
for package in dist/*.psp; do
  echo "Signing $package..."
  flavor sign "$package" --private-key "$KEY_FILE" \
    --output "signed/$(basename $package)"
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

```bash
# Verify all components
flavor verify package.psp --deep

# Output:
# ✅ Index block valid
# ✅ Metadata signature valid
# ✅ All slot checksums valid
# ✅ Package integrity confirmed
```

#### Verification with External Key

```bash
# Verify with specific public key
flavor verify package.psp --public-key trusted.pub

# Verify against multiple trusted keys
flavor verify package.psp --trusted-keys keys/trusted/
```

### Programmatic Verification

```python
from flavor.verification import FlavorVerifier

# Verify package
verifier = FlavorVerifier()
result = verifier.verify_package("package.psp")

if result["signature_valid"]:
    print(f"✅ Package signed by {result['key_fingerprint']}")
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

Distribute public keys separately:

```toml
[tool.flavor.security]
trust_model = "pre-shared"
require_known_key = true
```

**Distribution Methods**:
```bash
# Via secure channel
scp public.pem user@server:/etc/flavor/trusted-keys/

# Via configuration management
ansible-playbook deploy-keys.yml

# Via package manager
apt-get install myapp-signing-keys
```

**Verification**:
```bash
# Must match known key
flavor verify package.psp --trusted-keys /etc/flavor/trusted-keys/
```

### 3. Web of Trust

Multiple signatures from trusted parties:

```bash
# Sign with multiple keys
flavor pack pyproject.toml --private-key key1.pem
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

### Public Key Formats

Export public keys in various formats:

```bash
# Raw binary (32 bytes)
flavor keygen --export-public raw > key.raw

# PEM format
flavor keygen --export-public pem > key.pem

# SSH format
flavor keygen --export-public ssh > key.pub

# JSON Web Key
flavor keygen --export-public jwk > key.json
```

### Distribution Channels

#### 1. Package Metadata

```bash
# Embed in package documentation
flavor pack pyproject.toml --embed-key-info
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
   flavor keygen --output /secure/usb/prod.pem
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
   flavor keygen --output "keys/$(date +%Y-Q%q).pem"
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
# Verify with correct key
flavor verify package.psp --public-key correct-key.pub

# Check package integrity
sha256sum package.psp

# Re-sign if corrupted
flavor resign package.psp --private-key private.pem
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
FLAVOR_LOG_LEVEL=debug flavor verify package.psp

# Inspect signature details
flavor inspect package.psp --show-signature

# Extract and examine public key
flavor extract-key package.psp > embedded.pub
openssl pkey -in embedded.pub -pubin -text
```

## Advanced Topics

### Multi-Signature Packages

```python
# Sign with multiple keys
from flavor.signing import multi_sign

multi_sign("package.psp", [
    "key1.pem",
    "key2.pem", 
    "key3.pem"
])
```

### Threshold Signatures

```toml
[tool.flavor.security.multisig]
required_signatures = 2
total_signers = 3
```

### Hardware Token Integration

```bash
# YubiKey signing
flavor pack pyproject.toml --pkcs11-module /usr/lib/opensc-pkcs11.so
```

### Notarization

```bash
# macOS notarization
xcrun altool --notarize-app \
  --primary-bundle-id "com.example.myapp" \
  --file package.psp
```

## Related Documentation

- [Cryptographic Specification](../../spec/crypto.md) - Technical details
- [Security Model](../../guide/concepts/security.md) - Security architecture
- [Package Verification](../../api/python/index.md#verify_package) - API reference
- [Troubleshooting](../../troubleshooting/index.md#signature-and-security) - Common issues
