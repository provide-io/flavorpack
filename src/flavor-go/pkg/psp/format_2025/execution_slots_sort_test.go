package format_2025

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/provide-io/flavor/go/flavor/pkg/logging"
)

// TestExtractAndMergeSlotsToWorkenv_TwoSlotDirsSort covers line 106-108 in execution_slots.go:
// the sort comparator branch "both are slot directories - sort by slot number in reverse".
// We inject two slot_N_* directories into the temp extraction dir so the sort
// comparator compares two slot dirs and returns slotI > slotJ.
func TestExtractAndMergeSlotsToWorkenv_TwoSlotDirsSort(t *testing.T) {
	slotContents := []byte("sort-test-data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "sort-slot", slotContents)

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

	// Inject two slot directories (slot_0_* and slot_2_*) into the temp extraction
	// directory. Both must be actual directories (not files) and contain a file
	// so the slot merge proceeds without immediately erroring.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	if err := os.MkdirAll(tempExtractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(tempExtractDir): %v", err)
	}

	// Create slot_0_alpha as a directory with a file — will be merged into workenv.
	slot0Dir := filepath.Join(tempExtractDir, "slot_0_alpha")
	if err := os.MkdirAll(slot0Dir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot0Dir): %v", err)
	}
	if err := os.WriteFile(filepath.Join(slot0Dir, "file0.txt"), []byte("slot0"), 0o644); err != nil {
		t.Fatalf("WriteFile(file0.txt): %v", err)
	}

	// Create slot_2_beta as a directory with a file.
	slot2Dir := filepath.Join(tempExtractDir, "slot_2_beta")
	if err := os.MkdirAll(slot2Dir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot2Dir): %v", err)
	}
	if err := os.WriteFile(filepath.Join(slot2Dir, "file2.txt"), []byte("slot2"), 0o644); err != nil {
		t.Fatalf("WriteFile(file2.txt): %v", err)
	}

	// extractAndMergeSlotsToWorkenv will first extract the real bundle slots,
	// then also process the injected directories. The sort comparator will see
	// both slot_0_alpha and slot_2_beta as slot directories, triggering line 106.
	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err != nil {
		t.Fatalf("extractAndMergeSlotsToWorkenv: %v", err)
	}
}

// TestExtractAndMergeSlotsToWorkenv_Slot0FileRenameFailure covers lines 154-157 in
// execution_slots.go: when os.Rename fails for a file in a slot_0_* directory, the
// function falls back to copyFile. We make the workenv read-only so both rename
// and copy fail, triggering the error return path.
func TestExtractAndMergeSlotsToWorkenv_Slot0FileRenameFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}

	slotContents := []byte("rename-fail-data")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "rename-slot", slotContents)

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

	// Inject a slot_0_injected directory with a regular FILE inside.
	// When the merge runs, it will try to Rename the file to workenv. We make
	// workenv read-only first so both rename and copyFile fail.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	if err := os.MkdirAll(tempExtractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(tempExtractDir): %v", err)
	}
	slot0Dir := filepath.Join(tempExtractDir, "slot_0_injected")
	if err := os.MkdirAll(slot0Dir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot0Dir): %v", err)
	}
	if err := os.WriteFile(filepath.Join(slot0Dir, "payload.bin"), []byte("payload"), 0o644); err != nil {
		t.Fatalf("WriteFile(payload.bin): %v", err)
	}

	// Make workenv read-only so os.Rename and copyFile both fail.
	if err := os.Chmod(workenvDir, 0o555); err != nil {
		t.Fatalf("Chmod(workenv): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(workenvDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when os.Rename and copyFile both fail for slot_0 file")
	}
}

// TestExtractAndMergeSlotsToWorkenv_SlotNFileRenameFailure covers lines 198-205 in
// execution_slots.go: when os.Rename fails for a file in a slot_N_* directory, the
// function falls back to copyFile. We make the workenv read-only so both fail.
func TestExtractAndMergeSlotsToWorkenv_SlotNFileRenameFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}

	slotContents := []byte("slot-n-rename-fail")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "slot-n-rename", slotContents)

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

	// Inject a slot_2_injected directory with a regular FILE inside.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	if err := os.MkdirAll(tempExtractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(tempExtractDir): %v", err)
	}
	slot2Dir := filepath.Join(tempExtractDir, "slot_2_injected")
	if err := os.MkdirAll(slot2Dir, 0o755); err != nil {
		t.Fatalf("MkdirAll(slot2Dir): %v", err)
	}
	if err := os.WriteFile(filepath.Join(slot2Dir, "slotfile.bin"), []byte("slot-n-data"), 0o644); err != nil {
		t.Fatalf("WriteFile(slotfile.bin): %v", err)
	}

	// Make workenv read-only so os.Rename and copyFile both fail.
	if err := os.Chmod(workenvDir, 0o555); err != nil {
		t.Fatalf("Chmod(workenv): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(workenvDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when os.Rename and copyFile both fail for slot_N file")
	}
}

// TestExtractAndMergeSlotsToWorkenv_RegularFileRenameFailure covers lines 227-231 in
// execution_slots.go: when os.Rename fails for a regular (non-slot_*) file, the
// function falls back to copyFile. We make the workenv read-only so both fail.
func TestExtractAndMergeSlotsToWorkenv_RegularFileRenameFailure(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("chmod-based permission tests are not reliable on Windows")
	}
	if os.Getuid() == 0 {
		t.Skip("cannot test permission errors as root")
	}

	slotContents := []byte("regular-file-rename-fail")
	bundlePath, _ := buildSlotsBundleForSlotsTest(t, "regular-rename", slotContents)

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

	// Inject a regular file (not a slot_* prefix) into the temp extraction dir.
	tempExtractDir := paths.TempExtraction(os.Getpid())
	if err := os.MkdirAll(tempExtractDir, 0o755); err != nil {
		t.Fatalf("MkdirAll(tempExtractDir): %v", err)
	}
	if err := os.WriteFile(filepath.Join(tempExtractDir, "regular.bin"), []byte("regular"), 0o644); err != nil {
		t.Fatalf("WriteFile(regular.bin): %v", err)
	}

	// Make workenv read-only so os.Rename and copyFile both fail.
	if err := os.Chmod(workenvDir, 0o555); err != nil {
		t.Fatalf("Chmod(workenv): %v", err)
	}
	t.Cleanup(func() { _ = os.Chmod(workenvDir, 0o755) })

	_, err = extractAndMergeSlotsToWorkenv(reader, metadata, paths, index, logging.NewNullLogger())
	if err == nil {
		t.Fatal("expected error when os.Rename and copyFile both fail for regular file")
	}
}
