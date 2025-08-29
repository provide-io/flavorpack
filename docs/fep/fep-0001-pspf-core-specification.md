# The Progressive Secure Package Format (PSPF/2025)

**Abstract**

This document specifies the Progressive Secure Package Format (PSPF/2025), a polyglot file format designed for the secure, portable, and efficient distribution of software applications. A PSPF package is a single file that functions simultaneously as a native operating system executable and a structured, cryptographically verifiable archive.

The format is engineered to address the shortcomings of traditional single-binary bundlers and heavyweight containerization solutions. Its core features include a self-contained, mandatory Ed25519 signature verification model; a "Progressive Extraction" mechanism that utilizes a persistent cache for superior startup performance on subsequent runs; and a future-proofed design with a large, extensible index block that accommodates supply chain metadata and post-quantum cryptography. The specification defines the binary layout, the JSON-based metadata schema, the security model, and the runtime protocol for atomic extraction and execution.

## Table of Contents

1.  [Introduction](#1-introduction)
    1.1. [Requirements Language](#11-requirements-language)
    1.2. [Motivation](#12-motivation)
    1.3. [Terminology](#13-terminology)
2.  [Architectural Model](#2-architectural-model)
    2.1. [The Polyglot Principle](#21-the-polyglot-principle)
    2.2. [The Progressive Extraction Model](#22-the-progressive-extraction-model)
    2.3. [The Data-Driven "Ingredient" Philosophy](#23-the-data-driven-ingredient-philosophy)
3.  [PSPF/2025 Binary Format Specification](#3-pspf2025-binary-format-specification)
    3.1. [Overall Structure](#31-overall-structure)
    3.2. [The Native Launcher](#32-the-native-launcher)
    3.3. [The 8192-Byte Index Block](#33-the-8192-byte-index-block)
    3.4. [The Metadata Block](#34-the-metadata-block)
    3.5. [The Slot System](#35-the-slot-system)
    3.6. [The Magic Footer](#36-the-magic-footer)
4.  [Metadata Specification (JSON)](#4-metadata-specification-json)
    4.1. [Top-Level Structure](#41-top-level-structure)
    4.2. [The "slots" Array](#42-the-slots-array)
    4.3. [The "execution" Object](#43-the-execution-object)
    4.4. [The "runtime" and "workenv" Objects](#44-the-runtime-and-workenv-objects)
5.  [Security Model](#5-security-model)
    5.1. [Cryptographic Guarantees](#51-cryptographic-guarantees)
    5.2. [Key Management](#52-key-management)
    5.3. [Verification Workflow](#53-verification-workflow)
6.  [Runtime Protocol](#6-runtime-protocol)
    6.1. [The "workenv" Cache](#61-the-workenv-cache)
    6.2. [Atomic Extraction Process](#62-atomic-extraction-process)
    6.3. [Cache Validation](#63-cache-validation)
7.  [Security Considerations](#7-security-considerations)
8.  [IANA Considerations](#8-iana-considerations)
9.  [References](#9-references)

## 1. Introduction

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 when, and only when, they appear in all capitals, as shown here.

### 1.2. Motivation

The distribution of modern applications often involves a trade-off between ease of use, portability, security, and performance. Traditional single-binary bundlers often suffer from high startup latency due to full, temporary extraction on every run and may lack integrated, mandatory security verification. Conversely, full containerization solutions, while providing strong isolation, introduce significant overhead, require a host daemon, and present a more complex user workflow.

PSPF/2025 is designed to occupy a strategic middle ground. It provides the dependency-bundling and environmental consistency benefits of containers without the overhead of a daemon, while offering superior performance and a more robust, built-in security model than traditional bundlers. Its primary goal is to enable the distribution of any application as a single, secure, and directly executable file.

### 1.3. Terminology

*   **PSPF Package**: A single, contiguous file conforming to the PSPF/2025 specification. It is also referred to as a "bundle".
*   **Launcher**: A statically-linked, native executable binary that is prepended to the PSPF archive data. It serves as the entry point for the operating system and is the trusted component responsible for verifying, extracting, and executing the package.
*   **Builder**: A tool that assembles a PSPF package from a manifest and application contents.
*   **Component**: A generic term for a compiled (e.g., Go, Rust) part of the packaging system, such as a Launcher or a Builder.
*   **Slot**: A discrete, individually addressable data blob within the package that contains a component of the application, such as a runtime, a library, application code, or an asset.
*   **Working Environment (workenv)**: A persistent cache directory on the host filesystem where a Launcher extracts the contents of a PSPF package. It is referred to as the "working environment" or `workenv` throughout this document. Its path is derived from the package's content, ensuring different package versions extract to different locations.
*   **Polyglot File**: A file that is valid as two or more different file types simultaneously. A PSPF package is a polyglot of a native executable and a structured archive.[1][2]

## 2. Architectural Model

### 2.1. The Polyglot Principle

A PSPF/2025 file is a polyglot artifact created using a "stacked" technique.[1] The file begins with a complete, platform-specific native executable (the Launcher). The structured archive data, including the Index Block and all content Slots, is appended immediately after the launcher binary.

The execution flow is as follows:
1.  The user executes the file. The operating system's loader identifies the standard executable header and runs the Launcher.
2.  The Launcher is self-aware; it determines its own size on disk.
3.  It then seeks past its own binary code to a known offset where it begins parsing the rest of the file as a structured PSPF archive.

This design provides a seamless user experience, as the package is directly runnable with no external dependencies or separate extraction tools required.

### 2.2. The Progressive Extraction Model

Unlike bundlers that extract their entire payload to a temporary directory on every execution [3], PSPF utilizes a persistent cache model. The Launcher extracts package contents (Slots) into a durable `workenv` directory.[4]

This enables "Progressive Extraction", an intelligent caching strategy driven by `lifecycle` metadata associated with each Slot. For example, a `volatile` slot containing installation wheels can be extracted, used, and immediately deleted to conserve cache space, while a `lazy` slot containing a large asset might only be extracted on-demand when a specific application feature is accessed.[4] This model significantly reduces startup latency on subsequent runs and optimizes disk I/O.

### 2.3. The Data-Driven "Component" Philosophy

A foundational principle of the architecture is that the native Components (Launchers and Builders) MUST be generic, data-driven engines.[4][4] They are explicitly forbidden from containing any package-specific or application-specific logic.

All runtime behavior—such as environment variable manipulation, setup commands, and execution flow—is dictated entirely by the declarative JSON metadata within the package. This strict separation of concerns enhances security, as the generic Launcher can be rigorously audited as a single component. It also ensures long-term maintainability and extensibility; new features can be added to the metadata schema and implemented once in the Launcher, making them available to all packages without modification.

## 3. PSPF/2025 Binary Format Specification

### 3.1. Overall Structure

A PSPF/2025 package is a single, contiguous file with the following structure:

```
+----------------------------------+
| Native Launcher Binary           | (variable size)
+----------------------------------+
| Index Block                      | (8192 bytes)
+----------------------------------+
| Metadata Block                   | (variable size, gzipped)
+----------------------------------+
| Slot Table                       | (slot_count * 64 bytes)
+----------------------------------+
| Slot 0 Data                      | (variable size)
+----------------------------------+
| ...                              |
+----------------------------------+
| Slot N Data                      | (variable size)
+----------------------------------+
| Magic Footer                     | (8 bytes: 📦🪄)
+----------------------------------+
```

### 3.2. The Native Launcher

The file MUST begin with a native, statically-linked executable binary valid for the target operating system and architecture (e.g., ELF for Linux, Mach-O for macOS). This Launcher serves as the trusted entry point and verifier for the package.

### 3.3. The 8192-Byte Index Block

Located immediately after the Launcher, the Index Block is a fixed-size 8192-byte structure containing critical metadata, pointers, and security information. Its large, fixed size is a deliberate design choice for performance and future-proofing. All multi-byte integer fields MUST be stored in little-endian byte order.

| Offset | Size | Field Name            | Description                                       |
|:-------|:-----|:----------------------|:--------------------------------------------------|
| 0      | 8    | `format_magic`        | "PSPF2025" (ASCII)                                |
| 8      | 4    | `format_version`      | 0x20250001 for this spec.                         |
| 12     | 4    | `index_checksum`      | Adler-32 of the index with this field zeroed.     |
| 16     | 8    | `package_size`        | Total size of the entire file in bytes.           |
| 24     | 8    | `launcher_size`       | Size of the Launcher binary in bytes.             |
| 32     | 8    | `metadata_offset`     | Absolute file offset to Metadata Block.           |
| 40     | 8    | `metadata_size`       | Size of the compressed Metadata Block.            |
| 48     | 8    | `slot_table_offset`   | Absolute file offset to the Slot Table.           |
| 56     | 8    | `slot_table_size`     | Total size of the Slot Table.                     |
| 64     | 4    | `slot_count`          | Number of content Slots in the package.           |
| 68     | 4    | `flags`               | Bitfield for feature flags.                       |
| 72     | 32   | `public_key`          | 32-byte Ed25519 public key.                       |
| 104    | 32   | `metadata_checksum`   | SHA256 of the *uncompressed* JSON metadata.       |
| 136    | 512  | `integrity_signature` | First 64 bytes for Ed25519 signature.             |
| 648    | 64   | Performance Hints     | `access_mode`, `cache_strategy`, etc.             |
| 712    | 128  | Supply Chain Meta     | `build_timestamp`, `source_hash`, etc.            |
| 840    | 32   | Capabilities          | `capabilities`, `requirements`, etc.              |
| 872    | 512  | `future_crypto`       | Reserved for post-quantum signatures.             |
| 1384   | 6808 | `reserved`            | Reserved for future expansion.                    |

### 3.4. The Metadata Block

This block contains a single gzipped JSON object that serves as the package manifest. It defines the package contents, execution behavior, and runtime environment.

### 3.5. The Slot System

#### 3.5.1. The Slot Table

A contiguous block of 64-byte Slot Descriptor entries, one for each content Slot in the package. The location and total size of this table are defined in the Index Block.

#### 3.5.2. The Slot Descriptor

Each Slot is described by a 64-byte binary structure containing its location, size, checksum, and semantic metadata.

| Offset | Size | Field Name      | Description                               |
|:-------|:-----|:----------------|:------------------------------------------|
| 0      | 8    | `id`            | Unique slot identifier (typically index). |
| 8      | 8    | `name_hash`     | 64-bit hash of the slot's name.           |
| 16     | 8    | `offset`        | Absolute file offset to Slot Data.        |
| 24     | 8    | `size`          | Size of the Slot Data in bytes.           |
| 32     | 8    | `original_size` | Uncompressed size of the data.            |
| 40     | 4    | `checksum`      | Adler-32 checksum of the Slot Data.       |
| 44     | 1    | `encoding`      | Numeric ID for encoding (0=raw, 3=tgz).   |
| 45     | 1    | `encryption`    | Numeric ID for encryption algorithm.      |
| 46     | 2    | `alignment`     | Required alignment boundary in bytes.     |
| 48     | 1    | `purpose`       | Numeric ID for the slot's purpose.        |
| 49     | 1    | `lifecycle`     | Numeric ID for the slot's lifecycle.      |
| 50     | 2    | `permissions`   | Unix-style file permissions (octal).      |
| 52     | 12   | `reserved`      | Reserved for future use.                  |

#### 3.5.3. Slot Data

The actual content of the application, such as tarballs of Python wheels, a runtime binary, or static assets. The data for each slot is stored as a contiguous block of bytes at the offset specified in its corresponding Slot Descriptor.

### 3.6. The Magic Footer

The file MUST end with the 8-byte UTF-8 sequence for the emojis "📦🪄" (`0xF0 0x9F 0x93 0xA6 0xF0 0x9F 0xAA 0x84`). This serves as a quick and effective check against truncated files.

## 4. Metadata Specification (JSON)

### 4.1. Top-Level Structure

The root of the JSON metadata object contains several key-value pairs that define the package. Essential keys include `package`, `slots`, and `execution`.

### 4.2. The "slots" Array

This REQUIRED array contains one JSON object for each Slot in the package. Each object provides human-readable metadata that complements the binary Slot Descriptor.

```json
"slots": [
  {
    "slot": 0,  // Optional: position validator
    "id": "string",  // Arbitrary identifier for the slot
    "source": "string",  // Source path within the package
    "target": "string",  // Destination path in workenv
    "purpose": "payload|runtime|config|asset|library",
    "lifecycle": "runtime|volatile|temp|cache|init|lazy|eager",
    "resolution": "build|runtime|lazy",  // Optional: when to resolve
    "checksum": "sha256:...",
    "size": "number",
    "encoding": "raw|tar|gzip|tgz",  // String in JSON, converts to numeric in binary
    "permissions": "0755"  // Optional: Unix-style permissions (includes executable bit)
  }
]
```

*   **slot**: (Optional) Expected array position for well-formedness checking. If present and doesn't match actual position, builders MUST fail with a critical error.
*   **id**: Arbitrary string identifier for the slot. Used for logging and referencing.
*   **source**: Path to the source file within the package or build context. No prefix means the file is embedded in the package.
*   **target**: Destination path within the workenv where the file will be placed.
*   **purpose**: Defines the role of the slot's content. MUST be one of: `"payload"`, `"runtime"`, `"config"`, `"asset"`, `"library"`.
*   **lifecycle**: Defines how the Launcher should manage the slot's data over time. MUST be one of: `"runtime"`, `"volatile"`, `"temp"`, `"cached"`, `"init"`, `"lazy"`, `"eager"`.
*   **resolution**: (Optional) Specifies when the slot content is resolved. MUST be one of:
    - `"build"` - Content is embedded at build time (default if omitted)
    - `"runtime"` - Content is resolved when the package runs  
    - `"lazy"` - Content is resolved on first access
*   **encoding**: Compression/encoding type. MUST be one of these exact string literals:
    - `"raw"` - No compression (converts to uint8 value 0 in binary)
    - `"tar"` - TAR archive (converts to uint8 value 1 in binary)
    - `"gzip"` - GZIP compressed (converts to uint8 value 2 in binary)
    - `"tgz"` - TAR + GZIP (converts to uint8 value 3 in binary)
*   **permissions**: (Optional) Unix-style file permissions. MUST be an octal string with leading zero (e.g., `"0755"`, `"0644"`). Converts to uint16 in binary format. If omitted, defaults to `"0644"`.

#### 4.2.1. JSON to Binary Field Mappings

The following table defines the exact mappings between JSON manifest fields and binary format fields:

| JSON Field | JSON Type | Binary Field | Binary Type | Conversion |
|:-----------|:----------|:-------------|:------------|:-----------|
| `slot` | number | - | - | Validation only, not stored |
| `id` | string | `name_hash` | uint64 | SHA256 hash, first 8 bytes |
| `source` | string | - | - | Used at build time only |
| `target` | string | Stored in metadata | - | Preserved as string in metadata |
| `encoding` | string | `encoding` | uint8 | `"raw"`→0, `"tar"`→1, `"gzip"`→2, `"tgz"`→3 |
| `permissions` | string | `permissions` | uint16 | Octal string to integer (e.g., `"0755"`→0x01ED) |
| `purpose` | string | `purpose` | uint8 | `"payload"`→0, `"runtime"`→1, `"config"`→2, `"asset"`→3, `"library"`→4 |
| `lifecycle` | string | `lifecycle` | uint8 | `"runtime"`→0, `"volatile"`→1, `"temp"`→2, `"cached"`→3, `"init"`→4, `"lazy"`→5, `"eager"`→6 |
| `resolution` | string | - | - | Build-time directive, not stored in binary |

Implementations MUST reject invalid values in JSON manifests rather than attempting fallback conversions.

### 4.3. The "execution" Object

This REQUIRED object defines how the application should be run.

```json
"execution": {
  "command": "string",
  "args": ["string"],
  "env": {"key": "value"}
}
```

### 4.4. The "runtime" and "workenv" Objects

These OPTIONAL objects provide fine-grained control over the runtime environment, allowing for the manipulation of environment variables and the creation of specific directories within the workenv.

## 5. Security Model

### 5.1. Cryptographic Guarantees

The security model is founded on the mandatory use of the Ed25519 digital signature algorithm. The signature provides a strong guarantee of authenticity and integrity for the package's entire behavioral manifest.

The signature, stored in the `integrity_signature` field of the Index Block, is computed over the uncompressed JSON metadata block. This is a critical design choice, as it ensures that the manifest defining all files, commands, and environment settings cannot be altered after the package is built.

### 5.2. Key Management

The 32-byte Ed25519 public key corresponding to the signing key is embedded directly in the `public_key` field of the Index Block, making the package a self-verifying artifact.

Key pairs can be generated in two ways:
*   **Deterministic**: A seed string can be provided to the Builder to generate a deterministic key pair. This is essential for reproducible builds and supply chain verification.
*   **Ephemeral**: If no seed is provided, the Builder generates a new, random key pair for each build. The private key is used for the signing operation and is then immediately discarded, minimizing its exposure.

### 5.3. Verification Workflow

Before any application code is executed, the Launcher MUST perform a rigorous, multi-layered verification process. Execution is aborted if any check fails.

1.  **Trailing Magic Check**: Verify the presence of the 8-byte magic footer to protect against file truncation.
2.  **Index Discovery**: Locate the `PSPF2025` magic header.
3.  **Index Checksum**: Calculate the Adler-32 checksum of the 8KB Index Block and compare it to the stored `index_checksum` value.
4.  **Metadata Checksum**: Calculate the SHA256 checksum of the uncompressed JSON metadata and compare it to the stored `metadata_checksum` value.
5.  **Cryptographic Signature Verification**: Use the embedded public key to verify the Ed25519 signature against the uncompressed JSON metadata. This is the final and most critical integrity check.

## 6. Runtime Protocol

### 6.1. The "workenv" Cache

At runtime, the Launcher extracts package contents into a persistent cache directory, the `workenv`. The path is typically derived from a system cache location and a unique identifier for the package (e.g., `~/.cache/flavor/workenv/{workenv_name}/`). This persistence is the key to the format's performance on subsequent runs.

### 6.2. Atomic Extraction Process

To ensure the `workenv` is never left in a corrupted or partially extracted state, the Launcher MUST implement a resilient atomic extraction process.

1.  **Lock Acquisition**: Acquire an exclusive, PID-based lock to prevent concurrent extraction of the same package. The mechanism MUST include detection and cleanup of stale locks from crashed processes.
2.  **Temporary Extraction**: Extract all Slot contents into a temporary, PID-specific directory. This ensures that any running applications using an existing valid `workenv` are not disturbed.
3.  **Shebang Rewriting**: If applicable, scan the extracted `bin/` directory and rewrite script shebangs to point to the absolute path of the interpreter within the final destination `workenv`.
4.  **Atomic Move**: Use an atomic filesystem rename operation to move the temporary directory to its final `workenv` location. This is the critical step that guarantees atomicity.
5.  **Finalization and Cleanup**: Write a completion marker, save the package checksum for future validation, and release the PID lock.

### 6.3. Cache Validation

On subsequent executions, the Launcher MUST validate the integrity of the existing `workenv` before running the application. This is achieved by checking for the completion marker and comparing a stored checksum of the original package against the current package file. If validation fails, a full re-extraction is triggered.

## 7. Security Considerations

The security of the PSPF model relies on the integrity of the Launcher binary. A compromised Launcher could bypass the verification steps. Therefore, Launchers SHOULD be built as statically-linked binaries from audited source code to minimize external dependencies and attack surface.

Implementations MAY include an "insecure" mode (e.g., via an environment variable like `FLAVOR_INSECURE=1`) to bypass verification for debugging purposes. This mode MUST NOT be used in production environments and SHOULD generate prominent warnings when active.

## 8. IANA Considerations

(This section intentionally left blank)

## 9. References

[1] *TODO: Add reference*
[2] *TODO: Add reference*
[3] *TODO: Add reference*
[4] *TODO: Add reference*
