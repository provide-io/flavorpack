package format_2025

import (
	"archive/tar"
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

// buildBundleForNilLoggerTest builds a minimal bundle whose path can be used
// to construct a Reader directly (without the constructor that always sets a logger).
func buildBundleForNilLoggerTest(t *testing.T) string {
	t.Helper()
	raw := []byte("hello world")
	return buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "main",
		Target: "{workenv}/out.txt",
	}, 0o644, false)
}

// TestReadSlotNilLogger covers lines 96-98 in reader_slots.go:
// when r.logger is nil at the time ReadSlot's local logger check executes,
// ReadSlot falls back to hclog.L(). We first warm up the cached index by
// calling ReadIndex with a valid logger, then nil out the logger field so
// ReadSlot's nil-check branch is reached without panicking in ReadMagicTrailer.
func TestReadSlotNilLogger(t *testing.T) {
	bundlePath := buildBundleForNilLoggerTest(t)

	// Open normally so the index gets cached.
	r, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = r.Close() }()

	// Warm up the index cache.
	if _, err := r.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}

	// Now nil out the logger so ReadSlot's nil-check is exercised.
	r.logger = nil

	data, err := r.ReadSlot(0)
	if err != nil {
		t.Fatalf("ReadSlot with nil logger error = %v", err)
	}
	if len(data) == 0 {
		t.Fatal("expected non-empty data from ReadSlot")
	}
}

// TestExtractSlotNilLogger covers lines 149-151 in reader_slots.go:
// when r.logger is nil at ExtractSlot's logger check, it falls back to hclog.L().
// We warm up the cached index and metadata first so they don't need r.logger.
func TestExtractSlotNilLogger(t *testing.T) {
	bundlePath := buildBundleForNilLoggerTest(t)
	destDir := t.TempDir()

	// Open normally.
	r, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = r.Close() }()

	// Warm up caches.
	if _, err := r.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex() error = %v", err)
	}
	if _, err := r.ReadMetadata(); err != nil {
		t.Fatalf("ReadMetadata() error = %v", err)
	}

	// Nil out logger so ExtractSlot's nil-check is exercised.
	r.logger = nil

	extractedPath, err := r.ExtractSlot(0, destDir)
	if err != nil {
		t.Fatalf("ExtractSlot with nil logger error = %v", err)
	}
	if extractedPath == "" {
		t.Fatal("expected non-empty extracted path")
	}
}

// TestExtractSlotTarSymlinkRejected covers line 286 in reader_slots.go:
// a tar entry with TypeSymlink is rejected with an error.
func TestExtractSlotTarSymlinkRejected(t *testing.T) {
	// Build a tar archive that contains a symlink entry.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeSymlink,
		Name:     "evil-link",
		Linkname: "/etc/passwd",
	}); err != nil {
		t.Fatalf("WriteHeader(symlink): %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("Close(tar): %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "symlink-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error when extracting tar with symlink entry")
	}
}

// TestExtractSlotTarPathTraversal covers lines 247-249 in reader_slots.go:
// a tar entry that escapes the extraction directory is rejected.
func TestExtractSlotTarPathTraversal(t *testing.T) {
	// Build a tar archive that contains an entry with a path traversal.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeReg,
		Name:     "../../../evil.txt",
		Mode:     0o644,
		Size:     5,
	}); err != nil {
		t.Fatalf("WriteHeader(traversal): %v", err)
	}
	if _, err := tw.Write([]byte("evil\n")); err != nil {
		t.Fatalf("Write(traversal data): %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("Close(tar): %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "traversal-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error for path traversal in tar")
	}
}

// TestExtractSlotTarMkdirError covers lines 253-255 in reader_slots.go:
// os.MkdirAll fails when extracting a directory entry from a tar archive.
func TestExtractSlotTarMkdirError(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	// Build a tar archive with a directory entry.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeDir,
		Name:     "subdir/",
		Mode:     0o755,
	}); err != nil {
		t.Fatalf("WriteHeader(dir): %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("Close(tar): %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "dir-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Use a read-only destDir so MkdirAll for the tar dir entry fails.
	destDir := t.TempDir()
	if err := os.Chmod(destDir, 0o555); err != nil {
		t.Fatalf("Chmod(destDir): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(destDir, 0o755) })

	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error when MkdirAll fails for tar directory entry")
	}
}

// TestExtractSlotTarOpenFileError covers lines 263-265 in reader_slots.go:
// os.OpenFile fails when extracting a regular file from a tar archive.
func TestExtractSlotTarOpenFileError(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	// Build a tar archive with a regular file entry.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeReg,
		Name:     "output.txt",
		Mode:     0o644,
		Size:     int64(len("hello")),
	}); err != nil {
		t.Fatalf("WriteHeader(file): %v", err)
	}
	if _, err := tw.Write([]byte("hello")); err != nil {
		t.Fatalf("Write(file data): %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("Close(tar): %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "file-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Use a read-only destDir so creating output.txt inside it fails.
	destDir := t.TempDir()
	if err := os.Chmod(destDir, 0o555); err != nil {
		t.Fatalf("Chmod(destDir): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(destDir, 0o755) })

	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error when OpenFile fails for tar regular file entry")
	}
}

// TestExtractSlotSingleFileWriteError covers lines 324-326 in reader_slots.go:
// os.WriteFile fails when writing a non-tar slot to a non-writable destination.
func TestExtractSlotSingleFileWriteError(t *testing.T) {
	if os.Getuid() == 0 {
		t.Skip("skipping permission test when running as root")
	}

	raw := []byte("some data to write")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "write-fail-slot",
		Target: "readonly/output.txt",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Create a destDir with a read-only parent directory.
	destDir := t.TempDir()
	readonlyDir := filepath.Join(destDir, "readonly")
	if err := os.MkdirAll(readonlyDir, 0o555); err != nil {
		t.Fatalf("MkdirAll(readonly): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(readonlyDir, 0o755) })

	_, err = reader.ExtractSlot(0, destDir)
	if err == nil {
		t.Fatal("expected error when WriteFile fails due to read-only directory")
	}
}

// TestExtractSlotGzipStillCompressedWarning covers lines 320-322 in reader_slots.go:
// when the decompressed data starts with gzip magic bytes, a warning is logged.
// This doesn't cause an error but we can verify the data is still written.
func TestExtractSlotGzipStillCompressedWarning(t *testing.T) {
	// Create data that looks like it's still gzip-compressed (starts with 0x1f 0x8b 0x08).
	// Must be at least 10 bytes so the logger can format the first 10 bytes.
	raw := []byte{0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "still-gzip-slot",
		Target: "output.bin",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer func() { _ = reader.Close() }()

	destDir := t.TempDir()
	extractedPath, err := reader.ExtractSlot(0, destDir)
	if err != nil {
		t.Fatalf("ExtractSlot(still-gzip) error = %v", err)
	}
	if extractedPath == "" {
		t.Fatal("expected non-empty path from ExtractSlot")
	}
}
