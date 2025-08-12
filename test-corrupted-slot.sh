#!/bin/bash
set -e

echo "=== Testing Corrupted Slot Data Detection ==="
echo

# Create test data
echo "This is valid test data for the slot" > test-data.txt

# Create manifest
cat > test-corrupt.json << EOF
{
  "name": "test-corrupt",
  "version": "1.0.0",
  "description": "Test corrupted slot detection",
  "launcher": "go",
  "command": "cat {slot:0}",
  "slots": [
    {
      "path": "test-data.txt",
      "name": "data.txt",
      "compression": "none",
      "purpose": "data",
      "lifecycle": "persistent"
    }
  ],
  "environment": {}
}
EOF

echo "1. Building valid bundle..."
./pspf-builder -m test-corrupt.json -o test-corrupt.pspf
chmod +x test-corrupt.pspf

echo "2. Verifying valid bundle..."
if FLAVOR_LAUNCHER_CLI=true ./test-corrupt.pspf verify > /dev/null 2>&1; then
    echo "✓ Valid bundle verification passed"
else
    echo "✗ Valid bundle verification failed unexpectedly"
fi

echo "3. Getting bundle info..."
FLAVOR_LAUNCHER_CLI=true ./test-corrupt.pspf info | grep "Size:" | awk '{print $NF}'
BUNDLE_SIZE=$(stat -f%z test-corrupt.pspf 2>/dev/null || stat -c%s test-corrupt.pspf)

echo "4. Corrupting slot data..."
# The slot data is typically after launcher (3.7MB) + index (256) + some alignment
# Let's corrupt somewhere in the middle of the bundle where slot data likely is
CORRUPTION_OFFSET=$((3770000 + 256 + 100))
echo "   Corrupting data at offset $CORRUPTION_OFFSET"
printf '\x00\x00\xDE\xAD\xBE\xEF\x00\x00' | dd of=test-corrupt.pspf bs=1 seek=$CORRUPTION_OFFSET conv=notrunc 2>/dev/null

echo "5. Verifying corrupted bundle..."
if FLAVOR_LAUNCHER_CLI=true ./test-corrupt.pspf verify > /dev/null 2>&1; then
    echo "✗ Corrupted bundle verification passed (should have failed)"
else
    echo "✓ Corrupted bundle verification failed as expected"
fi

echo "6. Trying to extract corrupted slot..."
if FLAVOR_LAUNCHER_CLI=true ./test-corrupt.pspf extract 0 /tmp/corrupt-extract > /dev/null 2>&1; then
    echo "✗ Extraction succeeded (should have failed with checksum error)"
else
    echo "✓ Extraction failed as expected"
fi

echo "7. Running corrupted bundle..."
if ./test-corrupt.pspf 2>&1 | grep -q "checksum"; then
    echo "✓ Execution detected checksum error"
else
    echo "Note: Execution may not detect corruption if it doesn't verify checksums"
fi

# Cleanup
rm -f test-data.txt test-corrupt.json test-corrupt.pspf