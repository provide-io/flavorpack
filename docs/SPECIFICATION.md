# Progressive Secure Package Format (PSPF) Specification
## 2025 Edition

### Version: 2025.0
### Status: Implemented (Go/Rust/Python), Spec Updated 2025-08-17
### Date: 2025-08-17

---

## Changelog

### Version 2025.0 (2025-08-15)
- **BREAKING**: Renamed `EphemeralPublicKey` to `PublicKey` in index structure
- **BREAKING**: Metadata is now gzipped JSON (not tar.gz archive)
- Clarified that signature covers uncompressed JSON
- Added implementation requirements section
- Specified exact storage of checksums and signatures
- Documented cross-language compatibility requirements
- Initial specification release
- Implemented in Go and Rust

---

## 1. Introduction

The Progressive Secure Package Format (PSPF) 2025 Edition is a self-extracting, polyglot archive format designed for secure, language-agnostic software distribution. It combines the benefits of traditional executable formats with modern package management needs.

### 1.1 Design Principles

1. **Polyglot by Design**: Valid as both an OS executable and PSPF package
2. **Progressive Extraction**: Load only what's needed, when needed
3. **Language Agnostic**: No assumptions about payload content or runtime
4. **Secure by Default**: Ed25519 signature-based integrity sealing built-in
5. **Minimal Overhead**: Fixed 8192-byte index + 8-byte magic
6. **Future-Proof**: Extensible through metadata, not format changes

## 2. File Structure

### 2.1 Overall Layout

```
┌──────────────────────────────┐ Offset
│                              │ 0
│      Launcher Binary         │ Platform-specific executable
│                              │ Variable size
├──────────────────────────────┤ Launcher_Size
│      Index Block             │ Fixed 8192 bytes
│      (See Section 2.2)       │
├──────────────────────────────┤ Launcher_Size + 8192
│      Metadata (gzipped JSON) │ Compressed JSON metadata
│                              │ Variable size
├──────────────────────────────┤ Aligned to 8-byte boundary
│      Slot Table              │ Table of slot descriptors
│                              │ (64 bytes per slot)
├──────────────────────────────┤ Aligned to 8-byte boundary
│      Slot 0                  │ First slot data
├──────────────────────────────┤ Aligned to 8-byte boundary
│      Slot 1                  │ Second slot data
├──────────────────────────────┤
│      ...                     │
├──────────────────────────────┤ Aligned to 8-byte boundary
│      Slot N                  │ Last slot data
├──────────────────────────────┤
│      Padding (if needed)     │ Zero bytes for alignment
├──────────────────────────────┤ EOF - 8
│      Emoji Magic             │ 📦🪄 (exactly 8 bytes)
└──────────────────────────────┘ EOF
```

**Performance Note**: The slot table is positioned immediately after metadata and BEFORE the actual slot data. This allows readers to:
1. Read the index to get metadata and slot table offsets
2. Read both metadata and slot table (small, sequential reads)
3. Know exact locations of all slots without seeking to end of file
4. Directly seek to any slot for random access

### 2.2 Index Block Structure (8192 bytes)

This structure reflects the current Go and Rust implementations, which are the canonical source of truth.

