#!/bin/bash
# Cache build dependencies for offline installation on Windows
# Usage: cache-build-deps.sh <output_dir>

set -euo pipefail

OUTPUT_DIR="${1:-wheelhouse}"

echo "📦 Caching build dependencies to $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Download build dependencies as wheels
# Include platform-specific deps for Windows (colorama is required by build on Windows)
pip download build wheel setuptools pip -d "$OUTPUT_DIR"

# Download Windows-specific dependencies (colorama is needed by build on Windows)
pip download colorama -d "$OUTPUT_DIR"

echo ""
echo "✅ Cached dependencies:"
ls -la "$OUTPUT_DIR"
