package format_2025

import (
	"archive/tar"
	"bytes"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// TestExtractSlotTarWithExecutableFile covers reader_slots.go lines 279-283:
// the "set executable bit" branch when a tar entry has mode with execute bits
// (hdr.Mode&0111 != 0). We build a tar with a file mode 0755 and verify
// ExtractSlot runs os.Chmod on it.
func TestExtractSlotTarWithExecutableFile(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod / executable-bit tests not reliable on Windows")
	}
	t.Parallel()

	// Build a tar archive with an executable file (mode 0755).
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeReg,
		Name:     "script.sh",
		Mode:     0o755,
		Size:     int64(len("#!/bin/sh\n")),
	}); err != nil {
		t.Fatalf("WriteHeader: %v", err)
	}
	if _, err := tw.Write([]byte("#!/bin/sh\n")); err != nil {
		t.Fatalf("tar.Write: %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("tar.Close: %v", err)
	}
	tarData := buf.Bytes()

	// Build a bundle storing the raw tar (no compression, OP_TAR operation).
	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "exec-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	destDir := t.TempDir()
	extractedPath, err := reader.ExtractSlot(0, destDir)
	if err != nil {
		t.Fatalf("ExtractSlot: %v", err)
	}

	// Verify the file was extracted and has executable permissions.
	scriptPath := filepath.Join(extractedPath, "script.sh")
	info, err := os.Stat(scriptPath)
	if err != nil {
		t.Fatalf("Stat(script.sh): %v", err)
	}
	if info.Mode()&0111 == 0 {
		t.Errorf("expected script.sh to be executable, got mode %v", info.Mode())
	}
}

// TestExtractSlotTarWithSymlink covers reader_slots.go line 286:
// when a tar entry is a TypeSymlink, ExtractSlot returns an error.
func TestExtractSlotTarWithSymlink(t *testing.T) {
	t.Parallel()

	// Build a tar archive with a symlink entry.
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeSymlink,
		Name:     "link.sh",
		Linkname: "/etc/passwd",
		Mode:     0o777,
	}); err != nil {
		t.Fatalf("WriteHeader(symlink): %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("tar.Close: %v", err)
	}
	tarData := buf.Bytes()

	bundle := buildSingleSlotBundleForTests(t, tarData, tarData, []uint8{OP_TAR}, SlotMetadata{
		ID:     "symlink-slot",
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
		t.Fatal("expected error for symlink tar entry, got nil")
	}
}