```go
// PSPFIndex represents the PSPF 2025 index block (8192 bytes)
type PSPFIndex struct {
    // Core identification (16 bytes)
    FormatMagic       [8]byte  // "PSPF2025"
    FormatVersion     uint32   // 0x20250001
    IndexChecksum     uint32   // Adler-32 of index block (with this field as 0)
    
    // File structure (48 bytes)
    PackageSize       uint64   // Total file size
    LauncherSize      uint64   // Size of launcher binary
    MetadataOffset    uint64   // Offset to metadata archive
    MetadataSize      uint64   // Size of metadata archive
    SlotTableOffset   uint64   // Offset to slot table
    SlotTableSize     uint64   // Size of slot table
    
    // Slot information (8 bytes)
    SlotCount         uint32   // Number of slots
    Flags             uint32   // Feature flags
    
    // Security (576 bytes)
    PublicKey          [32]byte  // Ed25519 public key for signature verification
    MetadataChecksum   [32]byte  // Adler-32 of compressed metadata (first 4 bytes, rest zeros)
    IntegritySignature [512]byte // Ed25519 signature of uncompressed JSON (first 64 bytes, rest zeros)
    
    // Performance hints (64 bytes)
    AccessMode        uint8    // 0=auto, 1=mmap, 2=file, 3=stream
    CacheStrategy     uint8    // 0=none, 1=lazy, 2=eager, 3=critical
    CompressionType   uint8    // 0=none, 1=gzip, 2=zstd, 3=brotli
    EncryptionType    uint8    // 0=none, 1=aes256-gcm, 2=chacha20
    PageSize          uint32   // Optimal page size for alignment
    MaxMemory         uint64   // Suggested maximum memory usage
    MinMemory         uint64   // Minimum required memory
    CpuFeatures       uint64   // Required CPU features (bit flags)
    GpuRequirements   uint64   // GPU requirements (bit flags)
    NumaHints         uint64   // NUMA topology hints
    StreamChunkSize   uint32   // Optimal streaming chunk size
    Padding1          [12]byte // Alignment padding
    
    // Extended metadata (128 bytes)
    BuildTimestamp    uint64   // Unix timestamp of build
    BuildMachine      [32]byte // Build machine identifier
    SourceHash        [32]byte // Hash of source code/inputs
    DependencyHash    [32]byte // Hash of all dependencies
    LicenseID         [16]byte // SPDX license identifier
    ProvenanceURI     [8]byte  // Short URI to provenance data
    
    // Capabilities (32 bytes)
    Capabilities      uint64   // What this package can do
    Requirements      uint64   // What this package needs
    Extensions        uint64   // Extended features
    Compatibility     uint32   // Minimum reader version
    ProtocolVersion   uint32   // Protocol version for negotiation
    
    // Future cryptography space (512 bytes)
    // Reserved for post-quantum signatures and additional algorithms
    FutureCrypto      [512]byte
    
    // Reserved for future use (6808 bytes)
    // This large reserved space ensures we never need to change
    // the index size again, even with post-quantum cryptography
    Reserved          [6808]byte
}
```

### 2.3 Emoji Magic Structure (8 bytes)

The bundle MUST end with exactly 2 UTF-8 encoded emojis:

| Position | Bytes | Emoji | Purpose |
|----------|-------|--------|---------|
| EOF-8    | 4     | 📦     | Package emoji |
| EOF-4    | 4     | 🪄     | Magic wand emoji |

This magic footer:
- Provides clear visual identification of PSPF files
- Is consistent across all implementations
- Uses exactly 8 bytes (4 bytes per emoji in UTF-8)

## 3. Metadata Specification

The metadata MUST be gzip-compressed JSON data. The signature and public key are stored in the index block, not embedded in the metadata.

**Key points:**
- Metadata is pure JSON (no tar archive)
- Stored compressed with gzip
- Signature covers the uncompressed JSON
- Public key and signature are in the index block

### 3.1 Metadata JSON Schema

