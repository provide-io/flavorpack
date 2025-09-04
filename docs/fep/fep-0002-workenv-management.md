# FEP-0002: Working Environment Management Specification

**Status**: Implemented  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-03  

## 1. Introduction

This specification defines the Working Environment (workenv) management system for PSPF/2025 packages. The workenv provides a persistent extraction cache with cryptographic validation, atomic operations, and lifecycle-based resource management.

### 1.1. Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

### 1.2. Design Goals

1. Persistent caching with cryptographic validation
2. Atomic extraction preventing corruption from concurrent access
3. Platform-agnostic directory structure
4. Lifecycle-based automatic resource cleanup
5. Deterministic path resolution through placeholder expansion

## 2. Directory Structure

### 2.1. Base Path Resolution

The workenv base directory SHALL be determined using the following platform-specific algorithm:

```
Platform  Priority Order
--------  --------------
Linux     1. $XDG_CACHE_HOME/flavor/workenv/
          2. $HOME/.cache/flavor/workenv/

macOS     1. $XDG_CACHE_HOME/flavor/workenv/
          2. $HOME/Library/Caches/flavor/workenv/

Windows   1. %LOCALAPPDATA%\flavor\workenv\
          2. %APPDATA%\flavor\workenv\
```

### 2.2. Package Directory Structure

Each package SHALL have its own directory named `{package_name}_{package_version}`:

```
{base_path}/{package_name}_{package_version}/
├── .lock           # Process lock file (8 bytes)
├── .complete       # Extraction marker (0 bytes)
├── .manifest       # Cached metadata (JSON)
├── slot_0/         # Extracted slot 0
├── slot_1/         # Extracted slot 1
├── slot_N/         # Extracted slot N
└── {custom}/       # Package-defined directories
```

### 2.3. Lock File Format

The `.lock` file SHALL contain an 8-byte process identifier:

```
Offset  Size  Type     Description
------  ----  -------  -----------
0       4     uint32   Process ID (PID)
4       4     uint32   Unix timestamp
```

## 3. Cache Validation Protocol

### 3.1. Validation Sequence

Implementations MUST validate cached content before use:

1. Verify `.complete` marker exists
2. Compare cached `.manifest` with package metadata
3. Verify slot checksums if present
4. Execute custom validation if specified

### 3.2. Completion Marker

The `.complete` file is a zero-byte file that MUST be created atomically after successful extraction:

1. Extract all required slots
2. Sync filesystem buffers
3. Create `.complete` atomically
4. Release lock

### 3.3. Custom Validation

Packages MAY specify custom validation in metadata:

```json
{
  "workenv": {
    "cache_validation": {
      "check_file": "{workenv}/version.txt",
      "expected_content": "1.0.0",
      "checksum": "sha256:abcd1234..."
    }
  }
}
```

Implementations SHALL:
1. Expand placeholders in `check_file`
2. Read file content
3. Compare with `expected_content` or verify `checksum`
4. Invalidate cache on mismatch

## 4. Atomic Extraction Protocol

### 4.1. Lock Acquisition

Implementations MUST use file-based locking:

1. Open `.lock` with exclusive write access
2. Write PID and timestamp
3. Verify lock ownership
4. Proceed with extraction
5. Release lock on completion or failure

### 4.2. Lock Recovery

If lock acquisition fails:

1. Read lock file content
2. Check if owning process exists
3. If process dead AND timestamp > 300 seconds old:
   - Break lock and proceed
4. Otherwise:
   - Wait with exponential backoff
   - Maximum wait time: 30 seconds

### 4.3. Partial Extraction Recovery

If `.complete` marker missing but partial content exists:

1. Acquire exclusive lock
2. Remove all existing content
3. Perform fresh extraction
4. Create `.complete` marker
5. Release lock

## 5. Placeholder System

### 5.1. Standard Placeholders

Implementations MUST support these placeholders:

```
Placeholder      Description                      Example Value
--------------   ------------------------------   -------------
{workenv}        Workenv directory path          /REDACTED_ABS_PATH
{home}           User home directory              /home/user
{tmp}            System temp directory            /tmp
{package}        Package name from metadata       myapp
{version}        Package version from metadata    1.0.0
{platform}       Platform identifier              linux_amd64
{slot_N}         Path to extracted slot N         /REDACTED_ABS_PATH
```

### 5.2. Expansion Rules

1. Placeholders SHALL be case-sensitive
2. Unknown placeholders SHALL remain unexpanded
3. Nested placeholders are NOT supported
4. Expansion SHALL occur before path operations

### 5.3. Platform Identifiers

Platform identifiers SHALL use the format `{os}_{arch}`:

