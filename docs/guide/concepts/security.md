# Security Model

FlavorPack implements multiple layers of security to ensure package integrity, authenticity, and safe execution.

## Overview

The FlavorPack security model provides comprehensive protection through multiple layers:

```mermaid
graph TD
    A[Package Build] --> B[Sign with Ed25519]
    B --> C[Package Distribution]
    C --> D[User Downloads]

    D --> E{Verify Signature}
    E -->|Invalid| F[❌ Reject Package]
    E -->|Valid| G{Verify Checksums}

    G -->|Invalid| F
    G -->|Valid| H{Verify Format}

    H -->|Invalid| F
    H -->|Valid| I[✅ Extract to Cache]

    I --> J{Validate Extraction}
    J -->|Failed| F
    J -->|Success| K[🚀 Execute Package]

    style B fill:#e8f5e9
    style E fill:#fff3e0
    style G fill:#fff3e0
    style H fill:#fff3e0
    style F fill:#ffebee
    style K fill:#e3f2fd
```

### Security Layers

1. **Cryptographic Signatures**: Ed25519 digital signatures for authenticity
2. **Integrity Verification**: SHA-256 checksums for all components
3. **Format Validation**: PSPF structure verification
4. **Isolation**: Sandboxed execution environments
5. **Access Control**: Permission-based slot extraction
6. **Audit Trail**: Comprehensive logging and verification

## Threat Model

### Protected Against

FlavorPack's security model defends against:

| Threat | Protection |
|--------|------------|
| **Package Tampering** | Ed25519 signatures detect modification |
| **Supply Chain Attacks** | Signature verification ensures authenticity |
| **Data Corruption** | SHA-256 checksums validate integrity |
| **Path Traversal** | Sanitized extraction paths |
| **Code Injection** | No dynamic code generation |
| **Privilege Escalation** | Restricted permissions |

### Out of Scope

FlavorPack does not protect against:

- Malicious code in legitimate packages
- Compromised signing keys
- Operating system vulnerabilities
- Network-based attacks during download
- Side-channel attacks

## Cryptographic Security

### Ed25519 Signatures

Every package is signed with Ed25519:

```python
# Key generation
from cryptography.hazmat.primitives.asymmetric import ed25519

private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Signing
signature = private_key.sign(package_hash)

# Verification
try:
    public_key.verify(signature, package_hash)
    print("✅ Signature valid")
except InvalidSignature:
    print("❌ Signature invalid - package tampered!")
```

### Key Management

#### Key Generation Options

1. **Random Keys** (Recommended for production)
   ```bash
   flavor keygen --out-dir keys/
   ```

2. **Deterministic Keys** (For CI/CD)
   ```bash
   flavor pack --key-seed "$SECRET_SEED"
   ```

3. **External Keys** (Enterprise)
   ```bash
   flavor pack --private-key /secure/private.pem
   ```

#### Key Storage Best Practices

- **Never commit private keys** to version control
- **Use hardware security modules** (HSM) when available
- **Rotate keys periodically** (yearly recommended)
- **Separate keys by environment** (dev/staging/prod)
- **Backup keys securely** with encryption

### Signature Verification

Verification happens automatically on package execution:

```python
def verify_package(package_path):
    """Verify package signature."""
    reader = PSPFReader(package_path)
    
    # Extract signature components
    index = reader.read_index()
    public_key = index.public_key
    signature = index.signature
    
    # Calculate metadata hash
    metadata = reader.read_metadata()
    metadata_hash = hashlib.sha256(metadata).digest()
    
    # Verify signature
    key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
    key.verify(signature, metadata_hash)
```

## Integrity Verification

### Checksum Validation

Every component has SHA-256 checksums:

| Component | Checksum Location | Validation |
|-----------|------------------|------------|
| **Index Block** | Magic trailer | CRC32 |
| **Metadata** | Index block | SHA-256 |
| **Slots** | Metadata JSON | SHA-256 |
| **Extracted Files** | Cache manifest | SHA-256 |

### Verification Levels

#### ✅ Currently Available

```bash
# Standard verification (index + metadata + signatures)
flavor verify package.psp
```

The verify command performs comprehensive validation:
- Validates PSPF format structure
- Verifies index block integrity
- Checks metadata consistency
- Validates Ed25519 signature
- Reports any integrity issues

#### 📋 Planned Verification Modes

Additional verification levels are planned for future releases:

```bash
# Coming in future versions
flavor verify package.psp --quick     # Quick (index only)
flavor verify package.psp --deep      # Deep (all slots)
flavor verify package.psp --paranoid  # Paranoid (extract and verify)
```

## Execution Security

### Work Environment Isolation

Each package runs in an isolated directory:

```python
# Unique work environment per package
work_dir = cache_dir / generate_package_id(metadata)

# Restricted file access
os.chdir(work_dir)
# Package cannot access parent directories
```

### Permission Enforcement

Slot extraction respects file permissions:

