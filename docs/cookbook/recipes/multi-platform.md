# Multi-Platform Builds

Build packages for multiple platforms by packaging on each target OS/architecture.

## Overview

FlavorPack packages the runtime and launcher for the **current build host**. To produce binaries for multiple platforms, run packaging on each target platform.

## Single-Platform Build

```bash
# Builds for current platform automatically
flavor pack --manifest pyproject.toml
```

## Multi-Platform Build Strategy

Use CI to run builds on each OS:

{% raw %}
```yaml
name: Multi-Platform Build

on: [push]

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install FlavorPack
        run: uv tool install flavorpack

      - name: Build helpers
        run: make build-helpers

      - name: Build package
        run: flavor pack --manifest pyproject.toml --strip

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: myapp-${{ matrix.os }}
          path: dist/*.psp
```
{% endraw %}

## Verification

```bash
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

- [Packaging Guide](../../guide/packaging/index.md)
- [CI/CD Integration](ci-cd.md)
