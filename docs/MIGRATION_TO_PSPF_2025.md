# Migration Guide: Flavor v0.1 to PSPF 2025

## Overview

This guide helps migrate from the existing Flavor v0.1 format to the new PSPF 2025 format. The new format introduces significant improvements in structure, security, and cross-language compatibility.

## Key Changes

### 1. Format Structure

#### v0.1 (Footer-based)
```
┌─────────────────────────┐
│ Go Launcher Binary      │
├─────────────────────────┤
│ UV Binary               │
├─────────────────────────┤
│ Payload Archive         │
├─────────────────────────┤
│ Metadata Archive        │
├─────────────────────────┤
│ Footer (120 bytes)      │ ← At EOF
├─────────────────────────┤
│ Magic (📦FLAVOR📦)      │ ← At EOF
└─────────────────────────┘
```

#### PSPF 2025 (Index-based)
```
┌─────────────────────────┐
│ Launcher Binary         │
├─────────────────────────┤
│ Index Block (256 bytes) │ ← At launcher_size offset
├─────────────────────────┤
│ Metadata Archive        │
├─────────────────────────┤
│ Slot 0                  │
├─────────────────────────┤
│ Slot 1                  │
├─────────────────────────┤
│ ...                     │
├─────────────────────────┤
│ Slot Table              │
├─────────────────────────┤
│ Emoji Magic (16 bytes)  │ ← 📦[L][R]🪄
└─────────────────────────┘
```

### 2. Magic Signature

- **v0.1**: `📦FLAVOR📦` (fixed)
- **PSPF 2025**: `📦[Launcher][Random]🪄` (dynamic)
  - 🐹 for Go launcher
  - 🦀 for Rust launcher
  - 🐍 for Python launcher
  - 🟢 for Node.js launcher

### 3. Version Numbers

- **v0.1**: `0x0001`
- **PSPF 2025**: `0x20250001`

### 4. Index/Footer Location

- **v0.1**: Footer at EOF - 120 bytes
- **PSPF 2025**: Index at launcher_size offset

## Code Migration

### Go Migration

#### Reading v0.1 Format
```go
// Old v0.1 code
import "flavor/go/pkg/flavor"

footer := &flavor.FlavorFooter{}
// Read from EOF - 120
```

#### Reading PSPF 2025 Format
```go
// New PSPF 2025 code
import "flavor/go/pkg/flavor"

// Check format version first
if isPSPF2025(data) {
    index := &flavor.PSPFIndex2025{}
    err := index.Unpack(data[launcherSize:launcherSize+256])
} else {
    // Fall back to v0.1
    footer := &flavor.FlavorFooter{}
}
```

### Rust Migration

#### Reading v0.1 Format
```rust
// Old v0.1 code
use flavor::FlavorFooter;

let footer = FlavorFooter::from_bytes(&footer_data)?;
```

#### Reading PSPF 2025 Format
```rust
// New PSPF 2025 code
use flavor::flavor_2025::{PSPFIndex2025, verify_emoji_magic};

// Check format version first
if verify_emoji_magic(&mut file)? {
    let index = PSPFIndex2025::unpack(&index_data)?;
} else {
    // Fall back to v0.1
    let footer = FlavorFooter::from_bytes(&footer_data)?;
}
```

### Python Migration

#### Reading v0.1 Format
```python
# Old v0.1 code
from flavor.psp.format_v1 import PSPFReader

reader = PSPFReader(bundle_path)
footer = reader.read_footer()
```

#### Reading PSPF 2025 Format
```python
# New PSPF 2025 code
from flavor.psp.format_2025 import PSPFReader

reader = PSPFReader(bundle_path)
if reader.verify_magic():  # Checks for 📦??🪄
    index = reader.read_index()
else:
    # Fall back to v0.1
    from flavor.psp.format_v1 import PSPFReader as V1Reader
    reader = V1Reader(bundle_path)
```

## Metadata Changes

### v0.1 Metadata
```json
{
    "format_version": "0.1",
    "package": {
        "name": "myapp",
        "version": "1.0.0",
        "entry_point": "main.py"
    },
    "runtime_slots": [...],
    "cache_policy": {...}
}
```

### PSPF 2025 Metadata
```json
{
    "format": "PSPF/2025",
    "package": {
        "name": "myapp",
        "version": "1.0.0",
        "description": "My application"
    },
    "slots": [
        {
            "index": 0,
            "name": "payload",
            "size": 1024,
            "compression": "gzip",
            "purpose": "payload",
            "lifecycle": "persistent"
        }
    ],
    "execution": {
        "primary_slot": 0,
        "command": "{slot:0}/main"
    },
    "verification": {
        "integrity_seal": {
            "required": true,
            "algorithm": "ecdsa-p256"
        }
    }
}
```

## Slot System

### v0.1 Approach
- Fixed slots: UV binary, Python install, payload
- No lifecycle management
- Limited compression options

### PSPF 2025 Approach
- Dynamic slot system
- Lifecycle policies: persistent, volatile, temporary, install
- Multiple compression algorithms
- Platform-specific slots

## Security Changes

### v0.1 Security
- ECDSA signatures with persistent keys
- Package signature at fixed offset
- Public key embedded in footer

### PSPF 2025 Security
- Ephemeral keys for integrity sealing
- Optional persistent signatures for trust
- Keys stored in metadata archive
- Enhanced checksum verification

## Building Packages

### v0.1 Builder
```bash
flavor-go build --output app.flavor
```

### PSPF 2025 Builder
```bash
flavor package --manifest pspf.toml --output app.pspf
```

## Compatibility Mode

To support both formats during transition:

```go
func DetectFormat(path string) (string, error) {
    file, err := os.Open(path)
    if err != nil {
        return "", err
    }
    defer file.Close()
    
    // Check for PSPF 2025 emoji magic
    file.Seek(-16, 2)
    magic := make([]byte, 16)
    file.Read(magic)
    
    if bytes.Contains(magic, []byte("📦")) && bytes.Contains(magic, []byte("🪄")) {
        return "PSPF/2025", nil
    }
    
    // Check for v0.1 magic
    file.Seek(-len(FLAVOR_MAGIC_EOF_STRING), 2)
    v1Magic := make([]byte, len(FLAVOR_MAGIC_EOF_STRING))
    file.Read(v1Magic)
    
    if bytes.Equal(v1Magic, FLAVOR_MAGIC_EOF_STRING) {
        return "Flavor/0.1", nil
    }
    
    return "", errors.New("unknown format")
}
```

## Testing

Run compatibility tests:

```bash
# Test all combinations
pytest tests/test_pspf_2025_all_combinations.py -v

# Test specific migration
pytest tests/test_migration_v01_to_2025.py -v
```

## Timeline

1. **Phase 1**: Add PSPF 2025 support alongside v0.1
2. **Phase 2**: Migrate tools to prefer PSPF 2025
3. **Phase 3**: Deprecate v0.1 format
4. **Phase 4**: Remove v0.1 support (6 months later)

## Support

For migration assistance:
- GitHub Issues: https://github.com/anthropics/claude-code/issues
- Documentation: https://docs.anthropic.com/en/docs/claude-code