```python
def extract_with_permissions(slot, target):
    """Extract slot with secure permissions."""
    # Extract content
    extract_slot(slot, target)
    
    # Apply permissions
    permissions = slot.get("permissions", "0644")
    os.chmod(target, int(permissions, 8))
    
    # Validate no setuid/setgid
    if os.stat(target).st_mode & (stat.S_ISUID | stat.S_ISGID):
        raise SecurityError("Setuid/setgid not allowed")
```

### Path Traversal Prevention

All paths are sanitized:

```python
def safe_path(base, user_path):
    """Prevent path traversal attacks."""
    # Resolve to absolute path
    full_path = (base / user_path).resolve()
    
    # Ensure within base directory
    if not full_path.is_relative_to(base):
        raise SecurityError(f"Path traversal detected: {user_path}")
    
    return full_path
```

## Trust Models

### Self-Signed Packages

Default mode for internal distribution:

```yaml
# Package contains its own public key
trust_model: self-signed
verification: integrity_only
use_case: internal_tools
```

### Pre-Shared Keys

For controlled environments:

```yaml
# Public key distributed separately
trust_model: pre-shared
verification: authenticity
use_case: enterprise_deployment
```

### 📋 Certificate-Based (Planned Feature)

PKI integration is planned for future releases to support public distribution:

```yaml
# X.509 certificate chains (not yet implemented)
trust_model: pki
verification: chain_of_trust
use_case: public_distribution
```

This will enable integration with existing PKI infrastructure and code signing certificates for broader distribution scenarios.

## Security Configuration

### Environment Variables

```bash
# Validation level (testing only)
FLAVOR_VALIDATION=none          # Skip verification (DANGER! Never use in production)

# Logging
FLAVOR_LOG_LEVEL=debug          # Verbose security logging
FOUNDATION_LOG_LEVEL=debug      # Python component logging
```

!!! warning "Security Configuration"
    For signature verification configuration, use CLI flags (`--private-key`, `--public-key`, `--key-seed`) rather than environment variables. See the [Environment Variables Guide](../../guide/usage/environment/) for the complete list of available variables.

### Configuration File

!!! info "📋 Planned Feature - Not Yet Implemented"
    Configuration file support is planned for a future release. Currently, all configuration is done via environment variables and CLI flags.

#### Current Configuration Methods

Use environment variables for configuration:

```bash
# Security settings
export FLAVOR_VALIDATION=none          # Skip verification (TESTING ONLY)

# Logging
export FLAVOR_LOG_LEVEL=debug
export FOUNDATION_LOG_LEVEL=debug

# Cache location
export FLAVOR_CACHE=/custom/cache
```

#### Planned Configuration File Format

Future releases will support a configuration file:

```toml
# ~/.flavor/config.toml (not yet supported - planned feature)
[security]
verify_signatures = true
require_https = true
allowed_key_fingerprints = [
    "abc123...",
    "def456..."
]

[audit]
log_file = "/var/log/flavor-audit.log"
log_verification = true
log_extraction = true
```

## Audit Logging

### Security Events

All security-relevant events are logged:

```python
import logging
from provide.foundation.logger import logger

# Signature verification
logger.info("security.verification", 
    package=package_path,
    signature_valid=True,
    public_key_fingerprint=fingerprint
)

# Failed verification
logger.error("security.verification.failed",
    package=package_path,
    reason="Invalid signature",
    public_key_fingerprint=fingerprint
)

# Extraction
logger.info("security.extraction",
    package=package_path,
    slot=slot_id,
    target=target_path,
    permissions=permissions
)
```

### Audit Trail Format

```json
{
  "timestamp": "2025-01-07T10:30:15Z",
  "event": "security.verification",
  "level": "info",
  "package": "/path/to/package.psp",
  "signature_valid": true,
  "public_key_fingerprint": "SHA256:abc123...",
  "metadata_hash": "def456...",
  "user": "username",
  "pid": 12345
}
```

## Security Best Practices

### For Package Creators

1. **Sign all production packages**
   ```bash
   flavor pack --private-key prod.pem manifest.toml
   ```

2. **Use deterministic builds**
   ```bash
   FLAVOR_DETERMINISTIC=1 flavor pack --manifest manifest.toml
   ```

3. **Verify after building**
   ```bash
   flavor verify package.psp
   ```

4. **Document security requirements**
   ```toml
   [tool.flavor.security]
   minimum_version = "0.3.0"
   required_capabilities = ["crypto", "isolation"]
   ```

### For Package Users

1. **Always verify packages**
   ```bash
   # Verify before running
   flavor verify package.psp
   ```

2. **Check key fingerprints**
   ```bash
   flavor inspect package.psp | grep "Public Key"
   ```

3. **Use audit logging**
   ```bash
   FLAVOR_AUDIT_LOG=audit.log ./package.psp
   ```

4. **Regular cache cleanup**
   ```bash
   flavor workenv clean --older-than 7
   ```

### For System Administrators

1. **Restrict execution**
   ```bash
   # AppArmor/SELinux policies
   aa-enforce /usr/local/bin/flavor
   ```

2. **Monitor audit logs**
   ```bash
   tail -f /var/log/flavor-audit.log | grep "failed"
   ```

