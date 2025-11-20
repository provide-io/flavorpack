# Glossary

Definitions of key terms and concepts used in FlavorPack and PSPF documentation.

## A

### Archive Operation
A transformation applied to files before packaging, typically TAR format, which combines multiple files into a single archive. See [Operations](#operation).

## B

### Builder
A native binary (written in Go or Rust) that assembles PSPF packages from prepared slots and metadata. Builders implement the PSPF/2025 binary format specification.

**Related**: [Helper](#helper), [Launcher](#launcher)

**Available Builders**:
- `flavor-go-builder` - Go implementation (~3-4 MB)
- `flavor-rs-builder` - Rust implementation (~1 MB)

## C

### Cache
Local storage location (`~/.cache/flavor/`) where extracted package contents are stored for reuse. See [Workenv](#workenv-work-environment).

### Checksum
A cryptographic hash (SHA-256) used to verify data integrity. Every slot and the overall package has checksums to detect corruption or tampering.

### Codec
The compression algorithm used for a slot's data. Common codecs include `gzip`, `zstd`, and `xz`.

**See**: [Operation Chain](#operation-chain)

## D

### Deterministic Build
A build process that produces identical output given the same inputs, achieved through deterministic key generation using a seed value.

```bash
flavor pack --key-seed "my-stable-seed"
```

## E

### Ed25519
A modern elliptic curve signature algorithm used by FlavorPack for package signing and verification. Provides 128-bit security with 32-byte keys and 64-byte signatures.

**Key Benefits**:
- Fast signature generation and verification
- Small key and signature sizes
- No configuration parameters required

### Entry Point
The function or command that executes when a package runs. Specified in the manifest:

```toml
[tool.flavor]
entry_point = "myapp.cli:main"
```

### Extraction
The process of unpacking slot data from a PSPF package into the workenv cache for execution.

**Extraction Modes**:
- **On-demand**: Extract only when needed
- **Cached**: Reuse previously extracted data
- **Progressive**: Extract incrementally as needed

## F

### Format Version
The PSPF specification version, currently `0x2025000c` for PSPF/2025 Edition.

## H

### Helper
A general term for native binaries (builders and launchers) written in Go or Rust that handle low-level PSPF operations.

**Types**:
- **Builders**: Create packages
- **Launchers**: Extract and execute packages

**See**: [Builder](#builder), [Launcher](#launcher)

## I

### Index Block
An 8192-byte (8 KB) structure at the end of every PSPF package containing:
- Format version and magic numbers
- Offsets to metadata and slot sections
- Ed25519 public key (32 bytes)
- Package signature (64 bytes)
- Slot count and checksums

**Location**: EOF - 8196 bytes (inside the magic trailer)

## L

### Launcher
A platform-specific native executable embedded at the start of every `.psp` file. The launcher:
- Validates package signatures
- Extracts slots to workenv
- Sets up the runtime environment
- Executes the application

**Available Launchers**:
- `flavor-go-launcher` - Go implementation (~3-4 MB)
- `flavor-rs-launcher` - Rust implementation (~1 MB)

### Lifecycle
Defines when and how a slot is extracted and managed:

- **`cached`**: Extract once, reuse indefinitely
- **`ephemeral`**: Extract on every run, delete after
- **`persistent`**: Extract once, update only when changed

## M

### Magic Footer
The final 8 bytes of a PSPF package: the 🪄 emoji (UTF-8: `0xF0 0x9F 0xAA 0x84`), marking the end of the package.

### Magic Trailer
The complete 8200-byte structure at the end of a PSPF package:
- Start Magic (4 bytes): 📦 emoji
- Index Block (8192 bytes)
- End Magic (4 bytes): 🪄 emoji

### Manifest
A configuration file (typically `pyproject.toml`) that describes how to package an application. Contains project metadata, dependencies, entry points, and FlavorPack-specific settings.

**Example**:
```toml
[project]
name = "myapp"
version = "1.0.0"

[tool.flavor]
entry_point = "myapp:main"
```

### Metadata Block
A compressed JSON structure in the PSPF package containing:
- Package information (name, version)
- Build metadata (timestamp, builder version)
- Slot definitions
- Runtime configuration

**Format**: Gzipped JSON

## O

### Operation
A transformation applied to slot data, such as archiving (TAR) or compression (GZIP, ZSTD). Operations are identified by numeric codes defined in the PSPF specification.

**Common Operations**:
- `0x01` - TAR (archive)
- `0x10` - GZIP (compress)
- `0x1B` - ZSTD (compress)
- `0x1C` - XZ (compress)

### Operation Chain
A sequence of up to 8 operations applied to a slot, encoded as a 64-bit integer. Operations are applied left-to-right.

**Examples**:
- `TAR|GZIP` → Create tar archive, then gzip compress (tar.gz)
- `TAR|ZSTD` → Create tar archive, then zstd compress (tar.zst)

**See**: [FEP-0001 Operation Chain System](spec/fep-0001-core-format-and-operation-chains/#5-operation-chain-system)

### Orchestrator
The Python-based component that coordinates the packaging process, managing dependency resolution, slot preparation, and helper invocation.

## P

### Polyglot
A file that is valid in multiple formats simultaneously. PSPF packages are polyglot files that function as both:
- Native OS executables (ELF on Linux, Mach-O on macOS)
- Structured PSPF packages with metadata and slots

### Progressive Extraction
The ability to extract and load package components on-demand rather than all at once, improving startup time and memory efficiency.

### PSPF
**Progressive Secure Package Format** - The binary file format used by FlavorPack for creating self-contained, cryptographically signed executable packages.

**Current Version**: PSPF/2025 (Edition 2025)

**Key Features**:
- Self-extracting executables
- Ed25519 signature verification
- Composable operation chains
- Cross-platform compatibility

## S

### Signature
An Ed25519 cryptographic signature (64 bytes) computed over the package metadata and embedded in the index block. Verified automatically at runtime.

### Slot
A numbered data container within a PSPF package. Each slot contains:
- Binary data (typically compressed archives)
- A 64-byte descriptor with metadata
- Operations chain specification
- Checksums

**Common Slots**:
- **Slot 0**: Python runtime environment
- **Slot 1**: Application code and dependencies
- **Slot 2+**: Additional resources (data, config, etc.)

### Slot Descriptor
A 64-byte binary structure describing a slot's metadata:
- Offset and size
- Checksum
- Operations (64-bit encoded chain)
- Lifecycle settings
- Name and purpose

**See**: [Slot Descriptor Specification](spec/SLOT_DESCRIPTOR_SPECIFICATION/)

### Slot Table
An array of slot descriptors, one per slot, located after the metadata block in a PSPF package.

**Size**: `slot_count × 64 bytes`

### Static Binary
An executable linked with all dependencies included, requiring no external shared libraries. All Linux helpers are built as static binaries using musl libc for maximum compatibility.

## T

### Tar.gz
Colloquial term for a TAR archive compressed with GZIP. In PSPF terms, this is an operation chain: `TAR|GZIP`.

## W

### Workenv (Work Environment)
A cached directory where PSPF packages extract their contents for execution. Located at `~/.cache/flavor/workenv/` by default.

**Benefits**:
- Faster subsequent executions (no re-extraction)
- Shared cache across package runs
- Automatic validation via checksums

**Structure**:
```
~/.cache/flavor/
└── pspf-{hash}/
    ├── slot_0/  (Python runtime)
    ├── slot_1/  (Application code)
    └── metadata.json
```

**Management**:
```bash
flavor workenv list      # View cached packages
flavor workenv clean     # Clear cache
flavor workenv inspect   # Inspect specific package
```

## Acronyms

| Acronym | Full Term | Description |
|---------|-----------|-------------|
| **PSPF** | Progressive Secure Package Format | The binary format specification |
| **FEP** | FlavorPack Enhancement Proposal | Design documents for PSPF features |
| **EOF** | End of File | The final byte position in a file |
| **SHA** | Secure Hash Algorithm | Cryptographic hash function (SHA-256) |
| **PEM** | Privacy Enhanced Mail | ASCII encoding format for keys |
| **CLI** | Command-Line Interface | Terminal-based user interface |
| **API** | Application Programming Interface | Programmatic interface |
| **CI/CD** | Continuous Integration/Continuous Deployment | Automated build and release pipelines |

## File Extensions

| Extension | Description |
|-----------|-------------|
| `.psp` | PSPF package file (self-contained executable) |
| `.toml` | TOML manifest file (typically `pyproject.toml`) |
| `.key` | PEM-encoded Ed25519 key file |
| `.tar.gz` | TAR archive compressed with GZIP |
| `.tar.zst` | TAR archive compressed with ZSTD |

## Common Commands

Quick reference for frequently used terms in commands:

```bash
# Package (noun) - A .psp file
./myapp.psp

# Pack (verb) - Create a package
flavor pack

# Verify (verb) - Check package integrity
flavor verify myapp.psp

# Extract (verb) - Unpack slot data
flavor extract myapp.psp 0 output.tar.gz

# Inspect (verb) - View package metadata
flavor inspect myapp.psp

# Helper (noun) - Native binary
flavor helpers list

# Workenv (noun) - Cached extraction directory
flavor workenv clean
```

## See Also

- **[PSPF Format Specification](spec/pspf-2025/)** - Complete format documentation
- **[CLI Reference](../guide/usage/cli/)** - Command-line interface
- **[Core Concepts](../guide/concepts/index/)** - Foundational concepts
- **[Architecture](../development/architecture/)** - System design

---

**Can't find a term?** [Open an issue](https://github.com/provide-io/flavorpack/issues) to suggest additions to this glossary.
