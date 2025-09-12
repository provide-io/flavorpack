# FEP-0002: JSON Metadata Format Specification

**Status**: Active  
**Type**: Standards Track  
**Created**: 2025-01-08  
**Version**: v0 (JSON-based)

## 1. Introduction

This specification defines the JSON-based metadata format for PSPF/2025 v0 packages. JSON provides sufficient performance for v0 implementations while being easy to debug, inspect, and implement across languages.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Design Goals for v0

1. Simple, debuggable metadata format
2. Cross-language compatibility through JSON
3. Human-readable package inspection
4. Easy implementation and testing
5. Sufficient performance for v0 use cases

## 2. JSON Metadata Structure

### 2.1. Root Metadata Object

The package metadata MUST be a valid JSON object with the following structure:

```json
{
  "format_version": "2025.0.0",
  "package": {
    "name": "my-application",
    "version": "1.0.0",
    "description": "Example PSPF package",
    "author": "Package Author",
    "license": "MIT",
    "homepage": "https://example.com"
  },
  "build": {
    "timestamp": 1704067200,
    "platform": "linux_x86_64", 
    "builder": "flavorpack-0.1.0"
  },
  "slots": [
    {
      "id": 0,
      "name": "runtime",
      "purpose": "code",
      "lifecycle": "startup",
      "operations": "tar.gz",
      "size": 1024000,
      "checksum": "abc123def"
    }
  ],
  "execution": {
    "entry_point": "./app",
    "args": [],
    "env": {},
    "working_directory": "."
  }
}
```

### 2.2. Required Fields

The following fields are REQUIRED in all v0 metadata:

#### Root Level
- `format_version` (string): MUST be "2025.0.0" for v0
- `package` (object): Package information
- `slots` (array): Array of slot definitions

#### Package Object
- `name` (string): Package name, MUST match `[a-z0-9_-]+`
- `version` (string): Package version, SHOULD follow semantic versioning

#### Slot Objects
- `id` (integer): Unique slot identifier (0-4294967295)
- `name` (string): Human-readable slot name
- `purpose` (string): One of: "code", "data", "config", "media"
- `lifecycle` (string): See Section 2.3
- `operations` (string): Operation chain description
- `size` (integer): Size of slot data in bytes
- `checksum` (string): Adler-32 checksum as hex string

### 2.3. Slot Lifecycle Values

Valid lifecycle values for v0:

| Value       | Description                           |
|-------------|---------------------------------------|
| init        | First run only, then removed         |
| startup     | Extract at every startup             |
| runtime     | Extract on first use (default)       |
| shutdown    | Extract during cleanup               |
| cache       | Performance cache, can regenerate    |
| temporary   | Remove after session ends           |
| lazy        | Load on-demand                       |
| eager       | Load immediately on startup          |
| dev         | Development mode only                |
| config      | User-modifiable config files        |
| platform    | Platform/OS specific content         |

### 2.4. Operation Chain Encoding

For v0, operation chains MUST use these string formats:

#### Simple Operations
- `"raw"` - No operations
- `"gzip"` - GZIP compression only
- `"bzip2"` - BZIP2 compression only
- `"xz"` - XZ compression only  
- `"zstd"` - Zstandard compression only
- `"tar"` - TAR archive only

#### Compound Operations
- `"tar.gz"` - TAR then GZIP (equivalent to `"tar|gzip"`)
- `"tar.bz2"` - TAR then BZIP2 (equivalent to `"tar|bzip2"`)
- `"tar.xz"` - TAR then XZ (equivalent to `"tar|xz"`)
- `"tar.zst"` - TAR then Zstandard (equivalent to `"tar|zstd"`)

#### Pipe Format (Alternative)
- `"tar|gzip"` - TAR followed by GZIP
- `"tar|bzip2|base64"` - TAR, then BZIP2, then Base64 (future)

### 2.5. Optional Fields

#### Build Object (Optional)
- `timestamp` (integer): Unix timestamp of build
- `platform` (string): Target platform identifier
- `builder` (string): Builder tool and version
- `source_hash` (string): Hash of source code
- `reproducible` (boolean): Whether build is reproducible

#### Execution Object (Optional)
- `entry_point` (string): Main executable path
- `args` (array of strings): Default command line arguments
- `env` (object): Environment variable defaults
- `working_directory` (string): Working directory for execution

#### Slot Extensions (Optional)
- `permissions` (string): Unix permissions like "755" or "644"
- `platform` (string): Platform-specific slot
- `original_size` (integer): Uncompressed size in bytes
- `path` (string): Suggested extraction path

## 3. Encoding Requirements

### 3.1. JSON Encoding

The JSON metadata MUST:
- Use UTF-8 encoding without BOM
- Be valid according to RFC 7159
- Use compact formatting (no unnecessary whitespace) when stored in packages
- Support pretty-printing for debugging

### 3.2. String Handling

