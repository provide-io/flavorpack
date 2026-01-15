# Release Process

Complete guide to releasing new versions of FlavorPack.

## Overview

FlavorPack uses platform-specific wheels that include native Go/Rust helper binaries. The release process builds separate wheels for each supported platform.

## Semantic Versioning

FlavorPack follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR**: Breaking API changes or format version changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

Current alpha version format: `0.0.XXXX-alpha` where XXXX is the build number.

## Release Checklist

### Pre-Release

- [ ] All tests passing (`make test`)
- [ ] Cross-language compatibility verified (`make validate-pspf`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated with changes
- [ ] Version bumped in `pyproject.toml`
- [ ] Helpers built for all platforms

### Release Build

- [ ] Build helpers: `make build-helpers`
- [ ] Build wheels: `make release-all`
- [ ] Validate wheels: `make release-validate-full`
- [ ] Test installation from wheel

### Publishing

- [ ] Create git tag: `git tag v0.X.Y`
- [ ] Push tag: `git push --tags`
- [ ] Upload to TestPyPI: `make release-upload-test`
- [ ] Test install from TestPyPI
- [ ] Upload to PyPI: `make release-upload`
- [ ] Create GitHub release with notes
- [ ] Announce release

## Building Wheels

### Build for Specific Platform

```bash
# Build wheel for current platform (auto-detected)
make wheel PLATFORM=darwin_arm64

# Available platforms:
# - darwin_arm64   (Apple Silicon)
# - darwin_amd64   (Intel Mac)
# - linux_amd64    (x86_64 Linux)
# - linux_arm64    (ARM64 Linux)
```

### Build for All Platforms

```bash
# Build wheels for all supported platforms
make release-all
```

This creates wheels in `dist/` with names like:
- `flavorpack-0.0.1023-py3-none-macosx_11_0_arm64.whl`
- `flavorpack-0.0.1023-py3-none-linux_x86_64.whl`

### Build Universal Wheel

```bash
# Build wheel without embedded helpers (requires separate helper installation)
make wheel-universal
```

## Validation

### Quick Validation

```bash
# Validate wheel structure and metadata
make release-validate
```

### Full Validation

```bash
# Validate + test installation
make release-validate-full
```

### Manual Testing

```bash
# Install from local wheel
pip install dist/flavorpack-*.whl

# Test basic operations
flavor --version
flavor helpers list
flavor pack --manifest pyproject.toml --output test.psp
flavor verify test.psp
```

## Version Bumping

### Update Version

Edit `pyproject.toml`:

```toml
[project]
name = "flavorpack"
version = "0.1.0"  # Update this
```

### Update Changelog

Add entry to `CHANGELOG.md`:

```markdown
## [0.1.0] - 2025-10-24

### Added
- New feature description

### Changed
- Changed behavior description

### Fixed
- Bug fix description
```

### Create Git Tag

```bash
# Create annotated tag
git tag -a v0.1.0 -m "Release v0.1.0"

# Push tag
git push origin v0.1.0

# Or push all tags
git push --tags
```

## Publishing to PyPI

### TestPyPI (Recommended First)

```bash
# Upload to TestPyPI for testing
make release-upload-test

# Test installation
pip install --index-url https://test.pypi.org/simple/ flavorpack
```

### Production PyPI

```bash
# Upload to production PyPI
make release-upload
```

**Prerequisites**:
- PyPI account with API token
- `~/.pypirc` configured or `TWINE_USERNAME`/`TWINE_PASSWORD` set

## GitHub Release

### Create Release

1. Go to [Releases page](https://github.com/provide-io/flavorpack/releases)
2. Click "Draft a new release"
3. Select the version tag
4. Generate release notes or write manually
5. Attach wheel files from `dist/`
6. Publish release

### Release Notes Template

```markdown
# FlavorPack v0.1.0

## Highlights

Brief description of major changes.

## What's Changed

### Added
- Feature 1
- Feature 2

### Changed
- Change 1
- Change 2

### Fixed
- Fix 1
- Fix 2

## Installation

\`\`\`bash
pip install flavorpack==0.1.0
\`\`\`

## Assets

- Platform-specific wheels for macOS (Intel/Apple Silicon), Linux (x86_64/ARM64)
- Source distribution

**Full Changelog**: https://github.com/provide-io/flavorpack/compare/v0.0.X...v0.1.0
```

## Release Automation

### CI/CD Pipeline

The release process can be automated through GitHub Actions:

1. **On tag push**: Trigger release build
2. **Build helpers**: Build for all platforms
3. **Build wheels**: Create platform-specific wheels
4. **Validate**: Run validation suite
5. **Upload**: Publish to PyPI
6. **Create release**: Auto-create GitHub release

See [CI/CD Documentation](ci-cd/) for workflow details.

## Troubleshooting

### Wheel Build Fails

```bash
# Clean and rebuild
make release-clean
make build-helpers
make release-all
```

### Missing Helpers

```bash
# Ensure helpers are built first
make build-helpers
ls dist/bin/flavor-*

# Should show binaries for all platforms
```

### PyPI Upload Fails

```bash
# Check credentials
twine check dist/*.whl

# Upload with verbose output
twine upload --verbose dist/*.whl
```

### Version Conflict

```bash
# If version already exists on PyPI, bump version
# Update pyproject.toml
# Rebuild wheels
make release-clean
make release-all
```

## Post-Release

### Verification

- [ ] Check PyPI page: https://pypi.org/project/flavorpack/
- [ ] Test fresh installation: `pip install flavorpack`
- [ ] Verify helper binaries included
- [ ] Test basic commands work
- [ ] Check documentation site is updated

### Announcement

- Update project README if needed
- Post to discussions/community channels
- Update any external documentation
- Notify users of breaking changes (if any)

## Emergency Rollback

If a critical issue is found after release:

1. **Yank the release on PyPI** (marks it as unavailable but doesn't delete)
2. **Create hotfix branch** from the tagged release
3. **Fix the issue** and bump patch version
4. **Create new release** following normal process
5. **Announce the issue** and new fixed version

```bash
# Yank a release (requires PyPI permissions)
pip install twine
twine upload --repository pypi --yank dist/flavorpack-X.Y.Z-*.whl
```

---

**See also:**
- [CI/CD](ci-cd/) - Automated release workflows
- [Contributing](contributing/) - Development guidelines
- [Testing](testing/index/) - Test requirements before release
