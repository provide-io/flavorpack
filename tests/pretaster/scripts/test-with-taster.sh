#!/bin/bash
# Test script that uses actual taster.psp for testing

set -e

# Get workenv directory
WORKENV="${FLAVOR_WORKENV:-$(dirname "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")")}"

# Get the path to taster.psp (bundled in the package)
TASTER_PSP="${TASTER_PSP:-$WORKENV/bin/taster.psp}"

if [ ! -f "$TASTER_PSP" ]; then
    echo "❌ Error: taster.psp not found at $TASTER_PSP"
    echo "Workenv: $WORKENV"
    echo "Contents of $WORKENV/bin:"
    ls -la "$WORKENV/bin/" 2>/dev/null || echo "  Directory not found"
    exit 1
fi

# Make it executable if needed
chmod +x "$TASTER_PSP" 2>/dev/null || true

# Execute taster with the provided arguments
exec "$TASTER_PSP" "$@"