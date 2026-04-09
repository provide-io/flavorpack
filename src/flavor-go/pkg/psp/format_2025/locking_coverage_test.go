package format_2025

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestMarkExtractionIncompleteMkdirAllFails covers the MkdirAll error path
// in MarkExtractionIncomplete (line 154-156).
func TestMarkExtractionIncompleteMkdirAllFails(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	// Use a base path under a read-only parent so MkdirAll fails.
	dir := t.TempDir()
	readOnlyDir := filepath.Join(dir, "readonly")
	if err := os.Mkdir(readOnlyDir, 0o555); err != nil {
		t.Fatalf("Mkdir: %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(readOnlyDir, 0o755) })

	// Create paths whose Extract() resolves under the read-only dir.
	paths := NewWorkenvPaths(filepath.Join(readOnlyDir, "subdir"), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	// Should not panic; covers the warn branch for MkdirAll failure.
	MarkExtractionIncomplete(paths, logger)
}

// TestTryAcquireLockOpenFileFails covers the openLockFileFn error path
// in TryAcquireLock (line 69-76) for non-EEXIST errors.
func TestTryAcquireLockOpenFileFails(t *testing.T) {
	old := openLockFileFn
	t.Cleanup(func() { openLockFileFn = old })

	openLockFileFn = func(path string, flag int, perm os.FileMode) (*os.File, error) {
		return nil, errors.New("injected open error")
	}

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	acquired, err := TryAcquireLock(paths, logger)
	if err == nil {
		t.Fatal("expected error from TryAcquireLock when openLockFileFn fails")
	}
	if acquired {
		t.Fatal("expected acquired=false when openLockFileFn fails")
	}
}

// TestTryAcquireLockUnreadableLockFile covers the branch where an existing
// lock file cannot be read (line 61-63).
func TestTryAcquireLockUnreadableLockFile(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	// Create the extract dir and a lock file with no read permission.
	if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}
	lockPath := paths.LockFile()
	if err := os.WriteFile(lockPath, []byte("12345"), 0o000); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(lockPath, 0o644) })

	// The unreadable lock file should be removed and lock re-acquired.
	acquired, err := TryAcquireLock(paths, logger)
	if err != nil {
		t.Fatalf("TryAcquireLock() unexpected error: %v", err)
	}
	if !acquired {
		t.Fatal("expected lock to be acquired after removing unreadable lock file")
	}
	ReleaseLock(paths, logger)
}

// TestTryAcquireLockInvalidPIDContent covers the branch where the lock file
// contains non-numeric content (line 56-59).
func TestTryAcquireLockInvalidPIDContent(t *testing.T) {
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}
	if err := os.WriteFile(paths.LockFile(), []byte("not-a-pid"), 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	acquired, err := TryAcquireLock(paths, logger)
	if err != nil {
		t.Fatalf("TryAcquireLock() unexpected error: %v", err)
	}
	if !acquired {
		t.Fatal("expected lock to be acquired after removing invalid-PID lock file")
	}
	ReleaseLock(paths, logger)
}

// TestCleanupStaleExtractionsMissingTmpDir covers the early return in
// CleanupStaleExtractions when the tmp directory does not exist.
func TestCleanupStaleExtractionsMissingTmpDir(t *testing.T) {
	t.Parallel()

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	// tmp/ doesn't exist yet, should return nil.
	if err := CleanupStaleExtractions(paths, logger); err != nil {
		t.Fatalf("CleanupStaleExtractions() error = %v", err)
	}
}

// TestCleanupStaleExtractionsSkipsNonNumericDirs covers the branch where
// a directory name under tmp/ is not a valid PID (strconv.Atoi fails).
func TestCleanupStaleExtractionsSkipsNonNumericDirs(t *testing.T) {
	t.Parallel()

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	tmpDir := paths.Tmp()
	if err := os.MkdirAll(tmpDir, 0o755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}
	// Create a directory with a non-numeric name.
	if err := os.Mkdir(filepath.Join(tmpDir, "not-a-pid"), 0o755); err != nil {
		t.Fatalf("Mkdir: %v", err)
	}
	// Create a regular file (not a directory).
	if err := os.WriteFile(filepath.Join(tmpDir, "file.txt"), []byte("data"), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	if err := CleanupStaleExtractions(paths, logger); err != nil {
		t.Fatalf("CleanupStaleExtractions() error = %v", err)
	}
	// Verify non-numeric dir was not removed.
	if _, err := os.Stat(filepath.Join(tmpDir, "not-a-pid")); err != nil {
		t.Fatal("expected non-numeric directory to survive cleanup")
	}
}

// TestCleanupStaleExtractionsSkipsRunningProcess covers the branch where
// a directory name is a valid PID of a running process (should be skipped).
func TestCleanupStaleExtractionsSkipsRunningProcess(t *testing.T) {
	t.Parallel()

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	tmpDir := paths.Tmp()
	if err := os.MkdirAll(tmpDir, 0o755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}
	// Use our own PID as a running process.
	pidDir := filepath.Join(tmpDir, fmt.Sprintf("%d", os.Getpid()))
	if err := os.Mkdir(pidDir, 0o755); err != nil {
		t.Fatalf("Mkdir: %v", err)
	}

	if err := CleanupStaleExtractions(paths, logger); err != nil {
		t.Fatalf("CleanupStaleExtractions() error = %v", err)
	}
	// Our PID dir should still exist.
	if _, err := os.Stat(pidDir); err != nil {
		t.Fatal("expected running-process directory to survive cleanup")
	}
}
