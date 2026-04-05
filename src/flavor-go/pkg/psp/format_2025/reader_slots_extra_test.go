//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"archive/tar"
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

// buildTarArchiveWithDirOnly returns a tar archive containing only a single directory entry.
func buildTarArchiveWithDirOnly(t *testing.T, dirName string) []byte {
	t.Helper()

	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeDir,
		Name:     dirName + "/",
		Mode:     0o755,
	}); err != nil {
		t.Fatalf("WriteHeader(dir) error = %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("Close(tar writer) error = %v", err)
	}
	return buf.Bytes()
}

// TestExtractSlotTarWithDirectoryEntry verifies that tar entries of type TypeDir
// are handled correctly: the directory is created, not rejected.
func TestExtractSlotTarWithDirectoryEntry(t *testing.T) {
	t.Parallel()

	tarRaw := buildTarArchiveWithDirOnly(t, "emptydir")
	bundle := buildSingleSlotBundleForTests(t, tarRaw, tarRaw, []uint8{OP_TAR}, SlotMetadata{
		ID:     "dir-only-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	destDir := t.TempDir()
	extractedPath, err := reader.ExtractSlot(0, destDir)
	if err != nil {
		t.Fatalf("ExtractSlot(dir-only tar) error = %v", err)
	}
	if extractedPath != destDir {
		t.Fatalf("ExtractSlot path = %q, want %q", extractedPath, destDir)
	}

	// The directory should have been created inside destDir.
	dirPath := filepath.Join(destDir, "emptydir")
	if info, err := os.Stat(dirPath); err != nil || !info.IsDir() {
		t.Fatalf("expected extracted directory at %q, stat error = %v", dirPath, err)
	}
}

// TestReadSlotEncryptionNotImplemented covers the OP_AES256_GCM error path in ReadSlot.
func TestReadSlotEncryptionNotImplemented(t *testing.T) {
	t.Parallel()

	raw := []byte("encrypted payload placeholder")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, []uint8{OP_AES256_GCM}, SlotMetadata{
		ID:     "encrypted-slot",
		Target: "{workenv}/secret.bin",
	}, 0o600, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error for AES256_GCM operation, got nil")
	}
}

// TestReadSlotUnknownOperation covers the unknown-operation error path in ReadSlot
// (operation != OP_NONE and not one of the known ops).
func TestReadSlotUnknownOperation(t *testing.T) {
	t.Parallel()

	raw := []byte("payload with unknown op")
	// 0xFE is not a defined operation code.
	bundle := buildSingleSlotBundleForTests(t, raw, raw, []uint8{0xFE}, SlotMetadata{
		ID:     "unknown-op-slot",
		Target: "{workenv}/out.bin",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error for unknown operation, got nil")
	}
}

// TestExtractSlotNonTarTargetingWorkenv covers the non-tar slot targeting {workenv}
// (empty targetPath with isTar=false), which writes to a slot-specific subdirectory.
func TestExtractSlotNonTarTargetingWorkenv(t *testing.T) {
	t.Parallel()

	raw := []byte("just a binary blob")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "blob-slot",
		Target: "{workenv}",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	destDir := t.TempDir()
	extractedPath, err := reader.ExtractSlot(0, destDir)
	if err != nil {
		t.Fatalf("ExtractSlot(non-tar workenv) error = %v", err)
	}

	// Extracted to slot-specific subdirectory.
	if extractedPath == destDir {
		t.Fatal("expected slot to be written to a subdirectory, not destDir itself")
	}

	// Verify file exists.
	if _, err := os.Stat(extractedPath); err != nil {
		t.Fatalf("extracted path %q does not exist: %v", extractedPath, err)
	}
}

// TestIsTarballGNUTarFormat covers the GNU tar format branch in isTarball
// (line 144) where the magic at offset 257 is "ustar  \x00".
func TestIsTarballGNUTarFormat(t *testing.T) {
	t.Parallel()

	data := make([]byte, 512)
	copy(data[257:265], "ustar  \x00")

	if !isTarball(data) {
		t.Fatal("expected isTarball to return true for GNU tar format")
	}
}

// TestIsTarballNoMagic covers the case where data is 512+ bytes but has no tar magic.
func TestIsTarballNoMagic(t *testing.T) {
	t.Parallel()

	data := make([]byte, 512)
	if isTarball(data) {
		t.Fatal("expected isTarball to return false when no tar magic present")
	}
}

// TestIsTarballTooSmall covers the case where data is less than 512 bytes.
func TestIsTarballTooSmall(t *testing.T) {
	t.Parallel()

	if isTarball([]byte("too short")) {
		t.Fatal("expected isTarball to return false for short data")
	}
}

// TestExtractSlotDestPathIsExistingDirectory covers the path where destPath is an
// existing directory (returns the directory without writing a file).
func TestExtractSlotDestPathIsExistingDirectory(t *testing.T) {
	t.Parallel()

	raw := []byte("some payload")
	// The target resolves to an existing directory.
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "dir-dest-slot",
		Target: "subdir",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	destDir := t.TempDir()
	// Pre-create the target subdirectory.
	subdir := filepath.Join(destDir, "subdir")
	if err := os.MkdirAll(subdir, 0o755); err != nil {
		t.Fatalf("MkdirAll(subdir) error = %v", err)
	}

	extractedPath, err := reader.ExtractSlot(0, destDir)
	if err != nil {
		t.Fatalf("ExtractSlot(dir dest) error = %v", err)
	}
	if extractedPath != subdir {
		t.Fatalf("ExtractSlot path = %q, want %q", extractedPath, subdir)
	}
}
