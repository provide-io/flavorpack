# FEP-0002: PSPF/2025 JSON Metadata Format Specification

**Status**: Standards Track  
**Type**: Core Protocol  
**Created**: 2025-01-08  
**Version**: v0.1  
**Category**: Standards Track  

## Abstract

This document specifies the JSON-based metadata format for PSPF/2025 packages. The metadata provides structured information about package contents, slot definitions, execution parameters, and build provenance. This specification defines the exact JSON schema, validation rules, encoding requirements, and parsing algorithms to ensure cross-language compatibility between Python, Go, and Rust implementations.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Conventions and Terminology](#2-conventions-and-terminology)
3. [JSON Metadata Structure](#3-json-metadata-structure)
4. [Field Specifications](#4-field-specifications)
5. [Validation Rules](#5-validation-rules)
6. [Encoding and Serialization](#6-encoding-and-serialization)
7. [ABNF Grammar](#7-abnf-grammar)
8. [JSON Schema Definition](#8-json-schema-definition)
9. [Processing Algorithms](#9-processing-algorithms)
10. [Error Handling](#10-error-handling)
11. [Security Considerations](#11-security-considerations)
12. [Implementation Requirements](#12-implementation-requirements)
13. [Test Vectors](#13-test-vectors)
14. [References](#14-references)

## 1. Introduction

### 1.1 Motivation

PSPF/2025 packages require structured metadata to describe their contents, execution requirements, and provenance. JSON provides an ideal balance between human readability, cross-language support, and parsing efficiency for v0 implementations. Future versions may introduce binary formats for performance-critical applications.

### 1.2 Scope

This specification defines:
- Complete JSON schema for PSPF/2025 package metadata
- Validation rules and semantic constraints
- Encoding and normalization requirements
- Cross-language parsing algorithms
- Extension mechanisms for vendor-specific fields

This specification does NOT define:
- Binary wire format (reserved for future versions)
- Network transmission protocols
- Metadata compression algorithms (handled at package level)
- Runtime behavior of metadata fields

### 1.3 Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) [RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) when, and only when, they appear in all capitals, as shown here.

### 1.4 Related Documents

- **FEP-0001**: Core binary format and operation chains
- **FEP-0003**: Operation registry and allocation policy
- **RFC 7159**: The JavaScript Object Notation (JSON) Data Interchange Format
- **RFC 4627**: JSON Media Type

## 2. Conventions and Terminology

### 2.1 Definitions

**Metadata**: Structured information describing package contents and requirements
**Slot Definition**: JSON object describing a single data slot in the package
**Operation String**: Human-readable representation of an operation chain
**Canonical Form**: Normalized JSON representation for signature verification
**Extension Field**: Vendor-specific field prefixed with "x-"

### 2.2 Notation Conventions

JSON examples use standard JSON notation with comments for clarity (comments are not valid in actual JSON):

```json
{
  "field": "value",    // Comment for documentation
  "number": 123,       // Integer value
  "array": [1, 2, 3]   // Array of integers
}
```

ABNF grammar follows [RFC5234] notation.

Regular expressions use PCRE syntax.

### 2.3 Data Type Definitions

| JSON Type | PSPF Type  | Range/Format                           |
|-----------|------------|-----------------------------------------|
| string    | identifier | `^[a-z0-9][a-z0-9_-]*$` max 255 chars |
| string    | version    | Semantic versioning or custom format   |
| string    | checksum   | Hex string, lowercase, no prefix       |
| string    | operations | Operation chain string (see Section 7) |
| number    | uint32     | 0 to 4,294,967,295                    |
| number    | uint64     | 0 to 18,446,744,073,709,551,615      |
| number    | timestamp  | Unix timestamp (seconds since epoch)   |
| string    | path       | Forward slashes, no ".." traversal     |

## 3. JSON Metadata Structure

### 3.1 Root Object

The metadata MUST be a single JSON object with the following structure:

```json
{
  "format_version": "2025.0.0",
  "package": {
    "name": "package-name",
    "version": "1.0.0",
    "description": "Package description",
    "author": "Author Name",
    "license": "License-Identifier",
    "homepage": "https://example.com"
  },
  "build": {
    "timestamp": 1704067200,
    "platform": "linux_x86_64",
    "builder": "flavorpack-0.1.0",
    "source_hash": "abc123...",
    "reproducible": true
  },
  "slots": [
    {
      "id": 0,
      "name": "slot-name",
      "purpose": "code",
      "lifecycle": "runtime",
      "operations": "tar.gz",
      "size": 1024,
      "original_size": 2048,
      "checksum": "deadbeef",
      "permissions": "755"
    }
  ],
  "execution": {
    "entry_point": "./bin/app",
    "args": ["--config", "app.conf"],
    "env": {
      "KEY": "value"
    },
    "working_directory": "."
  },
  "dependencies": {
    "runtime": ["libc.so.6"],
    "optional": ["libfoo.so.1"]
  },
  "extensions": {
    "x-vendor-field": "vendor-specific-value"
  }
}
```

### 3.2 Object Hierarchy

```
root
├── format_version* (string)
├── package* (object)
│   ├── name* (string)
│   ├── version* (string)
│   ├── description (string)
│   ├── author (string)
│   ├── license (string)
│   └── homepage (string)
├── build (object)
│   ├── timestamp (number)
│   ├── platform (string)
│   ├── builder (string)
│   ├── source_hash (string)
│   └── reproducible (boolean)
├── slots* (array)
│   └── [slot] (object)
│       ├── id* (number)
│       ├── name* (string)
│       ├── purpose* (string)
│       ├── lifecycle* (string)
│       ├── operations* (string)
│       ├── size* (number)
│       ├── original_size (number)
│       ├── checksum* (string)
│       └── permissions (string)
├── execution (object)
│   ├── entry_point (string)
│   ├── args (array of strings)
│   ├── env (object)
│   └── working_directory (string)
├── dependencies (object)
│   ├── runtime (array of strings)
│   └── optional (array of strings)
└── extensions (object)
    └── x-* (any)

* = required field
```

## 4. Field Specifications

### 4.1 Root Level Fields

#### 4.1.1 format_version (REQUIRED)

**Type**: string  
**Pattern**: `^\d{4}\.\d+\.\d+$`  
**Example**: "2025.0.0"  

Identifies the metadata format version. For v0, this MUST be "2025.0.0".

#### 4.1.2 package (REQUIRED)

**Type**: object  

Contains basic package identification and information.

#### 4.1.3 build (OPTIONAL)

**Type**: object  

Contains build-time information for reproducibility and provenance.

#### 4.1.4 slots (REQUIRED)

**Type**: array of objects  
**Min Items**: 0  
**Max Items**: 65535  

Array of slot definitions. MAY be empty for launcher-only packages.

#### 4.1.5 execution (OPTIONAL)

**Type**: object  

Runtime execution parameters and environment configuration.

#### 4.1.6 dependencies (OPTIONAL)

**Type**: object  

External dependencies required or recommended for package execution.

#### 4.1.7 extensions (OPTIONAL)

**Type**: object  

Vendor-specific extensions. All keys MUST begin with "x-".

### 4.2 Package Object Fields

#### 4.2.1 name (REQUIRED)

**Type**: string  
**Pattern**: `^[a-z0-9][a-z0-9_-]*$`  
**Min Length**: 1  
**Max Length**: 255  
**Example**: "my-application"  

Package identifier. MUST be lowercase alphanumeric with hyphens and underscores.

#### 4.2.2 version (REQUIRED)

**Type**: string  
**Pattern**: `^[0-9]+(\.[0-9]+)*([+-].+)?$`  
**Max Length**: 255  
**Example**: "1.2.3-beta+build.456"  

Package version. SHOULD follow semantic versioning but MAY use custom schemes.

#### 4.2.3 description (OPTIONAL)

**Type**: string  
**Max Length**: 4096  
**Example**: "A high-performance web server"  

Human-readable package description.

#### 4.2.4 author (OPTIONAL)

**Type**: string  
**Max Length**: 255  
**Example**: "Jane Doe <jane@example.com>"  

Package author or maintainer.

#### 4.2.5 license (OPTIONAL)

**Type**: string  
**Max Length**: 255  
**Example**: "MIT" or "Apache-2.0"  

SPDX license identifier or custom license name.

#### 4.2.6 homepage (OPTIONAL)

**Type**: string  
**Format**: URI  
**Max Length**: 2048  
**Example**: "https://example.com/project"  

Project homepage or documentation URL.

### 4.3 Slot Object Fields

#### 4.3.1 id (REQUIRED)

**Type**: number  
**Minimum**: 0  
**Maximum**: 4294967295  
**Example**: 0  

Unique slot identifier within the package. MUST be unique across all slots.

#### 4.3.2 name (REQUIRED)

**Type**: string  
**Pattern**: `^[a-zA-Z0-9][a-zA-Z0-9_.-]*$`  
**Max Length**: 255  
**Example**: "python-runtime"  

Human-readable slot name.

#### 4.3.3 purpose (REQUIRED)

**Type**: string  
**Enum**: ["code", "data", "config", "media"]  
**Example**: "code"  

Slot content classification:
- `code`: Executable binaries or scripts
- `data`: Application data files
- `config`: Configuration files
- `media`: Images, audio, video, or other media

#### 4.3.4 lifecycle (REQUIRED)

**Type**: string  
**Enum**: See table below  
**Example**: "runtime"  

| Value      | Description                              | Extraction Behavior           |
|------------|------------------------------------------|-------------------------------|
| init       | First run only, then removed            | Extract once, delete after    |
| startup    | Extract at every startup                | Always extract fresh          |
| runtime    | Extract on first use (default)          | Extract once, keep cached     |
| shutdown   | Extract during cleanup                  | Extract at termination        |
| cache      | Performance cache, can regenerate       | Extract if missing            |
| temporary  | Remove after session ends               | Extract, delete at exit       |
| lazy       | Load on-demand                          | Extract when accessed         |
| eager      | Load immediately on startup             | Extract before execution      |
| dev        | Development mode only                   | Extract if DEV flag set       |
| config     | User-modifiable config files           | Extract if not present        |
| platform   | Platform/OS specific content            | Extract if platform matches  |

#### 4.3.5 operations (REQUIRED)

**Type**: string  
**Pattern**: See Section 7  
**Example**: "tar.gz" or "tar|gzip"  

Operation chain string describing transformations applied to slot data.

#### 4.3.6 size (REQUIRED)

**Type**: number  
**Minimum**: 0  
**Maximum**: 2^53-1 (JSON safe integer)  
**Example**: 1048576  

Size of slot data as stored in package (after operations applied).

#### 4.3.7 original_size (OPTIONAL)

**Type**: number  
**Minimum**: 0  
**Maximum**: 2^53-1  
**Example**: 4194304  

Original size before operations applied. If omitted, assumed equal to `size`.

#### 4.3.8 checksum (REQUIRED)

**Type**: string
**Pattern**: `^[a-f0-9]{16}$`
**Example**: "deadbeef01234567"

SHA-256 hash of stored slot data (first 8 bytes) as 16-character hex string.

#### 4.3.9 permissions (OPTIONAL)

**Type**: string  
**Pattern**: `^[0-7]{3,4}$`  
**Example**: "755" or "0644"  

Unix-style permissions as octal string.

### 4.4 Build Object Fields

#### 4.4.1 timestamp (OPTIONAL)

**Type**: number  
**Example**: 1704067200  

Unix timestamp of package creation.

#### 4.4.2 platform (OPTIONAL)

**Type**: string  
**Pattern**: `^[a-z]+_[a-z0-9]+$`  
**Example**: "linux_x86_64", "darwin_arm64", "windows_amd64"  

Target platform identifier.

#### 4.4.3 builder (OPTIONAL)

**Type**: string  
**Max Length**: 255  
**Example**: "flavorpack-0.1.0"  

Tool and version used to create package.

#### 4.4.4 source_hash (OPTIONAL)

**Type**: string  
**Pattern**: `^[a-f0-9]{64}$`  
**Example**: "abc123..."  

SHA-256 hash of source code tree.

#### 4.4.5 reproducible (OPTIONAL)

**Type**: boolean  
**Example**: true  

Whether package was built reproducibly.

### 4.5 Execution Object Fields

#### 4.5.1 entry_point (OPTIONAL)

**Type**: string  
**Max Length**: 4096  
**Example**: "./bin/app"  

Path to main executable within extracted package.

#### 4.5.2 args (OPTIONAL)

**Type**: array of strings  
**Max Items**: 1024  
**Example**: ["--config", "app.conf"]  

Default command-line arguments.

#### 4.5.3 env (OPTIONAL)

**Type**: object  
**Max Properties**: 1024  
**Example**: {"PATH": "/app/bin:$PATH"}  

Environment variables to set. Values MAY contain variable references.

#### 4.5.4 working_directory (OPTIONAL)

**Type**: string  
**Default**: "."  
**Example**: "./data"  

Working directory for execution relative to extraction root.

## 5. Validation Rules

### 5.1 Structural Validation

The JSON document MUST:
1. Be valid JSON according to [RFC7159]
2. Have a single root object
3. Include all required fields
4. Not exceed 10MB when uncompressed
5. Use UTF-8 encoding without BOM

### 5.2 Semantic Validation

#### 5.2.1 Slot Validation

- Slot IDs MUST be unique within the package
- Slot names SHOULD be unique (warning if not)
- Slot checksums MUST be exactly 8 hex characters
- Operations strings MUST use only supported operations

#### 5.2.2 Path Validation

All path strings MUST:
- Use forward slashes as separators
- Not contain ".." components
- Not begin with "/" (relative paths only)
- Not contain null bytes
- Be valid UTF-8

#### 5.2.3 Cross-Reference Validation

- `slot.size` MUST match actual slot data size in package
- `slot.checksum` MUST match computed Adler-32 of slot data
- `execution.entry_point` SHOULD reference an extracted file

### 5.3 Extension Field Validation

Extension fields in the `extensions` object:
- MUST begin with "x-" prefix
- MAY contain any valid JSON value
- SHOULD use lowercase names with hyphens
- MUST NOT conflict with standard fields

## 6. Encoding and Serialization

### 6.1 JSON Encoding Rules

Metadata MUST be encoded as:
- UTF-8 without byte order mark (BOM)
- No trailing whitespace
- No comments (not valid JSON)
- Unix line endings (LF, not CRLF)

### 6.2 Canonical Form

For signature verification, metadata MUST be normalized to canonical form:

1. **Object Key Ordering**: All object keys MUST be sorted lexicographically
2. **Whitespace**: No unnecessary whitespace (compact form)
3. **Number Format**: No leading zeros, no trailing decimal points
4. **String Escaping**: Minimal escaping (only required characters)
5. **Unicode Normalization**: NFC normalization for all strings

Canonical encoding:
```
jsonCanonical = json.dumps(
    metadata,
    separators=(',', ':'),
    sort_keys=True,
    ensure_ascii=False
)
```

### 6.3 Compression

When stored in packages, metadata SHOULD be compressed using GZIP with:
- Compression level: 9 (best compression)
- No embedded filename or timestamp
- CRC32 verification enabled

## 7. ABNF Grammar

### 7.1 Operation String Grammar

```abnf
operation-string = simple-op / compound-op / pipe-chain

simple-op = "raw" / "gzip" / "bzip2" / "xz" / "zstd" / "tar"

compound-op = "tar.gz" / "tar.bz2" / "tar.xz" / "tar.zst" /
              "tgz" / "tbz2" / "txz"

pipe-chain = operation 1*( "|" operation )

operation = ALPHA 1*( ALPHA / DIGIT / "_" )

ALPHA = %x41-5A / %x61-7A  ; A-Z / a-z
DIGIT = %x30-39            ; 0-9
```

### 7.2 Version String Grammar

```abnf
version = major [ "." minor [ "." patch ] ] [ prerelease ] [ build ]

major = 1*DIGIT
minor = 1*DIGIT
patch = 1*DIGIT

prerelease = "-" 1*prerelease-char
build = "+" 1*build-char

prerelease-char = ALPHA / DIGIT / "-" / "."
build-char = ALPHA / DIGIT / "-" / "."
```

### 7.3 Identifier Grammar

```abnf
identifier = identifier-start *identifier-char

identifier-start = LOWER / DIGIT
identifier-char = LOWER / DIGIT / "-" / "_"

LOWER = %x61-7A  ; a-z
```

## 8. JSON Schema Definition

### 8.1 Complete JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://pspf.io/schemas/2025.0.0/metadata.json",
  "title": "PSPF/2025 Package Metadata",
  "type": "object",
  "required": ["format_version", "package", "slots"],
  "additionalProperties": false,
  "properties": {
    "format_version": {
      "type": "string",
      "const": "2025.0.0"
    },
    "package": {
      "type": "object",
      "required": ["name", "version"],
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[a-z0-9][a-z0-9_-]*$",
          "minLength": 1,
          "maxLength": 255
        },
        "version": {
          "type": "string",
          "pattern": "^[0-9]+(\\.[0-9]+)*([+-].+)?$",
          "maxLength": 255
        },
        "description": {
          "type": "string",
          "maxLength": 4096
        },
        "author": {
          "type": "string",
          "maxLength": 255
        },
        "license": {
          "type": "string",
          "maxLength": 255
        },
        "homepage": {
          "type": "string",
          "format": "uri",
          "maxLength": 2048
        }
      }
    },
    "build": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "timestamp": {
          "type": "integer",
          "minimum": 0
        },
        "platform": {
          "type": "string",
          "pattern": "^[a-z]+_[a-z0-9]+$"
        },
        "builder": {
          "type": "string",
          "maxLength": 255
        },
        "source_hash": {
          "type": "string",
          "pattern": "^[a-f0-9]{64}$"
        },
        "reproducible": {
          "type": "boolean"
        }
      }
    },
    "slots": {
      "type": "array",
      "minItems": 0,
      "maxItems": 65535,
      "items": {
        "type": "object",
        "required": ["id", "name", "purpose", "lifecycle", "operations", "size", "checksum"],
        "additionalProperties": false,
        "properties": {
          "id": {
            "type": "integer",
            "minimum": 0,
            "maximum": 4294967295
          },
          "name": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
            "maxLength": 255
          },
          "purpose": {
            "type": "string",
            "enum": ["code", "data", "config", "media"]
          },
          "lifecycle": {
            "type": "string",
            "enum": ["init", "startup", "runtime", "shutdown", "cache", 
                     "temporary", "lazy", "eager", "dev", "config", "platform"]
          },
          "operations": {
            "type": "string",
            "pattern": "^(raw|gzip|bzip2|xz|zstd|tar|tar\\.gz|tar\\.bz2|tar\\.xz|tar\\.zst|tgz|tbz2|txz|([a-z]+)(\\|[a-z]+)*)$"
          },
          "size": {
            "type": "integer",
            "minimum": 0,
            "maximum": 9007199254740991
          },
          "original_size": {
            "type": "integer",
            "minimum": 0,
            "maximum": 9007199254740991
          },
          "checksum": {
            "type": "string",
            "pattern": "^[a-f0-9]{16}$"
          },
          "permissions": {
            "type": "string",
            "pattern": "^[0-7]{3,4}$"
          }
        }
      }
    },
    "execution": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "entry_point": {
          "type": "string",
          "maxLength": 4096
        },
        "args": {
          "type": "array",
          "maxItems": 1024,
          "items": {
            "type": "string"
          }
        },
        "env": {
          "type": "object",
          "maxProperties": 1024,
          "additionalProperties": {
            "type": "string"
          }
        },
        "working_directory": {
          "type": "string",
          "maxLength": 4096
        }
      }
    },
    "dependencies": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "runtime": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "optional": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "extensions": {
      "type": "object",
      "patternProperties": {
        "^x-": {}
      },
      "additionalProperties": false
    }
  }
}
```

## 9. Processing Algorithms

### 9.1 Metadata Parsing Algorithm

```
function parseMetadata(jsonBytes):
    // 1. Decode UTF-8
    text = utf8Decode(jsonBytes)
    if error:
        return ERROR_INVALID_ENCODING
    
    // 2. Parse JSON
    try:
        metadata = jsonParse(text)
    catch:
        return ERROR_INVALID_JSON
    
    // 3. Validate against schema
    if not validateSchema(metadata, PSPF_SCHEMA):
        return ERROR_SCHEMA_VIOLATION
    
    // 4. Check format version
    if metadata.format_version != "2025.0.0":
        return ERROR_UNSUPPORTED_VERSION
    
    // 5. Validate semantic constraints
    if not validateSemantics(metadata):
        return ERROR_SEMANTIC_VIOLATION
    
    return metadata
```

### 9.2 Canonical Form Algorithm

```
function canonicalize(metadata):
    // 1. Deep copy to avoid mutation
    canonical = deepCopy(metadata)
    
    // 2. Sort all object keys recursively
    canonical = sortKeysRecursive(canonical)
    
    // 3. Normalize numbers
    canonical = normalizeNumbers(canonical)
    
    // 4. Normalize Unicode strings to NFC
    canonical = normalizeUnicode(canonical)
    
    // 5. Serialize with minimal whitespace
    json = JSON.stringify(canonical, null, 0)
    
    // 6. Ensure consistent separators
    json = json.replace(/: /g, ':')
    json = json.replace(/, /g, ',')
    
    return json
```

### 9.3 Checksum Verification Algorithm

```
function verifyMetadataChecksum(metadata, expectedHash):
    // 1. Canonicalize metadata
    canonical = canonicalize(metadata)
    
    // 2. Encode to UTF-8
    bytes = utf8Encode(canonical)
    
    // 3. Compute SHA-256
    computedHash = sha256(bytes)
    
    // 4. Compare hashes
    return constantTimeEqual(computedHash, expectedHash)
```

## 10. Error Handling

### 10.1 Error Codes

```c
// JSON Errors (1000-1099)
#define ERROR_INVALID_ENCODING      1000
#define ERROR_INVALID_JSON          1001
#define ERROR_SCHEMA_VIOLATION      1002
#define ERROR_UNSUPPORTED_VERSION   1003
#define ERROR_SEMANTIC_VIOLATION    1004

// Field Errors (1100-1199)
#define ERROR_MISSING_REQUIRED      1100
#define ERROR_INVALID_TYPE          1101
#define ERROR_INVALID_PATTERN       1102
#define ERROR_INVALID_ENUM          1103
#define ERROR_OUT_OF_RANGE          1104

// Slot Errors (1200-1299)
#define ERROR_DUPLICATE_SLOT_ID     1200
#define ERROR_INVALID_OPERATIONS    1201
#define ERROR_CHECKSUM_MISMATCH     1202
#define ERROR_SIZE_MISMATCH         1203

// Path Errors (1300-1399)
#define ERROR_PATH_TRAVERSAL        1300
#define ERROR_INVALID_PATH          1301
#define ERROR_ABSOLUTE_PATH         1302
```

### 10.2 Error Recovery

Implementations SHOULD attempt graceful degradation:

1. **Missing Optional Fields**: Use defaults where sensible
2. **Unknown Extension Fields**: Ignore "x-" prefixed fields
3. **Version Mismatch**: Attempt compatibility if minor version
4. **Encoding Issues**: Try alternative encodings (UTF-16, Latin-1)

### 10.3 Diagnostic Output

Error messages MUST include:
- Error code
- Field path (e.g., "slots[2].checksum")
- Expected vs actual values
- Line/column number if available

Example:
```json
{
  "error": 1102,
  "field": "slots[2].checksum",
  "message": "Invalid pattern",
  "expected": "^[a-f0-9]{8}$",
  "actual": "DEADBEEF",
  "line": 45,
  "column": 23
}
```

## 11. Security Considerations

### 11.1 Input Validation

Implementations MUST protect against:

**JSON Bombs**: Deeply nested structures or large expansions
- Maximum nesting depth: 100 levels
- Maximum string length: 10MB
- Maximum array size: 65535 items
- Maximum object properties: 10000

**Resource Exhaustion**: 
- Limit total metadata size to 10MB uncompressed
- Timeout parsing after 5 seconds
- Limit memory usage during parsing

**Injection Attacks**:
- Sanitize all strings before use in commands
- Validate paths to prevent directory traversal
- Escape special characters in environment variables

### 11.2 Trust Boundaries

Metadata is untrusted input until verified:

1. Parse and validate structure
2. Verify metadata checksum from index block
3. Verify package signature
4. Only then trust content

### 11.3 Information Disclosure

Sensitive information in metadata:
- Build paths may reveal system layout
- Environment variables may contain secrets
- Source hashes may reveal proprietary code structure

Implementations SHOULD:
- Redact sensitive paths in logs
- Not expose full metadata to untrusted code
- Sanitize error messages

## 12. Implementation Requirements

### 12.1 Parser Requirements

All implementations MUST:
1. Accept any valid JSON according to schema
2. Reject invalid JSON with appropriate errors
3. Handle UTF-8, UTF-16, and UTF-32 encodings
4. Support full Unicode range including emoji
5. Parse numbers up to 2^53-1 accurately

### 12.2 Cross-Language Compatibility

#### Python Implementation
```python
import json
import jsonschema
from typing import Dict, Any

def parse_metadata(data: bytes) -> Dict[str, Any]:
    """Parse and validate PSPF metadata."""
    text = data.decode('utf-8')
    metadata = json.loads(text)
    jsonschema.validate(metadata, PSPF_SCHEMA)
    return metadata

def canonicalize(metadata: Dict[str, Any]) -> bytes:
    """Convert to canonical form."""
    return json.dumps(
        metadata,
        separators=(',', ':'),
        sort_keys=True,
        ensure_ascii=False
    ).encode('utf-8')
```

#### Go Implementation
```go
package pspf

import (
    "encoding/json"
    "github.com/xeipuuv/gojsonschema"
)

type Metadata struct {
    FormatVersion string   `json:"format_version"`
    Package      Package  `json:"package"`
    Slots        []Slot   `json:"slots"`
    // ... other fields
}

func ParseMetadata(data []byte) (*Metadata, error) {
    var meta Metadata
    if err := json.Unmarshal(data, &meta); err != nil {
        return nil, err
    }
    
    // Validate against schema
    result, err := ValidateSchema(meta)
    if err != nil || !result.Valid() {
        return nil, ErrSchemaViolation
    }
    
    return &meta, nil
}
```

#### Rust Implementation
```rust
use serde::{Deserialize, Serialize};
use serde_json;
use jsonschema;

#[derive(Debug, Deserialize, Serialize)]
struct Metadata {
    format_version: String,
    package: Package,
    slots: Vec<Slot>,
    // ... other fields
}

fn parse_metadata(data: &[u8]) -> Result<Metadata, Error> {
    let text = std::str::from_utf8(data)?;
    let metadata: Metadata = serde_json::from_str(text)?;
    
    // Validate against schema
    let schema = json!(PSPF_SCHEMA);
    let compiled = jsonschema::JSONSchema::compile(&schema)?;
    compiled.validate(&json!(metadata))?;
    
    Ok(metadata)
}
```

### 12.3 Performance Requirements

Implementations SHOULD meet these targets:

- **Parsing**: < 10ms for 100KB metadata
- **Validation**: < 5ms for schema validation
- **Canonicalization**: < 2ms for typical metadata
- **Memory Usage**: < 10x metadata size

## 13. Test Vectors

### 13.1 Minimal Valid Metadata

**Input**:
```json
{
  "format_version": "2025.0.0",
  "package": {
    "name": "test",
    "version": "1.0.0"
  },
  "slots": []
}
```

**Canonical Form** (hex):
```
7b22666f726d61745f76657273696f6e223a22323032352e302e30222c227061636b616765223a7b226e616d65223a2274657374222c2276657273696f6e223a22312e302e30227d2c22736c6f7473223a5b5d7d
```

**SHA-256**: `5f95b7cf2f47fc5b7866ea021fe51cea6bc3bbceb9d3eb87a1244bd8db576eb0`

### 13.2 Complete Metadata Example

**Input**:
```json
{
  "format_version": "2025.0.0",
  "package": {
    "name": "example-app",
    "version": "2.1.0-beta+build.123",
    "description": "Example application",
    "author": "PSPF Team",
    "license": "MIT",
    "homepage": "https://pspf.io"
  },
  "build": {
    "timestamp": 1704067200,
    "platform": "linux_x86_64",
    "builder": "flavorpack-0.1.0",
    "source_hash": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
    "reproducible": true
  },
  "slots": [
    {
      "id": 0,
      "name": "runtime",
      "purpose": "code",
      "lifecycle": "startup",
      "operations": "tar.gz",
      "size": 1048576,
      "original_size": 4194304,
      "checksum": "deadbeef",
      "permissions": "755"
    },
    {
      "id": 1,
      "name": "config",
      "purpose": "config",
      "lifecycle": "config",
      "operations": "gzip",
      "size": 1024,
      "checksum": "cafebabe"
    }
  ],
  "execution": {
    "entry_point": "./bin/app",
    "args": ["--config", "/etc/app.conf"],
    "env": {
      "APP_HOME": "/opt/app",
      "LOG_LEVEL": "info"
    },
    "working_directory": "."
  },
  "dependencies": {
    "runtime": ["libc.so.6", "libssl.so.3"],
    "optional": ["libcuda.so.12"]
  },
  "extensions": {
    "x-vendor-signature": "xyz789",
    "x-custom-field": {
      "nested": "value"
    }
  }
}
```

### 13.3 Invalid Examples

**Duplicate Slot ID**:
```json
{
  "format_version": "2025.0.0",
  "package": {"name": "test", "version": "1.0.0"},
  "slots": [
    {"id": 0, "name": "slot1", ...},
    {"id": 0, "name": "slot2", ...}  // ERROR: Duplicate ID
  ]
}
```
Expected Error: `ERROR_DUPLICATE_SLOT_ID (1200)`

**Invalid Operation String**:
```json
{
  "format_version": "2025.0.0",
  "package": {"name": "test", "version": "1.0.0"},
  "slots": [{
    "id": 0,
    "operations": "invalid|operation",  // ERROR: Unknown operation
    ...
  }]
}
```
Expected Error: `ERROR_INVALID_OPERATIONS (1201)`

**Path Traversal Attempt**:
```json
{
  "execution": {
    "entry_point": "../../etc/passwd"  // ERROR: Path traversal
  }
}
```
Expected Error: `ERROR_PATH_TRAVERSAL (1300)`

## 14. References

### 14.1 Normative References

[RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.

[RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.

[RFC7159] Bray, T., Ed., "The JavaScript Object Notation (JSON) Data Interchange Format", RFC 7159, March 2014.

[RFC5234] Crocker, D., Ed., and P. Overell, "Augmented BNF for Syntax Specifications: ABNF", STD 68, RFC 5234, January 2008.

[RFC4627] Crockford, D., "The application/json Media Type for JavaScript Object Notation (JSON)", RFC 4627, July 2006.

### 14.2 Informative References

[FEP-0001] "PSPF/2025 Core Format & Operation Chains Specification", FEP-0001, January 2025.

[FEP-0003] "PSPF/2025 Operation Registry and Allocation Policy", FEP-0003, January 2025.

[JSON-SCHEMA] "JSON Schema: A Media Type for Describing JSON Documents", draft-handrews-json-schema-02, September 2019.

[SEMVER] Preston-Werner, T., "Semantic Versioning 2.0.0", https://semver.org/spec/v2.0.0.html

[SPDX] "Software Package Data Exchange (SPDX) Specification", https://spdx.org/specifications

---

**Authors' Addresses**

[Author contact information]

**Copyright Notice**

Copyright (c) 2025 IETF Trust and the persons identified as the document authors. All rights reserved.