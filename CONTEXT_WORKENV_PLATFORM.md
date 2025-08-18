# Context: Workenv & Platform Features Implementation

## Current State Summary

### Completed Work
1. **Renamed `execution.environment` to `execution.env`** for consistency
2. **Added workenv section to metadata structures** (Rust and Python)
3. **Updated SPECIFICATION.md** with new metadata structure
4. **Fixed Python builder** to include workenv in metadata
5. **Started workenv directory setup** in Rust launcher

### Key Design Decisions Made

#### 1. Path Requirements
- **ALL paths in metadata MUST use `{workenv}` prefix**
- This ensures developers can trust that paths are managed and consistent
- Example: `{workenv}/tmp`, `{workenv}/var/log`, NOT just `tmp` or `var/log`
- Applications can use `$FLAVOR_WORKENV` environment variable for runtime paths

#### 2. Environment Variable Layers (processed in order)
1. **Runtime Security Layer** (`runtime.env`)
   - First layer: security filtering
   - `unset`: Remove sensitive variables
   - `pass`: Whitelist specific variables
   - `map`: Rename variables for compatibility
   - `set`: Override with safe defaults

2. **Work Environment Layer** (`workenv.env`)
   - Second layer: setup workenv-specific paths
   - Sets TMPDIR, XDG directories, etc.
   - All paths use `{workenv}` placeholder

3. **Execution Layer** (`execution.env`)
   - Final layer: application-specific settings
   - Sets variables needed by the application

#### 3. Directory Permissions
- **Default permission mode**: 0700 (user-only access) when not specified
- **Default umask**: 0077 (planned, not implemented)
- Directories like `tmp` and `home` should be 0700
- Directories like `var`, `etc` can be 0755

## Pending Implementation Plan

### TDD Implementation Plan for Platform Features & Workenv

#### Test Files to Create/Modify:

##### 1. `tests/format_2025/test_platform_placeholders.py` (NEW)
Test placeholder substitution for {os}, {arch}, {platform}, {workenv}:
```python
def test_substitute_placeholders():
    """Test that placeholders are correctly substituted."""
    # Test cases:
    # - "{workenv}/tmp" -> "/actual/path/tmp"
    # - "{workenv}/cache/{platform}" -> "/actual/path/cache/darwin_arm64"
    # - "{os}_{arch}" -> "darwin_arm64"
    
def test_nested_placeholders():
    """Test nested and combined placeholders."""
    # - "{workenv}/{os}/{arch}/bin" -> "/actual/path/darwin/arm64/bin"
    
def test_invalid_placeholders():
    """Test that invalid placeholders are left as-is."""
    # - "{unknown}" -> "{unknown}"
```

##### 2. `tests/format_2025/test_workenv_directories.py` (NEW)
Test workenv directory creation with permissions and umask:
```python
def test_workenv_paths_require_prefix():
    """All workenv directory paths MUST start with {workenv}."""
    # Test validation rejects: "tmp", "var/log"
    # Test validation accepts: "{workenv}/tmp", "{workenv}/var/log"
    
def test_directory_creation_with_mode():
    """Test directories are created with specified mode."""
    # Create dir with mode "0700" -> verify permissions
    # Create dir with mode "0755" -> verify permissions
    
def test_directory_umask_default():
    """Test default umask is applied when no mode specified."""
    # Default umask should be 0077 (owner-only)
    # Created dirs should be 0700 by default
    
def test_directory_umask_override():
    """Test umask can be overridden in metadata."""
    # Set umask: "0022" in workenv metadata
    # Verify new dirs respect umask
```

##### 3. `tests/format_2025/test_platform_environment.py` (NEW)
Test platform-specific environment variables:
```python
def test_flavor_os_variable():
    """Test FLAVOR_OS is set correctly."""
    # macOS -> "darwin"
    # Linux -> "linux"
    # Windows -> "windows"
    
def test_flavor_arch_variable():
    """Test FLAVOR_ARCH is set correctly."""
    # x86_64 -> "amd64"
    # aarch64 -> "arm64"
    
def test_flavor_platform_variable():
    """Test FLAVOR_PLATFORM combines OS and arch."""
    # -> "darwin_arm64", "linux_amd64", etc.
    
def test_flavor_os_version():
    """Test FLAVOR_OS_VERSION contains version info."""
    # macOS -> "15.6" or similar
    # Linux -> kernel version
    
def test_flavor_cpu_type():
    """Test FLAVOR_CPU_TYPE contains CPU info."""
    # -> "Apple M1", "Intel Core i7", etc.
```

