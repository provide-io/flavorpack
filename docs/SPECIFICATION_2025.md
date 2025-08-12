# Progressive Secure Package Format (PSPF) 2025 Specification

## Overview

The Progressive Secure Package Format (PSPF) 2025 Edition is a metadata-first, self-extracting archive format designed for secure, cross-platform software distribution. This specification defines a generic, language-agnostic format that supports multiple runtime environments while maintaining cryptographic integrity.

## Terminology

To ensure clarity and developer experience, PSPF uses these specific terms:

- **Slot**: A compressed archive containing a specific component (runtime, toolchain, library, or asset)
- **Payload**: The main application bundle (your actual code/application)
- **Toolchain**: Development tools that manage dependencies or build processes (not "package manager")
- **Runtime**: The execution environment for a language (not "language runtime")
- **Bundle**: The complete PSPF file containing all components
- **Extraction**: The process of decompressing components from the bundle to disk
- **Loading**: The process of making extracted components available for execution
- **Purpose**: The role a slot serves (runtime/toolchain/library/asset)
- **Cache Strategy**: How aggressively to verify cached components
- **Entry Point**: The command or path to start the application

## Key Design Principles

1. **Metadata-First**: Package metadata is always loaded into memory on launch, enabling intelligent runtime decisions
2. **Language Agnostic**: Supports any runtime environment (Python, Node.js, Go, Rust, Java, etc.)
3. **Progressive Extraction**: Components are extracted on-demand based on metadata directives
4. **Cryptographic Security**: All payloads are signed and verified
5. **Self-Describing**: Packages contain all information needed for execution

## File Structure

```
┌─────────────────────────┐
│   1. Launcher Binary    │ ← Platform-specific executable
├─────────────────────────┤
│   2. Metadata Archive   │ ← Contains psp.json + signatures + keys
├─────────────────────────┤
│   3. Slot 0             │ ← Any purpose (runtime/toolchain/payload/etc.)
├─────────────────────────┤
│   4. Slot 1             │ ← Defined by psp.json
├─────────────────────────┤
│   ... Slot N           │ ← Variable number of slots
├─────────────────────────┤
│   Footer                │ ← Fixed-size structure (512 bytes)
├─────────────────────────┤
│   Emoji Magic           │ ← 📦[L][R]🪄 (16 bytes)
└─────────────────────────┘
```

## Component Specifications

### 1. Launcher Binary

The launcher is a platform-specific executable that:
- Reads and validates the PSPF structure
- Loads metadata into memory
- Manages runtime extraction and caching
- Executes the payload with appropriate runtime

Platform naming convention: `{os}_{arch}` (e.g., `darwin_arm64`, `linux_amd64`, `windows_amd64`)

### 2. Metadata Archive

A compressed tar.gz archive that MUST contain a `psp.json` file at its root. This archive is ALWAYS decompressed into memory on launch. The archive structure:

```
metadata.tgz/
├── psp.json                  # Required: Package manifest
├── integrity/                # Required: Integrity sealing
│   ├── seal.sig             # Ephemeral key signature of psp.json
│   ├── seal.pem             # Ephemeral public key
│   └── seal-metadata.json   # Key generation time, etc.
├── signatures/               # Optional: Trust signatures
│   ├── publisher.sig        # Publisher signature
│   ├── notary.sig          # Third-party attestation
│   └── slots/              # Per-slot signatures
│       └── ...
├── keys/                    # Optional: Trusted public keys
│   ├── publisher.pem       # Publisher's long-term key
│   └── notary.pem         # Notary's public key
├── manifest.json           # Optional: Human-readable metadata
├── requirements.json       # Optional: Dependencies
└── README.md              # Optional: Documentation
```

#### Required: psp.json

The `psp.json` file contains all integrity-critical information required to securely extract and execute the package.

