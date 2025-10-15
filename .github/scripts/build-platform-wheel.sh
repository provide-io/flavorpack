#!/bin/bash
# Build platform-specific wheel with correct tags
# Usage: build-platform-wheel.sh <platform_tag>

set -euo pipefail

PLATFORM_TAG="${1}"

if [ -z "$PLATFORM_TAG" ]; then
    echo "❌ Error: Platform tag is required"
    echo "Usage: $0 <platform_tag>"
    exit 1
fi

echo "🎡 Building wheel for platform: $PLATFORM_TAG"

# Build the wheel
python -m build --wheel --outdir dist/

# Fix the platform tags
for wheel in dist/*.whl; do
    if [[ $(basename "$wheel") =~ py3-none-any ]]; then
        new_wheel=$(echo "$wheel" | sed "s/py3-none-any/py3-none-$PLATFORM_TAG/")
        mv "$wheel" "$new_wheel"
        echo "✅ Created: $(basename "$new_wheel")"
    else
        echo "✓ Wheel already has platform tags: $(basename "$wheel")"
    fi
done

# Display wheel info
echo ""
echo "📦 Built wheels:"
for wheel in dist/*.whl; do
    echo "  - $(basename "$wheel") ($(du -h "$wheel" | cut -f1))"
done