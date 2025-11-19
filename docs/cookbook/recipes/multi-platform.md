# Multi-Platform Builds

Build packages for multiple platforms from a single codebase.

## Overview

FlavorPack supports building packages for different platforms (Linux, macOS, Windows) and architectures (AMD64, ARM64) from a single build machine.

## Single-Platform Build

Build for your current platform:

```bash
# Builds for current platform automatically
flavor pack --manifest pyproject.toml
```

## Cross-Platform Build

Build for specific platforms:

```bash
# Build for Linux AMD64
flavor pack \
  --launcher-bin dist/bin/flavor-rs-launcher-linux_amd64 \
  --output dist/myapp-linux-amd64.psp

# Build for macOS ARM64
flavor pack \
  --launcher-bin dist/bin/flavor-rs-launcher-darwin_arm64 \
  --output dist/myapp-macos-arm64.psp

# Build for Linux ARM64
flavor pack \
  --launcher-bin dist/bin/flavor-rs-launcher-linux_arm64 \
  --output dist/myapp-linux-arm64.psp
```

## Build Script

Automate multi-platform builds:

```bash
#!/bin/bash
# build-all-platforms.sh

PLATFORMS=(
    "linux_amd64"
    "linux_arm64"
    "darwin_amd64"
    "darwin_arm64"
)

for platform in "${PLATFORMS[@]}"; do
    echo "Building for $platform..."

    flavor pack \
        --launcher-bin "dist/bin/flavor-rs-launcher-$platform" \
        --output "dist/myapp-$platform.psp" \
        --strip

    if [ $? -eq 0 ]; then
        echo "✅ Built myapp-$platform.psp"
    else
        echo "❌ Failed to build for $platform"
    fi
done

echo "Build complete!"
ls -lh dist/*.psp
```

## CI/CD Integration

### GitHub Actions

{% raw %}
```yaml
name: Multi-Platform Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        platform:
          - linux_amd64
          - linux_arm64
          - darwin_amd64
          - darwin_arm64

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install FlavorPack
        run: pip install flavor

      - name: Build helpers
        run: make build-helpers

      - name: Build package
        run: |
          flavor pack \
            --launcher-bin dist/bin/flavor-rs-launcher-${{ matrix.platform }} \
            --output dist/myapp-${{ matrix.platform }}.psp \
            --strip

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: myapp-${{ matrix.platform }}
          path: dist/myapp-${{ matrix.platform }}.psp
```
{% endraw %}

## Platform-Specific Configuration

```toml
# pyproject.toml

[tool.flavor]
entry_point = "myapp:main"

[tool.flavor.platforms.linux]
# Linux-specific settings
exclude = ["*.dll", "*.dylib"]

[tool.flavor.platforms.darwin]
# macOS-specific settings
exclude = ["*.so", "*.dll"]

[tool.flavor.platforms.windows]
# Windows-specific settings
exclude = ["*.so", "*.dylib"]
```

## Verification

Verify all platform builds:

```bash
#!/bin/bash
# verify-all.sh

for package in dist/*.psp; do
    echo "Verifying $package..."
    flavor verify "$package"
done
```

## Distribution

Organize releases by platform:

```
releases/
├── v1.0.0/
│   ├── myapp-linux-amd64.psp
│   ├── myapp-linux-arm64.psp
│   ├── myapp-darwin-amd64.psp
│   ├── myapp-darwin-arm64.psp
│   ├── checksums.txt
│   └── README.md
```

Generate checksums:

```bash
cd dist
sha256sum *.psp > checksums.txt
```

## See Also

- [Packaging Guide](../../guide/packaging/index/)
- [Platform Support](../../guide/packaging/platforms/)
- [CI/CD Integration](ci-cd/)