```json
{
  "$schema": "https://pspf.io/schemas/2025/psp.json",
  "format": "PSPF/2025",
  "package": {
    "name": "string (required)",
    "version": "string (required)"
  },
  "slots": [
    {
      "index": "number (0-based)",
      "name": "string",
      "size": "number (bytes)",
      "checksum": "string (adler32 or sha256:hex)",
      "encoding": "none|gzip|zstd|brotli",
      "purpose": "payload|runtime|config|asset|library|binary|installer|data",
      "lifecycle": "runtime|init|startup|shutdown|cache|temp|lazy|eager|dev|config|platform|volatile",
      "extract_to": "string (optional, custom extraction path)",
      "platform": "string (optional, platform-specific slot)"
    }
  ],
  "execution": {
    "primary_slot": "number (index of primary executable slot)",
    "command": "string with {workenv} substitutions",
    "env": {
      "KEY": "value"
    }
  },
  "runtime": {
    "env": {
      "set": {"KEY": "value"},
      "unset": ["KEY"],
      "pass": ["KEY"],
      "map": {"OLD_KEY": "NEW_KEY"}
    }
  },
  "workenv": {
    "directories": [
      {
        "path": "tmp",
        "mode": "0700"
      },
      {
        "path": "var",
        "mode": "0755"
      },
      {
        "path": "var/log",
        "mode": "0755"
      },
      {
        "path": "var/cache",
        "mode": "0755"
      },
      {
        "path": "var/run",
        "mode": "0755"
      }
    ],
    "env": {
      "TMPDIR": "{workenv}/tmp",
      "TMP": "{workenv}/tmp",
      "TEMP": "{workenv}/tmp",
      "XDG_RUNTIME_DIR": "{workenv}/var/run",
      "XDG_CACHE_HOME": "{workenv}/var/cache",
      "XDG_DATA_HOME": "{workenv}/var",
      "XDG_STATE_HOME": "{workenv}/var"
    }
  },
  "setup_commands": [
    {
      "type": "execute|enumerate_and_execute|write_file",
      "command": "string (for execute/enumerate)",
      "enumerate": {
        "path": "string",
        "pattern": "string"
      },
      "path": "string (for write_file)",
      "content": "string (for write_file)"
    }
  ],
  "cache_validation": {
    "check_file": "{workenv}/validation_marker",
    "expected_content": "string"
  },
  "verification": {
    "integrity_seal": {
      "required": true,
      "algorithm": "ed25519"
    },
    "signed": true,
    "require_verification": true,
    "trust_signatures": ["optional array of trusted signature fingerprints"]
  },
  "build": {
    "tool": "string (e.g., flavor-python, flavor-go, flavor-rust)",
    "tool_version": "string",
    "timestamp": "ISO8601",
    "deterministic": "boolean",
    "platform": {
      "os": "string (darwin, linux, windows)",
      "arch": "string (arm64, amd64, x86_64)",
      "host": "string (hostname)"
    }
  },
  "launcher": {
    "tool": "string (e.g., flavor-rs-launcher, flavor-go-launcher)",
    "tool_version": "string",
    "size": "number (bytes)",
    "checksum": "string (sha256:hex)",
    "capabilities": ["array of launcher capabilities (mmap, async, sandbox)"]
  },
  "compatibility": {
    "min_format_version": "string (e.g., 1.0.0)",
    "features": ["array of PSPF features used (workenv_dirs, runtime_env, setup_commands, etc.)"]
  }
}
```

### 3.2 Slot Lifecycles

The `lifecycle` field instructs launchers how to handle slot content:

#### Timing-based Lifecycles
- **`init`** - First run only, content is extracted once then removed after initialization
- **`startup`** - Extracted/executed at every startup before main execution
- **`runtime`** - Available during application execution (default)
- **`shutdown`** - Executed during cleanup/exit phase

#### Retention-based Lifecycles
- **`cache`** - Kept for performance, can be regenerated if needed
- **`temp`** - Removed after current session ends
- **`volatile`** - Removed immediately after setup commands complete

#### Access-based Lifecycles
- **`lazy`** - Loaded on-demand, not extracted initially
- **`eager`** - Loaded immediately on startup

#### Environment-based Lifecycles
- **`dev`** - Only extracted in development/debug mode
- **`config`** - User-modifiable configuration files
- **`platform`** - Platform/OS specific content

**Requirements:**
- Launchers MUST support `init`, `runtime`, `cache`, and `volatile` lifecycles
- Launchers SHOULD support other lifecycles where appropriate
- Unknown lifecycles should be treated as `runtime` for forward compatibility

### 3.3 Metadata Sections

#### 3.3.1 Package Information
Basic package identification:
- **`name`**: Package name
- **`version`**: Package version using semantic versioning

#### 3.3.2 Execution Configuration
Controls how the package is executed:
- **`primary_slot`**: Index of the main executable slot
- **`command`**: Command to execute with `{workenv}` placeholder substitution
- **`env`**: Environment variables to set for the application

#### 3.3.3 Runtime Environment
Security and environment filtering:
- **`env.set`**: Variables to set (overrides existing)
- **`env.unset`**: Variables to remove from environment
- **`env.pass`**: Variables to pass through from parent
- **`env.map`**: Map old variable names to new ones

