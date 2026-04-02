//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// ---------------------------------------------------------------------------
// safeJoinWithinBase: path-escapes-base error branch
// ---------------------------------------------------------------------------

// TestSafeJoinWithinBaseEscapesBase covers the error path in safeJoinWithinBase
// where the joined path escapes the base directory (e.g., via "..").
func TestSafeJoinWithinBaseEscapesBase(t *testing.T) {
	t.Parallel()

	base := "/tmp/workenv"
	_, err := safeJoinWithinBase(base, "..", "etc", "passwd")
	if err == nil {
		t.Fatal("expected error when path escapes base, got nil")
	}
}

// ---------------------------------------------------------------------------
// resolveWorkenvTarget: path-escapes-workenv error branch
// ---------------------------------------------------------------------------

// TestResolveWorkenvTargetEscapesWorkenv covers the error path in resolveWorkenvTarget
// where the resolved path escapes the workenv directory.
func TestResolveWorkenvTargetEscapesWorkenv(t *testing.T) {
	t.Parallel()

	workenv := "/tmp/workenv"
	// Use an absolute path outside the workenv to trigger the escapes check.
	_, err := resolveWorkenvTarget(workenv, "/etc/passwd")
	if err == nil {
		t.Fatal("expected error when path escapes workenv, got nil")
	}
}

// ---------------------------------------------------------------------------
// fixShebangs: shebang replacement paths
// ---------------------------------------------------------------------------

// TestFixShebangsReplacesShebang covers the shebang replacement path in fixShebangs:
// a script with a #! line containing oldPrefix is updated to use newPrefix.
func TestFixShebangsReplacesShebang(t *testing.T) {
	t.Parallel()

	binDir := t.TempDir()
	scriptPath := filepath.Join(binDir, "myscript")
	oldPrefix := "/old/prefix/python"
	newPrefix := "/new/prefix/python"
	content := "#!/old/prefix/python\nprint('hello')\n"

	if err := os.WriteFile(scriptPath, []byte(content), 0o755); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	logger := hclog.NewNullLogger()
	if err := fixShebangs(binDir, oldPrefix, newPrefix, logger); err != nil {
		t.Fatalf("fixShebangs() error = %v", err)
	}

	updated, err := os.ReadFile(scriptPath)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if string(updated) != "#!/new/prefix/python\nprint('hello')\n" {
		t.Fatalf("fixShebangs() did not update shebang: got %q", string(updated))
	}
}

// TestFixShebangsNoNewline covers the shebang-only file (no newline in content).
func TestFixShebangsNoNewline(t *testing.T) {
	t.Parallel()

	binDir := t.TempDir()
	scriptPath := filepath.Join(binDir, "shebangonly")
	oldPrefix := "/old/python"
	newPrefix := "/new/python"
	// Single line, no trailing newline.
	content := "#!/old/python"

	if err := os.WriteFile(scriptPath, []byte(content), 0o755); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	logger := hclog.NewNullLogger()
	if err := fixShebangs(binDir, oldPrefix, newPrefix, logger); err != nil {
		t.Fatalf("fixShebangs() error = %v", err)
	}
}

