#!/bin/bash
set -euo pipefail

# Write the release body listing the assets the release actually attaches.
# Usage: generate-release-notes.sh <version> <repository> [output_file]
#
# The asset list was spelled out by hand inline in release.yml, which made it a
# second place naming files the pipeline names elsewhere. That is the split that
# shipped v0.5.0 promising Windows packages the release job was dropping. Here
# the platform table is written once and every name is derived from it, so the
# extension rule cannot disagree with itself.

VERSION="${1:-}"
REPOSITORY="${2:-}"
OUTPUT="${3:-release/release-notes.md}"

if [ -z "$VERSION" ] || [ -z "$REPOSITORY" ]; then
    echo "❌ Usage: $0 <version> <repository> [output_file]"
    exit 1
fi

DOCS_BASE="https://foundry.provide.io/flavorpack"
DOWNLOAD_BASE="https://github.com/${REPOSITORY}/releases/download/v${VERSION}"

# platform | wheel tag | description
# One row per platform that is built and attached.
PLATFORMS="
linux_amd64|manylinux2014_x86_64|Linux x86_64
linux_arm64|manylinux2014_aarch64|Linux ARM64
darwin_amd64|macosx_10_9_x86_64|macOS Intel
darwin_arm64|macosx_11_0_arm64|macOS Apple Silicon
windows_amd64|win_amd64|Windows x86_64
windows_arm64|win_arm64|Windows ARM64
"

# A Windows package is written .exe so it is directly runnable; everything else
# is .psp. This is the same rule the build scripts apply, stated once.
package_extension() {
    case "$1" in
        windows_*) echo ".exe" ;;
        *) echo ".psp" ;;
    esac
}

wheel_lines() {
    echo "$PLATFORMS" | while IFS='|' read -r platform tag description; do
        [ -n "$platform" ] || continue
        echo "- \`flavorpack-${VERSION}-py3-none-${tag}.whl\` - ${description}"
    done
}

package_lines() {
    echo "$PLATFORMS" | while IFS='|' read -r platform tag description; do
        [ -n "$platform" ] || continue
        echo "- \`flavor-${VERSION}-${platform}$(package_extension "$platform")\` - ${description}"
    done
}

mkdir -p "$(dirname "$OUTPUT")"

cat > "$OUTPUT" << EOF
# Flavor Pack ${VERSION}

## 🎯 Quick Install

### Install from PyPI
\`\`\`bash
# Install platform-specific wheel with embedded helpers
pip install flavorpack==${VERSION}

# Or download and run the self-contained PSP
curl -LO ${DOWNLOAD_BASE}/flavor-${VERSION}-linux_amd64.psp
chmod +x flavor-${VERSION}-linux_amd64.psp
./flavor-${VERSION}-linux_amd64.psp --help
\`\`\`

## 📦 Release Assets

### Python Wheels
Platform-specific wheels with embedded Go and Rust helpers:
$(wheel_lines)

### Self-Contained PSP Packages
Ready-to-run executables (no Python required):
$(package_lines)

### Test Packages
- \`taster-${VERSION}-<platform>.psp\` (\`.exe\` on Windows) - Comprehensive test suite

## 🔧 What's New

See [Changelog](${DOCS_BASE}/community/changelog/) for detailed changes.

## 🔒 Verification

All packages are signed with Ed25519. Verify checksums:
\`\`\`bash
curl -LO ${DOWNLOAD_BASE}/checksums.txt
sha256sum -c checksums.txt
\`\`\`

## 📚 Documentation

- [User Guide](${DOCS_BASE}/guide/)
- [API Reference](${DOCS_BASE}/api/)
- [Troubleshooting](${DOCS_BASE}/troubleshooting/)
EOF

echo "📝 Wrote release notes to $OUTPUT"