#### 3.3.4 Work Environment Setup
Initializes the isolated work environment:
- **`directories`**: List of directories to create with Unix permissions
  - `path`: Relative path within workenv
  - `mode`: Unix permission mode (e.g., "0700" for user-only)
- **`env`**: Environment variables pointing to workenv paths
  - Supports `{workenv}` placeholder substitution
  - Commonly sets TMPDIR, XDG directories, etc.

#### 3.3.5 Setup Commands
Commands executed after extraction but before main execution:
- **`execute`**: Run a single command
- **`enumerate_and_execute`**: Run command for each file matching pattern
- **`write_file`**: Create a file with specific content

All commands support `{workenv}`, `{package_name}`, and `{version}` placeholders.

#### 3.3.6 Cache Validation
Determines if cached workenv is still valid:
- **`check_file`**: Path to validation marker file
- **`expected_content`**: Content that must match for cache to be valid

#### 3.3.7 Verification Metadata
Cryptographic integrity and signature verification:
- **`integrity_seal`**: Configuration for integrity verification
  - `required`: Whether integrity verification is mandatory
  - `algorithm`: Signature algorithm (ed25519)
- **`signed`**: Whether the package is cryptographically signed
- **`require_verification`**: Whether verification must pass for execution
- **`trust_signatures`**: Optional array of trusted signature fingerprints

#### 3.3.8 Build Metadata
Information about how the package was built:
- **`tool`**: Build tool used (flavor-python, flavor-go, flavor-rust)
- **`tool_version`**: Version of the build tool
- **`timestamp`**: ISO8601 timestamp of when package was built
- **`deterministic`**: Whether build used deterministic key generation
- **`platform`**: Build platform information
  - `os`: Operating system (darwin, linux, windows)
  - `arch`: Architecture (arm64, amd64, x86_64)
  - `host`: Hostname of build machine

#### 3.3.9 Launcher Metadata
Information about the embedded launcher:
- **`tool`**: Launcher tool name (flavor-rs-launcher, flavor-go-launcher)
- **`tool_version`**: Version of the launcher
- **`size`**: Size of launcher binary in bytes
- **`checksum`**: SHA256 checksum of launcher binary
- **`capabilities`**: Array of launcher capabilities
  - `mmap`: Memory-mapped I/O support
  - `async`: Asynchronous execution support
  - `sandbox`: Sandboxing capabilities

#### 3.3.10 Compatibility Metadata
Package compatibility information:
- **`min_format_version`**: Minimum PSPF format version required
- **`features`**: Array of PSPF features used by this package
  - `workenv_dirs`: Uses workenv directory creation
  - `runtime_env`: Uses runtime environment filtering
  - `setup_commands`: Uses setup command execution
  - `cache_validation`: Uses cache validation
  - `volatile_slots`: Contains volatile lifecycle slots

### 3.4 Slot Purpose

The `purpose` field describes the semantic type of content:

- **`payload`** - Main application data
- **`runtime`** - Executable code
- **`config`** - Configuration files
- **`asset`** - Static resources (images, fonts, etc.)
- **`library`** - Shared libraries or dependencies
- **`binary`** - Native executable binaries
- **`installer`** - Installation files (packages, wheels)
- **`data`** - Generic data files

Purpose and lifecycle are orthogonal - any purpose can have any lifecycle.

### 3.5 Environment Variable Processing Order

Environment variables are processed in layers, each with specific purposes:

1. **Runtime Security Layer** (`runtime.env`)
   - First layer: security filtering
   - `unset`: Remove sensitive variables
   - `pass`: Whitelist specific variables
   - `map`: Rename variables for compatibility
   - `set`: Override with safe defaults

2. **Work Environment Layer** (`workenv.env`)
   - Second layer: setup workenv-specific paths
   - Sets TMPDIR, XDG directories, etc.
   - All paths relative to `{workenv}`

3. **Execution Layer** (`execution.env`)
   - Final layer: application-specific settings
   - Sets variables needed by the application
   - Can reference `{workenv}` paths

