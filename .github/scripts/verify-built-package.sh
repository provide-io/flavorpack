#!/bin/bash

set -e

TASTER_PATH=$1

echo "Verifying taster package by running it..."

# Make executable
chmod +x "$TASTER_PATH"

# Test that it can run without dd-based verification
"$TASTER_PATH" --version || exit 1
echo "✅ Taster package is executable and responds to commands"
