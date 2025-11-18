# Advanced Debugging

Deep debugging techniques for FlavorPack packages, builds, and runtime issues.

## Overview

This guide covers advanced debugging techniques for diagnosing complex issues in FlavorPack packages, from build failures to runtime errors.

---

## Logging Levels

### Configure Logging

FlavorPack uses hierarchical logging with multiple levels:

```bash
# Trace - Every operation logged
FOUNDATION_LOG_LEVEL=trace flavor pack

# Debug - Detailed diagnostic info
FOUNDATION_LOG_LEVEL=debug flavor pack

# Info - Normal operations (default)
FOUNDATION_LOG_LEVEL=info flavor pack

# Warning - Warnings only
FOUNDATION_LOG_LEVEL=warning flavor pack

# Error - Errors only
FOUNDATION_LOG_LEVEL=error flavor pack
```

### Component-Specific Logging

Control logging for specific components:

```bash
# Builder logging
FLAVOR_BUILDER_LOG_LEVEL=trace flavor pack

# Launcher logging
FLAVOR_LAUNCHER_LOG_LEVEL=debug ./myapp.psp

# Foundation logging
FOUNDATION_LOG_LEVEL=trace flavor pack

# Python packaging
PYTHONVERBOSE=1 flavor pack
```

### Log Output

```bash
# Log to file
FLAVOR_LOG_FILE=build.log flavor pack

# Log to stderr (separate from stdout)
FLAVOR_LOG_STDERR=1 flavor pack

# Structured JSON logging
FLAVOR_LOG_FORMAT=json flavor pack
```

---

## Build Debugging

### Trace Build Process

```mermaid
graph LR
    A[Parse Manifest] --> B[Resolve Dependencies]
    B --> C[Create Python Environment]
    C --> D[Package Dependencies]
    D --> E[Create Slots]
    E --> F[Select Helpers]
    F --> G[Invoke Builder]
    G --> H[Assemble Package]
    H --> I[Sign Package]
    I --> J[Verify Package]

    style C fill:#ffe4e1
    style E fill:#e1f5ff
    style G fill:#fff4e6
    style I fill:#e8f5e9
```

### Debug Build Failures

```bash
# Maximum verbosity
FLAVOR_LOG_LEVEL=trace \
FOUNDATION_LOG_LEVEL=debug \
PYTHONVERBOSE=1 \
  flavor pack --manifest pyproject.toml 2>&1 | tee build-debug.log

# Analyze log
grep -i "error" build-debug.log
grep -i "failed" build-debug.log
grep -i "warning" build-debug.log
```

### Isolate Build Stages

```bash
# Test manifest parsing
flavor inspect --manifest pyproject.toml

# Test dependency resolution
uv pip compile pyproject.toml

# Test Python environment creation
uv venv /tmp/test-env
source /tmp/test-env/bin/activate
uv pip install -e .

# Test slot creation manually
tar -czf runtime.tar.gz /tmp/test-env/
ls -lh runtime.tar.gz
```

### Debug Helper Selection

```bash
# See which helpers are selected
FOUNDATION_LOG_LEVEL=debug flavor pack 2>&1 | grep -i "helper"

# Output example:
# 🔍 Selected launcher: flavor-rs-launcher-linux_amd64
# 🔍 Selected builder: flavor-rs-builder-linux_amd64

# Force specific helpers
flavor pack \
  --launcher-bin dist/bin/flavor-rs-launcher-linux_amd64 \
  --builder-bin dist/bin/flavor-rs-builder-linux_amd64
```

---

## Runtime Debugging

### Trace Package Execution

```bash
# Enable all runtime logging
FLAVOR_LOG_LEVEL=trace \
FLAVOR_LAUNCHER_LOG_LEVEL=trace \
  ./myapp.psp 2>&1 | tee runtime-debug.log
```

### Debug Extraction Process

```bash
# Watch extraction in real-time
FLAVOR_LOG_LEVEL=debug ./myapp.psp &
PID=$!

# Monitor cache directory
watch -n 1 "ls -lh ~/.cache/flavor/workenv/"

# Wait for completion
wait $PID
```

### Debug Import Errors

**Step 1: Compare sys.path**

