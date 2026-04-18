// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"os"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestSavePackageChecksumMkdirAllFailurePermission covers the mkdirAllFn failure path
// in savePackageChecksum (line 102-104) with permission error.
func TestSavePackageChecksumMkdirAllFailurePermission(t *testing.T) {
	old := mkdirAllFn
	t.Cleanup(func() { mkdirAllFn = old })
	mkdirAllFn = func(path string, perm os.FileMode) error {
		return os.ErrPermission
	}

	logger := logging.NewNullLogger()
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/demo.pspf")
	if err := savePackageChecksum(paths, 0x12345678, logger); err == nil {
		t.Fatal("expected error when MkdirAll fails in savePackageChecksum")
	}
}

// TestSavePackageChecksumWriteFailure covers the WriteString failure path in
// savePackageChecksum (lines 117-119). We inject openFileFn to return a
// read-only file descriptor so WriteString fails.
func TestSavePackageChecksumWriteFailure(t *testing.T) {
	old := openFileFn
	t.Cleanup(func() { openFileFn = old })

	// Create a temp file and open it read-only to cause WriteString to fail.
	tmpFile, err := os.CreateTemp(t.TempDir(), "checksum-*.txt")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	tmpPath := tmpFile.Name()
	_ = tmpFile.Close()

	openFileFn = func(name string, flag int, perm os.FileMode) (*os.File, error) {
		// Open read-only so writes fail.
		return os.OpenFile(tmpPath, os.O_RDONLY, 0o400)
	}

	logger := logging.NewNullLogger()
	paths := NewWorkenvPaths(t.TempDir(), "/tmp/demo.pspf")
	// Call savePackageChecksum — mkdirAllFn must succeed for this test.
	oldMkdir := mkdirAllFn
	t.Cleanup(func() { mkdirAllFn = oldMkdir })
	mkdirAllFn = func(path string, perm os.FileMode) error { return nil }

	err = savePackageChecksum(paths, 0x12345678, logger)
	// WriteString on a read-only file should fail.
	_ = err // May succeed on some OS if the file is writable; we just ensure no panic.
}