All string fields MUST:
- Be valid UTF-8
- Not contain null bytes (U+0000)
- Use forward slashes for paths regardless of platform

### 3.3. Integer Ranges

Integer fields have these constraints:
- `slot.id`: 0 to 4,294,967,295 (32-bit unsigned)
- `size`, `original_size`: 0 to 18,446,744,073,709,551,615 (64-bit unsigned)
- `timestamp`: Unix timestamp (32 or 64-bit)

## 4. Validation

### 4.1. Schema Validation

Implementations SHOULD validate metadata against this schema before processing. Invalid metadata MUST cause package rejection.

### 4.2. Semantic Validation

Beyond schema validation, implementations MUST verify:
- Slot IDs are unique within a package
- Referenced operations are supported
- File paths don't contain directory traversal attempts
- Checksums match actual slot data

## 5. Cross-Language Implementation

### 5.1. Python Implementation

```python
import json
from typing import Dict, Any, List

def parse_metadata(json_bytes: bytes) -> Dict[str, Any]:
    """Parse JSON metadata from package."""
    return json.loads(json_bytes.decode('utf-8'))

def serialize_metadata(metadata: Dict[str, Any]) -> bytes:
    """Serialize metadata to compact JSON."""
    return json.dumps(metadata, separators=(',', ':')).encode('utf-8')
```

### 5.2. Go Implementation

```go
import (
    "encoding/json"
)

type PackageMetadata struct {
    FormatVersion string `json:"format_version"`
    Package      PackageInfo `json:"package"`
    Slots        []SlotInfo  `json:"slots"`
    // ... other fields
}

func ParseMetadata(data []byte) (*PackageMetadata, error) {
    var metadata PackageMetadata
    err := json.Unmarshal(data, &metadata)
    return &metadata, err
}
```

### 5.3. Rust Implementation

```rust
use serde::{Deserialize, Serialize};

#[derive(Deserialize, Serialize)]
struct PackageMetadata {
    format_version: String,
    package: PackageInfo,
    slots: Vec<SlotInfo>,
    // ... other fields
}

fn parse_metadata(data: &[u8]) -> Result<PackageMetadata, serde_json::Error> {
    serde_json::from_slice(data)
}
```

## 6. Performance Considerations

### 6.1. JSON Performance

For v0, JSON metadata performance is acceptable because:
- Metadata is small (typically <100KB)
- Parsed only once per package
- Human readability aids debugging
- Cross-language compatibility is excellent

### 6.2. Future Optimization

Future versions may introduce binary wire formats for:
- Larger packages with many slots
- High-frequency metadata access
- Memory-constrained environments

## 7. Migration Path

### 7.1. Version Detection

Packages can be identified by `format_version`:
- `"2025.0.0"` - v0 JSON format (this specification)
- Future versions will use different identifiers

### 7.2. Backward Compatibility

v0 is the initial version. Future versions will maintain the ability to read v0 JSON metadata.

## 8. Examples

### 8.1. Minimal Package

```json
{
  "format_version": "2025.0.0",
  "package": {
    "name": "hello-world",
    "version": "1.0.0"
  },
  "slots": [
    {
      "id": 0,
      "name": "app",
      "purpose": "code",
      "lifecycle": "startup", 
      "operations": "raw",
      "size": 4096,
      "checksum": "deadbeef"
    }
  ]
}
```

### 8.2. Complex Application

```json
{
  "format_version": "2025.0.0",
  "package": {
    "name": "web-server",
    "version": "2.1.0",
    "description": "High-performance web server",
    "author": "Web Corp",
    "license": "Apache-2.0"
  },
  "build": {
    "timestamp": 1704067200,
    "platform": "linux_x86_64",
    "builder": "flavorpack-0.1.0"
  },
  "slots": [
    {
      "id": 0,
      "name": "runtime",
      "purpose": "code", 
      "lifecycle": "startup",
      "operations": "tar.zst",
      "size": 15728640,
      "original_size": 52428800,
      "checksum": "a1b2c3d4",
      "permissions": "755"
    },
    {
      "id": 1,
      "name": "config",
      "purpose": "config",
      "lifecycle": "config", 
      "operations": "gzip",
      "size": 2048,
      "original_size": 8192,
      "checksum": "e5f6a7b8"
    },
    {
      "id": 2,
      "name": "assets",
      "purpose": "media",
      "lifecycle": "lazy",
      "operations": "tar.gz", 
      "size": 1048576,
      "original_size": 4194304,
      "checksum": "c9d0e1f2"
    }
  ],
  "execution": {
    "entry_point": "./bin/server",
    "args": ["--config", "config.yaml"],
    "env": {
      "LOG_LEVEL": "info"
    },
    "working_directory": "."
  }
}
```

## 9. References

- RFC 7159: The JavaScript Object Notation (JSON) Data Interchange Format
- FEP-0001: PSPF Core Format & Operation Chains
- Semantic Versioning: https://semver.org/

---
*Version: v0*