```bash
# Development environment
python -c "import sys; print('\n'.join(sys.path))"

# Package environment
FLAVOR_LAUNCHER_CLI=1 ./myapp.psp shell
>>> import sys
>>> print('\n'.join(sys.path))
>>> exit()
```

**Step 2: Find missing module**

```bash
# Search in cache
find ~/.cache/flavor/workenv -name "missing_module*"

# Search in package slots
flavor extract-all myapp.psp /tmp/debug
find /tmp/debug -name "missing_module*"
```

**Step 3: Check if module was included**

```bash
# Extract slot 1 (app code)
flavor extract myapp.psp 1 app.tar.gz
tar -tzf app.tar.gz | grep missing_module

# If not found, check dependencies
flavor inspect myapp.psp --json | jq '.package.dependencies'
```

### Debug Environment Issues

```bash
# Dump environment
FLAVOR_LAUNCHER_CLI=1 ./myapp.psp shell
>>> import os
>>> for k, v in sorted(os.environ.items()):
...     if 'FLAVOR' in k or 'PYTHON' in k:
...         print(f"{k}={v}")
>>> exit()
```

---

## System-Level Debugging

### strace / dtruss

Track system calls to understand what the package is doing:

**Linux (strace):**

```bash
# Trace all system calls
strace -f ./myapp.psp 2>&1 | tee strace.log

# Trace file operations only
strace -f -e trace=open,openat,stat,read,write ./myapp.psp

# Trace network operations
strace -f -e trace=socket,connect,send,recv ./myapp.psp

# Follow child processes
strace -f -ff -o strace-out ./myapp.psp
# Creates strace-out.PID files
```

**macOS (dtruss):**

```bash
# Trace all system calls (requires sudo)
sudo dtruss -f ./myapp.psp 2>&1 | tee dtruss.log

# Trace file operations only
sudo dtruss -t open,read,write ./myapp.psp
```

### lsof - Open Files

```bash
# List open files for running package
./myapp.psp &
PID=$!
lsof -p $PID

# Filter to show only package-related files
lsof -p $PID | grep -E "(\.psp|\.cache|flavor)"
```

### Memory Profiling

```bash
# Monitor memory usage (Linux)
/usr/bin/time -v ./myapp.psp command 2>&1 | grep -E "(Maximum|Average)"

# Monitor memory usage (macOS)
/usr/bin/time -l ./myapp.psp command 2>&1 | grep "maximum resident"

# Profile with valgrind (advanced)
valgrind --leak-check=full --track-origins=yes ./myapp.psp
```

---

## Package Integrity Debugging

### Verify Package Structure

```bash
# Check magic footer
tail -c 8 myapp.psp | xxd
# Should show: f09f 93a6 f09f aa84 (📦🪄)

# Check index block location
FILESIZE=$(stat -f%z myapp.psp)  # macOS
# FILESIZE=$(stat -c%s myapp.psp)  # Linux
INDEX_START=$((FILESIZE - 8200))
dd if=myapp.psp bs=1 skip=$INDEX_START count=100 | xxd | head
```

### Verify Checksums

```bash
# Extract and verify all slots
flavor extract-all myapp.psp /tmp/verify
cd /tmp/verify

# Check slot integrity
for slot in slot_*.tar.gz; do
    echo "Verifying $slot..."

    # Test tar.gz integrity
    if tar -tzf "$slot" > /dev/null 2>&1; then
        echo "  ✅ Valid archive"
    else
        echo "  ❌ Corrupted archive"
    fi

    # Calculate checksum
    sha256sum "$slot"
done
```

### Compare Package Metadata

```bash
# Extract metadata
flavor inspect myapp.psp --json > actual.json

# Compare with expected
cat > expected.json << 'EOF'
{
  "package": {
    "name": "myapp",
    "version": "1.0.0"
  }
}
EOF

# Diff
diff <(jq -S . expected.json) <(jq -S '.package' actual.json)
```

---

## Helper Debugging

### Test Helpers Directly

```bash
# Test launcher
dist/bin/flavor-rs-launcher-linux_amd64 --version
dist/bin/flavor-rs-launcher-linux_amd64 --help

# Test builder with minimal package
cat > test-manifest.json << 'EOF'
{
  "package": {"name": "test", "version": "1.0.0"},
  "slots": [],
  "execution": {"command": ["echo", "test"]}
}
EOF

dist/bin/flavor-rs-builder-linux_amd64 \
  --manifest test-manifest.json \
  --launcher dist/bin/flavor-rs-launcher-linux_amd64 \
  --output test.psp

# Test resulting package
./test.psp
```

