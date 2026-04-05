package format_2025

import (
	"math"
	"os"
	"path/filepath"
	"testing"
)

// TestRemovePathReturnsRealError covers the error return path in removePath
// when os.Remove fails with a non-NotExist error (e.g., permission denied).
func TestRemovePathReturnsRealError(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}
	t.Parallel()

	dir := t.TempDir()
	// Create a file inside a directory, then make the directory read-only
	// so that os.Remove on the file fails with permission denied.
	inner := filepath.Join(dir, "inner")
	if err := os.Mkdir(inner, 0o755); err != nil {
		t.Fatalf("Mkdir: %v", err)
	}
	target := filepath.Join(inner, "file.txt")
	if err := os.WriteFile(target, []byte("data"), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	// Make parent directory read-only to prevent removal.
	if err := os.Chmod(inner, 0o555); err != nil {
		t.Fatalf("Chmod: %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(inner, 0o755) })

	err := removePath(target)
	if err == nil {
		t.Fatal("expected permission error from removePath, got nil")
	}
}

// TestRemoveAllPathReturnsRealError covers the error return path in removeAllPath
// when os.RemoveAll fails with a non-NotExist error (e.g., permission denied).
func TestRemoveAllPathReturnsRealError(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}
	t.Parallel()

	dir := t.TempDir()
	// Create a nested directory structure that cannot be removed due to permissions.
	inner := filepath.Join(dir, "locked")
	nested := filepath.Join(inner, "nested")
	if err := os.MkdirAll(nested, 0o755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}
	if err := os.WriteFile(filepath.Join(nested, "file.txt"), []byte("data"), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	// Make nested dir non-writable so RemoveAll fails.
	if err := os.Chmod(nested, 0o555); err != nil {
		t.Fatalf("Chmod nested: %v", err)
	}
	if err := os.Chmod(inner, 0o555); err != nil {
		t.Fatalf("Chmod inner: %v", err)
	}
	t.Cleanup(func() {
		_ = os.Chmod(inner, 0o755)
		_ = os.Chmod(nested, 0o755)
	})

	err := removeAllPath(inner)
	if err == nil {
		t.Fatal("expected permission error from removeAllPath, got nil")
	}
}

// TestFloat64ToFileModeCheckedNaN covers the NaN branch in float64ToFileModeChecked.
func TestFloat64ToFileModeCheckedNaN(t *testing.T) {
	t.Parallel()

	_, err := float64ToFileModeChecked(math.NaN(), "mode")
	if err == nil {
		t.Fatal("expected error for NaN")
	}
}

// TestFloat64ToFileModeCheckedInf covers the Inf branch in float64ToFileModeChecked.
func TestFloat64ToFileModeCheckedInf(t *testing.T) {
	t.Parallel()

	_, err := float64ToFileModeChecked(math.Inf(1), "mode")
	if err == nil {
		t.Fatal("expected error for +Inf")
	}

	_, err = float64ToFileModeChecked(math.Inf(-1), "mode")
	if err == nil {
		t.Fatal("expected error for -Inf")
	}
}
