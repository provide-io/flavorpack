package workenv

import (
	"os"
	"path/filepath"
	"testing"
)

// TestCreateWorkenvRootMkdirAllFailure covers the os.MkdirAll failure path at
// the main workenv directory level in CreateWorkenv (line 108): when the path
// itself cannot be created because a file already exists as a path component.
func TestCreateWorkenvRootMkdirAllFailure(t *testing.T) {
	base := t.TempDir()
	// Place a regular file at a path component so that MkdirAll for the target
	// path fails.
	blockPath := filepath.Join(base, "blocked")
	if err := os.WriteFile(blockPath, []byte("blocking"), 0o600); err != nil {
		t.Fatalf("WriteFile(blocking): %v", err)
	}
	// Create target path that would require traversing the file "blocked".
	targetPath := filepath.Join(blockPath, "workenv")

	err := CreateWorkenv(targetPath, nil)
	if err == nil {
		t.Fatal("expected error when MkdirAll fails due to path conflict")
	}
}
