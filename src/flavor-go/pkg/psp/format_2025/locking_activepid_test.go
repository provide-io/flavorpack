package format_2025

import (
	"os"
	"strconv"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestTryAcquireLockHeldByActiveProcess covers locking.go:71-74
// (lock held by active process: isProcessRunningFn returns true).
func TestTryAcquireLockHeldByActiveProcess(t *testing.T) {
	cacheRoot := t.TempDir()
	paths := NewWorkenvPaths(cacheRoot, "/fake/bundle.pspf")

	// Create extract directory and write a lock file with a known PID
	extractDir := paths.Extract()
	if err := os.MkdirAll(extractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll() error = %v", err)
	}

	fakePID := 99999
	lockPath := paths.LockFile()
	if err := os.WriteFile(lockPath, []byte(strconv.Itoa(fakePID)+"\n"), 0o600); err != nil {
		t.Fatalf("WriteFile(lock) error = %v", err)
	}

	// Override isProcessRunningFn to claim the fake PID is still running
	old := isProcessRunningFn
	t.Cleanup(func() { isProcessRunningFn = old })
	isProcessRunningFn = func(pid int) bool { return pid == fakePID }

	logger := hclog.NewNullLogger()
	acquired, err := TryAcquireLock(paths, logger)
	if err != nil {
		t.Fatalf("TryAcquireLock() error = %v", err)
	}
	if acquired {
		t.Fatal("expected lock acquisition to fail (lock held by active process)")
	}

	// Lock file should still exist (not removed by TryAcquireLock)
	if _, err := os.Stat(lockPath); err != nil {
		t.Fatalf("expected lock file to still exist: %v", err)
	}
}