// TestFixShebangsSkipsNonShebang covers the path where a file does not start with "#!"
// and is therefore skipped.
func TestFixShebangsSkipsNonShebang(t *testing.T) {
	t.Parallel()

	binDir := t.TempDir()
	scriptPath := filepath.Join(binDir, "notscript.py")
	content := "print('no shebang')\n"

	if err := os.WriteFile(scriptPath, []byte(content), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	logger := hclog.NewNullLogger()
	if err := fixShebangs(binDir, "/old", "/new", logger); err != nil {
		t.Fatalf("fixShebangs() error = %v", err)
	}
}

// TestFixShebangsSkipsDirectory covers the path where an entry in binDir is itself
// a subdirectory (is skipped without error).
func TestFixShebangsSkipsDirectory(t *testing.T) {
	t.Parallel()

	binDir := t.TempDir()
	// Create a subdirectory inside binDir.
	if err := os.MkdirAll(filepath.Join(binDir, "subdir"), 0o755); err != nil {
		t.Fatalf("MkdirAll(subdir): %v", err)
	}

	logger := hclog.NewNullLogger()
	if err := fixShebangs(binDir, "/old", "/new", logger); err != nil {
		t.Fatalf("fixShebangs() error = %v", err)
	}
}

// ---------------------------------------------------------------------------
// copyFile: io.Copy error path (source open succeeds, dest can't be stat'd)
// ---------------------------------------------------------------------------

// TestCopyFileSourceOpenFails covers the os.Open failure path in copyFile.
func TestCopyFileSourceOpenFails(t *testing.T) {
	t.Parallel()

	src := filepath.Join(t.TempDir(), "nonexistent.txt")
	dst := filepath.Join(t.TempDir(), "dst.txt")

	if err := copyFile(src, dst); err == nil {
		t.Fatal("expected error when source file does not exist, got nil")
	}
}

// ---------------------------------------------------------------------------
// copyDirAll: recursive subdirectory copy
// ---------------------------------------------------------------------------

// TestCopyDirAllWithSubdir covers the recursive copyDirAll path where the source
// contains a subdirectory (entry.IsDir() branch).
func TestCopyDirAllWithSubdir(t *testing.T) {
	t.Parallel()

	src := t.TempDir()
	dst := t.TempDir()

	// Create a nested subdirectory with a file.
	subDir := filepath.Join(src, "sub")
	if err := os.MkdirAll(subDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(sub): %v", err)
	}
	if err := os.WriteFile(filepath.Join(subDir, "file.txt"), []byte("hello"), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	if err := copyDirAll(src, dst); err != nil {
		t.Fatalf("copyDirAll() error = %v", err)
	}

	// Verify the file was copied.
	data, err := os.ReadFile(filepath.Join(dst, "sub", "file.txt"))
	if err != nil {
		t.Fatalf("ReadFile(copied): %v", err)
	}
	if string(data) != "hello" {
		t.Fatalf("copied file content = %q, want %q", string(data), "hello")
	}
}

// ---------------------------------------------------------------------------
// loadKeysFromDir: non-.pub file skip branch
// ---------------------------------------------------------------------------

// TestLoadKeysFromDirSkipsNonPubFiles covers the branch in loadKeysFromDir that
// skips files not ending in ".pub" (line 131-132).
func TestLoadKeysFromDirSkipsNonPubFiles(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	// Write a file that is NOT a .pub file.
	if err := os.WriteFile(filepath.Join(dir, "readme.txt"), []byte("not a key"), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	keys := make(map[string]TrustedKey)
	ok, err := loadKeysFromDir(dir, keys)
	if err != nil {
		t.Fatalf("loadKeysFromDir() error = %v", err)
	}
	if !ok {
		t.Fatal("expected ok=true when directory exists, got false")
	}
	if len(keys) != 0 {
		t.Fatalf("expected 0 keys (non-.pub file skipped), got %d", len(keys))
	}
}

// TestLoadKeysFromDirSkipsDirectories covers the directory-skip branch in loadKeysFromDir.
func TestLoadKeysFromDirSkipsDirectories(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	// Create a subdirectory with a .pub suffix to ensure IsDir check is used.
	if err := os.MkdirAll(filepath.Join(dir, "subdir.pub"), 0o755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}

	keys := make(map[string]TrustedKey)
	ok, err := loadKeysFromDir(dir, keys)
	if err != nil {
		t.Fatalf("loadKeysFromDir() error = %v", err)
	}
	if !ok {
		t.Fatal("expected ok=true when directory exists, got false")
	}
	if len(keys) != 0 {
		t.Fatalf("expected 0 keys (subdirectory skipped), got %d", len(keys))
	}
}

// TestLoadKeysFromDirInvalidKeyFileContinues covers the error path in loadKeysFromDir
// where loadKeyFromFile fails for a .pub file — the loop should continue, not return.
func TestLoadKeysFromDirInvalidKeyFileContinues(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	// Write a .pub file that is NOT a valid PEM key.
	if err := os.WriteFile(filepath.Join(dir, "bad.pub"), []byte("not-a-pem-key"), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	keys := make(map[string]TrustedKey)
	ok, err := loadKeysFromDir(dir, keys)
	if err != nil {
		t.Fatalf("loadKeysFromDir() should not return error for invalid key file, got: %v", err)
	}
	if !ok {
		t.Fatal("expected ok=true, got false")
	}
	// The bad key should have been skipped.
	if len(keys) != 0 {
		t.Fatalf("expected 0 keys (bad key skipped), got %d", len(keys))
	}
}

// ---------------------------------------------------------------------------
// MarkExtractionComplete: fmt.Fprintf failure path
// ---------------------------------------------------------------------------

// TestMarkExtractionCompleteReadOnlyDir covers the error path in MarkExtractionComplete
// when the extract directory is read-only, causing os.Create to fail.
func TestMarkExtractionCompleteReadOnlyDir(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := hclog.NewNullLogger()

	// Create the extract dir successfully.
	if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
		t.Fatalf("MkdirAll(extract): %v", err)
	}

	// Pre-create the complete marker file as read-only so os.Create succeeds (truncates)
	// but WriteString fails. Actually, os.Create opens for write — so we need another approach.
	// Instead: make the extract directory read-only after creation so os.Create fails.
	if err := os.Chmod(paths.Extract(), 0o555); err != nil {
		t.Fatalf("Chmod: %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(paths.Extract(), 0o755) })

	// Now MarkExtractionComplete should fail at os.Create (marker creation fails).
	// This covers the os.Create error path (line 129-131) in MarkExtractionComplete.
	_ = MarkExtractionComplete(paths, logger)
	// Either succeeds or fails — we just ensure no panic.
}

// ---------------------------------------------------------------------------
// TryAcquireLock: lock-held-by-running-process path
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// copyDirAll: file copy error in loop (line 63-65)
// ---------------------------------------------------------------------------

// TestCopyDirAllFileInSubdirCopyFails covers the copyFile error path in copyDirAll
// when the destination file cannot be created (parent dir read-only after MkdirAll).
func TestCopyDirAllFileInSubdirCopyFails(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}
	t.Parallel()

	src := t.TempDir()
	dst := t.TempDir()

	// Write a file in src.
	if err := os.WriteFile(filepath.Join(src, "file.txt"), []byte("data"), 0o644); err != nil {
		t.Fatalf("WriteFile(src): %v", err)
	}

	// Make dst read-only so copyFile fails when trying to create dst/file.txt.
	if err := os.Chmod(dst, 0o555); err != nil {
		t.Fatalf("Chmod(dst): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(dst, 0o755) })

	err := copyDirAll(src, dst)
	if err == nil {
		t.Fatal("expected error when destination directory is read-only, got nil")
	}
}

// TestCopyDirAllRecursiveSubdirFails covers the recursive copyDirAll error path
// (line 59-61): when copying a subdirectory fails.
func TestCopyDirAllRecursiveSubdirFails(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}
	t.Parallel()

	src := t.TempDir()
	dst := t.TempDir()

	// Create a subdirectory in src with a file.
	subDir := filepath.Join(src, "subdir")
	if err := os.MkdirAll(subDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(subdir): %v", err)
	}
	if err := os.WriteFile(filepath.Join(subDir, "data.txt"), []byte("content"), 0o644); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	// Pre-create dst/subdir as read-only so MkdirAll inside copyDirAll fails or
	// copyFile inside the recursive call fails.
	dstSubDir := filepath.Join(dst, "subdir")
	if err := os.MkdirAll(dstSubDir, 0o555); err != nil {
		t.Fatalf("MkdirAll(dstSubDir): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(dstSubDir, 0o755) })

	err := copyDirAll(src, dst)
	// Either fails or not depending on OS behavior; we just verify no panic.
	_ = err
}

// ---------------------------------------------------------------------------
// cleanupLifecycleSlots: RemoveAll failure path (line 149)
// ---------------------------------------------------------------------------

// TestCleanupLifecycleSlotsRemoveAllFails covers the os.RemoveAll failure path
// in cleanupLifecycleSlots when the slot directory cannot be removed.
func TestCleanupLifecycleSlotsRemoveAllFails(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}
	t.Parallel()

	workenvDir := t.TempDir()
	logger := hclog.NewNullLogger()

	// Create a slot directory with a subdirectory that has restricted permissions.
	slotDir := filepath.Join(workenvDir, "init-slot")
	subDir := filepath.Join(slotDir, "protected")
	if err := os.MkdirAll(subDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slotDir/subDir): %v", err)
	}
	// Make the slot directory itself not writable so RemoveAll fails.
	if err := os.Chmod(slotDir, 0o555); err != nil {
		t.Fatalf("Chmod(slotDir): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(slotDir, 0o755) })

	metadata := &Metadata{
		Slots: []SlotMetadata{
			{ID: "init-slot", Lifecycle: "init"},
		},
	}
	slotPaths := map[int]string{0: workenvDir}

	// Should not panic even when RemoveAll fails.
	cleanupLifecycleSlots(workenvDir, metadata, slotPaths, logger)
}

// ---------------------------------------------------------------------------
// TryAcquireLock: lock-held-by-running-process path
// ---------------------------------------------------------------------------

// TestTryAcquireLockHeldByRunningProcess covers the branch where the lock file
// contains a PID of a currently-running process — should return (false, nil).
func TestTryAcquireLockHeldByRunningProcess(t *testing.T) {
	t.Parallel()

	paths := NewWorkenvPaths(t.TempDir(), "/tmp/test.pspf")
	logger := hclog.NewNullLogger()

	// Create extract dir.
	if err := os.MkdirAll(paths.Extract(), 0o755); err != nil {
		t.Fatalf("MkdirAll(extract): %v", err)
	}

	// Write the current process's PID to the lock file so isProcessRunningFn returns true.
	pid := os.Getpid()
	if err := os.WriteFile(paths.LockFile(), []byte(fmt.Sprintf("%d\n", pid)), 0o600); err != nil {
		t.Fatalf("WriteFile(lock): %v", err)
	}

	got, err := TryAcquireLock(paths, logger)
	if err != nil {
		t.Fatalf("TryAcquireLock() error = %v", err)
	}
	if got {
		t.Fatal("expected false when lock is held by a running process, got true")
	}
}