3. **Manage allowed keys**
   ```bash
   # Whitelist specific keys
   export FLAVOR_ALLOWED_KEYS="fingerprint1,fingerprint2"
   ```

4. **Network isolation**
   ```bash
   # Firewall rules for package downloads
   iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT
   ```

## Vulnerability Reporting

### Responsible Disclosure

Report security issues to:
- Email: security@provide.io
- PGP Key: [public key]
- Response time: 48 hours

### Security Updates

Stay informed:
- Security advisories: GitHub Security tab
- Mailing list: flavor-security@provide.io
- RSS feed: /security/feed.xml

## Compliance

### Standards

FlavorPack follows:
- **NIST** cryptographic standards
- **OWASP** secure coding practices
- **CIS** benchmark configurations

### Certifications

Working towards:
- SOC 2 Type II
- ISO 27001
- FedRAMP authorization

## SBOM & Provenance

Every signed FlavorPack package includes a CycloneDX 1.6 Software Bill of Materials (SBOM) embedded in the attestation slot (slot 0). The SBOM lists the package name, version, build tools, and Python/Go/Rust dependencies captured at build time.

```bash
# Print the CycloneDX 1.6 SBOM JSON from a package
flavor inspect --sbom package.psp

# Print provenance JSON (builder version, build timestamp, target platform)
flavor inspect --provenance package.psp
```

The PSPF index field `attestation_sbom_digest` holds the raw SHA-256 of the attestation slot content. This digest is written at build time and re-verified at runtime, so the SBOM cannot be replaced without invalidating the package signature.

---

## Launch-Time Policy Enforcement

Execution policies restrict when and where a package may run. Policy checks are performed by the Go or Rust launcher before any payload code is extracted or executed.

**Enforcement sequence** (first failure aborts execution):

1. **Platform** — `OS_arch` of the current host must be in the package's `platforms` list (if set)
2. **Root/Admin** — if `refuse_root = true`, the launcher refuses to run as root on Unix or as Administrator on Windows
3. **Age** — the build timestamp embedded in the package must be no older than `max_age_days`
4. **Environment** — every name listed in `require_env` must resolve to a non-empty value in the current environment
5. **SBOM** — if the operator policy sets `require_sbom = true`, the package must contain an attestation slot

**Package policy vs. operator policy:**

A package embeds its own policy at build time. At runtime the launcher also reads the operator policy from disk (`/etc/flavor/policy.toml` or `~/.config/flavor/policy.toml`) and merges the two using the "stricter wins" rule:

| Field | Merge rule |
|-------|-----------|
| `refuse_root` | `package OR operator` |
| `max_age_days` | `min(package, operator)` |
| `platforms` | intersection of both lists |
| `require_env` | package list only |
| `require_sbom` | operator only |

---

## Operator Policy

System administrators and users can enforce site-wide or per-user constraints through a TOML policy file.

**File locations:**

| Scope | Path |
|-------|------|
| System | `/etc/flavor/policy.toml` |
| User | `~/.config/flavor/policy.toml` |

**File format:**

```toml
[trust]
require_trusted_key = true

[execution]
refuse_root = true
max_age_days = 180
allow_platforms = ["linux_amd64", "linux_arm64"]

[attestation]
require_sbom = true
```

Create a default policy file with:

```bash
# User-scoped policy
flavor policy init

# System-scoped policy (requires appropriate permissions)
flavor policy init --global

# Show the effective merged policy for the current environment
flavor policy show
```

---

## Attestation Index Fields

Three fields are written into the PSPF index block at build time and re-verified at runtime. They bind security metadata to the package in a tamper-evident way.

| Field | Type | Description |
|-------|------|-------------|
| `attestation_policy_hash` | 64-byte hex string | SHA-256 of the canonical policy JSON (`json.dumps(policy, sort_keys=True, separators=(",", ":"))`, hex-encoded). Lets launchers detect policy tampering. |
| `attestation_key_fp` | 32-byte field | First 32 bytes of the hex-encoded SHA-256 fingerprint of the signer's Ed25519 public key. Cross-referenced by `flavor trust verify`. |
| `attestation_sbom_digest` | 32 bytes (binary) | Raw SHA-256 of the attestation slot content. Verified by `flavor inspect --sbom`. |

These fields are set once at `flavor pack` time and are covered by the Ed25519 signature. Any post-build modification will cause `flavor verify` to fail.

!!! info "PKI / X.509 (Future)"
    Integration with X.509 certificate chains and external PKI infrastructure is not yet implemented. The `trust_model = "pki"` configuration shown in older documentation refers to a planned future capability.

---

## Related Documentation

- [Cryptographic Specification](../../reference/spec/pspf-2025/) - Technical crypto details
- [Package Format](../../reference/spec/fep-0001-core-format-and-operation-chains/) - Binary security features
- [CLI Reference](../../guide/usage/cli/#security-commands) - Security commands reference
- [Signing Guide](../packaging/signing/) - Key management and trusted key store
- [Configuration](../packaging/configuration/#execution-policy) - Execution policy configuration
- [Troubleshooting](../concepts/security/) - Security issues
