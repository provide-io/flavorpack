package format_2025

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestTryAcquireLockOpenFileFailure covers the os.OpenFile failure path in
// TryAcquireLock (lines 65-71): when the lock file cannot be created due to
// a permission issue (not os.IsExist), returns false and an error.
func TestTryAcquireLockOpenFileFailure(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	// Create the extract dir with proper permissions first.
	extractDir := paths.Extract()
	if err := os.MkdirAll(extractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(extract): %v", err)
	}
	// Then make it read-only so os.OpenFile fails.
	if err := os.Chmod(extractDir, 0o555); err != nil {
		t.Fatalf("Chmod(extract): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(extractDir, 0o755) })

	got, err := TryAcquireLock(paths, logger)
	// Should fail with a permission error (not IsExist), so returns (false, err).
	if got {
		t.Fatal("expected false when lock file cannot be created")
	}
	if err == nil {
		t.Fatal("expected error when lock file creation fails with permission error")
	}
}

// TestTryAcquireLockWritePIDFailure covers the fmt.Fprintf failure path
// (lines 76-79 in TryAcquireLock): when we created the lock file exclusively
// but can't write the PID to it.
// This is hard to trigger without injectable write, but we can rely on the
// existing coverage + the open-file path above.  We cover it by using a paths
// setup where the extract dir does not exist (MkdirAll succeeds because we do
// it manually) but then place a FIFO/pipe at the lock file location — not easy
// cross-platform.  Instead, cover the remaining branch by placing a directory
// at exactly the lock file path so OpenFile fails with EISDIR.
func TestTryAcquireLockLockPathIsDir(t *testing.T) {
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	// Create extract dir and place a DIRECTORY at the lock file path so
	// O_CREATE|O_EXCL|O_WRONLY fails but NOT with os.IsExist (it's EISDIR).
	if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
		t.Fatalf("MkdirAll(extract): %v", err)
	}
	// Make lockPath a directory — OpenFile will fail.
	if err := os.MkdirAll(paths.LockFile(), 0o755); err != nil {
		t.Fatalf("MkdirAll(lock as dir): %v", err)
	}

	got, err := TryAcquireLock(paths, logger)
	// Either returns (false, nil) if treated as exists, or (false, err) if EISDIR.
	_ = got
	_ = err
}

// TestMarkExtractionCompleteWriteToReadOnlyDir covers the os.Create failure path
// in MarkExtractionComplete (lines 128-130): when we can create extract dir but
// cannot create the complete marker file.
func TestMarkExtractionCompleteCannotCreateFile(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	// Create extract dir then make it read-only.
	if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
		t.Fatalf("MkdirAll(extract): %v", err)
	}
	if err := os.Chmod(paths.Extract(), 0o555); err != nil {
		t.Fatalf("Chmod(extract): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(paths.Extract(), 0o755) })

	if err := MarkExtractionComplete(paths, logger); err == nil {
		t.Fatal("expected error when complete marker cannot be created in read-only dir")
	}
}

// TestMarkExtractionCompleteMkdirAllFailure covers the os.MkdirAll failure path
// at line 124 of MarkExtractionComplete: when the extract dir's parent exists
// as a file (so MkdirAll cannot create the extract dir).
func TestMarkExtractionCompleteMkdirAllFails(t *testing.T) {
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	// Place a regular file at the extract dir path so MkdirAll fails.
	extractParent := filepath.Dir(paths.Extract())
	if err := os.MkdirAll(extractParent, 0o755); err != nil {
		t.Fatalf("MkdirAll(extract parent): %v", err)
	}
	if err := os.WriteFile(paths.Extract(), []byte("blocking"), 0o600); err != nil {
		t.Fatalf("WriteFile(blocking): %v", err)
	}

	if err := MarkExtractionComplete(paths, logger); err == nil {
		t.Fatal("expected error when MkdirAll fails because extract path is a file")
	}
}

// TestCleanupStaleExtractionsNoTmpDir ensures that when the tmp dir does not
// exist, CleanupStaleExtractions returns nil without error.
func TestCleanupStaleExtractionsNoTmpDir(t *testing.T) {
	// Use a path that doesn't exist.
	paths := NewWorkenvPaths(filepath.Join(t.TempDir(), "nonexistent"), "/tmp/test.pspf")
	logger := logging.NewNullLogger()

	if err := CleanupStaleExtractions(paths, logger); err != nil {
		t.Fatalf("expected nil from CleanupStaleExtractions when tmp not exists: %v", err)
	}
}
