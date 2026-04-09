package format_2025

import (
	"errors"
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestTryAcquireLockIsExistError covers locking.go:71-74
// (openLockFileFn returns os.ErrExist → return false, nil).
// This simulates the TOCTOU race where the lock file didn't exist at Stat time
// but was created before OpenFile with O_EXCL.
func TestTryAcquireLockIsExistError(t *testing.T) {
	cacheRoot := t.TempDir()
	paths := NewWorkenvPaths(cacheRoot, "/fake/bundle.pspf")

	// Create extract directory
	if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
		t.Fatalf("MkdirAll() error = %v", err)
	}

	// Override openLockFileFn to return an os.ErrExist-wrapped error
	old := openLockFileFn
	t.Cleanup(func() { openLockFileFn = old })
	openLockFileFn = func(_ string, _ int, _ os.FileMode) (*os.File, error) {
		return nil, &os.PathError{Op: "open", Path: paths.LockFile(), Err: errors.New("file exists")}
	}

	// We also need os.IsExist to return true for the injected error.
	// Use the actual os package error type that IsExist recognizes.
	openLockFileFn = func(_ string, _ int, _ os.FileMode) (*os.File, error) {
		// Create the file for real first so os.IsExist recognizes it
		f, err := os.OpenFile(paths.LockFile(), os.O_CREATE|os.O_EXCL|os.O_WRONLY, FilePerms)
		if err == nil {
			_ = f.Close()
		}
		// Now try again to get the EEXIST error
		_, err = os.OpenFile(paths.LockFile(), os.O_CREATE|os.O_EXCL|os.O_WRONLY, FilePerms)
		return nil, err // returns ErrExist since file now exists
	}

	logger := logging.NewNullLogger()
	acquired, err := TryAcquireLock(paths, logger)
	if err != nil {
		t.Fatalf("TryAcquireLock() unexpected error = %v", err)
	}
	if acquired {
		t.Fatal("expected lock acquisition to fail (IsExist path)")
	}
}
