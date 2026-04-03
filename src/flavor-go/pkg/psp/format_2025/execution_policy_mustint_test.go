package format_2025

import (
	"testing"
)

// TestMustIntInt64OverflowViaInjectedMaxInt covers execution_policy.go:258-260
// (int64 value exceeds maxInt — overflow check for int64 case).
// On 64-bit systems maxInt == math.MaxInt64, so int64 overflow is impossible natively.
// We override maxIntVal to 100 so that int64(101) triggers the overflow path.
func TestMustIntInt64OverflowViaInjectedMaxInt(t *testing.T) {
	old := maxIntVal
	t.Cleanup(func() { maxIntVal = old })
	maxIntVal = 100

	_, err := mustInt("test_field", int64(101))
	if err == nil {
		t.Fatal("expected overflow error from mustInt with int64(101) when maxIntVal=100")
	}
}

// TestMustIntInt64NegativeOverflowViaInjectedMaxInt covers the negative int64 overflow path.
func TestMustIntInt64NegativeOverflowViaInjectedMaxInt(t *testing.T) {
	old := maxIntVal
	t.Cleanup(func() { maxIntVal = old })
	maxIntVal = 100

	// value < -int64(maxInt) - 1 → -100 - 1 = -101, so int64(-102) overflows
	_, err := mustInt("test_field", int64(-102))
	if err == nil {
		t.Fatal("expected overflow error from mustInt with int64(-102) when maxIntVal=100")
	}
}

// TestMustIntUintOverflowViaInjectedMaxInt covers the uint overflow path via injection.
func TestMustIntUintOverflowViaInjectedMaxInt(t *testing.T) {
	old := maxIntVal
	t.Cleanup(func() { maxIntVal = old })
	maxIntVal = 100

	_, err := mustInt("test_field", uint(101))
	if err == nil {
		t.Fatal("expected overflow error from mustInt with uint(101) when maxIntVal=100")
	}
}

// TestMustIntUint64OverflowViaInjectedMaxInt covers the uint64 overflow path via injection.
func TestMustIntUint64OverflowViaInjectedMaxInt(t *testing.T) {
	old := maxIntVal
	t.Cleanup(func() { maxIntVal = old })
	maxIntVal = 100

	_, err := mustInt("test_field", uint64(101))
	if err == nil {
		t.Fatal("expected overflow error from mustInt with uint64(101) when maxIntVal=100")
	}
}