```json
{
  "format_version": "2025",
  "package": {
    "name": "string",
    "version": "string"
  },
  "slots": [
    {
      "index": "number",
      "purpose": "string",
      "name": "string",
      "checksum": "string",
      "size": "number",
      "compression": "string",
      "lifecycle": "string",
      "cleanup": "string (optional)",
      "extract_order": "number (optional)",
      "extract_condition": "string (optional)",
      "entry_point": "string (optional)"
    }
  ],
  "verification": {
    "integrity_seal": {
      "required": "boolean",
      "key_lifecycle": "string" (ephemeral/persistent),
      "algorithm": "string" (default: "ecdsa-p256")
    },
    "trusted_signatures": {
      "required": "boolean",
      "allowed_signers": ["string"] (optional)
    },
    "checksum_algorithm": "string" (default: "sha256")
  },
  "extraction": {
    "slot_order": ["number"],
    "cache_strategy": "string",
    "parallel_extraction": "boolean"
  },
  "execution": {
    "primary_slot": "number",
    "command": "string"
  }
}
```

#### Optional Metadata Files

The metadata archive may also contain:
- `manifest.json` - Human-readable package information (author, description, license, etc.)
- `requirements.json` - Dependencies and compatibility information
- `config/` - Package-specific configuration files
- `README.md` - Package documentation

#### psp.json Field Descriptions

**Integrity-Critical Fields:**
- **format_version**: PSPF specification edition (must be "2025")
- **package**: Minimal package identification
  - **name**: Package identifier (alphanumeric + hyphens/underscores)
  - **version**: Semantic version string
- **slots**: All package components including payload(s)
  - **index**: Zero-based position in file
  - **purpose**: Slot purpose ("runtime", "toolchain", "library", "asset", "payload")
  - **name**: Human-readable identifier for the slot
  - **checksum**: SHA256 hex string of compressed data
  - **size**: Compressed size in bytes
  - **compression**: "gzip", "zstd", or "none"
  - **lifecycle**: Extraction lifecycle policy (see below)
  - **cleanup**: Optional cleanup timing ("after_install", "after_first_run", "on_update")
  - **extract_order**: Optional extraction sequence number
  - **extract_condition**: Optional condition expression (e.g., "platform == 'darwin_arm64'")
  - **entry_point**: Optional command for executable slots
- **verification**: Security requirements
  - **integrity_seal**: Package integrity verification
    - **required**: Whether integrity seal is mandatory
    - **key_lifecycle**: "ephemeral" (disposable) or "persistent" (long-term)
    - **algorithm**: Signature algorithm (default: "ecdsa-p256")
  - **trusted_signatures**: Identity/trust verification
    - **required**: Whether trusted signatures are needed
    - **allowed_signers**: List of allowed public key fingerprints
  - **checksum_algorithm**: Hash algorithm (default: "sha256")
- **extraction**: Extraction orchestration
  - **slot_order**: Explicit extraction order for slots
  - **cache_strategy**: "strict" (always verify), "trust" (verify once), "dev" (skip verification)
  - **parallel_extraction**: Whether slots can be extracted in parallel
- **execution**: How to run the package
  - **primary_slot**: Index of the main executable slot
  - **command**: Command template with slot references (e.g., "{slot:1}/bin/python -m {slot:3}/myapp")

### 3. Runtime Slots

Variable number of compressed archives containing components needed for package execution. Each slot corresponds to an entry in psp.json's `slots` array.

#### Slot Purpose Categories

- **runtime**: Language runtime environments (Python, Node.js, JVM, .NET)
- **toolchain**: Development/build tools (compilers, packagers, bundlers)
- **library**: Shared libraries or frameworks
- **asset**: Static resources, data files, or configuration
- **payload**: Application code/binaries (wheels, JARs, executables)

#### Slot Lifecycle Policies

The `lifecycle` field controls extraction and retention:

- **"persistent"**: Extract once, keep in cache (default)
- **"temporary"**: Extract for current execution, remove after
- **"install"**: Extract once for installation, then remove
- **"volatile"**: Always extract fresh, never cache
- **"lazy"**: Extract only when first accessed

#### Common Slot Examples

| Purpose | Examples | Typical Use | Common Lifecycle |
|---------|----------|-------------|------------------|
| runtime | `python-3.13`, `node-20`, `jvm-21` | Execution environment | persistent |
| toolchain | `uv`, `npm`, `cargo`, `maven` | Dependency management | persistent |
| library | `opencv`, `cuda`, `qt` | Native dependencies | persistent |
| asset | `models`, `data`, `config` | Application resources | persistent |
| payload | `myapp.whl`, `app.jar`, `main.exe` | Application code | install/persistent |

### 4. Footer Structure

Fixed-size structure (512 bytes) for efficient random access:

