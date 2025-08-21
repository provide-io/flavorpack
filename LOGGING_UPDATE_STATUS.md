# Flavor Helper Logging Update Status

## Overview
This document tracks the logging standardization effort for Flavor's Go and Rust helpers (launchers and builders). The goal is to provide consistent, language-identifiable logging with proper log level management.

## Completed Work

### 1. Test Script Fix
- **File**: `.github/scripts/test-flavor-with-taster.sh`
- **Change**: Line 149 - Fixed `file test-workenv` → `file workenv-test`
- **Status**: ✅ Complete

### 2. Language Emoji Prefixes
- **Rust (🦀)**: Added via custom `env_logger` formatter
- **Go (🐹)**: Added via custom `prefixWriter` wrapper
- **Implementation**:
  - Rust: `helpers/flavor-rs/src/logger.rs` lines 40-56
  - Go: `helpers/flavor-go/pkg/psp/format_2025/launcher.go` lines 29-69, 118-121
- **Status**: ✅ Complete

### 3. Log Message Harmonization
- Standardized startup messages between languages
- Added consistent emoji usage in debug/trace messages
- **Key Messages**:
  - Startup: "PSPF {Rust|Go} Launcher starting..."
  - Package info: "📦 Package: {name} v{version}"
  - Work environment: "📁 Work environment: {path}"
- **Status**: ✅ Complete

### 4. Trace Logging Support
- Both launchers already had trace support
- Go: via `hclog.IsTrace()` and `logger.Trace()`
- Rust: via `log::trace!()` macro
- **Status**: ✅ Complete

## Pending Work

### 1. Log Level Priority Chain
**Required for all 4 helpers:**
```
Priority: --log-level CLI flag → FLAVOR_{BUILDER|LAUNCHER}_LOG_LEVEL → FLAVOR_LOG_LEVEL
```

#### Rust Launcher (`helpers/flavor-rs/src/bin/flavor-rs-launcher.rs`)
- [ ] Add `--log-level` CLI flag parsing before line 362
- [ ] Pass log level to `JsonLogger::init()`
- [ ] Remove RUST_LOG references (lines 209, 219)

#### Rust Builder (`helpers/flavor-rs/src/bin/flavor-rs-builder.rs`)
- [ ] Add `log_level: Option<String>` to Args struct (around line 55)
- [ ] Implement priority chain before line 68
- [ ] Pass log level to `JsonLogger::init()`

#### Go Launcher (`helpers/flavor-go/cmd/flavor-go-launcher/main.go`)
- [ ] Add `--log-level` flag parsing in main()
- [ ] Pass to `format_2025.Launch()` as parameter

#### Go Builder (`helpers/flavor-go/cmd/flavor-go-builder/main.go`)
- [ ] Add `--log-level` to cobra flags (around line 59)
- [ ] Implement priority chain in `buildBundle()`

### 2. Startup Messages
**Required format:**
```
{emoji×3} Hello from Flavor's PSPF {Tool} {emoji×3}
{emoji} Log level: {level} (source: {source})
```

### 3. Logger Updates

#### Rust (`helpers/flavor-rs/src/logger.rs`)
- [ ] Modify `JsonLogger::init()` to accept `(level: &str, source: &str)`
- [ ] Remove RUST_LOG/env_logger::from_default_env support
- [ ] Add startup messages after init

#### Go Launchers/Builders
- [ ] Update logger setup to track source
- [ ] Add startup messages immediately after logger creation

### 4. Go Builder Emoji Prefixes
- [ ] Add 🐹 prefix to all log messages in `pkg/psp/format_2025/builder.go`
- [ ] Currently missing prefix (unlike launcher which has it)

## File Locations

### Rust Components
- **Launcher**: `helpers/flavor-rs/src/bin/flavor-rs-launcher.rs`
- **Builder**: `helpers/flavor-rs/src/bin/flavor-rs-builder.rs`
- **Logger**: `helpers/flavor-rs/src/logger.rs`
- **Launcher Logic**: `helpers/flavor-rs/src/psp/format_2025/launcher.rs`

### Go Components
- **Launcher Main**: `helpers/flavor-go/cmd/flavor-go-launcher/main.go`
- **Builder Main**: `helpers/flavor-go/cmd/flavor-go-builder/main.go`
- **Launcher Logic**: `helpers/flavor-go/pkg/psp/format_2025/launcher.go`
- **Builder Logic**: `helpers/flavor-go/pkg/psp/format_2025/builder.go`
- **Execution**: `helpers/flavor-go/pkg/psp/format_2025/execution.go`
- **Runtime**: `helpers/flavor-go/pkg/psp/format_2025/runtime.go`

## Test Commands

### Build Helpers
```bash
cd /REDACTED_ABS_PATH
./helpers/build.sh
```

