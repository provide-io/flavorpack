#!/bin/bash

set -e

PLATFORM=$1

FLAVOR_PSP=$(find flavor-psp -name "flavor-*-${PLATFORM}.psp" -o -name "flavor-*-${PLATFORM}.exe" | head -1)
if [ -z "$FLAVOR_PSP" ]; then
  echo "❌ Flavor PSP not found for platform: $PLATFORM"
  echo "Available files:"
  ls -la flavor-psp/
  exit 1
fi
FLAVOR_DIR=$(dirname "$FLAVOR_PSP")
chmod +x "$FLAVOR_PSP"
# Create a wrapper script named 'flavor' that calls the PSP
echo '#!/bin/bash' > "$FLAVOR_DIR/flavor"
echo "exec \"$PWD/$FLAVOR_PSP\" \"\$@\"" >> "$FLAVOR_DIR/flavor"
chmod +x "$FLAVOR_DIR/flavor"
# Add to PATH (works on both Linux and Windows)
echo "$PWD/$FLAVOR_DIR" >> $GITHUB_PATH
