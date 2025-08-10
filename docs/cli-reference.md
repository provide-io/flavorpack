# CLI Reference

Complete reference for all Flavor command-line tools.

## 📦 flavor-packager

The main packaging tool for creating, verifying, and managing Flavor packages.

### Global Options

```bash
flavor-packager [OPTIONS] <COMMAND>
```

**Global Options:**
- `--help, -h` - Show help information
- `--version, -V` - Show version information

### Commands Overview

| Command | Purpose | 
|---------|---------|
| [`keygen`](#keygen) | Generate ECDSA key pairs for signing |
| [`build`](#build) | Build a Flavor package from components |
| [`verify`](#verify) | Verify package integrity and signatures |
| [`info`](#info) | Display package information |

---

### `keygen`

Generate ECDSA P-256 key pair for Flavor package signing.

```bash
flavor-packager keygen --out-dir <DIRECTORY>
```

**Arguments:**
- `--out-dir <DIR>` - Directory to store generated keys (required)

**Examples:**
```bash
# Generate keys in current directory
flavor-packager keygen --out-dir ./keys

# Generate keys in home directory
flavor-packager keygen --out-dir ~/.flavor/keys

# Generate keys with specific names (advanced)
mkdir ./signing-keys
flavor-packager keygen --out-dir ./signing-keys
# Creates: provider-private.key, provider-public.key
```

**Output Files:**
- `provider-private.key` - ECDSA private key (PEM format)
- `provider-public.key` - ECDSA public key (PEM format)

**Security Notes:**
- Private keys are created with 600 permissions (owner read/write only)
- Never commit private keys to version control
- Store private keys securely (consider using a key management system)

---

### `build`

Build a Flavor package from component parts.

```bash
flavor-packager build [OPTIONS]
```

**Required Options:**
- `--out <PATH>` - Output path for the Flavor file
- `--payload-dir <DIR>` - Directory containing the provider payload  
- `--package-key <PATH>` - Path to the private key for signing
- `--public-key <PATH>` - Path to the public key for verification
- `--launcher-bin <PATH>` - Path to the flavor-launcher binary

**Examples:**

**Basic Usage:**
```bash
flavor-packager build \
  --out my-provider \
  --payload-dir ./src \
  --package-key ./keys/provider-private.key \
  --public-key ./keys/provider-public.key \
  --launcher-bin $(which flavor-launcher)
```

**Production Build:**
```bash
flavor-packager build \
  --out ./dist/terraform-provider-mycompany_v1.2.3 \
  --payload-dir ./build/provider \
  --package-key "$SIGNING_KEY_PATH" \
  --public-key ./keys/provider-public.key \
  --launcher-bin ./bin/flavor-launcher
```

**CI/CD Build:**
```bash
# Using environment variables
export PSPF_PACKAGE_KEY="$CI_SIGNING_KEY"
export PSPF_PUBLIC_KEY="$CI_PUBLIC_KEY"

flavor-packager build \
  --out "./dist/provider_${VERSION}_${PLATFORM}" \
  --payload-dir ./payload \
  --package-key "$PSPF_PACKAGE_KEY" \
  --public-key "$PSPF_PUBLIC_KEY" \
  --launcher-bin ./launchers/flavor-launcher-${PLATFORM}
```

**Build Process:**
1. Validates input files and directories
2. Creates compressed payload archive
3. Generates cryptographic signature
4. Combines launcher + payload + signature + metadata
5. Outputs single executable Flavor file

---

### `verify`

Verify the integrity and signature of a Flavor file.

```bash
flavor-packager verify <PSPF_FILE>
```

**Arguments:**
- `<PSPF_FILE>` - Path to the Flavor file to verify (required)

**Examples:**

**Basic Verification:**
```bash
flavor-packager verify ./my-provider
```

**Batch Verification:**
```bash
# Verify all packages in a directory
for package in ./dist/*; do
  echo "Verifying $package..."
  flavor-packager verify "$package"
done
```

**CI/CD Verification:**
```bash
# Verify before deployment
if flavor-packager verify "./dist/provider_${VERSION}"; then
  echo "✅ Package verified - safe to deploy"
  ./deploy.sh
else
  echo "❌ Package verification failed - aborting"
  exit 1
fi
```

**Verification Process:**
1. Validates Flavor footer format and magic numbers
2. Verifies footer checksum integrity  
3. Extracts and validates public key
4. Verifies ECDSA signature against payload
5. Reports overall package trust status

**Output:**
```
✅ Footer read and checksum verified
✅ Public key parsed successfully
✅ Package signature is valid
✅ Flavor file is valid and trusted
```

---

### `info`

Display detailed information about a Flavor package.

```bash
flavor-packager info <PSPF_FILE>
```

**Arguments:**
- `<PSPF_FILE>` - Path to the Flavor file to inspect (required)

**Examples:**
```bash
# Show package information
flavor-packager info ./my-provider

# Show info for multiple packages
flavor-packager info ./dist/*
```

**Sample Output:**
```
📦 Flavor Package Information
==========================
File: ./my-provider
Size: 45.2 MB

📋 Package Details:
  Flavor Version: 1.0
  Footer Magic: ✅ Valid (0x50535030)
  Footer Checksum: ✅ Valid

📊 Component Sizes:
  Launcher Binary: 1.4 MB
  Python Runtime: 25.8 MB  
  Provider Payload: 15.2 MB
  Signature: 256 bytes
  Public Key: 178 bytes
  Metadata: 1.1 KB

🔒 Security Info:
  Signature Algorithm: ECDSA P-256
  Signature Valid: ✅ Yes
  Public Key Fingerprint: sha256:abc123...
  
⚡ Performance:
  Estimated startup: ~500ms
  Payload compression: 65%
```

---

## 🚀 flavor-launcher

The runtime launcher that extracts and executes Flavor packages.

> **Note:** The launcher is typically embedded in packages and not used directly. These commands are for debugging and development.

### Usage

```bash
flavor-launcher [OPTIONS]
```

**Options:**
- `--help, -h` - Show help information
- `--version, -V` - Show version information
- `--force-extract` - Force re-extraction even if cache exists
- `--cache-dir <DIR>` - Override default cache directory
- `--verbose, -v` - Enable verbose logging
- `--dry-run` - Show what would be extracted without running

**Examples:**

**Debug Package Extraction:**
```bash
# Force re-extract and show verbose output
./my-provider-package --force-extract --verbose

# Use custom cache directory
./my-provider-package --cache-dir /tmp/flavor-cache

# Dry run to see extraction plan
./my-provider-package --dry-run
```

**Cache Management:**
```bash
# Check cache status
flavor-launcher --cache-dir ~/.cache/flavor --verbose

# Clear cache for fresh extraction
rm -rf ~/.cache/flavor/*/
```

---

## 🌍 Environment Variables

Flavor tools respect these environment variables:

### Build Environment
- `PSPF_PACKAGE_KEY` - Default private key path for signing
- `PSPF_PUBLIC_KEY` - Default public key path  
- `PSPF_LAUNCHER_BIN` - Default launcher binary path
- `PSPF_CACHE_DIR` - Default cache directory

### Runtime Environment  
- `PSPF_LOG_LEVEL` - Logging level (`TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`)
- `PSPF_CACHE_DIR` - Cache directory for extracted packages
- `PSPF_FORCE_EXTRACT` - Force extraction (set to `1` or `true`)

### Examples:
```bash
# Set up build environment
export PSPF_PACKAGE_KEY=~/.flavor/keys/private.key
export PSPF_PUBLIC_KEY=~/.flavor/keys/public.key
export PSPF_LAUNCHER_BIN=$(which flavor-launcher)

# Simplified build command
flavor-packager build --out my-provider --payload-dir ./src

# Debug runtime
export PSPF_LOG_LEVEL=DEBUG
export PSPF_FORCE_EXTRACT=1
./my-provider-package
```

---

## 🔧 Exit Codes

Flavor tools use standard exit codes:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments |
| `3` | File not found |
| `4` | Permission denied |  
| `5` | Verification failed |
| `6` | Signature invalid |
| `7` | Format error |

**Usage in Scripts:**
```bash
#!/bin/bash
set -e  # Exit on error

if ! flavor-packager verify ./my-provider; then
    case $? in
        5|6) echo "❌ Security verification failed" ;;
        7)   echo "❌ Package format corrupted" ;;
        *)   echo "❌ Unknown verification error" ;;
    esac
    exit 1
fi

echo "✅ Package verified successfully"
```

---

## 🐛 Debugging and Troubleshooting

### Verbose Output
Enable detailed logging for troubleshooting:

```bash
# For building
PSPF_LOG_LEVEL=DEBUG flavor-packager build ...

# For runtime
PSPF_LOG_LEVEL=TRACE ./my-provider-package --verbose
```

### Common Issues

**"Package verification failed":**
```bash
# Check if package is corrupted
flavor-packager info ./my-provider

# Verify with specific key
flavor-packager verify ./my-provider
```

**"Permission denied":**
```bash
# Fix permissions
chmod +x ./my-provider-package

# Check ownership
ls -la ./my-provider-package
```

**"Cache extraction errors":**
```bash
# Clear cache and retry
rm -rf ~/.cache/flavor/
./my-provider-package --force-extract
```

### Performance Profiling

```bash
# Time package operations
time flavor-packager build ...
time flavor-packager verify ...
time ./my-provider-package --dry-run
```

---

**Need more help?** 👉 [Troubleshooting Guide](./troubleshooting.md) | [FAQ](./faq.md) | [Examples](./examples/)