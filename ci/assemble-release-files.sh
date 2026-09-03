#!/bin/bash
set -euo pipefail

# Gather every downloaded artifact into the single directory the GitHub release
# is cut from.
# Usage: assemble-release-files.sh <artifacts_dir> <output_dir>
#
# This is the last hop before assets are attached. It ran as a chain of
# `cp ... 2>/dev/null || true` lines globbing *.psp, so both Windows .exe
# packages were dropped here -- after being built, collected and uploaded --
# and the `|| true` kept the job green while it happened. The v0.5.0 Windows
# binaries had to be attached by hand.

ARTIFACTS_DIR="${1:-artifacts}"
OUTPUT_DIR="${2:-release}"

if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo "❌ Artifacts directory not found: $ARTIFACTS_DIR"
    echo "   Nothing was downloaded, so there is nothing to release."
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# collect <label> <glob>...
# Copies each existing match and names it in the log, reporting the count in
# COLLECTED. A copy that fails is fatal: a release missing an asset it was told
# to carry is the defect this script exists to prevent, not a line to scroll
# past.
COLLECTED=0
collect() {
    local label="$1"
    shift

    COLLECTED=0
    local candidate
    for candidate in "$@"; do
        if [ -f "$candidate" ]; then
            local name
            name=$(basename "$candidate")
            echo "  📦 ${label}: $name"
            cp "$candidate" "$OUTPUT_DIR/$name"
            COLLECTED=$((COLLECTED + 1))
        fi
    done
}

echo "🗂️ Assembling release files from $ARTIFACTS_DIR"

collect wheel "$ARTIFACTS_DIR"/release-wheels/*.whl
WHEELS=$COLLECTED

# .psp and .exe are one asset class under two names: a Windows flavor package is
# written .exe so it is directly runnable. Globbing only *.psp is what dropped
# every Windows package from every release.
collect package "$ARTIFACTS_DIR"/release-psp/*.psp "$ARTIFACTS_DIR"/release-psp/*.exe
PACKAGES=$COLLECTED

collect asset "$ARTIFACTS_DIR"/release-assets/*.txt "$ARTIFACTS_DIR"/release-assets/*.md
DOCS=$COLLECTED

# A package arrives from an artifact download without its execute bit, and the
# whole promise of a PSP is that a user downloads it and runs it.
for package in "$OUTPUT_DIR"/*.psp "$OUTPUT_DIR"/*.exe; do
    if [ -f "$package" ]; then
        chmod +x "$package"
    fi
done

echo ""
echo "📋 Assembled: $WHEELS wheel(s), $PACKAGES package(s), $DOCS other asset(s)"

if [ "$((WHEELS + PACKAGES))" -eq 0 ]; then
    echo "❌ No wheels and no packages. The release would ship nothing installable."
    exit 1
fi

# The release body is read from this file. Publishing without it produces a
# release with an empty description and no way to tell what is in it.
if [ ! -f "$OUTPUT_DIR/release-notes.md" ]; then
    echo "❌ release-notes.md was not assembled — the release would have no body."
    exit 1
fi

if [ ! -f "$OUTPUT_DIR/checksums.txt" ]; then
    echo "❌ checksums.txt was not assembled — no asset could be verified."
    exit 1
fi

ls -la "$OUTPUT_DIR/"
