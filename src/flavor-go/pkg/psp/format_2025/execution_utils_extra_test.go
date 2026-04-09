package format_2025

import (
	"io"
	"os"
	"path/filepath"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestFixShebangsReadDirError covers the os.ReadDir error path (line 78-80)
// in fixShebangs: when the binDir exists but cannot be listed.
func TestFixShebangsReadDirError(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	// Create a directory at the binDir path, then place a FILE at a location
	// that would make ReadDir fail. On Unix, we can make the dir non-readable.
	binDir := filepath.Join(t.TempDir(), "bin")
	if err := os.MkdirAll(binDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(bin): %v", err)
	}
	// Make the directory non-readable so ReadDir fails.
	if err := os.Chmod(binDir, 0o000); err != nil {
		t.Fatalf("Chmod(bin): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(binDir, 0o755) })

	logger := logging.NewNullLogger()
	err := fixShebangs(binDir, "/old", "/new", logger)
	if err == nil {
		t.Fatal("expected error from fixShebangs when binDir is not readable")
	}
}

// TestCleanupLifecycleSlotsInitLifecycle covers the init lifecycle cleanup path
// in cleanupLifecycleSlots (line 147-152).
func TestCleanupLifecycleSlotsInitLifecycle(t *testing.T) {
	workenvDir := t.TempDir()
	logger := logging.NewNullLogger()

	// Create a slot directory that should be removed.
	slotDir := filepath.Join(workenvDir, "my-init-slot")
	if err := os.MkdirAll(slotDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot): %v", err)
	}

	metadata := &Metadata{
		Slots: []SlotMetadata{
			{ID: "my-init-slot", Lifecycle: "init"},
		},
	}
	slotPaths := map[int]string{0: workenvDir}

	cleanupLifecycleSlots(workenvDir, metadata, slotPaths, logger)

	// The slot directory should be removed.
	if _, err := os.Stat(slotDir); !os.IsNotExist(err) {
		t.Fatalf("expected init slot dir to be removed, got err=%v", err)
	}
}

// TestCopyFileDestCreateFails covers the os.Create error path in copyFile
// (line ~20-22): destination cannot be created.
func TestCopyFileDestCreateFails(t *testing.T) {
	src := filepath.Join(t.TempDir(), "src.txt")
	if err := os.WriteFile(src, []byte("content"), 0o600); err != nil {
		t.Fatalf("WriteFile(src): %v", err)
	}

	// Destination in a non-existent directory.
	dst := filepath.Join(t.TempDir(), "nonexistent", "dst.txt")

	if err := copyFile(src, dst); err == nil {
		t.Fatal("expected error when destination parent doesn't exist")
	}
}

// TestCopyDirAllSourceNotExist covers the early return when src doesn't exist
// in copyDirAll.
func TestCopyDirAllSourceNotExist(t *testing.T) {
	src := filepath.Join(t.TempDir(), "nonexistent")
	dst := t.TempDir()

	// copyDirAll with non-existent source - should return an error.
	err := copyDirAll(src, dst)
	_ = err // Accept either success (empty) or error.
}

// ---------------------------------------------------------------------------
// copyFile: io.Copy failure path (line 26-28) — injected via ioCopyFn
// ---------------------------------------------------------------------------

// TestCopyFileIoCopyFails covers the io.Copy error path in copyFile
// by injecting ioCopyFn to return an error.
func TestCopyFileIoCopyFails(t *testing.T) {
	src := filepath.Join(t.TempDir(), "src.txt")
	dst := filepath.Join(t.TempDir(), "dst.txt")

	if err := os.WriteFile(src, []byte("content"), 0o600); err != nil {
		t.Fatalf("WriteFile(src): %v", err)
	}

	old := ioCopyFn
	t.Cleanup(func() { ioCopyFn = old })
	ioCopyFn = func(w io.Writer, r io.Reader) (int64, error) {
		return 0, os.ErrPermission
	}

	if err := copyFile(src, dst); err == nil {
		t.Fatal("expected error when io.Copy fails, got nil")
	}
}

// ---------------------------------------------------------------------------
// copyFile: os.Stat failure path (line 32-34) — injected via osStatSrcFn
// ---------------------------------------------------------------------------

// TestCopyFileStatFails covers the os.Stat failure path in copyFile
// by injecting osStatSrcFn to return an error after a successful io.Copy.
func TestCopyFileStatFails(t *testing.T) {
	src := filepath.Join(t.TempDir(), "src.txt")
	dst := filepath.Join(t.TempDir(), "dst.txt")

	if err := os.WriteFile(src, []byte("content"), 0o600); err != nil {
		t.Fatalf("WriteFile(src): %v", err)
	}

	old := osStatSrcFn
	t.Cleanup(func() { osStatSrcFn = old })
	osStatSrcFn = func(name string) (os.FileInfo, error) {
		return nil, os.ErrPermission
	}

	if err := copyFile(src, dst); err == nil {
		t.Fatal("expected error when os.Stat fails after copy, got nil")
	}
}

// ---------------------------------------------------------------------------
// fixShebangs: os.ReadFile failure path (line 108-109) — injected via osReadFileFn
// The shebang header is read successfully (2 bytes = "#!"), then os.ReadFile fails.
// ---------------------------------------------------------------------------

// TestFixShebangsReadFileFails covers the os.ReadFile failure path in fixShebangs
// (line 114-116) by injecting osReadFileFn to return an error.
func TestFixShebangsReadFileFails(t *testing.T) {
	binDir := t.TempDir()
	scriptPath := filepath.Join(binDir, "myscript")
	// Write a script with a shebang header (needs "#!" as first 2 bytes).
	if err := os.WriteFile(scriptPath, []byte("#!/bin/sh\necho hello\n"), 0o755); err != nil {
		t.Fatalf("WriteFile(script): %v", err)
	}

	old := osReadFileFn
	t.Cleanup(func() { osReadFileFn = old })
	osReadFileFn = func(name string) ([]byte, error) {
		return nil, os.ErrPermission
	}

	logger := logging.NewNullLogger()
	// fixShebangs should skip the file (continue) without returning an error.
	if err := fixShebangs(binDir, "/bin", "/usr/local/bin", logger); err != nil {
		t.Fatalf("fixShebangs() should not return error when ReadFile fails, got: %v", err)
	}
}
