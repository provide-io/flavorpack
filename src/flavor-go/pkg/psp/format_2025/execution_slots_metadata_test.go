package format_2025

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestExtractAndMergeSlotsToWorkenv_MetadataDirMkdirAllFailure covers lines 56-59 in
// execution_slots.go: when os.MkdirAll for packageMetadataDir fails, the function
// returns an error. We place a regular file at paths.Metadata() so that creating
// packageMetadataDir (a child of paths.Metadata()) fails.
func TestExtractAndMergeSlotsToWorkenv_MetadataDirMkdirAllFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}

	slotContents := []byte("meta-dir-fail-data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "meta-dir-fail", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	workenvDir := paths.Workenv()
	if err := os.MkdirAll(workenvDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create the tempExtractDir so extraction can begin (this also
	// creates paths.Metadata() as a side effect of MkdirAll).
	tempExtractDir := paths.TempExtraction(os.Getpid())
	if err := os.MkdirAll(tempExtractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(tempExtractDir): %v", err)
	}

	// Make paths.Metadata() non-writable so MkdirAll(packageMetadataDir)
	// (which is paths.Metadata()/package) fails with permission denied.
	if err := os.Chmod(paths.Metadata(), 0o555); err != nil {
		t.Fatalf("Chmod(metadata): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(paths.Metadata(), 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when MkdirAll(packageMetadataDir) fails")
	}
}

// TestExtractAndMergeSlotsToWorkenv_MetadataWriteFileFailure covers lines 68-72 in
// execution_slots.go: when os.WriteFile for metadataFile fails, the function returns
// an error. We create packageMetadataDir as read-only so the write fails.
func TestExtractAndMergeSlotsToWorkenv_MetadataWriteFileFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}

	slotContents := []byte("meta-write-fail-data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "meta-write-fail", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	workenvDir := paths.Workenv()
	if err := os.MkdirAll(workenvDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create the tempExtractDir so extraction can begin.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	if err := os.MkdirAll(tempExtractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(tempExtractDir): %v", err)
	}

	// Create packageMetadataDir as read-only so os.WriteFile inside it fails.
	packageMetadataDir := filepath.Join(paths.Metadata(), "package")
	if err := os.MkdirAll(packageMetadataDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(packageMetadataDir): %v", err)
	}
	if err := os.Chmod(packageMetadataDir, 0o555); err != nil {
		t.Fatalf("Chmod(packageMetadataDir): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(packageMetadataDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when os.WriteFile for metadataFile fails")
	}
}

// TestExtractAndMergeSlotsToWorkenv_ReadDirTempExtractFailure covers lines 80-83 in
// execution_slots.go: when os.ReadDir(tempExtractDir) fails, the function returns an
// error. We create tempExtractDir but make it unreadable before the merge phase.
func TestExtractAndMergeSlotsToWorkenv_ReadDirTempExtractFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}

	slotContents := []byte("readdir-fail-data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "readdir-fail", slotContents)

	reader, err := NewReaderWithLogger(bundlePath, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("NewReaderWithLogger: %v", err)
	}
	defer func() { _ = reader.Close() }()

	metadata, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	index, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	cacheDir := t.TempDir()
	paths := NewWorkenvPaths(cacheDir, bundlePath)
	workenvDir := paths.Workenv()
	if err := os.MkdirAll(workenvDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	// Pre-create the tempExtractDir (extraction will succeed into it).
	tempExtractDir := paths.TempExtraction(os.Getpid())
	if err := os.MkdirAll(tempExtractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(tempExtractDir): %v", err)
	}

	// Pre-create packageMetadataDir and make it writable so metadata write succeeds.
	packageMetadataDir := filepath.Join(paths.Metadata(), "package")
	if err := os.MkdirAll(packageMetadataDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(packageMetadataDir): %v", err)
	}

	// Now make tempExtractDir unreadable so os.ReadDir fails.
	if err := os.Chmod(tempExtractDir, 0o000); err != nil {
		t.Fatalf("Chmod(tempExtractDir): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(tempExtractDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when os.ReadDir(tempExtractDir) fails")
	}
}
