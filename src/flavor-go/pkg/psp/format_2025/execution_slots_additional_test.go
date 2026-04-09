package format_2025

import (
	"archive/tar"
	"bytes"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// buildTarSlotBundle creates a bundle whose slot 0 payload is a tar archive
// containing a directory entry named dirName with one file inside.
func buildTarSlotBundle(t *testing.T, dirName, fileName string, content []byte) (string, *Metadata) {
	t.Helper()

	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)

	// Write directory entry
	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeDir,
		Name:     dirName + "/",
		Mode:     0o755,
	}); err != nil {
		t.Fatalf("WriteHeader(dir): %v", err)
	}

	// Write file inside directory
	hdr := &tar.Header{
		Name: dirName + "/" + fileName,
		Mode: 0o644,
		Size: int64(len(content)),
	}
	if err := tw.WriteHeader(hdr); err != nil {
		t.Fatalf("WriteHeader(file): %v", err)
	}
	if _, err := tw.Write(content); err != nil {
		t.Fatalf("Write(file): %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	tarData := buf.Bytes()

	slotMeta := SlotMetadata{
		Slot:   0,
		ID:     "tar-dir-slot",
		Target: "{workenv}",
		Size:   int64(len(tarData)),
	}
	md := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package:       PackageInfo{Name: "test", Version: "0.0.1"},
		Execution:     &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:         &BuildInfo{Tool: "flavor-go"},
		Slots:         []SlotMetadata{slotMeta},
	}
	spec := multiSlotBundleSpec{
		meta:         slotMeta,
		storedData:   tarData,
		originalData: tarData,
	}
	path := buildMultiSlotBundleForTests(t, []multiSlotBundleSpec{spec}, md)
	return path, &md
}

// TestExtractAndMergeSlotsToWorkenv_Slot0DirCopyDirAllFailure covers the error
// path on line 145-149: copyDirAll fails when copying a slot_0_* subdirectory
// into the workenv. We pre-inject a slot_0_foo/ directory into the temp extraction
// path and make the workenv unwritable so copyDirAll cannot create the destination.
func TestExtractAndMergeSlotsToWorkenv_Slot0DirCopyDirAllFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}

	slotContents := []byte("minimal")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "minimal", slotContents)

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

	// Pre-create a slot_0_injected/ directory in the temp extraction directory
	// with a subdirectory inside it so copyDirAll will be called.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	slotDir := filepath.Join(tempExtractDir, "slot_0_injected")
	innerDir := filepath.Join(slotDir, "inner")
	if err := os.MkdirAll(innerDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(inner): %v", err)
	}
	if err := os.WriteFile(filepath.Join(innerDir, "data.txt"), []byte("data"), 0o644); err != nil {
		t.Fatalf("WriteFile(data.txt): %v", err)
	}

	// Make the workenv directory unwritable so copyDirAll fails when trying
	// to create the destination directory inside it.
	if err := os.Chmod(workenvDir, 0o555); err != nil {
		t.Fatalf("Chmod(workenv): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(workenvDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when copyDirAll fails for slot_0_ directory")
	}
}

// TestExtractAndMergeSlotsToWorkenv_SlotNDirCopyDirAllFailure covers the error
// path on lines 189-193: copyDirAll fails when copying a slot_N_* subdirectory.
// We pre-inject a slot_2_foo/ directory and make the workenv unwritable.
func TestExtractAndMergeSlotsToWorkenv_SlotNDirCopyDirAllFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}

	slotContents := []byte("minimal")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "minimal2", slotContents)

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

	// Pre-create a slot_2_injected/ directory in the temp extraction directory
	// with a subdirectory inside it so copyDirAll will be called.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	slotDir := filepath.Join(tempExtractDir, "slot_2_injected")
	innerDir := filepath.Join(slotDir, "inner")
	if err := os.MkdirAll(innerDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(inner): %v", err)
	}
	if err := os.WriteFile(filepath.Join(innerDir, "data.txt"), []byte("data"), 0o644); err != nil {
		t.Fatalf("WriteFile(data.txt): %v", err)
	}

	// Make the workenv directory unwritable so copyDirAll fails.
	if err := os.Chmod(workenvDir, 0o555); err != nil {
		t.Fatalf("Chmod(workenv): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(workenvDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when copyDirAll fails for slot_N_ directory")
	}
}

// TestExtractAndMergeSlotsToWorkenv_RegularDirCopyDirAllFailure covers the error
// path on lines 220-224: copyDirAll fails for a regular (non-slot_*) directory.
func TestExtractAndMergeSlotsToWorkenv_RegularDirCopyDirAllFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}

	slotContents := []byte("minimal")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "minimal3", slotContents)

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

	// Pre-create a regular (non-slot_*) directory in the temp extraction directory.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	regularDir := filepath.Join(tempExtractDir, "lib")
	innerDir := filepath.Join(regularDir, "deep")
	if err := os.MkdirAll(innerDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(deep): %v", err)
	}
	if err := os.WriteFile(filepath.Join(innerDir, "lib.so"), []byte("lib"), 0o644); err != nil {
		t.Fatalf("WriteFile(lib.so): %v", err)
	}

	// Make the workenv directory unwritable so copyDirAll fails.
	if err := os.Chmod(workenvDir, 0o555); err != nil {
		t.Fatalf("Chmod(workenv): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(workenvDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when copyDirAll fails for regular directory")
	}
}

// TestExtractAndMergeSlotsToWorkenv_ExtractionFailed covers the ExtractSlot
// failure path (lines 43-48). We corrupt the slot data checksum to make
// ExtractSlot fail during extraction.
func TestExtractAndMergeSlotsToWorkenv_ExtractionFailed(t *testing.T) {
	t.Parallel()

	// buildSingleSlotBundleForTests with corruptChecksum=true causes ExtractSlot to fail.
	bundlePath := buildSingleSlotBundleForTests(t, []byte("corrupt slot data"), []byte("corrupt slot data"), nil, SlotMetadata{
		ID:     "corrupt-slot",
		Target: "{workenv}",
	}, 0, true /* corruptChecksum */)

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
	if err := os.MkdirAll(paths.Workenv(), 0o755); err != nil {
		t.Fatalf("MkdirAll(workenv): %v", err)
	}

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when ExtractSlot fails due to corrupt checksum")
	}
}