### Debug Helper Crashes

```bash
# Run helper with debug symbols (if available)
RUST_BACKTRACE=full dist/bin/flavor-rs-launcher-linux_amd64

# Use gdb (Linux)
gdb --args dist/bin/flavor-rs-launcher-linux_amd64 --version
(gdb) run
(gdb) backtrace

# Use lldb (macOS)
lldb dist/bin/flavor-rs-launcher-darwin_arm64
(lldb) run --version
(lldb) bt
```

---

## Network Debugging

### Debug Package Downloads

```bash
# Monitor network during build
sudo tcpdump -i any -w build-network.pcap &
TCPDUMP_PID=$!

flavor pack --manifest pyproject.toml

sudo kill $TCPDUMP_PID

# Analyze captures
wireshark build-network.pcap
```

### Debug Offline Builds

```bash
# Test with network disabled (Linux)
unshare -n flavor pack --manifest pyproject.toml

# Or use pip cache
pip download -d .cache/pip -r requirements.txt
PIP_FIND_LINKS=.cache/pip PIP_NO_INDEX=1 flavor pack
```

---

## Advanced Techniques

### Bisecting Issues

```bash
#!/bin/bash
# bisect-build.sh - Find which dependency causes build failure

# Binary search through dependencies
DEPS=($(grep "dependencies" pyproject.toml | sed 's/.*"\\(.*\\)".*/\\1/'))

test_build() {
    local deps="$1"
    echo "Testing with deps: $deps"

    # Create temp pyproject.toml
    cat > /tmp/test-pyproject.toml << EOF
[project]
name = "test"
version = "1.0.0"
dependencies = [$deps]
EOF

    flavor pack --manifest /tmp/test-pyproject.toml --output /tmp/test.psp
    return $?
}

# Test each dependency
for dep in "${DEPS[@]}"; do
    if ! test_build "\"$dep\""; then
        echo "Problem dependency: $dep"
    fi
done
```

### Reproduce CI Failures Locally

```bash
# Match CI environment
docker run -it --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  ubuntu:22.04 bash

# Inside container
apt-get update
apt-get install -y python3.11 python3-pip make
pip3 install flavor

# Run same commands as CI
make build-helpers
flavor pack --manifest pyproject.toml
```

---

## Debugging Checklist

When debugging issues:

- [ ] Enable trace logging (`FLAVOR_LOG_LEVEL=trace`)
- [ ] Check package integrity (`flavor verify`)
- [ ] Verify helper versions (`flavor helpers list`)
- [ ] Compare working vs broken environments
- [ ] Test with minimal manifest
- [ ] Check system resources (disk, memory)
- [ ] Review recent changes (git diff)
- [ ] Test on clean system/container
- [ ] Check for platform-specific issues
- [ ] Verify all dependencies declared

---

## Debugging Tools Reference

| Tool | Purpose | Example |
|------|---------|---------|
| `strace` | Trace system calls (Linux) | `strace -f ./myapp.psp` |
| `dtruss` | Trace system calls (macOS) | `sudo dtruss -f ./myapp.psp` |
| `lsof` | List open files | `lsof -p PID` |
| `gdb` | Debug native code (Linux) | `gdb ./myapp.psp` |
| `lldb` | Debug native code (macOS) | `lldb ./myapp.psp` |
| `valgrind` | Memory debugging | `valgrind --leak-check=full ./myapp.psp` |
| `xxd` | Hex dump | `xxd myapp.psp \| head` |
| `jq` | JSON processing | `flavor inspect myapp.psp --json \| jq` |

---

## See Also

- [Troubleshooting Guide](../../troubleshooting/common/) - Common issues
- [Performance Optimization](performance/) - Performance debugging
- [Testing Guide](../../development/testing/index/) - Testing techniques
- [Environment Variables](../usage/environment/) - Logging configuration

---

**Need more help?** Check the [troubleshooting guide](../../troubleshooting/common/) or report issues on GitHub.
