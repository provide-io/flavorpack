#!/bin/bash
set -euo pipefail

# Organize and rename wheels for release
# Usage: organize-release-wheels.sh <input_dir> <output_dir> <version>

INPUT_DIR="${1:-wheels}"
OUTPUT_DIR="${2:-release-wheels}"
# Not "${3}": set -u would abort on an unset argument before the check below
# could explain what was missing.
VERSION="${3:-}"

if [ -z "$VERSION" ]; then
    echo "❌ Error: Version is required"
    echo "Usage: $0 <input_dir> <output_dir> <version>"
    exit 1
fi

echo "📦 Organizing wheels for version $VERSION"

if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ Input directory not found: $INPUT_DIR"
    echo "   The download step produced nothing, so the release would ship no wheels."
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

COLLECTED=0

# Find all wheel files and copy them for the release.
for wheel_dir in "$INPUT_DIR"/flavor-wheel-*; do
    if [ -d "$wheel_dir" ]; then
        platform=$(basename "$wheel_dir" | sed -E 's/flavor-wheel-[0-9.]*-//')
        echo "  Processing platform: $platform"

        platform_wheels=0
        for wheel in "$wheel_dir"/*.whl; do
            if [ -f "$wheel" ]; then
                # Not renamed: PEP 440 normalises versions (0.0.2-dev1 becomes
                # 0.0.2.dev1) and the wheels already carry the normalised name.
                # Rewriting it here would produce a filename pip rejects.
                basename=$(basename "$wheel")

                echo "    Copying: $basename"
                cp "$wheel" "$OUTPUT_DIR/$basename"
                platform_wheels=$((platform_wheels + 1))
                COLLECTED=$((COLLECTED + 1))
            fi
        done

        # An artifact directory exists only because its build uploaded one, so
        # an empty one means that build produced no wheel and the release would
        # be short a platform without saying so.
        if [ "$platform_wheels" -eq 0 ]; then
            echo "❌ No wheel in $wheel_dir — platform $platform built nothing"
            exit 1
        fi
    fi
done

echo ""
if [ "$COLLECTED" -eq 0 ]; then
    echo "❌ No wheels collected from $INPUT_DIR."
    echo "   PyPI publishing consumes this directory, so the release would ship"
    echo "   nothing installable."
    exit 1
fi

echo "✅ Collected $COLLECTED wheel(s) in $OUTPUT_DIR:"
ls -la "$OUTPUT_DIR/"
