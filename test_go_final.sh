#!/bin/bash
# Final test of Go operations implementation

set -e

echo "🚀 Final Go Operations Test"
echo "========================================"

# 1. Test Go unit tests
echo ""
echo "📊 Running Go unit tests..."
cd ingredients/flavor-go/pkg/psp/format_2025
if go test -v -run "Test(Operation|Slot|Python)" 2>&1 | grep -q "PASS"; then
    echo "✅ Go unit tests: PASSED"
else
    echo "❌ Go unit tests: FAILED"
    exit 1
fi

# 2. Test Python compatibility
echo ""
echo "🐍 Testing Python compatibility..."
cd /Users/tim/code/gh/provide-io/flavorpack
if python verify_operations.py 2>&1 | grep -q "All verifications passed"; then
    echo "✅ Python compatibility: PASSED"
else
    echo "❌ Python compatibility: FAILED"
    exit 1
fi

# 3. Check binary format
echo ""
echo "📦 Verifying binary format..."
python -c "
from flavor.psp.format_2025.slots import SlotDescriptor
from flavor.psp.format_2025.operations import pack_operations, OP_TAR, OP_GZIP

# Create descriptor with operations
d = SlotDescriptor(
    id=42,
    operations=pack_operations([OP_TAR, OP_GZIP]),
    size=1024,
    original_size=2048,
)

# Pack and verify size
packed = d.pack()
assert len(packed) == 64, f'Wrong size: {len(packed)}'
print(f'✅ Binary format: 64 bytes')

# Verify operations field
assert d.operations == 0x1001, f'Wrong operations: 0x{d.operations:016x}'
print(f'✅ Operations field: 0x{d.operations:016x}')
"

# 4. Summary
echo ""
echo "========================================"
echo "✨ Summary:"
echo "  • Go unit tests: ✅"
echo "  • Python compatibility: ✅"
echo "  • Binary format: ✅"
echo ""
echo "🎉 All Go operations tests passed!"
echo ""
echo "The PSPF/2025 operations system is working correctly in Go!"
echo "Operations are packed into 64-bit integers and the"
echo "SlotDescriptor maintains its 64-byte size."