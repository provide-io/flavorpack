#!/bin/bash
set -e

# Organize downloaded artifacts into helpers/bin
# Usage: .github/scripts/organize-artifacts.sh [download-dir]
#
# With new platform-centric build, artifacts are organized as:
# - all-helpers-{sha}/bin/flavor-{lang}-{type}-{platform}[.exe]
# - helpers-{platform}/flavor-{lang}-{type}-{platform}[.exe]

DOWNLOAD_DIR="${1:-.}"

echo "📦 Organizing artifacts from: $DOWNLOAD_DIR"

# Create bin directory
mkdir -p helpers/bin

# Function to find and copy helpers
find_and_copy_helpers() {
    local search_dir="$1"
    local pattern="$2"
    
    if [ -d "$search_dir" ]; then
        find "$search_dir" -type f -name "$pattern" 2>/dev/null | while read -r file; do
            if [ -f "$file" ]; then
                echo "  Found: $(basename "$file")"
                cp "$file" helpers/bin/
            fi
        done
    fi
}

# Platforms we build for
PLATFORMS=(
    "linux_amd64"
    "linux_arm64"
    "darwin_amd64"
    "darwin_arm64"
    "windows_amd64"
)

# Helper types we build
HELPER_TYPES=(
    "flavor-go-launcher"
    "flavor-go-builder"
    "flavor-rs-launcher"
    "flavor-rs-builder"
)

echo "📍 Searching for platform-specific helpers..."

# Search in all possible locations
SEARCH_DIRS=(
    "$DOWNLOAD_DIR"
    "$DOWNLOAD_DIR/bin"
    "$DOWNLOAD_DIR/helpers/bin"
)

# Add any all-helpers-* directories
for dir in "$DOWNLOAD_DIR"/all-helpers-*/; do
    if [ -d "$dir" ]; then
        SEARCH_DIRS+=("$dir")
        SEARCH_DIRS+=("$dir/bin")
    fi
done

# Add any platform-specific directories (helpers-{platform})
for platform in "${PLATFORMS[@]}"; do
    if [ -d "$DOWNLOAD_DIR/helpers-${platform}" ]; then
        SEARCH_DIRS+=("$DOWNLOAD_DIR/helpers-${platform}")
    fi
done

# Search each directory for helpers
for dir in "${SEARCH_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  Checking: $dir"
        for platform in "${PLATFORMS[@]}"; do
            for helper in "${HELPER_TYPES[@]}"; do
                # Platform-specific binary (with or without .exe)
                find_and_copy_helpers "$dir" "${helper}-${platform}*"
            done
        done
    fi
done

# Set executable permissions on Unix platforms
if [ "$(uname)" != "Windows_NT" ]; then
    echo "🔐 Setting executable permissions..."
    chmod +x helpers/bin/flavor-* 2>/dev/null || true
fi

# List what we found
echo ""
echo "📦 Organized helpers:"
if [ -d helpers/bin ] && [ "$(ls -A helpers/bin 2>/dev/null)" ]; then
    ls -la helpers/bin/
else
    echo "  No helpers found in helpers/bin/"
fi

# Count helpers by type
echo ""
echo "📊 Summary by type:"
for helper in "${HELPER_TYPES[@]}"; do
    count=$(find helpers/bin -name "${helper}-*" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
        echo "  $helper: $count variants"
    fi
done

# Count helpers by platform
echo ""
echo "📊 Summary by platform:"
for platform in "${PLATFORMS[@]}"; do
    count=$(find helpers/bin -name "*-${platform}*" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
        echo "  $platform: $count helpers"
    fi
done

# Verify we have at least some helpers
TOTAL_HELPERS=$(find helpers/bin -name "flavor-*" 2>/dev/null | wc -l)
if [ "$TOTAL_HELPERS" -eq 0 ]; then
    echo ""
    echo "⚠️ Warning: No helpers found after organization"
    echo "  Search directories checked:"
    for dir in "${SEARCH_DIRS[@]}"; do
        echo "    - $dir"
    done
    echo ""
    echo "  Files found in download directory:"
    find "$DOWNLOAD_DIR" -type f -name "flavor-*" 2>/dev/null | head -10 || echo "    None"
    exit 1
else
    echo ""
    echo "✅ Successfully organized $TOTAL_HELPERS helper binaries"
fi