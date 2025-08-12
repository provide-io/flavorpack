#!/bin/bash
set -e

echo "=== Testing Reproducible Builds ==="
echo

# Create a simple test manifest
cat > test-reproducible.json << EOF
{
  "name": "test-reproducible",
  "version": "1.0.0",
  "description": "Test reproducible builds",
  "launcher": "go",
  "command": "echo 'Hello, reproducible!'",
  "slots": [],
  "environment": {}
}
EOF

echo "1. Building with Go builder (reproducible mode)..."
./pspf-builder -m test-reproducible.json -o test1.pspf --reproducible
sha256sum test1.pspf | cut -d' ' -f1 > hash1.txt

echo "2. Building again with Go builder (reproducible mode)..."
./pspf-builder -m test-reproducible.json -o test2.pspf --reproducible
sha256sum test2.pspf | cut -d' ' -f1 > hash2.txt

echo "3. Comparing hashes..."
HASH1=$(cat hash1.txt)
HASH2=$(cat hash2.txt)
if [ "$HASH1" = "$HASH2" ]; then
    echo "✓ Go builder: Reproducible builds work! (hashes match: $HASH1)"
else
    echo "✗ Go builder: Hashes don't match"
    echo "  Hash 1: $HASH1"
    echo "  Hash 2: $HASH2"
fi

echo
echo "4. Building with Rust builder (reproducible mode)..."
./src/flavor/rust/pspf-builder-rs/target/release/pspf-builder-rs -m test-reproducible.json -o test3.pspf --reproducible
sha256sum test3.pspf | cut -d' ' -f1 > hash3.txt

echo "5. Building again with Rust builder (reproducible mode)..."
./src/flavor/rust/pspf-builder-rs/target/release/pspf-builder-rs -m test-reproducible.json -o test4.pspf --reproducible
sha256sum test4.pspf | cut -d' ' -f1 > hash4.txt

echo "6. Comparing hashes..."
HASH3=$(cat hash3.txt)
HASH4=$(cat hash4.txt)
if [ "$HASH3" = "$HASH4" ]; then
    echo "✓ Rust builder: Reproducible builds work! (hashes match: $HASH3)"
else
    echo "✗ Rust builder: Hashes don't match"
    echo "  Hash 3: $HASH3"
    echo "  Hash 4: $HASH4"
fi

echo
echo "7. Testing non-reproducible builds..."
./pspf-builder -m test-reproducible.json -o test5.pspf
./pspf-builder -m test-reproducible.json -o test6.pspf
sha256sum test5.pspf > hash5.txt
sha256sum test6.pspf > hash6.txt

if diff hash5.txt hash6.txt > /dev/null; then
    echo "✗ Non-reproducible builds produced identical output (unexpected)"
else
    echo "✓ Non-reproducible builds produce different outputs (as expected)"
fi

echo
echo "8. Checking emoji magic..."
echo "Reproducible build emoji:"
xxd -s -16 -l 16 test1.pspf | tail -1
echo "Non-reproducible build emoji:"
xxd -s -16 -l 16 test5.pspf | tail -1

# Cleanup
rm -f test*.pspf hash*.txt test-reproducible.json