```c
struct PSPFooter {
    // Metadata archive (contains everything) - 24 bytes
    uint64_t metadata_offset;    // 8 bytes: Where metadata.tgz starts
    uint64_t metadata_size;      // 8 bytes: Size of compressed metadata.tgz
    uint64_t metadata_checksum;  // 8 bytes: Adler-32 of compressed metadata
    
    // Slot information - 16 bytes
    uint32_t slot_count;         // 4 bytes: Number of slots (0 to N)
    uint32_t reserved_pad;       // 4 bytes: Alignment padding
    uint64_t slot_table_offset;  // 8 bytes: Where SlotEntry array starts
    
    // Version and validation - 12 bytes
    uint16_t pspf_version;       // 2 bytes: 0x2025 for 2025 edition
    uint16_t flags;              // 2 bytes: Reserved flags
    uint32_t footer_checksum;    // 4 bytes: Adler-32 of footer
    
    // Reserved for future use - 460 bytes
    uint8_t reserved[460];       // Pad to exactly 512 bytes
};
// Total: 24 + 16 + 12 + 460 = 512 bytes

// Slot table (variable size, located at slot_table_offset)
struct SlotEntry {
    uint64_t offset;
    uint64_t size;
    uint64_t checksum;  // Adler-32 for quick validation
};
```

### 5. Emoji Magic (16 bytes)

The PSPF 2025 Edition uses a 4-emoji sequence as its magic identifier at the very end of the file (after the footer):

```
📦[L][R]🪄
```

Where:
- 📦 = Package identifier (ALWAYS first)
- [L] = Launcher language emoji:
  - 🐍 = Python launcher
  - 🦀 = Rust launcher
  - 🐹 = Go launcher
  - 🟢 = Node.js launcher
  - ⚡ = Native/no launcher
  - 🔮 = Unknown/generic
