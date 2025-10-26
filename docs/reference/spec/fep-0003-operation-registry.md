# FEP-0003: PSPF/2025 Operation Registry and Allocation Policy

**Status**: Standards Track
**Type**: Process Document
**Created**: 2025-01-08
**Version**: v0.1
**Category**: Standards Track

!!! info "Implementation Status"
    This document defines the operation registry structure and governance for the full 256-code space. **Currently, only the v0 required operations (Section 12.1) are implemented** in FlavorPack v0.0.1023. The remaining operations, categories, and procedures described here are planned for future releases and serve as the design specification for the operation system.

## Abstract

This document establishes the PSPF/2025 Operation Registry, defining the allocation policy, registration procedures, and governance model for the 256 available operation codes. The registry ensures consistent operation semantics across implementations while providing extensibility for future requirements and vendor-specific needs.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Registry Structure](#2-registry-structure)
3. [Operation Categories](#3-operation-categories)
4. [Allocation Policies](#4-allocation-policies)
5. [Registration Procedures](#5-registration-procedures)
6. [Operation Specifications](#6-operation-specifications)
7. [Compatibility Requirements](#7-compatibility-requirements)
8. [Deprecation Process](#8-deprecation-process)
9. [Registry Governance](#9-registry-governance)
10. [Security Considerations](#10-security-considerations)
11. [IANA Considerations](#11-iana-considerations)
12. [Current Registry](#12-current-registry)
13. [References](#13-references)

## 1. Introduction

### 1.1 Purpose

The PSPF/2025 Operation Registry serves as the authoritative source for operation code assignments and specifications. This registry ensures:

- Unique operation code assignments
- Consistent semantics across implementations
- Orderly allocation of the limited 256-code space
- Clear deprecation and versioning processes
- Vendor extension mechanisms

### 1.2 Scope

This document defines:
- Registry structure and organization
- Allocation policies for each category
- Registration procedures and requirements
- Operation specification templates
- Governance and change control processes

### 1.3 Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) [RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) when, and only when, they appear in all capitals, as shown here.

## 2. Registry Structure

### 2.1 Registry Format

The registry is maintained as a structured database with the following fields:

| Field                | Type    | Description                              | Required |
|----------------------|---------|------------------------------------------|----------|
| operation_code       | uint8   | 8-bit operation identifier (0x00-0xFF)  | Yes      |
| operation_name       | string  | Human-readable name (e.g., "OP_GZIP")   | Yes      |
| category            | enum    | Operation category (see Section 3)       | Yes      |
| status              | enum    | Current status (see Section 2.2)        | Yes      |
| specification       | uri     | Link to detailed specification           | Yes      |
| version_introduced  | string  | PSPF version that introduced operation  | Yes      |
| version_deprecated  | string  | PSPF version that deprecated operation  | No       |
| replacement        | uint8   | Replacement operation if deprecated      | No       |
| security_review    | date    | Date of last security review            | Yes      |
| implementation_notes| text    | Special implementation considerations    | No       |

### 2.2 Operation Status

Each operation has one of the following statuses:

| Status       | Description                                           | Implementation Requirement |
|--------------|-------------------------------------------------------|----------------------------|
| REQUIRED     | Must be implemented for conformance                  | MUST implement             |
| RECOMMENDED  | Should be implemented for compatibility              | SHOULD implement           |
| OPTIONAL     | May be implemented                                   | MAY implement              |
| EXPERIMENTAL | Under development, subject to change                 | MAY implement (at risk)    |
| DEPRECATED   | Obsolete, scheduled for removal                      | SHOULD NOT implement       |
| RESERVED     | Reserved for future use                              | MUST NOT implement         |
| PRIVATE      | Vendor-specific, not standardized                    | Implementation-defined     |

### 2.3 Version Management

Operations are versioned with the PSPF specification:

```
Version Format: YYYY.MAJOR.MINOR
Example: 2025.0.0

YYYY  = Year of specification
MAJOR = Breaking changes
MINOR = Backward-compatible additions
```

## 3. Operation Categories

### 3.1 Category Allocation

The 256 operation codes are divided into fixed categories:

```
┌──────────────┬─────────────┬──────┬────────────────────────────┐
│ Range        │ Category    │ Count│ Allocation Policy          │
├──────────────┼─────────────┼──────┼────────────────────────────┤
│ 0x00         │ NONE        │ 1    │ Fixed (no operation)       │
│ 0x01 - 0x0F  │ BUNDLE      │ 15   │ Standards Action          │
│ 0x10 - 0x2F  │ COMPRESS    │ 32   │ Standards Action          │
│ 0x30 - 0x4F  │ ENCRYPT     │ 32   │ Standards Action          │
│ 0x50 - 0x6F  │ ENCODE      │ 32   │ Specification Required    │
│ 0x70 - 0x8F  │ HASH        │ 32   │ Specification Required    │
│ 0x90 - 0xAF  │ SIGNATURE   │ 32   │ Standards Action          │
│ 0xB0 - 0xCF  │ TRANSFORM   │ 32   │ Specification Required    │
│ 0xD0 - 0xEF  │ CUSTOM      │ 32   │ Expert Review             │
│ 0xF0 - 0xFE  │ VENDOR      │ 15   │ Private Use               │
│ 0xFF         │ TERMINAL    │ 1    │ Fixed (chain terminator)  │
└──────────────┴─────────────┴──────┴────────────────────────────┘
```

### 3.2 Category Descriptions

#### 3.2.1 BUNDLE (0x01-0x0F)
Archive and container formats that combine multiple files.

**Requirements**:
- MUST preserve file metadata (names, permissions, timestamps)
- MUST support streaming extraction
- MUST handle empty archives
- SHOULD support deterministic output

#### 3.2.2 COMPRESS (0x10-0x2F)
Data compression algorithms reducing size without data loss.

**Requirements**:
- MUST be lossless
- MUST support streaming compression/decompression
- MUST detect corruption (via checksums or structure)
- SHOULD provide compression level options

#### 3.2.3 ENCRYPT (0x30-0x4F)
Cryptographic operations for confidentiality and privacy.

**Requirements**:
- MUST use approved cryptographic algorithms
- MUST undergo security review
- MUST specify key derivation methods
- MUST handle authentication tags where applicable

#### 3.2.4 ENCODE (0x50-0x6F)
Data encoding transformations (not cryptographic).

**Requirements**:
- MUST be reversible
- MUST handle all input bytes (0x00-0xFF)
- SHOULD be deterministic
- MAY increase data size

#### 3.2.5 HASH (0x70-0x8F)
Cryptographic hash functions for integrity verification.

**Requirements**:
- MUST be one-way functions
- MUST have fixed output size
- MUST be deterministic
- SHOULD be collision-resistant

#### 3.2.6 SIGNATURE (0x90-0xAF)
Digital signature algorithms for authentication.

**Requirements**:
- MUST provide non-repudiation
- MUST specify key formats
- MUST define signature encoding
- SHOULD support key rotation

#### 3.2.7 TRANSFORM (0xB0-0xCF)
Data transformation operations (split, merge, delta, etc.).

**Requirements**:
- MUST define transformation semantics precisely
- MUST handle edge cases (empty input, single byte, etc.)
- SHOULD be composable with other operations

#### 3.2.8 CUSTOM (0xD0-0xEF)
Reserved for future standardized operations.

**Requirements**:
- MUST undergo expert review
- MUST not duplicate existing operations
- MUST provide reference implementation

#### 3.2.9 VENDOR (0xF0-0xFE)
Private use for vendor-specific operations.

**Requirements**:
- MUST NOT be used in interoperable contexts
- SHOULD use identifier prefix (e.g., "x-vendor-")
- MAY have arbitrary semantics

## 4. Allocation Policies

### 4.1 Standards Action

Operations requiring "Standards Action" (BUNDLE, COMPRESS, ENCRYPT, SIGNATURE):

1. MUST be documented in a Standards Track FEP
2. MUST have two independent implementations
3. MUST pass interoperability testing
4. MUST undergo security review for cryptographic operations
5. MUST be approved by Registry Board

### 4.2 Specification Required

Operations requiring "Specification Required" (ENCODE, HASH, TRANSFORM):

1. MUST provide complete specification
2. MUST include test vectors
3. MUST demonstrate non-duplication
4. SHOULD have reference implementation
5. Expert reviewer approval required

### 4.3 Expert Review

Operations requiring "Expert Review" (CUSTOM):

1. MUST justify need for new operation
2. MUST provide use cases
3. MUST include implementation
4. Expert panel evaluation required

### 4.4 Private Use

VENDOR operations (0xF0-0xFE):

1. No registration required
2. MUST NOT appear in standard specifications
3. Implementations MAY refuse these operations
4. No interoperability guarantee

## 5. Registration Procedures

### 5.1 Registration Template

```yaml
operation_registration:
  # Administrative
  request_id: "PSPF-REG-2025-001"
  requestor: "Name <email>"
  date: "2025-01-08"
  
  # Operation Details
  proposed_code: 0x1C      # Requested code (or "any")
  proposed_name: "OP_LZ4"
  category: "COMPRESS"
  
  # Specification
  specification_url: "https://example.com/lz4-spec"
  reference_implementation: "https://github.com/example/lz4"
  
  # Technical Details
  input_constraints:
    min_size: 0
    max_size: "2^32-1"
    alignment: 1
    
  output_characteristics:
    size_change: "reduction"  # reduction|expansion|same
    deterministic: true
    streamable: true
    
  performance:
    complexity: "O(n)"
    memory_usage: "O(1)"
    
  # Compatibility
  combines_with: ["BUNDLE", "ENCODE"]
  conflicts_with: ["COMPRESS"]  # Can't double-compress
  
  # Security
  security_properties:
    - "No encryption"
    - "CRC32 integrity check"
  security_review: "url-to-review"
  
  # Testing
  test_vectors:
    - input: "48656c6c6f"  # "Hello"
      output: "..."
      
  # Rationale
  justification: |
    LZ4 provides fast compression suitable for
    real-time applications where speed is critical.
```

### 5.2 Review Process

```
Submission → Initial Review → Expert Review → Public Comment → 
Registry Board → Approval/Rejection → Publication
```

**Timeline**:
- Initial Review: 5 business days
- Expert Review: 10 business days  
- Public Comment: 30 days
- Board Decision: 10 business days
- Total: ~55 business days

### 5.3 Fast Track Process

For critical security updates or corrections:

1. Security team validation
2. Expedited expert review (48 hours)
3. Emergency board approval
4. Immediate publication
5. Post-hoc public review

## 6. Operation Specifications

### 6.1 Specification Requirements

Each operation MUST have a specification containing:

1. **Overview**
   - Purpose and use cases
   - Relationship to standards (RFCs, ISO, etc.)

2. **Algorithm Description**
   - Step-by-step processing
   - Mathematical formulation where applicable
   - Pseudocode or reference code

3. **Parameters**
   - Configuration options
   - Default values
   - Valid ranges

4. **Data Format**
   - Input requirements
   - Output format
   - Header/trailer structure

5. **Error Handling**
   - Error conditions
   - Recovery procedures
   - Error codes

6. **Security Considerations**
   - Threat model
   - Known vulnerabilities
   - Mitigation strategies

7. **Performance Characteristics**
   - Time complexity
   - Space complexity
   - Typical compression ratios (if applicable)

8. **Implementation Notes**
   - Platform-specific considerations
   - Optimization opportunities
   - Common pitfalls

9. **Test Vectors**
   - Minimum 10 test cases
   - Edge cases (empty, single byte, maximum size)
   - Invalid input handling

10. **References**
    - Authoritative specifications
    - Academic papers
    - Related operations

### 6.2 Specification Template Example

```markdown
# Operation Specification: OP_ZSTD

## 1. Overview
Zstandard (Zstd) is a fast compression algorithm providing
high compression ratios.

**Standards**: RFC 8878
**Category**: COMPRESS
**Code**: 0x1B
**Status**: REQUIRED

## 2. Algorithm
Zstandard uses a combination of LZ77 and Finite State Entropy.

### 2.1 Compression Process
1. Dictionary initialization
2. Sequence matching via LZ77
3. Entropy coding with FSE
4. Frame generation

### 2.2 Parameters
- `level`: Compression level (1-22, default: 3)
- `windowLog`: Window size (10-31, default: varies)
- `chainLog`: Hash chain size

## 3. Data Format
```
Frame := Magic Number + Frame Header + Data Blocks + [Content Checksum]
Magic := 0xFD2FB528 (little-endian)
```

## 4. Error Codes
- `ZSTD_error_dstSize_tooSmall`: Output buffer too small
- `ZSTD_error_corruption_detected`: Invalid compressed data

## 5. Security Considerations
- Validates all size fields to prevent integer overflow
- Limits decompression ratio to prevent zip bombs
- Uses xxHash64 for content checksums

## 6. Performance
- Compression: ~500 MB/s at level 3
- Decompression: ~1.5 GB/s
- Memory: O(2^windowLog)

## 7. Test Vectors
Input: "Hello, World!"
Level 3: 28 b5 2f fd 24 4d 91 00 00 48 65 6c 6c 6f 2c 20 57 6f 72 6c 64 21

## 8. References
- RFC 8878: Zstandard Compression
- https://github.com/facebook/zstd
```

## 7. Compatibility Requirements

### 7.1 Version Compatibility Matrix

| PSPF Version | Required Operations                | Optional Operations        |
|--------------|------------------------------------|-----------------------------|
| 2025.0.0 (v0)| NONE, TAR, GZIP, BZIP2, XZ, ZSTD | All others                 |
| 2025.1.0     | v0 + AES256_GCM, SHA256           | LZ4, BLAKE3                 |
| 2025.2.0     | v1 + ED25519_SIGN                 | CHACHA20_POLY1305          |

### 7.2 Backward Compatibility

1. New operations MUST NOT reuse deprecated codes for 10 years
2. Deprecated operations MUST remain documented
3. Implementations SHOULD warn on deprecated operation use
4. Major versions MAY remove support for deprecated operations

### 7.3 Forward Compatibility

1. Unknown operations MUST cause explicit errors
2. Implementations MUST NOT skip unknown operations
3. Version negotiation SHOULD occur before processing
4. Clear error messages MUST indicate unsupported operations

## 8. Deprecation Process

### 8.1 Deprecation Criteria

Operations may be deprecated when:
- Security vulnerabilities cannot be fixed
- Superior alternative exists
- No active use for 2+ years
- Specification has unresolvable ambiguities

### 8.2 Deprecation Timeline

```
T+0:   Deprecation proposal submitted
T+30:  Public comment period
T+60:  Registry Board decision
T+90:  Deprecation notice published
T+180: Status changed to DEPRECATED
T+2yr: MAY be removed from implementations
T+10yr: Code MAY be reassigned
```

### 8.3 Migration Guidance

Deprecation notices MUST include:
- Rationale for deprecation
- Recommended replacement operation
- Migration tools or scripts
- Timeline for removal
- Impact assessment

## 9. Registry Governance

### 9.1 Registry Board

The Registry Board consists of:
- 3 implementation representatives (Python, Go, Rust)
- 2 security experts
- 2 user community representatives
- 1 IANA liaison (non-voting)

**Terms**: 2 years, renewable once
**Meetings**: Quarterly or as needed
**Decisions**: Simple majority, chair breaks ties

### 9.2 Responsibilities

The Registry Board:
1. Reviews registration requests
2. Approves/rejects allocations
3. Manages deprecation process
4. Resolves disputes
5. Publishes annual registry report

### 9.3 Appeals Process

Rejected applicants may appeal to:
1. Registry Board (reconsideration)
2. PSPF Technical Committee
3. IETF/IANA (for process violations)

Timeline: 30 days per level

## 10. Security Considerations

### 10.1 Operation Security Review

Cryptographic operations undergo mandatory security review:

1. **Algorithm Analysis**
   - Peer-reviewed algorithm
   - No known vulnerabilities
   - Appropriate key sizes

2. **Implementation Review**
   - Side-channel resistance
   - Proper randomness
   - Secure defaults

3. **Composition Analysis**
   - Safe operation combinations
   - No security degradation
   - Clear composition rules

### 10.2 Security Levels

Operations are classified by security impact:

| Level    | Description                      | Review Requirement        |
|----------|----------------------------------|---------------------------|
| CRITICAL | Cryptographic, authentication    | Full security audit       |
| HIGH     | Compression, encoding           | Security review           |
| MEDIUM   | Transformation, bundling        | Security checklist        |
| LOW      | Formatting, metadata            | Self-assessment           |

### 10.3 Vulnerability Response

Security vulnerabilities in operations:

1. Report to security@pspf.io
2. 90-day disclosure timeline
3. CVE assignment if applicable
4. Coordinated patch release
5. Registry update with warnings

## 11. IANA Considerations

### 11.1 Registry Establishment

IANA is requested to establish the "PSPF Operation Code Registry" with:

- Registry Name: PSPF Operation Codes
- Reference: This document (FEP-0003)
- Registration Procedures: Varies by range (see Section 4)
- Size: 8 bits (256 values)

### 11.2 Initial Values

IANA shall populate the registry with v0 required operations:

```
Code  Name        Category  Status    Specification
----  ----------  --------  --------  -------------
0x00  OP_NONE     NONE      REQUIRED  FEP-0001
0x01  OP_TAR      BUNDLE    REQUIRED  FEP-0001
0x10  OP_GZIP     COMPRESS  REQUIRED  RFC 1952
0x13  OP_BZIP2    COMPRESS  REQUIRED  FEP-0001
0x16  OP_XZ       COMPRESS  REQUIRED  FEP-0001
0x1B  OP_ZSTD     COMPRESS  REQUIRED  RFC 8878
0xFF  OP_TERMINAL RESERVED  RESERVED  FEP-0001
```

## 12. Current Registry

### 12.1 Required Operations (v0)

| Code | Name      | Category | Specification    | Notes                    |
|------|-----------|----------|------------------|--------------------------|
| 0x00 | OP_NONE   | NONE     | FEP-0001        | Identity transform       |
| 0x01 | OP_TAR    | BUNDLE   | POSIX.1-2008    | POSIX TAR format        |
| 0x10 | OP_GZIP   | COMPRESS | RFC 1952        | GZIP compression        |
| 0x13 | OP_BZIP2  | COMPRESS | bzip2.org       | BZIP2 compression       |
| 0x16 | OP_XZ     | COMPRESS | tukaani.org/xz  | XZ/LZMA2 compression    |
| 0x1B | OP_ZSTD   | COMPRESS | RFC 8878        | Zstandard compression   |

### 12.2 Reserved Operations (Future Use)

| Code Range | Category   | Planned Use                          |
|------------|------------|--------------------------------------|
| 0x02-0x0F  | BUNDLE     | ZIP, CPIO, AR formats               |
| 0x11-0x12  | COMPRESS   | GZIP variants (fast/best)           |
| 0x1E-0x1F  | COMPRESS   | LZ4, LZ4HC                          |
| 0x30-0x31  | ENCRYPT    | AES-128/256 GCM                     |
| 0x70-0x71  | HASH       | SHA-256, SHA-512                    |
| 0x90       | SIGNATURE  | Ed25519 signatures                   |

### 12.3 Allocation Statistics

```
Category     Allocated  Available  Utilization
---------    ---------  ---------  -----------
NONE         1/1        0          100%
BUNDLE       1/15       14         7%
COMPRESS     5/32       27         16%
ENCRYPT      0/32       32         0%
ENCODE       0/32       32         0%
HASH         0/32       32         0%
SIGNATURE    0/32       32         0%
TRANSFORM    0/32       32         0%
CUSTOM       0/32       32         0%
VENDOR       0/15       15         0%
TERMINAL     1/1        0          100%
---------    ---------  ---------  -----------
TOTAL        8/256      248        3%
```

## 13. References

### 13.1 Normative References

[RFC2119](https://www.rfc-editor.org/rfc/rfc2119.html) Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.

[RFC8174](https://www.rfc-editor.org/rfc/rfc8174.html) Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.

[RFC8126] Cotton, M., Leiba, B., and T. Narten, "Guidelines for Writing an IANA Considerations Section in RFCs", BCP 26, RFC 8126, June 2017.

[FEP-0001] "PSPF/2025 Core Format & Operation Chains Specification", FEP-0001, January 2025.

### 13.2 Informative References

[RFC1952] Deutsch, P., "GZIP file format specification version 4.3", RFC 1952, May 1996.

[RFC8878] Collet, Y. and M. Kucherawy, Ed., "Zstandard Compression and the 'application/zstd' Media Type", RFC 8878, February 2021.

[POSIX.1-2008] IEEE, "IEEE Standard for Information Technology - Portable Operating System Interface (POSIX(R))", IEEE Std 1003.1-2008, 2008.

[BZIP2] Seward, J., "bzip2 and libbzip2", https://sourceware.org/bzip2/

[XZ] Collin, L., "XZ Utils", https://tukaani.org/xz/

---

**Authors' Addresses**

[Author contact information]

**Change Log**

- 2025-01-08: Initial version (v0.1)

**Copyright Notice**

Copyright (c) 2025 IETF Trust and the persons identified as the document authors. All rights reserved.