### Test Rust Launcher
```bash
# Build test package
workenv/flavor_darwin_arm64/bin/flavor package \
  --manifest helpers/taster/pyproject.toml \
  --launcher-bin helpers/bin/flavor-rs-launcher \
  --output /tmp/test-rs.psp \
  --key-seed test123

# Test log levels
chmod +x /tmp/test-rs.psp
/tmp/test-rs.psp --log-level trace --help  # Should use CLI flag
FLAVOR_LAUNCHER_LOG_LEVEL=debug /tmp/test-rs.psp --help  # Should use env var
FLAVOR_LOG_LEVEL=info /tmp/test-rs.psp --help  # Should use fallback
```

### Test Go Launcher
```bash
# Build test package
workenv/flavor_darwin_arm64/bin/flavor package \
  --manifest helpers/taster/pyproject.toml \
  --launcher-bin helpers/bin/flavor-go-launcher \
  --output /tmp/test-go.psp \
  --key-seed test123

# Test log levels
chmod +x /tmp/test-go.psp
/tmp/test-go.psp --log-level trace --help  # Should use CLI flag
FLAVOR_LAUNCHER_LOG_LEVEL=debug /tmp/test-go.psp --help  # Should use env var
FLAVOR_LOG_LEVEL=info /tmp/test-go.psp --help  # Should use fallback
```

### Test Builders
```bash
# Create test manifest
cat > /tmp/test-manifest.json << 'EOF'
{
  "package": {"name": "test", "version": "1.0.0"},
  "format": "PSPF/2025",
  "slots": [{"name": "test.txt", "path": "/tmp/test.txt"}],
  "execution": {"command": "/bin/echo", "args": ["test"], "env": {}, "primary_slot": 0}
}
EOF
echo "test" > /tmp/test.txt

# Test Rust builder
helpers/bin/flavor-rs-builder \
  --manifest /tmp/test-manifest.json \
  --output /tmp/test-build-rs.psp \
  --launcher-bin helpers/bin/flavor-rs-launcher \
  --key-seed test123 \
  --log-level debug

# Test Go builder  
helpers/bin/flavor-go-builder \
  --manifest /tmp/test-manifest.json \
  --output /tmp/test-build-go.psp \
  --launcher-bin helpers/bin/flavor-go-launcher \
  --key-seed test123 \
  --log-level debug
```

## Expected Output Examples

### Correct Startup (Rust Launcher - Debug)
```
🦀 [2025-08-20T10:45:42Z INFO flavor::psp::format_2025::launcher] 🦀🦀🦀 Hello from Flavor's PSPF Launcher 🦀🦀🦀
🦀 [2025-08-20T10:45:42Z DEBUG flavor::psp::format_2025::launcher] 🦀 Log level: debug (source: CLI --log-level)
🦀 [2025-08-20T10:45:42Z INFO flavor::psp::format_2025::launcher] PSPF Rust Launcher starting...
🦀 [2025-08-20T10:45:42Z DEBUG flavor::psp::format_2025::launcher] 📖 Reading PSPF bundle
```

### Correct Startup (Go Builder - Trace)
```
🐹 2025-08-20T10:45:34.724-0700 [INFO]  flavor-go-builder: 🐹🐹🐹 Hello from Flavor's PSPF Builder 🐹🐹🐹
🐹 2025-08-20T10:45:34.724-0700 [DEBUG] flavor-go-builder: 🐹 Log level: trace (source: FLAVOR_BUILDER_LOG_LEVEL)
🐹 2025-08-20T10:45:34.724-0700 [INFO]  flavor-go-builder: 🐹 PSPF Go Builder starting...
🐹 2025-08-20T10:45:34.724-0700 [DEBUG] flavor-go-builder: 🐹 📖 Reading manifest
```

## Notes

### Current Issues
1. Go builder (`pkg/psp/format_2025/builder.go`) doesn't have 🐹 prefix on log messages
2. RUST_LOG is still referenced in error messages but should be removed
3. FLAVOR_GO_LOG_LEVEL is deprecated but still checked in Go launcher

### Design Decisions
1. Language emojis make it immediately clear which implementation is running
2. Log level source tracking helps debug configuration issues
3. CLI flag takes precedence for explicit user control
4. Component-specific env vars allow different log levels for builder vs launcher
5. FLAVOR_LOG_LEVEL provides a convenient fallback for all components

## Implementation Order
1. Create this documentation ✅
2. Update Rust logger to accept parameters
3. Update Rust launcher with new logic
4. Update Rust builder with new logic
5. Update Go launcher with new logic
6. Update Go builder with new logic
7. Add 🐹 prefixes to Go builder
8. Test all combinations
9. Update this document with completion status