##### 4. `tests/format_2025/test_metadata_validation.py` (UPDATE)
Add tests for workenv validation:
```python
def test_workenv_directories_validation():
    """Test workenv.directories paths must use {workenv} prefix."""
    metadata = {
        "workenv": {
            "directories": [
                {"path": "tmp"},  # INVALID - should fail
                {"path": "{workenv}/tmp"},  # VALID
            ]
        }
    }
    
def test_workenv_env_validation():
    """Test workenv.env values can use placeholders."""
    metadata = {
        "workenv": {
            "env": {
                "CACHE": "{workenv}/cache/{platform}",  # VALID
                "TMP": "/tmp"  # VALID (absolute paths allowed in env)
            }
        }
    }
```

##### 5. `tests/test_utils_platform.py` (NEW)
Test platform detection utilities:
```python
def test_get_os_name():
    """Test OS name detection."""
    # Should return normalized names
    
def test_get_arch_name():
    """Test architecture detection."""
    # Should return normalized arch names
    
def test_get_os_version():
    """Test OS version detection."""
    # Should return version string or None
    
def test_get_cpu_info():
    """Test CPU information detection."""
    # Should return CPU type/family or None
```

#### Rust Tests to Add:

##### 6. `helpers/flavor-rust/src/psp/format_2025/execution.rs` (add tests module)
```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_substitute_placeholders() {
        let result = substitute_placeholders(
            "{workenv}/tmp",
            Path::new("/test/path"),
            &PackageInfo { name: "test".into(), version: "1.0".into() }
        );
        assert_eq!(result, "/test/path/tmp");
    }
    
    #[test]
    fn test_platform_placeholders() {
        let result = substitute_placeholders(
            "{os}_{arch}",
            Path::new("/test"),
            &PackageInfo { name: "test".into(), version: "1.0".into() }
        );
        // Should contain OS and arch
        assert!(result.contains("_"));
    }
}
```

### Implementation Changes Required

#### Python Changes:

1. **`src/flavor/packaging/orchestrator.py`**:
   - Update workenv directory paths to use `{workenv}` prefix
   - Change from `"path": "tmp"` to `"path": "{workenv}/tmp"`

2. **`src/flavor/psp/format_2025/paths.py`**:
   - Remove special handling for workenv section
   - Validate ALL paths require `{workenv}` prefix

3. **`src/flavor/utils/__init__.py`**:
   - Add `get_os_version()` function
   - Add `get_cpu_type()` function

#### Rust Changes:

1. **`helpers/flavor-rust/src/psp/format_2025/execution.rs`**:
   - Update `substitute_placeholders` to handle:
     - `{os}` -> OS name (darwin, linux, windows)
     - `{arch}` -> Architecture (arm64, amd64)
     - `{platform}` -> Combined (darwin_arm64)
   - Use `env::consts::OS` and `env::consts::ARCH`

2. **`helpers/flavor-rust/src/psp/format_2025/launcher.rs`**:
   - Fix `setup_workenv_directories` to substitute `{workenv}` in paths
   - Add platform environment variables:
     - `FLAVOR_OS`
     - `FLAVOR_ARCH`
     - `FLAVOR_PLATFORM`
     - `FLAVOR_OS_VERSION` (if available)
     - `FLAVOR_CPU_TYPE` (if available)

3. **`helpers/flavor-rust/src/utils.rs`**:
   - Add `get_os_version()` function
   - Add `get_cpu_info()` function

### New Features to Add:

1. **Environment Variables** (set by launcher at runtime):
   - `FLAVOR_OS` - Operating system (e.g., "darwin", "linux", "windows")
   - `FLAVOR_ARCH` - Architecture (e.g., "arm64", "amd64")
   - `FLAVOR_OS_VERSION` - OS version info (if available)
   - `FLAVOR_CPU_TYPE` - CPU type/family info (if available)
   - `FLAVOR_PLATFORM` - Combined platform string (e.g., "darwin_arm64")

