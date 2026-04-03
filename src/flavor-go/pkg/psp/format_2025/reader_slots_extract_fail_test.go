package format_2025

import (
	"archive/tar"
	"bytes"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// TestExtractSlotMkdirAllFailure covers reader_slots.go:230-232:
// when os.MkdirAll(extractDir) fails because destDir has a FILE as a path component.
// We build a tar bundle and pass a destDir where the target component path is blocked.
func TestExtractSlotMkdirAllFailure(t *testing.T) {
	t.Parallel()

	// Build a simple tar with a single file.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	content := []byte("hello")
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeReg,
		Name:     "data.txt",
		Mode:     0o644,
		Size:     int64(len(content)),
	}); err != nil {
		t.Fatalf("WriteHeader: %v", err)
	}
	if _, err := tw.Write(content); err != nil {
		t.Fatalf("tar.Write: %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("tar.Close: %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "fail-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Create a base temp dir, then put a FILE where the destDir would need a directory.
	base := t.TempDir()
	// Place a regular file at a path that ExtractSlot would try to use as a directory.
	// ExtractSlot creates: extractDir = destDir (when Target == "{workenv}" and no subpath).
	// We need extractDir itself to be blocked.
	// Strategy: create destDir as a FILE so MkdirAll fails.
	destDir := filepath.Join(base, "blocked")
	if err := os.WriteFile(destDir, []byte("blocker"), 0o644); err != nil {
		t.Fatalf("WriteFile(blocker): %v", err)
	}

	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error when extractDir is blocked by a file, got nil")
	}
	if !strings.Contains(err.Error(), "failed to create extraction directory") {
		t.Logf("note: got error %v", err)
	}
}

// TestExtractSlotSingleFileMkdirAllFailure covers reader_slots.go:304-306:
// when a non-TAR slot has a specific target path and MkdirAll(filepath.Dir(destPath)) fails
// because a parent path component is blocked by a regular file.
func TestExtractSlotSingleFileMkdirAllFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("file-as-directory blocking not reliable on Windows")
	}
	t.Parallel()

	// Build a non-TAR slot with target "{workenv}/data/output.bin".
	// The slot gets extracted to destDir/data/output.bin.
	// We pre-create destDir/data as a regular FILE so MkdirAll("destDir/data") fails.
	data := []byte("some binary content")
	bundle := buildSingleSlotBundleForTests(t, data, data, nil, SlotMetadata{
		ID:     "file-slot",
		Target: "{workenv}/data/output.bin",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	destDir := t.TempDir()
	// Block the parent directory "data" with a regular file.
	if err := os.WriteFile(filepath.Join(destDir, "data"), []byte("blocker"), 0o644); err != nil {
		t.Fatalf("WriteFile(data blocker): %v", err)
	}

	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error when parent dir of single file slot is blocked, got nil")
	}
}

// TestExtractSlotTarRegMkdirAllFailure covers reader_slots.go:258-260:
// when MkdirAll for the parent directory of a TypeReg tar entry fails because
// the parent path component is pre-occupied by a regular file.
func TestExtractSlotTarRegMkdirAllFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("file-as-directory blocking not reliable on Windows")
	}
	t.Parallel()

	// Build a tar with a file nested under "subdir/" (e.g., "subdir/data.txt").
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	content := []byte("nested content")
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeReg,
		Name:     "subdir/data.txt",
		Mode:     0o644,
		Size:     int64(len(content)),
	}); err != nil {
		t.Fatalf("WriteHeader(subdir/data.txt): %v", err)
	}
	if _, err := tw.Write(content); err != nil {
		t.Fatalf("tar.Write: %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("tar.Close: %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "nested-fail",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Pre-create a regular FILE named "subdir" in destDir so MkdirAll("subdir") fails.
	destDir := t.TempDir()
	if err := os.WriteFile(filepath.Join(destDir, "subdir"), []byte("blocker"), 0o644); err != nil {
		t.Fatalf("WriteFile(subdir blocker): %v", err)
	}

	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error when parent dir blocked by a file, got nil")
	}
}

// TestExtractSlotTarIoCopyError covers reader_slots.go:267-272:
// when io.Copy from the tar reader fails because the tar entry declares a size
// larger than the actual data in the archive (io.ErrUnexpectedEOF from tar reader).
func TestExtractSlotTarIoCopyError(t *testing.T) {
	t.Parallel()

	// Build a tar where a TypeReg entry declares size=100 but only 5 bytes are written.
	// The tar reader will return an error when io.Copy tries to read the declared 100 bytes.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)

	// Write a tar header claiming 100 bytes but only write 5.
	hdr := &tar.Header{
		Typeflag: tar.TypeReg,
		Name:     "file.txt",
		Mode:     0o644,
		Size:     100, // claim 100 bytes
	}
	if err := tw.WriteHeader(hdr); err != nil {
		t.Fatalf("WriteHeader: %v", err)
	}
	// Write only 5 bytes instead of the declared 100 — the tar is truncated.
	if _, err := tw.Write([]byte("short")); err != nil {
		t.Fatalf("tar.Write: %v", err)
	}
	// NOTE: Do NOT call tw.Close() — we want a truncated/corrupt archive.
	// We'll use the raw bytes directly.
	tarData := buf.Bytes()

	// Plant the ustar magic so isTarball returns true.
	paddedData := make([]byte, 512)
	copy(paddedData, tarData)
	copy(paddedData[257:], []byte("ustar"))
	// Reuse actual tar header bytes but inject ustar at 257 so isTarball fires.
	// Actually: our tar starts at offset 0, so the real header is at byte 0.
	// The ustar magic in a proper tar is at offset 257 within the 512-byte block.
	// The tar package writes "ustar" at offset 257 in the header block automatically.
	// So we just use the real tar bytes (already has ustar magic).

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "truncated-tar",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	destDir := t.TempDir()
	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error from io.Copy when tar entry is truncated, got nil")
	}
}

// TestExtractSlotTarCorruptData covers reader_slots.go:240-242:
// when the tar data is recognized as a tarball (has ustar magic) but the
// rest of the content is corrupt, so tr.Next() returns a non-EOF error.
func TestExtractSlotTarCorruptData(t *testing.T) {
	t.Parallel()

	// Build a 512-byte block with "ustar" at offset 257 but otherwise garbage.
	// This makes isTarball() return true, and then tar.NewReader.Next() fails.
	corruptTar := make([]byte, 512)
	// Fill with non-zero garbage to confuse the tar parser.
	for i := range corruptTar {
		corruptTar[i] = byte(0xff)
	}
	// Plant the ustar magic so isTarball returns true.
	copy(corruptTar[257:], []byte("ustar"))

	bundle := buildSingleSlotBundleForTests(t, corruptTar, corruptTar, []uint8{OP_TAR}, SlotMetadata{
		ID:     "corrupt-tar",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	destDir := t.TempDir()
	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error when tar data is corrupt, got nil")
	}
}
