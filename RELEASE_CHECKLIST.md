# Release Checklist

## Pre-Release Verification

### ✅ Code Quality
- [ ] All tests pass: `make test`
- [ ] Linting passes: `make lint`
- [ ] Type checking passes: `mypy src/flavor`

### ✅ Binary Compatibility
- [ ] Go binaries built with `CGO_ENABLED=0` (static)
- [ ] Rust binaries built with musl targets (static)
- [ ] Tested on CentOS 7 (glibc 2.17)
- [ ] Tested on Amazon Linux 2023 (glibc 2.34)
- [ ] Tested on Ubuntu 24.04 (glibc 2.39)
- [ ] Tested on Alpine Linux (musl native)

### ✅ Cross-Language Testing
- [ ] Run pretaster combination tests: `cd helpers/pretaster && ./tests/combination-tests.sh`
- [ ] Run compatibility tests: `cd helpers/pretaster && ./tests/compatibility-tests.sh`
- [ ] All builder/launcher combinations work

### ✅ Documentation
- [ ] README.md is up to date
- [ ] CLAUDE.md reflects current architecture
- [ ] API documentation is current
- [ ] Changelog updated with new features

## Build Process

### 1. Clean Environment
```bash
# Clean all caches
cd ingredients/flavor-rs && cargo clean
cd ../flavor-go && go clean -cache -testcache
find . -type d -name "__pycache__" -exec rm -rf {} +
rm -rf build/ dist/ workenv/
```

### 2. Build Ingredients
```bash
# Build all ingredients
cd ingredients
./build.sh

# Verify binaries are static
file bin/flavor-*-linux* | grep "statically linked"
```

### 3. Run Full Test Suite
```bash
# Python tests
pytest tests/ -v

# Pretaster tests
cd helpers/pretaster
./tests/combination-tests.sh
./tests/compatibility-tests.sh

# Taster tests
cd helpers/taster
pytest tests/
```

### 4. Create Release Artifacts
```bash
# Build Python wheel
make wheel

# Create release packages
make release-all
```

## Release Notes Template

```markdown
## Version X.Y.Z

### Highlights
- Static binaries for universal Linux compatibility
- Support for CentOS 7+ and Amazon Linux 2023
- Improved cross-platform testing with pretaster

### Binary Compatibility
All Linux binaries are now statically linked:
- Go: Built with CGO_ENABLED=0
- Rust: Built with musl libc
- Works on any Linux distribution (glibc 2.17+)

### Changes
- [List of changes]

### Testing
Verified on:
- CentOS 7 (glibc 2.17)
- Amazon Linux 2023 (glibc 2.34)
- Ubuntu 22.04/24.04
- Alpine Linux (musl)
```

## Post-Release

- [ ] Tag release in git
- [ ] Upload artifacts to release page
- [ ] Update documentation site
- [ ] Announce release