- [R] = Random/fun emoji (builder's choice)
  - 🌈🦄🎸🍕🚀🌮🎨🎭🎪🎯 etc.
- 🪄 = Magic wand (MUST ALWAYS be last)

#### File Structure Detail

```
[Launcher Binary]
[Metadata Archive]
[Slot 0]
[Slot 1]
[...]
[Footer - 512 bytes]      ← Ends at offset (filesize - 528)
[Emoji Magic - 16 bytes]  ← Last 16 bytes of file
EOF
```

#### Example Patterns

```
📦🐹🦄🪄  # Go launcher with unicorn
📦🦀🍕🪄  # Rust launcher with pizza
📦🐍🌈🪄  # Python launcher with rainbow
📦⚡🎸🪄  # Native binary with guitar
```

#### Reading Order

To read a PSPF 2025 file:
1. Seek to -16 bytes from EOF and read emoji magic
2. Verify first emoji is 📦 and last is 🪄
3. Seek to -528 bytes from EOF (512 + 16) and read footer
4. Verify footer checksum
5. Use footer offsets to read metadata and slots

#### Validation

```python
def validate_pspf_file(file_path):
    with open(file_path, 'rb') as f:
        # 1. Check emoji magic at very end
        f.seek(-16, 2)
        emoji_magic = f.read(16)
        
        if emoji_magic[0:4] != "📦".encode('utf-8'):
            raise ValueError("Invalid PSPF: Must start with 📦")
            
        if emoji_magic[-4:] != "🪄".encode('utf-8'):
            raise ValueError("Invalid PSPF: Must end with 🪄")
        
        # 2. Read footer (before emoji magic)
        f.seek(-528, 2)  # 512 byte footer + 16 byte emoji
        footer_bytes = f.read(512)
        
        # 3. Verify footer checksum
        if not verify_footer_checksum(footer_bytes):
            raise ValueError("Invalid footer checksum")
            
        return True
```


## Launcher Execution Flow

```python
def launch_pspf():
    # 1. Read and validate emoji magic (last 16 bytes)
    emoji_magic = read_file_end(16)
    
    # 2. Verify emoji magic pattern
    if emoji_magic[0:4] != "📦".encode('utf-8'):
        error("Invalid PSPF file: Must start with 📦")
    if emoji_magic[-4:] != "🪄".encode('utf-8'):
        error("Invalid PSPF file: Must end with 🪄")
    
    # 3. Read and parse footer (512 bytes before emoji magic)
    f.seek(-528, 2)  # 512 byte footer + 16 byte emoji
    footer_bytes = f.read(512)
    footer = parse_footer(footer_bytes)
    
    # Validate footer checksum (compute with checksum field as 0)
    if not verify_adler32(footer_bytes, footer.footer_checksum):
        error("Footer checksum mismatch")
    
    # 4. Load metadata into memory (always)
    metadata_bytes = read_section(footer.metadata_offset, footer.metadata_size)
    
    # Quick validation with Adler-32
    if adler32(metadata_bytes) != footer.metadata_checksum:
        error("Metadata checksum mismatch")
    
    metadata_tgz = decompress(metadata_bytes)
    metadata_files = extract_all(metadata_tgz)
    
    # 5. Parse and verify psp.json
    psp_json = metadata_files["psp.json"]
    psp = parse_json(psp_json)
    
    # Always verify integrity seal (ephemeral key)
    if psp.verification.integrity_seal.required:
        seal_sig = metadata_files["integrity/seal.sig"]
        seal_key = metadata_files["integrity/seal.pem"]
        verify_signature(psp_json, seal_sig, seal_key)
        
    # Optionally verify trust signatures (persistent keys)
    if psp.verification.trusted_signatures.required:
        verified = False
        for sig_file in metadata_files.get("signatures/", []):
            if sig_file.endswith(".sig"):
                signer = sig_file.replace(".sig", "")
                if f"keys/{signer}.pem" in metadata_files:
                    try:
                        verify_signature(
                            psp_json,
                            metadata_files[f"signatures/{sig_file}"],
                            metadata_files[f"keys/{signer}.pem"]
                        )
                        verified = True
                        break
                    except:
                        continue
        if not verified:
            error("No valid trusted signature found")
    
    # 6. Determine cache directory
    cache_dir = get_cache_dir(psp.package.name, psp.package.version)
    
    # 7. Process slots based on lifecycle and conditions
    slot_paths = {}
    for slot in psp.slots:
        if evaluate_condition(slot.extract_condition):
            # Verify slot signature if required
            if psp.verification.require_slot_signatures:
                slot_sig_path = f"signatures/slots/{slot.index}.sig"
                if slot_sig_path in metadata_files:
                    slot_data = read_slot(footer, slot.index)
                    verify_signature(
                        slot_data, 
                        metadata_files[slot_sig_path],
                        metadata_files["keys/primary.pem"]
                    )
                else:
                    error(f"Missing signature for slot {slot.index}")
            
            slot_path = extract_slot_by_lifecycle(
                slot=slot,
                footer=footer,
                cache_dir=cache_dir
            )
            slot_paths[slot.index] = slot_path
            
            # Handle special lifecycle actions
            if slot.lifecycle == "install" and slot.purpose == "payload":
                install_payload(slot_path, slot)
                if slot.cleanup == "after_install":
                    schedule_cleanup(slot_path)
    
    # 8. Execute package using command template
    command = psp.execution.command
    for index, path in slot_paths.items():
        command = command.replace(f"{{slot:{index}}}", str(path))
    
    execute_command(command)
```

## Security Model

### Trust Boundaries

```
Package File (Verified) → Memory (Trusted) → Execution (Trusted)
                              ↓
                      Disk Cache (Verified)
```

### Security Properties

1. **Integrity**: All components are checksummed
2. **Authenticity**: Payload is cryptographically signed
3. **Tamper Detection**: Footer checksum prevents modification
4. **Metadata Trust**: Metadata always loaded from package, never from cache

### Attack Prevention

- **Metadata Tampering**: Impossible as metadata is always loaded from package
- **Cache Poisoning**: All cached files verified against metadata checksums
- **Downgrade Attacks**: Version checking in metadata
- **Path Traversal**: Restricted extraction paths

## Examples

### Python Application (psp.json)

```json
{
  "format_version": "2025",
  "package": {
    "name": "myapp",
    "version": "1.0.0"
  },
  "slots": [
    {
      "index": 0,
      "purpose": "toolchain",
      "name": "uv",
      "checksum": "sha256:abc123...",
      "size": 8388608,
      "compression": "gzip",
      "lifecycle": "persistent"
    },
    {
      "index": 1,
      "purpose": "runtime",
      "name": "python-3.13",
      "checksum": "sha256:def456...",
      "size": 41943040,
      "compression": "zstd",
      "lifecycle": "persistent"
    },
    {
      "index": 2,
      "purpose": "payload",
      "name": "myapp.whl",
      "checksum": "sha256:789xyz...",
      "size": 1048576,
      "compression": "gzip",
      "lifecycle": "install",
      "cleanup": "after_install"
    }
  ],
  "verification": {
    "integrity_seal": {
      "required": true,
      "key_lifecycle": "ephemeral",
      "algorithm": "ecdsa-p256"
    },
    "trusted_signatures": {
      "required": false
    }
  },
  "extraction": {
    "slot_order": [0, 1, 2],
    "cache_strategy": "trust",
    "parallel_extraction": true
  },
  "execution": {
    "primary_slot": 2,
    "command": "{slot:1}/bin/python -m myapp.main"
  }
}
```

### Native Go Binary (psp.json)

```json
{
  "format_version": "2025",
  "package": {
    "name": "mytool",
    "version": "2.1.0"
  },
  "slots": [
    {
      "index": 0,
      "purpose": "payload",
      "name": "mytool",
      "checksum": "sha256:aaa111...",
      "size": 10485760,
      "compression": "none",
      "lifecycle": "persistent",
      "entry_point": "./mytool"
    }
  ],
  "verification": {
    "integrity_seal": {
      "required": true,
      "key_lifecycle": "ephemeral",
      "algorithm": "ecdsa-p256"
    },
    "trusted_signatures": {
      "required": false
    }
  },
  "extraction": {
    "slot_order": [0],
    "cache_strategy": "trust",
    "parallel_extraction": false
  },
  "execution": {
    "primary_slot": 0,
    "command": "{slot:0}/mytool"
  }
}
```

### Multi-Platform Package (psp.json)

```json
{
  "format_version": "2025",
  "package": {
    "name": "cross-platform-app",
    "version": "3.0.0"
  },
  "slots": [
    {
      "index": 0,
      "purpose": "runtime",
      "name": "python-darwin-arm64",
      "checksum": "sha256:mac123...",
      "size": 40000000,
      "compression": "zstd",
      "lifecycle": "persistent",
      "extract_condition": "platform == 'darwin_arm64'"
    },
    {
      "index": 1,
      "purpose": "runtime",
      "name": "python-linux-amd64",
      "checksum": "sha256:lin456...",
      "size": 42000000,
      "compression": "zstd",
      "lifecycle": "persistent",
      "extract_condition": "platform == 'linux_amd64'"
    },
    {
      "index": 2,
      "purpose": "payload",
      "name": "app-universal",
      "checksum": "sha256:app789...",
      "size": 5242880,
      "compression": "gzip",
      "lifecycle": "persistent"
    }
  ],
  "verification": {
    "integrity_seal": {
      "required": true,
      "key_lifecycle": "ephemeral",
      "algorithm": "ecdsa-p256"
    },
    "trusted_signatures": {
      "required": false
    }
  },
  "extraction": {
    "slot_order": [0, 1, 2],
    "cache_strategy": "strict",
    "parallel_extraction": false
  },
  "execution": {
    "primary_slot": 2,
    "command": "python -m app.main"
  }
}
```

## Advantages Over 2024 Edition (v0.1)

1. **Generic Format**: Not tied to Python or any specific language
2. **Metadata-First**: Enables intelligent decisions before extraction
3. **Flexible Runtimes**: Support for any number and type of runtime components
4. **Progressive Loading**: Extract only what's needed
5. **Multi-Platform**: Single package can support multiple platforms
6. **Extensible**: New runtime types without format changes

## Migration from 2024 Edition

Tools will be provided to convert 2024 Edition Python-specific packages to 2025 Edition format:

```bash
flavor migrate --input package.pspf --output package-2025.pspf
```

The migration process:
1. Extracts 2024 Edition components
2. Generates 2025 Edition metadata
3. Repackages with runtime slots
4. Preserves signatures

## Future Considerations

The 424-byte reserved section in the footer allows for future enhancements:
- Additional checksum algorithms
- Compression metadata
- Extended platform information
- Streaming support flags
- Dependency information

---

*PSPF 2025 Edition - A metadata-first approach to secure, portable software distribution*