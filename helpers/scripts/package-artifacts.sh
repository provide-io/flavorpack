#!/bin/bash
set -e

# package-artifacts.sh - Package helper binaries into structured artifacts
# Usage: ./package-artifacts.sh <language> <platform> <bin_dir> <output_dir> [version]

LANG=$1
PLATFORM=$2
BIN_DIR=$3
OUTPUT_DIR=$4
VERSION=${5:-"0.0.0"}  # Default to 0.0.0 if not provided

# Warn if using default version
if [ "$VERSION" = "0.0.0" ] && [ -z "$5" ]; then
    echo "⚠️ Warning: No version specified, using default 0.0.0"
fi

if [ -z "$LANG" ] || [ -z "$PLATFORM" ] || [ -z "$BIN_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <language> <platform> <bin_dir> <output_dir> [version]"
    echo "  language: go or rs"
    echo "  platform: linux_{386,amd64,arm,arm64}, darwin_{amd64,arm64}, windows_{386,amd64,arm,arm64}, freebsd_{386,amd64,arm,arm64}"
    echo "  bin_dir: directory containing built binaries"
    echo "  output_dir: directory to create artifact structure"
    echo "  version: version number (default: 0.0.0)"
    exit 1
fi

# Create artifact directory with version
ARTIFACT_DIR="${OUTPUT_DIR}/flavor-${LANG}-helpers-${VERSION}_${PLATFORM}"
mkdir -p "$ARTIFACT_DIR"

echo "📦 Creating artifact structure for flavor-${LANG}-helpers-${VERSION}_${PLATFORM}"

# Copy binaries based on platform
if [[ "$PLATFORM" == windows_* ]]; then
    # Windows binaries have .exe extension
    # Try platform-specific first, then fallback to generic
    for binary in "${BIN_DIR}"/flavor-${LANG}-*-${PLATFORM}.exe "${BIN_DIR}"/flavor-${LANG}-*.exe; do
        if [ -f "$binary" ]; then
            cp "$binary" "$ARTIFACT_DIR/"
        fi
    done
else
    # Unix binaries - try with platform suffix first, then without
    for pattern in "flavor-${LANG}-*-${PLATFORM}" "flavor-${LANG}-*"; do
        for binary in "${BIN_DIR}"/${pattern}; do
            if [ -f "$binary" ] && [[ ! "$binary" == *-*_* || "$binary" == *-${PLATFORM} ]]; then
                cp "$binary" "$ARTIFACT_DIR/"
            fi
        done
    done
fi

# Create README based on language
if [ "$LANG" = "go" ]; then
    cat > "$ARTIFACT_DIR/README.md" << EOF
# Flavor Go Helpers

Version: ${VERSION}
Platform: ${PLATFORM}
Built: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Contents

- \`flavor-go-builder\`: Go-based PSPF package builder
- \`flavor-go-launcher\`: Go-based PSPF package launcher

## Installation

1. Extract this archive to your desired location
2. Add the directory to your PATH or copy binaries to a directory in PATH
3. Make binaries executable (Unix): \`chmod +x flavor-go-*\`

## Usage

### Builder
\`\`\`bash
flavor-go-builder --manifest manifest.json --output package.psp
\`\`\`

### Launcher
The launcher is embedded in PSPF packages and executes them.

## Cross-compilation

These binaries were cross-compiled for ${PLATFORM} using Go's built-in cross-compilation support.

## Version Info

Run with \`--version\` flag to see version information:
\`\`\`bash
./flavor-go-builder --version
./flavor-go-launcher --version
\`\`\`

## Requirements

- No external dependencies required
- Binaries are statically linked

## More Information

- Repository: https://github.com/provide-io/flavor
- Documentation: https://github.com/provide-io/flavor/tree/main/helpers/flavor-go
EOF

elif [ "$LANG" = "rs" ]; then
    cat > "$ARTIFACT_DIR/README.md" << EOF
# Flavor Rust Helpers

Version: ${VERSION}
Platform: ${PLATFORM}
Built: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Contents

- \`flavor-rs-builder\`: Rust-based PSPF package builder
- \`flavor-rs-launcher\`: Rust-based PSPF package launcher

## Installation

1. Extract this archive to your desired location
2. Add the directory to your PATH or copy binaries to a directory in PATH
3. Make binaries executable (Unix): \`chmod +x flavor-rs-*\`

## Usage

### Builder
\`\`\`bash
flavor-rs-builder --manifest manifest.json --output package.psp
\`\`\`

### Launcher
The launcher is embedded in PSPF packages and executes them.

## Cross-compilation

These binaries were cross-compiled for ${PLATFORM} using Rust's cross-compilation toolchain.

## Version Info

Run with \`--version\` flag to see version information:
\`\`\`bash
./flavor-rs-builder --version
./flavor-rs-launcher --version
\`\`\`

## Requirements

- No external dependencies required
- Binaries are statically linked (where possible)
- Linux builds use musl for maximum compatibility

## More Information

- Repository: https://github.com/provide-io/flavor
- Documentation: https://github.com/provide-io/flavor/tree/main/helpers/flavor-rs
EOF
fi

# Add platform-specific notes
case "$PLATFORM" in
    linux_*)
        echo "" >> "$ARTIFACT_DIR/README.md"
        echo "## Linux Notes" >> "$ARTIFACT_DIR/README.md"
        echo "- Built on Ubuntu 24.04" >> "$ARTIFACT_DIR/README.md"
        echo "- Statically linked (Go with CGO_ENABLED=0)" >> "$ARTIFACT_DIR/README.md"
        echo "- Compatible with CentOS 7, RHEL 7, and newer" >> "$ARTIFACT_DIR/README.md"
        echo "- Should work on any Linux distribution with kernel 3.10+" >> "$ARTIFACT_DIR/README.md"
        ;;
    darwin_*)
        echo "" >> "$ARTIFACT_DIR/README.md"
        echo "## macOS Notes" >> "$ARTIFACT_DIR/README.md"
        echo "- Built on macOS 15" >> "$ARTIFACT_DIR/README.md"
        echo "- Minimum macOS version: 11.0 (Big Sur)" >> "$ARTIFACT_DIR/README.md"
        echo "- Universal binary supports both Intel and Apple Silicon" >> "$ARTIFACT_DIR/README.md"
        ;;
    windows_*)
        echo "" >> "$ARTIFACT_DIR/README.md"
        echo "## Windows Notes" >> "$ARTIFACT_DIR/README.md"
        echo "- Built on Windows Server 2025" >> "$ARTIFACT_DIR/README.md"
        echo "- Requires Windows 10 or later" >> "$ARTIFACT_DIR/README.md"
        echo "- May require Visual C++ Redistributables" >> "$ARTIFACT_DIR/README.md"
        ;;
    freebsd_*)
        echo "" >> "$ARTIFACT_DIR/README.md"
        echo "## FreeBSD Notes" >> "$ARTIFACT_DIR/README.md"
        echo "- Cross-compiled from Ubuntu 24.04" >> "$ARTIFACT_DIR/README.md"
        echo "- Should work on FreeBSD 12.0 or later" >> "$ARTIFACT_DIR/README.md"
        echo "- Statically linked for maximum compatibility" >> "$ARTIFACT_DIR/README.md"
        ;;
esac

# List contents
echo "📋 Artifact contents:"
ls -la "$ARTIFACT_DIR/"

# Count binaries
if [[ "$PLATFORM" == windows_* ]]; then
    BINARY_COUNT=$(find "$ARTIFACT_DIR" -type f -name "*.exe" | wc -l)
else
    BINARY_COUNT=$(find "$ARTIFACT_DIR" -type f -name "flavor-${LANG}-*" ! -name "*.md" | wc -l)
fi
echo "✅ Packaged $BINARY_COUNT binaries for ${PLATFORM}"

# Return success if we have binaries
if [ "$BINARY_COUNT" -gt 0 ]; then
    exit 0
else
    echo "⚠️ Warning: No binaries found for ${PLATFORM}"
    exit 1
fi