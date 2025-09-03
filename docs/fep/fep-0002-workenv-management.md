# FEP-0002: Working Environment (Workenv) Management

**Status**: Implemented  
**Type**: Standards Track  
**Created**: 2025-08-28  
**Updated**: 2025-09-02  
**Implementation**: Complete ✅

## Abstract

This document specifies the Working Environment (workenv) management system for PSPF/2025 packages. The workenv is a persistent cache directory where packages are extracted and executed, enabling fast startup times through intelligent caching while maintaining security through cryptographic validation.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Workenv Directory Structure](#2-workenv-directory-structure)
3. [Cache Management](#3-cache-management)
4. [Directory Creation](#4-directory-creation)
5. [Placeholder System](#5-placeholder-system)
6. [Lifecycle Management](#6-lifecycle-management)
7. [Implementation Status](#7-implementation-status)

## 1. Introduction

### 1.1 Motivation

Applications need a consistent, secure environment for execution. The workenv system provides:

- **Persistent caching**: Extract once, run many times
- **Cache validation**: Cryptographic verification of cached content
- **Atomic extraction**: Ensures consistency during parallel launches
- **Lifecycle management**: Automatic cleanup of temporary/init-only files
- **Platform isolation**: Separate environments per package version

### 1.2 Terminology

- **Workenv**: Working environment directory for a specific package
- **Cache validation**: Process to verify cached extraction is still valid
- **Placeholder**: Variable substitution in paths (e.g., `{workenv}`)
- **Lifecycle**: Timing and retention policy for extracted files

## 2. Workenv Directory Structure

### 2.1 Base Location

```
$HOME/.cache/flavor/workenv/
└── {package_name}_{package_version}/
    ├── bin/            # Extracted executables
    ├── lib/            # Libraries
    ├── data/           # Application data
    ├── tmp/            # Temporary files
    ├── .lock           # Process lock file
    └── .complete       # Extraction complete marker
```

### 2.2 Platform-Specific Paths

- **Linux/macOS**: `~/.cache/flavor/workenv/`
- **Windows**: `%LOCALAPPDATA%\flavor\workenv\`

### 2.3 Environment Variables

```python
# Set by launcher
FLAVOR_WORKENV = "/path/to/workenv"
FLAVOR_PACKAGE_NAME = "myapp"
FLAVOR_PACKAGE_VERSION = "1.0.0"
FLAVOR_SLOT_{N}_PATH = "/path/to/slot/N"
```

## 3. Cache Management

### 3.1 Cache Validation

The launcher validates cached content before use:

```python
def validate_cache(workenv_dir: Path, metadata: dict) -> bool:
    """Validate workenv cache using metadata directives."""
    
    # Check completion marker
    if not (workenv_dir / ".complete").exists():
        return False
    
    # Optional: Check file-based validation
    if "cache_validation" in metadata:
        validation = metadata["cache_validation"]
        check_file = validation.get("check_file", "")
        expected_content = validation.get("expected_content", "")
        
        # Substitute placeholders
        check_file = check_file.replace("{workenv}", str(workenv_dir))
        check_file = check_file.replace("{version}", package_version)
        
        # Verify content
        if Path(check_file).exists():
            actual = Path(check_file).read_text().strip()
            return actual == expected_content
    
    return True
```

### 3.2 Atomic Extraction

Process locking ensures safe concurrent access:

```python
# Launcher acquires exclusive lock
lock_file = workenv_dir / ".lock"
with file_lock(lock_file):
    if not cache_valid:
        extract_all_slots(workenv_dir)
        (workenv_dir / ".complete").touch()
```

### 3.3 Cache Cleanup

```bash
# Clean caches older than 30 days
flavor workenv clean --older-than 30

# Remove specific package cache
flavor workenv remove myapp_1.0.0

# List all cached environments
flavor workenv list
```

## 4. Directory Creation

### 4.1 Metadata Specification

Packages can declare required directories:

```json
{
  "workenv": {
    "directories": [
      {
        "path": "var/log",
        "permissions": "0755",
        "description": "Application logs"
      },
      {
        "path": "tmp",
        "permissions": "0700",
        "description": "Temporary files"
      }
    ],
    "umask": "0022"
  }
}
```

### 4.2 Directory Creation Process

```python
def create_workenv_directories(
    workenv_dir: Path,
    directories: list[dict],
    umask: int = 0o022
) -> None:
    """Create declared directories with proper permissions."""
    
    old_umask = os.umask(umask)
    try:
        for dir_spec in directories:
            path = workenv_dir / dir_spec["path"]
            perms = int(dir_spec.get("permissions", "0755"), 8)
            
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(perms & ~umask)
    finally:
        os.umask(old_umask)
```

## 5. Placeholder System

### 5.1 Supported Placeholders

| Placeholder | Description | Example |
|------------|-------------|---------|
| `{workenv}` | Workenv directory path | `/home/user/.cache/flavor/workenv/myapp_1.0.0` |
| `{home}` | User home directory | `/home/user` |
| `{tmp}` | System temp directory | `/tmp` |
| `{package}` | Package name | `myapp` |
| `{version}` | Package version | `1.0.0` |
| `{platform}` | Platform string | `linux_amd64` |
| `{slot_0}` | Slot 0 extraction path | `/home/user/.cache/flavor/workenv/myapp_1.0.0/slot_0` |

### 5.2 Placeholder Expansion

```python
def substitute_placeholders(path: str, workenv_dir: Path) -> str:
    """Expand placeholders in paths."""
    
    replacements = {
        "{workenv}": str(workenv_dir),
        "{home}": str(Path.home()),
        "{tmp}": tempfile.gettempdir(),
        "{package}": package_name,
        "{version}": package_version,
        "{platform}": get_platform_string(),
    }
    
    result = path
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    # Handle slot references
    for i in range(10):  # Support slots 0-9
        slot_path = workenv_dir / f"slot_{i}"
        if slot_path.exists():
            result = result.replace(f"{{slot_{i}}}", str(slot_path))
    
    return result
```

## 6. Lifecycle Management

### 6.1 Lifecycle-Based Cleanup

Different slot lifecycles affect retention:

```python
# After successful first run
if first_run:
    # Remove INIT lifecycle slots
    for slot in metadata["slots"]:
        if slot["lifecycle"] == LIFECYCLE_INIT:
            slot_path = workenv_dir / f"slot_{slot['id']}"
            shutil.rmtree(slot_path, ignore_errors=True)

# At shutdown
for slot in metadata["slots"]:
    if slot["lifecycle"] == LIFECYCLE_TEMPORARY:
        slot_path = workenv_dir / f"slot_{slot['id']}"
        shutil.rmtree(slot_path, ignore_errors=True)
```

### 6.2 Disk Space Management

```python
def check_disk_space(workenv_dir: Path, required_bytes: int) -> None:
    """Ensure sufficient disk space for extraction."""
    
    stat = os.statvfs(workenv_dir.parent)
    available = stat.f_bavail * stat.f_frsize
    
    # Require 2x space for safe extraction
    needed = required_bytes * DISK_SPACE_MULTIPLIER
    
    if available < needed:
        raise InsufficientDiskSpaceError(
            f"Need {needed} bytes, only {available} available"
        )
```

## 7. Implementation Status

### 7.1 Completed Components ✅

- **Python Implementation**
  - `src/flavor/psp/format_2025/launcher.py`: Workenv setup and management
  - `src/flavor/psp/metadata/paths.py`: Path utilities and placeholders
  - `src/flavor/commands/workenv.py`: CLI commands for workenv management
  - `src/flavor/cache.py`: Cache management utilities

- **Go Implementation**
  - Full workenv extraction and caching
  - Process locking for atomic operations
  - Platform-specific path handling

- **Rust Implementation**
  - Workenv management with memory-mapped I/O
  - Efficient cache validation
  - Cross-platform support

### 7.2 CLI Commands

```bash
# List all workenvs
flavor workenv list

# Get info about workenvs
flavor workenv info

# Clean old caches
flavor workenv clean --older-than 30

# Remove specific workenv
flavor workenv remove myapp_1.0.0

# Inspect workenv contents
flavor workenv inspect myapp_1.0.0
```

### 7.3 Test Coverage

- Cache validation tests
- Concurrent extraction tests
- Placeholder substitution tests
- Lifecycle management tests
- Disk space checks

### 7.4 Future Enhancements

- **Shared libraries**: Deduplication across package versions
- **Network caching**: Distributed cache for teams
- **Compression**: Transparent compression of cached content
- **Quota management**: Per-user/per-app space limits

## References

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [File Locking Best Practices](https://www.gnu.org/software/libc/manual/html_node/File-Locks.html)
- [Atomic File Operations](https://danluu.com/file-consistency/)

---
*Last Updated: 2025-09-02*