```
OS        Arch      Identifier
--------  --------  -----------
linux     amd64     linux_amd64
linux     arm64     linux_arm64
darwin    amd64     darwin_amd64
darwin    arm64     darwin_arm64
windows   amd64     windows_amd64
```

## 6. Directory Creation

### 6.1. Metadata Specification

Packages MAY declare required directories:

```json
{
  "workenv": {
    "directories": [
      {
        "path": "var/log",
        "mode": 493,
        "description": "Log directory"
      }
    ]
  }
}
```

Where `mode` is the decimal representation of Unix permissions (0755 = 493).

### 6.2. Creation Protocol

1. Set process umask if specified
2. For each directory:
   - Create with parents
   - Apply mode & ~umask
   - Continue on existing
3. Restore original umask

### 6.3. Security Requirements

Implementations MUST:
- Reject paths containing `..` components
- Reject absolute paths
- Verify paths remain within workenv
- Apply umask to all created directories

## 7. Environment Variables

### 7.1. Required Variables

Launchers MUST set before execution:

```
Variable                  Description                   Example
----------------------    ---------------------------   -------
FLAVOR_WORKENV           Absolute path to workenv      /REDACTED_ABS_PATH
FLAVOR_PACKAGE_NAME      Package name from metadata    myapp
FLAVOR_PACKAGE_VERSION   Package version from metadata 1.0.0
```

### 7.2. Optional Variables

Launchers SHOULD set if applicable:

```
Variable                  Description                   Example
----------------------    ---------------------------   -------
FLAVOR_SLOT_{N}_PATH     Path to extracted slot N      /REDACTED_ABS_PATH
FLAVOR_OS                Operating system               linux
FLAVOR_ARCH              Architecture                   amd64
FLAVOR_CACHE_DIR         Cache base directory           /REDACTED_ABS_PATH
```

## 8. Lifecycle Management

### 8.1. Slot Lifecycles

Slots SHALL be retained or removed based on lifecycle (from FEP-0001):

```
Value  Name        Retention Policy
-----  ----------  ----------------
0      INIT        Remove after first successful run
1      STARTUP     Extract every launch
2      RUNTIME     Standard caching
3      SHUTDOWN    Remove at termination
4      CACHE       Persistent caching
5      TEMPORARY   Remove at termination
6      LAZY        Extract on first access
7      EAGER       Extract immediately
```

### 8.2. Cleanup Protocol

After successful execution:
1. Remove INIT slots if first run
2. Remove TEMPORARY slots
3. Remove SHUTDOWN slots
4. Update `.manifest` with cleanup timestamp

### 8.3. Cache Expiration

Implementations MAY remove workenvs based on:
- Age (last access time)
- Size constraints
- Explicit user request
- Package uninstallation

## 9. Disk Space Management

### 9.1. Space Requirements

Before extraction, implementations SHOULD:

1. Calculate total uncompressed size from metadata
2. Add 20% overhead for filesystem metadata
3. Verify available space
4. Fail gracefully if insufficient

### 9.2. Quota Enforcement

Implementations MAY enforce quotas:

```json
{
  "workenv": {
    "max_cache_size": 1073741824,
    "max_cache_age_days": 30
  }
}
```

## 10. Error Handling

### 10.1. Error Conditions

Implementations MUST handle:

- Lock acquisition timeout
- Insufficient disk space
- Permission denied
- Corrupted cache
- Checksum mismatch

### 10.2. Recovery Actions

On error, implementations SHALL:

1. Release any held locks
2. Log error with context
3. Attempt cache removal if corrupted
4. Return specific error code
5. NOT leave partial extractions

## 11. Security Considerations

### 11.1. Path Traversal Prevention

Implementations MUST validate all paths:
- Reject `..` components
- Reject absolute paths
- Canonicalize before operations
- Verify within workenv boundaries

### 11.2. Permission Preservation

Implementations SHOULD:
- Preserve file permissions from slots
- Apply umask consistently
- Restrict workenv to user access only (0700)

### 11.3. Lock File Security

Lock files MUST be:
- Created with 0600 permissions
- Verified for ownership
- Protected from symbolic link attacks

## 12. Implementation Requirements

### 12.1. Minimum Implementation

A conforming implementation MUST:
- Create workenv directory structure
- Implement file-based locking
- Support atomic extraction
- Expand standard placeholders
- Set required environment variables

### 12.2. Recommended Implementation

Implementations SHOULD:
- Validate cached content
- Support lifecycle-based cleanup
- Implement disk space checks
- Provide cache management commands
- Support custom validation

## 13. References

- RFC 2119: Key words for use in RFCs
- FEP-0001: PSPF Core Specification
- XDG Base Directory Specification
- POSIX.1-2017: File locking

---
*Version: 2025.1*