# FEP-0002: PSPF/2025 JSON Metadata Format Specification

**Status**: Standards Track  
**Type**: Core Protocol  
**Created**: 2025-01-08  
**Updated**: 2026-09-01  
**Version**: v0.2  
**Category**: Standards Track  

## Abstract

This document specifies the JSON metadata document carried by PSPF/2025 packages. The metadata names the package, describes each data slot, states how the package is executed, and records how it was built and how it is verified. It is the structure the Python, Go and Rust implementations read to answer what a package is and what it contains.

This specification defines the document's fields, their types, which of them a reader may rely on, the encoding under which the document is stored, and the JSON Schema that a conforming document satisfies. The schema in Section 8 is checked against the packages in `tests/fixtures/format_compat/`, which are built by all three implementations.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Conventions and Terminology](#2-conventions-and-terminology)
3. [Document Structure](#3-document-structure)
4. [Field Specifications](#4-field-specifications)
5. [Validation Rules](#5-validation-rules)
6. [Encoding and Storage](#6-encoding-and-storage)
7. [Identifier and Version Grammar](#7-identifier-and-version-grammar)
8. [JSON Schema Definition](#8-json-schema-definition)
9. [Producer Variation](#9-producer-variation)
10. [Processing Algorithms](#10-processing-algorithms)
11. [Error Handling](#11-error-handling)
12. [Security Considerations](#12-security-considerations)
13. [Implementation Requirements](#13-implementation-requirements)
14. [Test Vectors](#14-test-vectors)
15. [References](#15-references)

## 1. Introduction

### 1.1 Motivation

A PSPF/2025 package is a launcher binary followed by data slots and an 8192-byte index (FEP-0001). The index carries offsets, sizes and checksums — the numbers needed to find and verify bytes. It carries no names, no descriptions and no instructions.

The metadata document supplies those. It is what lets a reader report that a file is `myapp v2.1.0`, list its slots and their purposes, name the command it runs, and state whether it is signed — without extracting anything and without executing the launcher.

JSON is used because three implementations in three languages must agree on it, and because the document is small enough that parsing cost does not matter next to the slot data it describes.

### 1.2 Scope

This document specifies:

- the fields of the metadata document, their types and their optionality
- the validation a reader performs before trusting the document
- the encoding and compression under which the document is stored
- a JSON Schema that a conforming document satisfies
- the points on which the three implementations differ

This document does not specify:

- the binary container, index layout or slot descriptors — FEP-0001
- operation codes and their semantics — FEP-0003
- the attestation slot, signing keys and policy evaluation — FEP-0004

### 1.3 Requirements Language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY and OPTIONAL are to be interpreted as described in [RFC2119].

A field marked REQUIRED is one every conforming producer writes and every reader may rely on. A field marked OPTIONAL may be absent, and a reader MUST behave correctly when it is.

### 1.4 Related Documents

| Document | Covers |
|----------|--------|
| FEP-0001 | Binary container, magic trailer, index block, slot descriptors |
| FEP-0003 | Operation registry and operation codes |
| FEP-0004 | Security attestation, signing keys, package policy |

## 2. Conventions and Terminology

### 2.1 Definitions

**Package**: A single file containing a launcher, slots, and a magic trailer.

**Slot**: One addressable region of package data, described by both a binary descriptor in the index and an entry in the `slots` array of this document.

**Metadata document**: The JSON object this specification defines.

**Metadata archive**: The metadata document as stored in the package — UTF-8 JSON, gzip-compressed. The index's metadata checksum covers these bytes.

**Workenv**: The directory a launcher extracts into at run time.

**Producer**: An implementation that writes packages. Three exist: `flavor-python`, `flavor-go`, `flavor-rs`.

**Reader**: An implementation that parses a metadata document.

### 2.2 Notation Conventions

Field paths use dots: `package.name`, `slots[].checksum`.

JSON examples are shown indented for readability. The stored form is not indented (Section 6).

### 2.3 Data Type Definitions

| Type | JSON representation | Notes |
|------|---------------------|-------|
| string | string | UTF-8 |
| integer | number | No fractional part |
| boolean | boolean | |
| object | object | |
| array | array | |
| checksum | string | `"<algorithm>:<hex>"`, e.g. `"sha256:34c4e0…"` |
| timestamp | string | RFC3339 |
| mode | string | Octal, quoted: `"0755"` |

## 3. Document Structure

### 3.1 Root Object

A complete document, taken from a package built by `flavor-rs`:

```json
{
  "format": "PSPF/2025",
  "format_version": "1.0.0",
  "package": {
    "name": "format-compat-fixture",
    "version": "1.0.0"
  },
  "slots": [
    {
      "slot": 0,
      "id": "payload",
      "source": "/build/inputs/payload.txt",
      "target": "data/payload.txt",
      "size": 125,
      "checksum": "sha256:34c4e0f57a67a89825fd5e3c48e70c535ade2032de5ac3698fea31def5a13454",
      "operations": "",
      "purpose": "data",
      "lifecycle": "runtime",
      "permissions": "0644",
      "resolution": "build"
    }
  ],
  "execution": {
    "primary_slot": 0,
    "command": "true",
    "env": {}
  },
  "verification": {
    "integrity_seal": {
      "required": true,
      "algorithm": "ed25519"
    },
    "signed": true,
    "require_verification": true
  },
  "build": {
    "tool": "flavor-rs",
    "tool_version": "0.4.6",
    "timestamp": "2026-08-31T21:05:39.665548+00:00",
    "deterministic": true,
    "platform": {
      "os": "macos",
      "arch": "aarch64",
      "host": "macos/aarch64 build-host.local"
    }
  },
  "launcher": {
    "tool": "launcher-stub.sh",
    "tool_version": "0.4.6",
    "size": 503,
    "checksum": "sha256:02b29c4db29e4141af819c700414368a14d89ea6e9bddd66760a61b706643d21",
    "capabilities": ["mmap", "signed"]
  },
  "compatibility": {
    "min_format_version": "1.0.0",
    "features": []
  },
  "setup_commands": []
}
```

### 3.2 Object Hierarchy

```
metadata (object)
├── format (string, REQUIRED)
├── format_version (string, OPTIONAL)
├── package (object, REQUIRED)
│   ├── name (string, REQUIRED)
│   ├── version (string, REQUIRED)
│   └── description (string, OPTIONAL)
├── slots (array, REQUIRED)
│   └── [] (object)
│       ├── slot (integer, REQUIRED)
│       ├── id (string, REQUIRED)
│       ├── source (string, REQUIRED)
│       ├── target (string, REQUIRED)
│       ├── size (integer, REQUIRED)
│       ├── checksum (string, REQUIRED)
│       ├── operations (string, REQUIRED)
│       ├── purpose (string, REQUIRED)
│       ├── lifecycle (string, REQUIRED)
│       ├── permissions (string|null, OPTIONAL)
│       ├── resolution (string, OPTIONAL)
│       └── self_ref (boolean, OPTIONAL)
├── execution (object, REQUIRED for interoperability — see §9.1)
│   ├── primary_slot (integer, OPTIONAL, default 0)
│   ├── command (string, REQUIRED)
│   └── env (object, OPTIONAL, default {})
├── verification (object, OPTIONAL)
│   ├── integrity_seal (object, REQUIRED within)
│   │   ├── required (boolean, REQUIRED)
│   │   └── algorithm (string, REQUIRED)
│   ├── signed (boolean, OPTIONAL, default false)
│   ├── require_verification (boolean, OPTIONAL, default true)
│   └── trust_signatures (object, OPTIONAL)
├── build (object, OPTIONAL)
├── launcher (object, OPTIONAL)
├── compatibility (object, OPTIONAL)
├── cache_validation (object, OPTIONAL)
├── runtime (object, OPTIONAL)
├── workenv (object, OPTIONAL)
├── setup_commands (array, OPTIONAL, default [])
└── policy (object, OPTIONAL — FEP-0004)
```

Readers ignore members they do not recognise. A producer MAY add fields; a reader MUST NOT fail on them.

## 4. Field Specifications

### 4.1 Root Level Fields

#### 4.1.1 format (REQUIRED)

**Type**: string  
**Value**: `"PSPF/2025"`

Names the format. Every producer writes this exact string.

#### 4.1.2 format_version (OPTIONAL)

**Type**: string  
**Example**: `"1.0.0"`

Version of the metadata structure. Readers treat an absent or empty value as unversioned and fall back on `format`. See §9.2.

#### 4.1.3 package (REQUIRED)

**Type**: object

Identity of the package. Section 4.2.

#### 4.1.4 slots (REQUIRED)

**Type**: array of objects  
**Min Items**: 0

One entry per data slot, in index order. MAY be empty for a package that carries no slots. Section 4.3.

#### 4.1.5 execution (REQUIRED for interoperability)

**Type**: object

How the package runs. Section 4.4.

Two of the three implementations treat this object as optional and refuse at the point of execution when it is absent; the Rust reader requires it to parse the document at all. A producer that intends its packages to be readable by every implementation MUST write it. See §9.1.

#### 4.1.6 verification (OPTIONAL)

**Type**: object

What verification the package declares for itself. Section 4.5.

#### 4.1.7 build (OPTIONAL)

**Type**: object

Provenance: which tool built the package, when, and on what platform. Section 4.6.

#### 4.1.8 launcher (OPTIONAL)

**Type**: object

The launcher binary prefixed to the package. Section 4.7.

#### 4.1.9 compatibility (OPTIONAL)

**Type**: object

The minimum format version and the feature names a reader needs. Section 4.8.

#### 4.1.10 cache_validation (OPTIONAL)

**Type**: object

A file and expected content a launcher checks to decide whether an existing workenv is still good. Section 4.9.

#### 4.1.11 runtime (OPTIONAL)

**Type**: object

Environment manipulation applied to the process the launcher starts. Section 4.10.

#### 4.1.12 workenv (OPTIONAL)

**Type**: object

Directories to create in the workenv and environment variables scoped to it. Section 4.11.

#### 4.1.13 setup_commands (OPTIONAL)

**Type**: array  
**Default**: `[]`

Commands run after extraction and before the main command.

#### 4.1.14 policy (OPTIONAL)

**Type**: object

Package-declared execution policy. Its contents are specified by FEP-0004 §8; this document treats the value as opaque and preserves it verbatim.

### 4.2 Package Object Fields

#### 4.2.1 name (REQUIRED)

**Type**: string  
**Example**: `"myapp"`

Package name. Section 7.1 gives the recommended grammar.

#### 4.2.2 version (REQUIRED)

**Type**: string  
**Example**: `"2.1.0"`

Package version. Section 7.2 gives the recommended grammar.

#### 4.2.3 description (OPTIONAL)

**Type**: string

Human-readable summary.

### 4.3 Slot Object Fields

Each entry describes one slot. The binary slot descriptor in the index (FEP-0001) is authoritative for offsets, sizes and the packed operation chain; this entry supplies the names and intent.

#### 4.3.1 slot (REQUIRED)

**Type**: integer  
**Minimum**: 0

Index of the slot. Validates position: the entry at array position *n* has `slot` equal to *n*.

#### 4.3.2 id (REQUIRED)

**Type**: string  
**Example**: `"payload"`

Identifier for the slot, unique within the package.

#### 4.3.3 source (REQUIRED)

**Type**: string

Path the slot content was read from at build time. Provenance only; a reader MUST NOT resolve it. It records a path on the build machine and has no meaning on the machine running the package. MAY be empty for a slot the producer synthesised.

#### 4.3.4 target (REQUIRED)

**Type**: string  
**Example**: `"data/payload.txt"`

Where the slot is written inside the workenv. Section 5.2.2 constrains the value.

#### 4.3.5 size (REQUIRED)

**Type**: integer  
**Minimum**: 0

Size in bytes of the slot as stored — after any operations in the chain have been applied.

#### 4.3.6 checksum (REQUIRED)

**Type**: string  
**Example**: `"sha256:34c4e0f57a67a89825fd5e3c48e70c535ade2032de5ac3698fea31def5a13454"`

Digest of the stored slot bytes, in `algorithm:hex` form.

#### 4.3.7 operations (REQUIRED)

**Type**: string  
**Examples**: `""`, `"gzip"`, `"tar|gzip"`, `"none"`

The operation chain applied to the slot, as a descriptive label. The empty string and `"none"` both denote a slot stored verbatim.

The authoritative chain is the packed operation codes in the binary slot descriptor (FEP-0001), registered in FEP-0003. A reader that extracts slots MUST use the packed codes. This field is for display.

#### 4.3.8 purpose (REQUIRED)

**Type**: string

What the slot holds. Producers use `code`, `data`, `config` and `media`; readers accept any string.

#### 4.3.9 lifecycle (REQUIRED)

**Type**: string

When the slot is extracted and how long it survives. Producers use the values below; readers accept any string.

| Value | Meaning |
|-------|---------|
| `runtime` | Extract on first use, keep cached |
| `startup` | Extract fresh at every start |
| `init` | Extract once, remove after first run |
| `eager` | Extract before execution begins |
| `lazy` | Extract when first accessed |
| `cache` | Regenerable; extract if missing |
| `temporary` | Remove when the session ends |
| `attestation` | Attestation payload (FEP-0004) |

#### 4.3.10 permissions (OPTIONAL)

**Type**: string or null  
**Example**: `"0644"`

Unix mode for the extracted file, as a quoted octal string. `null` and absence both mean the reader chooses. Ignored on platforms without Unix modes.

#### 4.3.11 resolution (OPTIONAL)

**Type**: string  
**Values**: `"build"`, `"runtime"`, `"lazy"`

When the slot content was or will be resolved.

#### 4.3.12 self_ref (OPTIONAL)

**Type**: boolean

True when the slot refers to the launcher binary itself rather than to separate stored bytes.

### 4.4 Execution Object Fields

#### 4.4.1 command (REQUIRED)

**Type**: string  
**Example**: `"{workenv}/bin/app --config {workenv}/etc/app.conf"`

The command line the launcher runs after extraction. Placeholders are substituted first:

| Placeholder | Substitution |
|-------------|--------------|
| `{workenv}` | Absolute path of the workenv directory |
| `{slot:N}` | Extracted path of slot *N* |

#### 4.4.2 primary_slot (OPTIONAL)

**Type**: integer  
**Default**: `0`  
**Minimum**: 0

Index of the slot the package treats as its principal content. Absence is equivalent to `0`.

#### 4.4.3 env (OPTIONAL)

**Type**: object, string values  
**Default**: `{}`  
**Example**: `{"MODE": "prod"}`

Environment variables set for the command. Values MAY contain the placeholders listed in §4.4.1.

`env` is the key. A reader MUST read the environment from it.

### 4.5 Verification Object Fields

#### 4.5.1 integrity_seal (REQUIRED within `verification`)

**Type**: object

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `required` | boolean | Yes | Whether the seal must be present and valid |
| `algorithm` | string | Yes | Signature algorithm, e.g. `"ed25519"` |

Declares the package's integrity seal. The seal itself lives in the index (FEP-0001); verifying it is specified by FEP-0004.

This object states what the package asks of a reader. It is not evidence: a reader MUST NOT treat `required: true` or `signed: true` as showing that a valid signature exists. Only checking the seal in the index shows that.

#### 4.5.2 signed (OPTIONAL)

**Type**: boolean  
**Default**: `false`

Whether the producer signed the package.

#### 4.5.3 require_verification (OPTIONAL)

**Type**: boolean  
**Default**: `true`

Whether a launcher refuses to run the package when verification fails.

#### 4.5.4 trust_signatures (OPTIONAL)

**Type**: object

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `required` | boolean | Yes | Whether a trusted signature must be present |
| `signers` | array | No | Accepted signers; defaults to `[]` |

Each entry of `signers`:

| Field | Type | Required |
|-------|------|----------|
| `name` | string | Yes |
| `key_id` | string | Yes |
| `algorithm` | string | Yes |

### 4.6 Build Object Fields

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `tool` | string | Yes | Producer name, e.g. `"flavor-rs"` |
| `tool_version` | string | Yes | Producer version |
| `timestamp` | string | Yes | RFC3339 build time |
| `deterministic` | boolean | No | Defaults to `false` |
| `platform` | object | Yes | Build platform |

`platform`:

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `os` | string | Yes | Build operating system |
| `arch` | string | Yes | Build architecture |
| `host` | string | No | Build host identity |

`host` names the machine that built the package. Producers write it only when `FLAVOR_INCLUDE_BUILD_HOST=1` is set, since it is an identifier a package need not carry. See §12.3.

The values of `os` and `arch` are producer-defined strings and are not comparable between producers. See §9.3.

### 4.7 Launcher Object Fields

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `tool` | string | Yes | Launcher implementation name |
| `tool_version` | string | Yes | Launcher version |
| `size` | integer | Yes | Launcher size in bytes |
| `checksum` | string | Yes | Digest of the launcher bytes, `algorithm:hex` |
| `capabilities` | array of strings | Yes | Capability names, e.g. `["mmap", "signed"]` |

`size` MUST equal the launcher size recorded in the index (FEP-0001), which is the value verification uses.

### 4.8 Compatibility Object Fields

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `min_format_version` | string | Yes | Lowest format version that can read the package |
| `features` | array of strings | Yes | Feature names a reader needs; MAY be empty |

### 4.9 Cache Validation Object Fields

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `check_file` | string | Yes | Path within the workenv to read |
| `expected_content` | string | No | Content that marks the workenv current |

A launcher reads `check_file` in an existing workenv and re-extracts when the content does not match.

### 4.10 Runtime Object Fields

**Type**: object with a single OPTIONAL member, `env`.

`runtime.env` directs how the launcher builds the environment of the command, distinct from `execution.env`, which only adds variables:

| Field | Type | Meaning |
|-------|------|---------|
| `set` | object | Variables to set, overriding any inherited value |
| `map` | object | Variables to rename, mapping source name to target name |
| `unset` | array of strings | Variables to remove |
| `pass` | array of strings | Variables to inherit; others are dropped |

All four are OPTIONAL.

### 4.11 Workenv Object Fields

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `directories` | array of objects | No | Directories to create before extraction |
| `env` | object | No | Environment variables scoped to the workenv |

Each entry of `directories`:

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `path` | string | Yes | Directory path, MAY contain `{workenv}` |
| `mode` | string | No | Octal mode, e.g. `"0700"` |

## 5. Validation Rules

### 5.1 Structural Validation

The stored document MUST:

1. Be valid JSON per [RFC7159]
2. Have a single object at its root
3. Contain every REQUIRED field
4. Be UTF-8 without a byte order mark
5. Not exceed 10 MB when decompressed

### 5.2 Semantic Validation

#### 5.2.1 Slot Validation

1. `slots[n].slot` MUST equal *n*
2. `slots[].id` MUST be unique within the package
3. The length of `slots` MUST equal the slot count in the index
4. `slots[].size` MUST equal the size in the corresponding slot descriptor
5. `slots[].checksum` MUST match the digest of the stored slot bytes

Items 3 to 5 compare this document against the index. A mismatch means the two disagree about the same package and the reader MUST reject it.

#### 5.2.2 Path Validation

`slots[].target` and `workenv.directories[].path` MUST NOT:

1. Be absolute after placeholder substitution
2. Contain a `..` component
3. Resolve outside the workenv root
4. Contain a NUL byte

A reader MUST check these after substitution, not before: a placeholder can expand into a traversal.

#### 5.2.3 Cross-Reference Validation

1. `execution.primary_slot`, when it names a slot, MUST be a valid index into `slots`
2. `{slot:N}` in `execution.command` MUST name a valid index
3. `launcher.size` MUST equal the launcher size in the index

### 5.3 Unknown Field Handling

A reader MUST ignore members it does not recognise, at every level. This is what lets a package written by a newer producer stay readable.

## 6. Encoding and Storage

### 6.1 JSON Encoding

The document MUST be encoded as:

- UTF-8, no byte order mark
- No comments
- LF line endings where any are present

Producers write the document compactly, without indentation.

### 6.2 Compression

The document is gzip-compressed before storage. The compressed bytes are the metadata archive, and they begin with the gzip magic `1f 8b`. A reader detects that magic and decompresses; a document stored without compression is read as-is.

### 6.3 Integrity

The index records `metadata_checksum`, the SHA-256 of the **stored archive bytes** — the gzip-compressed form, exactly as it sits in the file.

A reader verifying the metadata MUST hash the stored bytes. It MUST NOT re-serialise the document, re-order keys, or re-compress it before hashing: gzip output is not reproducible across compressors and JSON serialisation is not reproducible across languages, so any of those produces a digest that does not match.

The Ed25519 integrity seal covers the index, which carries this checksum. The metadata is therefore sealed through the index rather than signed directly.

## 7. Identifier and Version Grammar

The grammars here describe what producers generate. Readers accept any string, so a document that departs from them is still readable; a producer SHOULD follow them.

### 7.1 Package Name

```abnf
package-name = name-start *name-char

name-start = LOWER / DIGIT
name-char  = LOWER / DIGIT / "-" / "_"

LOWER = %x61-7A  ; a-z
DIGIT = %x30-39  ; 0-9
```

### 7.2 Version String

```abnf
version = major [ "." minor [ "." patch ] ] [ prerelease ] [ build ]

major = 1*DIGIT
minor = 1*DIGIT
patch = 1*DIGIT

prerelease = "-" 1*prerelease-char
build      = "+" 1*build-char

prerelease-char = ALPHA / DIGIT / "-" / "."
build-char      = ALPHA / DIGIT / "-" / "."
```

### 7.3 Slot Identifier

```abnf
slot-id = slot-id-start *slot-id-char

slot-id-start = LOWER / DIGIT / "_"
slot-id-char  = LOWER / DIGIT / "-" / "_"
```

A leading underscore marks a slot the producer synthesised rather than one the caller supplied. `_attestation` (FEP-0004) is the one in use.

### 7.4 Checksum

```abnf
checksum  = algorithm ":" hex
algorithm = 1*( LOWER / DIGIT )
hex       = 1*HEXDIG
```

The prefix appears exactly once. `"sha256:sha256:…"` is malformed. See §9.4.

## 8. JSON Schema Definition

The schema below is satisfied by every package in `tests/fixtures/format_compat/`, which covers all three producers.

`additionalProperties` is not constrained: §5.3 requires readers to tolerate unknown members, and a schema that forbade them would reject documents this specification requires readers to accept.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://provide.io/schemas/pspf-2025/metadata.json",
  "title": "PSPF/2025 Package Metadata",
  "type": "object",
  "required": ["format", "package", "slots"],
  "properties": {
    "format": { "type": "string", "const": "PSPF/2025" },
    "format_version": { "type": "string" },
    "package": {
      "type": "object",
      "required": ["name", "version"],
      "properties": {
        "name": { "type": "string", "minLength": 1, "maxLength": 255 },
        "version": { "type": "string", "minLength": 1, "maxLength": 255 },
        "description": { "type": "string" }
      }
    },
    "slots": {
      "type": "array",
      "maxItems": 65535,
      "items": {
        "type": "object",
        "required": [
          "slot", "id", "source", "target",
          "size", "checksum", "operations", "purpose", "lifecycle"
        ],
        "properties": {
          "slot": { "type": "integer", "minimum": 0 },
          "id": { "type": "string", "minLength": 1, "maxLength": 255 },
          "source": { "type": "string", "maxLength": 4096 },
          "target": { "type": "string", "maxLength": 4096 },
          "size": { "type": "integer", "minimum": 0 },
          "checksum": { "type": "string", "pattern": "^[a-z0-9]+:[0-9a-fA-F]+$|^[0-9a-fA-F]+$" },
          "operations": { "type": "string" },
          "purpose": { "type": "string" },
          "lifecycle": { "type": "string" },
          "permissions": { "type": ["string", "null"] },
          "resolution": { "type": "string", "enum": ["build", "runtime", "lazy"] },
          "self_ref": { "type": "boolean" }
        }
      }
    },
    "execution": {
      "type": "object",
      "required": ["command"],
      "properties": {
        "primary_slot": { "type": "integer", "minimum": 0 },
        "command": { "type": "string", "maxLength": 65535 },
        "env": { "type": "object", "additionalProperties": { "type": "string" } }
      }
    },
    "verification": {
      "type": "object",
      "required": ["integrity_seal"],
      "properties": {
        "integrity_seal": {
          "type": "object",
          "required": ["required", "algorithm"],
          "properties": {
            "required": { "type": "boolean" },
            "algorithm": { "type": "string" }
          }
        },
        "signed": { "type": "boolean" },
        "require_verification": { "type": "boolean" },
        "trust_signatures": {
          "type": "object",
          "required": ["required"],
          "properties": {
            "required": { "type": "boolean" },
            "signers": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["name", "key_id", "algorithm"],
                "properties": {
                  "name": { "type": "string" },
                  "key_id": { "type": "string" },
                  "algorithm": { "type": "string" }
                }
              }
            }
          }
        }
      }
    },
    "build": {
      "type": "object",
      "required": ["tool", "tool_version", "timestamp", "platform"],
      "properties": {
        "tool": { "type": "string" },
        "tool_version": { "type": "string" },
        "timestamp": { "type": "string" },
        "deterministic": { "type": "boolean" },
        "platform": {
          "type": "object",
          "required": ["os", "arch"],
          "properties": {
            "os": { "type": "string" },
            "arch": { "type": "string" },
            "host": { "type": "string" }
          }
        }
      }
    },
    "launcher": {
      "type": "object",
      "required": ["tool", "tool_version", "size", "checksum", "capabilities"],
      "properties": {
        "tool": { "type": "string" },
        "tool_version": { "type": "string" },
        "size": { "type": "integer", "minimum": 0 },
        "checksum": { "type": "string" },
        "capabilities": { "type": "array", "items": { "type": "string" } }
      }
    },
    "compatibility": {
      "type": "object",
      "required": ["min_format_version", "features"],
      "properties": {
        "min_format_version": { "type": "string" },
        "features": { "type": "array", "items": { "type": "string" } }
      }
    },
    "cache_validation": {
      "type": "object",
      "required": ["check_file"],
      "properties": {
        "check_file": { "type": "string" },
        "expected_content": { "type": "string" }
      }
    },
    "runtime": {
      "type": "object",
      "properties": {
        "env": {
          "type": "object",
          "properties": {
            "set": { "type": "object", "additionalProperties": { "type": "string" } },
            "map": { "type": "object", "additionalProperties": { "type": "string" } },
            "unset": { "type": "array", "items": { "type": "string" } },
            "pass": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    },
    "workenv": {
      "type": "object",
      "properties": {
        "directories": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["path"],
            "properties": {
              "path": { "type": "string" },
              "mode": { "type": "string" }
            }
          }
        },
        "env": { "type": "object", "additionalProperties": { "type": "string" } }
      }
    },
    "setup_commands": { "type": "array" },
    "policy": { "type": "object" }
  }
}
```

## 9. Producer Variation

The three implementations do not agree on everything. Each item below is a difference a reader encounters in packages that exist, with the issue tracking it. A producer aiming for packages every implementation can read should follow the guidance in each.

### 9.1 The execution block

`flavor-go` declares `execution` optional and refuses at the point of execution when it is missing. `flavor-python` behaves the same way. `flavor-rs` requires the object to parse the document at all, so a package without one cannot be inspected or verified by it, only rejected.

Tracked in provide-io/flavorpack#48. Until it closes, write `execution`.

### 9.2 format_version

`flavor-rs` and `flavor-python` write `"1.0.0"`. `flavor-go` writes the empty string.

A reader MUST NOT depend on this field to decide how to parse. `format` identifies the format; `compatibility.min_format_version` states the requirement.

### 9.3 Platform naming

`build.platform` records the build machine in each producer's own vocabulary. On the same Apple Silicon host:

| Producer | `os` | `arch` |
|----------|------|--------|
| `flavor-rs` | `macos` | `aarch64` |
| `flavor-go` | `darwin` | `arm64` |
| `flavor-python` | `darwin` | `arm64` |

The pairs name the same platform. A reader MUST NOT compare these values across producers or use them to decide whether a package will run.

### 9.4 Checksum prefixes

`launcher.checksum` written by `flavor-python` carries the algorithm prefix twice — `"sha256:sha256:02b2…"`. The digest after the second prefix is correct.

A reader parsing a checksum should strip the algorithm prefix repeatedly rather than once. Tracked in provide-io/flavorpack#49.

### 9.5 Target paths

`flavor-python` writes `slots[].target` with an explicit `{workenv}/` prefix; `flavor-rs` and `flavor-go` write a path relative to the workenv with no prefix. Both denote the same location. A reader MUST accept either, and MUST apply §5.2.2 after substitution.

## 10. Processing Algorithms

### 10.1 Reading

```
1. Read the index from the magic trailer                    (FEP-0001)
2. Read metadata_offset and metadata_size from the index
3. Read that many bytes at that offset                       -> archive
4. If archive begins with 1f 8b, gunzip it                   -> document
5. Parse the document as UTF-8 JSON
6. Apply the structural validation of §5.1
7. Apply the semantic validation of §5.2
```

Step 6 precedes step 7 because the cross-checks in §5.2 read fields that §5.1 has not yet shown to exist.

### 10.2 Verifying

```
1. archive <- the stored metadata bytes, before decompression
2. digest  <- SHA-256(archive)
3. Compare against index.metadata_checksum
```

The comparison is over the stored bytes. See §6.3.

### 10.3 Extracting

```
For each entry of slots, in order:
  1. Find the matching slot descriptor in the index
  2. Read the stored bytes for that descriptor
  3. Verify them against slots[].checksum
  4. Apply the inverse of the packed operation chain    (FEP-0003)
  5. Substitute placeholders in slots[].target
  6. Validate the result per §5.2.2
  7. Write the file and apply slots[].permissions
```

Step 4 uses the packed codes in the descriptor, not the `operations` string (§4.3.7). Step 6 follows step 5, never precedes it.

## 11. Error Handling

| Condition | Reader behaviour |
|-----------|------------------|
| Archive will not decompress | Reject the package |
| Document is not valid JSON | Reject the package |
| A REQUIRED field is absent | Reject the package |
| Slot count disagrees with the index | Reject the package |
| A slot checksum does not match | Reject the package |
| A target path fails §5.2.2 | Reject the package |
| `execution` absent | Read and report normally; refuse to run |
| `command` absent or empty | Read and report normally; refuse to run |
| An unrecognised member is present | Ignore it and continue |

Rejecting means refusing every operation on the package. Refusing to run means inspection and verification still work, and only execution fails. The distinction matters: a package that cannot run is exactly one an operator wants to be able to inspect.

## 12. Security Considerations

### 12.1 The metadata is not evidence

Every field in `verification` is a claim the package makes about itself, written by whoever built it. A reader MUST establish that a package is signed by checking the seal in the index, never by reading `verification.signed`.

### 12.2 Path traversal

`slots[].target` and `workenv.directories[].path` become filesystem paths. They arrive from the package, so an attacker who can write a package controls them. §5.2.2 applies to every one, after substitution.

### 12.3 What the document discloses

The document travels with the package and is readable by anyone holding it, without verification and without extraction.

`slots[].source` records build-machine paths, which can carry usernames and directory layout. `build.platform.host` names the build machine; producers write it only under `FLAVOR_INCLUDE_BUILD_HOST=1` for that reason. `execution.env` and `workenv.env` are stored in the clear and MUST NOT carry secrets.

### 12.4 Size limits

A reader MUST bound the decompressed document (§5.1) before parsing it. The archive is compressed, so a small package can carry a document that expands without limit.

## 13. Implementation Requirements

A conforming reader MUST:

1. Parse a document containing only the REQUIRED fields
2. Ignore members it does not recognise (§5.3)
3. Apply the defaults in Section 4 for absent OPTIONAL fields
4. Verify the metadata against the stored bytes (§6.3)
5. Validate every path after substitution (§5.2.2)
6. Bound the decompressed size before parsing (§12.4)
7. Read the package environment from `execution.env`
8. Take the operation chain from the slot descriptor, not `operations`

A conforming producer MUST:

1. Write every REQUIRED field
2. Write `format` as `"PSPF/2025"`
3. Write `slots` in index order with `slot` matching position
4. Write checksums as `algorithm:hex`, the prefix appearing once
5. Write `execution`, until #48 closes (§9.1)
6. Write the package environment under `env`

## 14. Test Vectors

The packages in `tests/fixtures/format_compat/v1/` are built once by each producer and committed. `rust.psp`, `go.psp` and `python.psp` carry the same payload and are signed with the same derived key, so a change that alters what a producer writes shows up as a difference between them.

`tests/fixtures/format_compat/execution/omits-primary-slot.json` is a document that omits `primary_slot` and carries a non-empty `env`. Every implementation reads it, resolves `primary_slot` to `0`, and sees `MODE=prod`.

The harnesses:

- `tests/format_2025/test_format_compat.py`
- `src/flavor-go/pkg/psp/format_2025/format_compat_test.go`
- `src/flavor-rs/tests/format_compat.rs`

A minimal conforming document:

```json
{
  "format": "PSPF/2025",
  "package": {"name": "minimal", "version": "1.0.0"},
  "slots": [],
  "execution": {"command": "true"}
}
```

## 15. References

- [RFC2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC7159] Bray, T., "The JavaScript Object Notation (JSON) Data Interchange Format", RFC 7159, March 2014.
- [RFC3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
- [RFC1952] Deutsch, P., "GZIP file format specification version 4.3", RFC 1952, May 1996.
- [FEP-0001] PSPF/2025 Core Format and Operation Chains
- [FEP-0003] PSPF/2025 Operation Registry
- [FEP-0004] PSPF/2025 Security Attestation Extension
