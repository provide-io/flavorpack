#!/bin/bash
set -e

# Generate platform-specific build metadata
# Usage: generate-platform-metadata.sh <platform> <version> <cache_hit> <output_dir>

PLATFORM="${1:-unknown}"
VERSION="${2:-unknown}"
CACHE_HIT="${3:-false}"
OUTPUT_DIR="${4:-metadata}"

# Runner info
RUNNER_OS="${RUNNER_OS:-unknown}"
RUNNER_ARCH="${RUNNER_ARCH:-unknown}"
RUNNER_NAME="${RUNNER_NAME:-unknown}"

# Job info
GITHUB_JOB="${GITHUB_JOB:-unknown}"
GITHUB_RUN_ID="${GITHUB_RUN_ID:-unknown}"
GITHUB_RUN_NUMBER="${GITHUB_RUN_NUMBER:-unknown}"
GITHUB_RUN_ATTEMPT="${GITHUB_RUN_ATTEMPT:-1}"
GITHUB_WORKFLOW="${GITHUB_WORKFLOW:-unknown}"
GITHUB_SHA="${GITHUB_SHA:-unknown}"
GITHUB_REF="${GITHUB_REF:-unknown}"

# Build info
BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BUILD_DURATION="${BUILD_DURATION:-0}"

# Determine build source
if [ "$CACHE_HIT" = "true" ]; then
    BUILD_SOURCE="cache"
else
    BUILD_SOURCE="built"
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate platform metadata JSON
cat > "$OUTPUT_DIR/platform-metadata.json" << EOF
{
  "platform": "$PLATFORM",
  "version": "$VERSION",
  "build": {
    "time": "$BUILD_TIME",
    "duration_seconds": $BUILD_DURATION,
    "source": "$BUILD_SOURCE",
    "cache_hit": $CACHE_HIT
  },
  "runner": {
    "os": "$RUNNER_OS",
    "arch": "$RUNNER_ARCH",
    "name": "$RUNNER_NAME"
  },
  "github": {
    "job": "$GITHUB_JOB",
    "workflow": "$GITHUB_WORKFLOW",
    "run_id": "$GITHUB_RUN_ID",
    "run_number": "$GITHUB_RUN_NUMBER",
    "run_attempt": "$GITHUB_RUN_ATTEMPT",
    "sha": "$GITHUB_SHA",
    "ref": "$GITHUB_REF"
  },
  "binaries": []
}
EOF

echo "📊 Generated platform metadata for $PLATFORM"
echo "   Version: $VERSION"
echo "   Source: $BUILD_SOURCE"
echo "   Output: $OUTPUT_DIR/platform-metadata.json"

# If binaries exist, add their metadata
if [ -d "helpers/bin" ]; then
    echo ""
    echo "🔍 Scanning binaries..."
    
    # Create temporary file for binary metadata
    BINARY_JSON="[]"
    
    for binary in helpers/bin/*-"$PLATFORM"*; do
        if [ -f "$binary" ]; then
            BINARY_NAME=$(basename "$binary")
            # Get file size (cross-platform)
            if [ -n "$RUNNER_OS" ] && [ "$RUNNER_OS" = "Windows" ]; then
                BINARY_SIZE=$(wc -c < "$binary" | tr -d ' ' 2>/dev/null || echo "0")
            else
                BINARY_SIZE=$(stat -f%z "$binary" 2>/dev/null || stat -c%s "$binary" 2>/dev/null || wc -c < "$binary" | tr -d ' ' 2>/dev/null || echo "0")
            fi
            BINARY_SHA256=$(shasum -a 256 "$binary" | cut -d' ' -f1)
            
            # Determine component type
            COMPONENT=""
            case "$BINARY_NAME" in
                *go-launcher*) COMPONENT="go-launcher" ;;
                *go-builder*) COMPONENT="go-builder" ;;
                *rs-launcher*) COMPONENT="rust-launcher" ;;
                *rs-builder*) COMPONENT="rust-builder" ;;
            esac
            
            # Try to get version
            BINARY_VERSION="unknown"
            if [[ "$PLATFORM" == "linux_amd64" ]] || [[ "$PLATFORM" == *"darwin"* ]]; then
                # Try to execute for version
                if timeout 2 "$binary" --version >/dev/null 2>&1; then
                    BINARY_VERSION=$("$binary" --version 2>/dev/null | head -1 | sed -E 's/^[^ ]+ ([0-9.]+).*/\1/' || echo "unknown")
                fi
            else
                # Extract from filename
                BINARY_VERSION=$(echo "$BINARY_NAME" | sed -E 's/.*-([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/' || echo "unknown")
            fi
            
            # Add to binary metadata
            BINARY_ENTRY=$(cat << JSON
{
  "name": "$BINARY_NAME",
  "component": "$COMPONENT",
  "version": "$BINARY_VERSION",
  "size": $BINARY_SIZE,
  "sha256": "$BINARY_SHA256"
}
JSON
)
            
            if [ "$BINARY_JSON" = "[]" ]; then
                BINARY_JSON="[$BINARY_ENTRY"
            else
                BINARY_JSON="$BINARY_JSON, $BINARY_ENTRY"
            fi
            
            echo "   📦 $COMPONENT: $BINARY_VERSION ($BINARY_SIZE bytes)"
        fi
    done
    
    if [ "$BINARY_JSON" != "[]" ]; then
        BINARY_JSON="$BINARY_JSON]"
        
        # Update the JSON with binary metadata
        python3 -c "
import json
with open('$OUTPUT_DIR/platform-metadata.json', 'r') as f:
    data = json.load(f)
data['binaries'] = $BINARY_JSON
with open('$OUTPUT_DIR/platform-metadata.json', 'w') as f:
    json.dump(data, f, indent=2)
"
    fi
fi

echo ""
echo "✅ Metadata generation complete"