//go:build !windows

package format_2025

import (
	"os"
	"runtime"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestTryAcquireLockPermissionDenied covers locking.go:71 (return false, err)
// when os.OpenFile returns a non-IsExist error (EACCES / permission denied).
// We make the Extract() directory non-writable so OpenFile with O_CREATE fails.
func TestTryAcquireLockPermissionDenied(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := hclog.NewNullLogger()

	// Create the Extract() directory so MkdirAll inside TryAcquireLock succeeds.
	extractDir := paths.Extract()
	if err := os.MkdirAll(extractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(extract): %v", err)
	}

	// Make Extract() non-writable so OpenFile(lockPath, O_CREATE|O_EXCL|O_WRONLY) fails
	// with EACCES (not EEXIST), which is the non-IsExist error path at line 71.
	if err := os.Chmod(extractDir, 0o555); err != nil {
		t.Fatalf("Chmod(extract): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(extractDir, 0o755) })

	acquired, err := TryAcquireLock(paths, logger)
	if err == nil {
		t.Fatal("expected non-nil error when OpenFile fails with permission denied, got nil")
	}
	if acquired {
		t.Fatal("expected acquired=false when OpenFile fails with permission denied")
	}
}