2. **Placeholders** (for use in metadata):
   - `{os}` - Operating system
   - `{arch}` - Architecture  
   - `{platform}` - Combined os_arch string
   - `{workenv}` - Work environment directory (already exists)

3. **Umask Support**:
   - Default umask: 0077 (owner-only)
   - Can be overridden in workenv metadata
   - Applied when creating directories without explicit mode

### Example Metadata Structure:
```json
{
  "workenv": {
    "umask": "0077",  // Optional, default is 0077
    "directories": [
      {"path": "{workenv}/tmp", "mode": "0700"},
      {"path": "{workenv}/var", "mode": "0755"},
      {"path": "{workenv}/var/log", "mode": "0755"},
      {"path": "{workenv}/var/cache", "mode": "0755"},
      {"path": "{workenv}/var/run", "mode": "0755"},
      {"path": "{workenv}/etc", "mode": "0755"},
      {"path": "{workenv}/home", "mode": "0700"},
      {"path": "{workenv}/state", "mode": "0755"},
      {"path": "{workenv}/cache/{platform}", "mode": "0755"}
    ],
    "env": {
      "TMPDIR": "{workenv}/tmp",
      "TMP": "{workenv}/tmp",
      "TEMP": "{workenv}/tmp",
      "XDG_RUNTIME_DIR": "{workenv}/var/run",
      "XDG_CACHE_HOME": "{workenv}/var/cache",
      "XDG_DATA_HOME": "{workenv}/share",
      "XDG_STATE_HOME": "{workenv}/state",
      "XDG_CONFIG_HOME": "{workenv}/etc",
      "HOME": "{workenv}/home",
      "PLATFORM_CACHE": "{workenv}/cache/{os}_{arch}"
    }
  }
}
```

### Implementation Order (TDD):
1. Write all Python tests first (they will fail)
2. Write Rust test module (will fail to compile)
3. Implement Python placeholder substitution
4. Implement Rust placeholder substitution
5. Implement workenv directory validation
6. Implement umask support
7. Implement platform environment variables
8. All tests should pass

### Current File States

#### Files that need updating:
1. `/REDACTED_ABS_PATH` - Line 197-204: Change paths to use `{workenv}` prefix
2. `/REDACTED_ABS_PATH` - Line 104-116: Remove special workenv handling
3. `/REDACTED_ABS_PATH` - Line 178-191: Add platform placeholders
4. `/REDACTED_ABS_PATH` - Line 53-75: Fix directory path substitution

### Platform Normalization Rules:
- **OS normalization**:
  - "macos" → "darwin"
  - Others remain as-is
- **Architecture normalization**:
  - "x86_64" → "amd64"
  - "aarch64" → "arm64"
  - Others remain as-is

### Security Considerations:
1. Default umask 0077 ensures new directories are owner-only by default
2. All paths MUST use `{workenv}` prefix for trust and consistency
3. Platform information is read-only (no user override)
4. Environment variable layers ensure security filtering happens first

## Commands to Run After Implementation:
```bash
# Build Rust helpers
cd /REDACTED_ABS_PATH
cargo build --release
cp target/release/flavor-rs-* ../bin/

# Run new tests
cd /REDACTED_ABS_PATH
pytest tests/format_2025/test_platform_placeholders.py -xvs
pytest tests/format_2025/test_workenv_directories.py -xvs
pytest tests/format_2025/test_platform_environment.py -xvs

# Build and test taster
cd helpers/taster
../../workenv/flavor_darwin_arm64/bin/flavor package \
  --manifest pyproject.toml \
  --output /tmp/taster-platform.psp \
  --launcher rust \
  --key-seed test123

# Test with custom workenv
chmod +x /tmp/taster-platform.psp
rm -rf /tmp/test-workenv
FLAVOR_WORKENV=/tmp/test-workenv /tmp/taster-platform.psp info

# Check created directories and permissions
ls -la /tmp/test-workenv/
```

## Notes for Next Session:
- No backward compatibility required (per user)
- Focus on TDD - write tests first, then implement
- Ensure all paths use `{workenv}` prefix for consistency
- Test with taster package for real-world validation