This layered approach ensures security policies are applied before application configuration.

## 4. Reading Order and Performance

The PSPF format is designed for efficient reading with minimal seeks:

1. **Read Index** (8KB at launcher_size offset)
   - Provides offsets and sizes for everything else
   - Single read operation

2. **Read Metadata** (small, typically < 10KB)
   - At index.MetadataOffset
   - Compressed JSON with package info

3. **Read Slot Table** (64 bytes × slot count)
   - At index.SlotTableOffset
   - Immediately follows metadata for sequential reading
   - Contains offsets, sizes, checksums for all slots

4. **Access Slots** (as needed)
   - Direct seek to any slot using table info
   - No need to read entire file
   - Parallel reads possible for multiple slots

This design minimizes I/O operations and allows efficient random access to slots.

## 5. Security Model

Every bundle MUST include cryptographic integrity verification using Ed25519:

1. **Key Generation**: Generate an Ed25519 key pair at build time (optionally deterministic with --key-seed)
2. **Signing**: Sign the uncompressed JSON metadata with the private key
3. **Storage in Index**:
   - Store the 32-byte public key in the `PublicKey` field
   - Store the 64-byte signature in the first 64 bytes of `IntegritySignature` field
   - Store Adler-32 checksum of compressed metadata in first 4 bytes of `MetadataChecksum`
4. **Private Key**: Discard after signing (or derive deterministically from seed)
5. **Verification**: The launcher MUST:
   - Read and decompress the metadata
   - Verify the Ed25519 signature of the JSON using the public key from the index
   - Verify the Adler-32 checksum matches the compressed data
   - Refuse to execute if verification fails

## 6. Implementation Requirements

### 6.1 Language-Specific Modules

Each language implementation MUST provide:

1. **Standalone Module**: A self-contained package/module that can be imported by other projects
   - Python: `flavor` package on PyPI
   - Rust: `flavor` crate on crates.io
   - Go: `github.com/provide-io/flavor-go` module

2. **Consistent API**: Each implementation should offer similar functionality:
   - Builder API for creating PSPF packages
   - Reader API for extracting and verifying packages
   - Launcher binaries for executing packages
   - Helper utilities for key generation, signing, etc.

3. **Developer Experience**: Prioritize ease of use:
   - Simple, intuitive APIs
   - Comprehensive documentation
   - Examples and tutorials
   - Type safety where applicable

### 6.2 Cross-Language Compatibility

All implementations MUST:
- Use identical binary formats for all structures
- Implement the same cryptographic algorithms (Ed25519, Adler-32)
- Handle endianness consistently (little-endian)
- Support reading packages created by any other implementation
- Pass cross-language compatibility tests

### 6.3 Field Names and Conventions

To maintain consistency across implementations:
- Use `PublicKey` not `EphemeralPublicKey` (keys aren't necessarily ephemeral)
- Use `package_size` not `file_size` for total package size
- Use `slot_table_offset` not `descriptor_offset`
- Metadata is always gzipped JSON (no conditionals)
- Signatures are stored in the index, not embedded in metadata

### 6.4 Implementation Notes

#### Checksum Calculations
- **Index Checksum**: Adler-32 of the entire 8192-byte index with the checksum field set to 0
- **Metadata Checksum**: Adler-32 of the compressed (gzipped) metadata bytes
- **Slot Checksums**: Adler-32 of the compressed slot data

#### Signature Verification
- **What to Sign**: The uncompressed JSON metadata (not the gzipped version)
- **Signature Storage**: First 64 bytes of the 512-byte `IntegritySignature` field
- **Public Key Storage**: 32-byte `PublicKey` field in the index
- **Algorithm**: Ed25519 (RFC 8032)

#### Compression
- **Metadata**: Always gzip compressed
- **Slots**: Compression optional, specified per-slot
- **Supported Algorithms**: none, gzip, zstd, brotli

#### Alignment
- **Index Block**: Always at `launcher_size` offset (no alignment needed)
- **Slots**: Aligned to 8-byte boundaries minimum
- **Page Alignment**: Optional, for memory-mapped I/O optimization
