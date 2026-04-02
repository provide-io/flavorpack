package workenv

import (
	"testing"
)

// TestIsValidReturnsFalseForMissingMarker covers the os.ReadFile failure path
// in IsValid (validation.go:25-27) when the marker file doesn't exist at all.
func TestIsValidReturnsFalseForMissingMarker(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	// No marker written at all — ReadFile should fail and IsValid returns false.
	if IsValid(dir, "flavorpack", "1.0.0", "abc123") {
		t.Fatal("expected IsValid to return false when marker file is absent")
	}
}
