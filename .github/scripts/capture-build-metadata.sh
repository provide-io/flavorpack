#!/bin/bash
set -e

# Capture comprehensive build metadata with all timing details
# Usage: .github/scripts/capture-build-metadata.sh <platform> <version> <output_dir>

PLATFORM="${1:-unknown}"
VERSION="${2:-0.0.0}"
OUTPUT_DIR="${3:-artifacts/metadata}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Get system information
RUNNER_OS=$(uname -s | tr '[:upper:]' '[:lower:]')
RUNNER_ARCH=$(uname -m)
RUNNER_VERSION=$(uname -r)
CPU_COUNT=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "unknown")
MEMORY_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "unknown")

# Map architecture names
case "$RUNNER_ARCH" in
    x86_64) RUNNER_ARCH="amd64" ;;
    aarch64|arm64) RUNNER_ARCH="arm64" ;;
esac

# Initialize metadata JSON
METADATA_FILE="$OUTPUT_DIR/flavor-helpers-${VERSION}-${PLATFORM}.build.json"

# Function to get current timestamp in ISO format
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Function to calculate duration in milliseconds
calculate_duration() {
    local start_ns=$1
    local end_ns=$2
    echo $(( (end_ns - start_ns) / 1000000 ))
}

# Get GitHub Actions context
GITHUB_RUN_ID="${GITHUB_RUN_ID:-unknown}"
GITHUB_RUN_NUMBER="${GITHUB_RUN_NUMBER:-unknown}"
GITHUB_SHA="${GITHUB_SHA:-unknown}"
GITHUB_REF="${GITHUB_REF:-unknown}"
GITHUB_WORKFLOW="${GITHUB_WORKFLOW:-unknown}"
GITHUB_JOB="${GITHUB_JOB:-unknown}"
GITHUB_ACTOR="${GITHUB_ACTOR:-unknown}"
GITHUB_EVENT_NAME="${GITHUB_EVENT_NAME:-unknown}"

# Start building metadata
cat > "$METADATA_FILE" << EOF
{
  "platform": "$PLATFORM",
  "version": "$VERSION",
  "artifact_name": "flavor-helpers-${VERSION}-${PLATFORM}.zip",
  "build_timestamp": "$(get_timestamp)",
  "github": {
    "run_id": "$GITHUB_RUN_ID",
    "run_number": "$GITHUB_RUN_NUMBER",
    "sha": "$GITHUB_SHA",
    "ref": "$GITHUB_REF",
    "workflow": "$GITHUB_WORKFLOW",
    "job": "$GITHUB_JOB",
    "actor": "$GITHUB_ACTOR",
    "event": "$GITHUB_EVENT_NAME"
  },
  "runner": {
    "os": "$RUNNER_OS",
    "arch": "$RUNNER_ARCH",
    "version": "$RUNNER_VERSION",
    "cpu_count": "$CPU_COUNT",
    "memory_kb": "$MEMORY_KB"
  },
  "environment": {
    "PATH": "$PATH",
    "GOVERSION": "$(go version 2>/dev/null || echo 'not installed')",
    "RUSTVERSION": "$(rustc --version 2>/dev/null || echo 'not installed')",
    "CC": "${CC:-not set}",
    "CXX": "${CXX:-not set}",
    "CARGO_TARGET": "${CARGO_BUILD_TARGET:-not set}"
  },
  "timings": {}
}
EOF

# Export for use in other scripts (only if GITHUB_ENV exists)
if [ -n "$GITHUB_ENV" ]; then
  echo "METADATA_FILE=$METADATA_FILE" >> $GITHUB_ENV
fi

# Output only the file path for GITHUB_OUTPUT capture
echo "$METADATA_FILE"