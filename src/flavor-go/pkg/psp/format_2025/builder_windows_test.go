package format_2025

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestAtomicReplaceNormalOperation tests the normal fast path (Layer 1).
// This covers typical x86_64 Windows scenarios where files aren't locked.
func TestAtomicReplaceNormalOperation(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	tempDir, err := os.MkdirTemp("", "atomic-replace-test-")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	logger := hclog.NewNullLogger()

	// Create source and destination files
	srcPath := filepath.Join(tempDir, "source.txt")
	dstPath := filepath.Join(tempDir, "destination.txt")

	srcContent := []byte("source content")
	dstContent := []byte("old destination content")

	if err := os.WriteFile(srcPath, srcContent, 0644); err != nil {
		t.Fatalf("Failed to write source file: %v", err)
	}

	if err := os.WriteFile(dstPath, dstContent, 0644); err != nil {
		t.Fatalf("Failed to write destination file: %v", err)
	}

	// Perform atomic replacement
	err = atomicReplace(srcPath, dstPath, logger)
	if err != nil {
		t.Errorf("atomicReplace failed: %v", err)
	}

	// Verify destination now contains source content
	result, err := os.ReadFile(dstPath)
	if err != nil {
		t.Fatalf("Failed to read destination file after replacement: %v", err)
	}

	if string(result) != string(srcContent) {
		t.Errorf("Destination content mismatch: got %q, want %q", string(result), string(srcContent))
	}

	// Verify source file is gone
	if _, err := os.Stat(srcPath); err == nil {
		t.Error("Source file still exists after replacement (should be moved)")
	}
}

// TestAtomicReplaceFilePreservedOnFailure tests that backup/recovery works.
// Regression test: ensures we don't lose data if atomic operation fails.
func TestAtomicReplaceFilePreservedOnFailure(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	tempDir, err := os.MkdirTemp("", "atomic-replace-recovery-")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	logger := hclog.NewNullLogger()

	// Create destination file with important content
	dstPath := filepath.Join(tempDir, "important.txt")
	dstContent := []byte("IMPORTANT DATA - MUST NOT BE LOST")

	if err := os.WriteFile(dstPath, dstContent, 0644); err != nil {
		t.Fatalf("Failed to write destination file: %v", err)
	}

	// Try to replace with non-existent source (will fail)
	srcPath := filepath.Join(tempDir, "nonexistent.txt")

	err = atomicReplace(srcPath, dstPath, logger)

	// Operation should fail
	if err == nil {
		t.Error("Expected atomicReplace to fail with non-existent source")
	}

	// Important: Destination file should still exist with original content
	result, err := os.ReadFile(dstPath)
	if err != nil {
		t.Fatalf("Destination file lost after failed replacement: %v", err)
	}

	if string(result) != string(dstContent) {
		t.Errorf("Destination content corrupted: got %q, want %q", string(result), string(dstContent))
	}
}

// TestAtomicReplaceVerification tests that the verification step works.
// Regression test: ensures we verify the operation actually succeeded.
func TestAtomicReplaceVerification(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	tempDir, err := os.MkdirTemp("", "atomic-replace-verify-")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	logger := hclog.NewNullLogger()

	srcPath := filepath.Join(tempDir, "source.txt")
	dstPath := filepath.Join(tempDir, "destination.txt")

	srcContent := []byte("verified content")

	if err := os.WriteFile(srcPath, srcContent, 0644); err != nil {
		t.Fatalf("Failed to write source file: %v", err)
	}

	if err := os.WriteFile(dstPath, []byte("old"), 0644); err != nil {
		t.Fatalf("Failed to write destination file: %v", err)
	}

	// Perform replacement
	err = atomicReplace(srcPath, dstPath, logger)
	if err != nil {
		t.Errorf("atomicReplace failed: %v", err)
	}

	// Verify operation actually succeeded (no zero-sized files, etc.)
	fileInfo, err := os.Stat(dstPath)
	if err != nil {
		t.Fatalf("Destination file missing after replacement: %v", err)
	}

	if fileInfo.Size() == 0 {
		t.Error("Destination file is empty (verification should catch this)")
	}

	// Verify contents
	result, err := os.ReadFile(dstPath)
	if err != nil {
		t.Fatalf("Failed to read destination: %v", err)
	}

	if string(result) != string(srcContent) {
		t.Errorf("Content verification failed: got %q, want %q", string(result), string(srcContent))
	}
}

// TestAtomicReplaceWithMultipleRuns tests that multiple sequential replacements work.
// Regression test: ensures no resource leaks or cumulative failures.
func TestAtomicReplaceWithMultipleRuns(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	tempDir, err := os.MkdirTemp("", "atomic-replace-multi-")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	logger := hclog.NewNullLogger()

	// Perform 5 sequential replacements
	for i := 0; i < 5; i++ {
		srcPath := filepath.Join(tempDir, fmt.Sprintf("source%d.txt", i))
		dstPath := filepath.Join(tempDir, fmt.Sprintf("dest%d.txt", i))

		content := []byte(fmt.Sprintf("content iteration %d", i))

		if err := os.WriteFile(srcPath, content, 0644); err != nil {
			t.Fatalf("Iteration %d: Failed to write source: %v", i, err)
		}

		if i > 0 {
			// Create destination file for replacement
			oldContent := []byte(fmt.Sprintf("old content %d", i-1))
			if err := os.WriteFile(dstPath, oldContent, 0644); err != nil {
				t.Fatalf("Iteration %d: Failed to write destination: %v", i, err)
			}
		}

		err := atomicReplace(srcPath, dstPath, logger)
		if err != nil {
			t.Errorf("Iteration %d: atomicReplace failed: %v", i, err)
		}

		// Verify replacement
		result, err := os.ReadFile(dstPath)
		if err != nil {
			t.Fatalf("Iteration %d: Failed to read destination: %v", i, err)
		}

		if string(result) != string(content) {
			t.Errorf("Iteration %d: Content mismatch: got %q, want %q", i, string(result), string(content))
		}
	}
}

// TestAtomicReplaceWithBackup tests backup creation and cleanup.
// Regression test: ensures backup mechanism works correctly.
func TestAtomicReplaceWithBackup(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	tempDir, err := os.MkdirTemp("", "atomic-replace-backup-")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	logger := hclog.NewNullLogger()

	srcPath := filepath.Join(tempDir, "source.txt")
	dstPath := filepath.Join(tempDir, "destination.txt")

	srcContent := []byte("new content")
	dstContent := []byte("old important content")

	if err := os.WriteFile(srcPath, srcContent, 0644); err != nil {
		t.Fatalf("Failed to write source: %v", err)
	}

	if err := os.WriteFile(dstPath, dstContent, 0644); err != nil {
		t.Fatalf("Failed to write destination: %v", err)
	}

	// Perform replacement (triggers backup path in Layer 3 if needed)
	err = atomicReplace(srcPath, dstPath, logger)
	if err != nil {
		t.Errorf("atomicReplace failed: %v", err)
	}

	// Verify replacement succeeded
	result, err := os.ReadFile(dstPath)
	if err != nil {
		t.Fatalf("Failed to read destination: %v", err)
	}

	if string(result) != string(srcContent) {
		t.Errorf("Content mismatch: got %q, want %q", string(result), string(srcContent))
	}

	// Verify backup was cleaned up (not left behind)
	backupPath := dstPath + ".backup"
	if _, err := os.Stat(backupPath); err == nil {
		t.Error("Backup file not cleaned up after successful replacement")
	}
}

// BenchmarkAtomicReplace benchmarks the atomic replacement operation.
// Used to ensure performance doesn't degrade with defense-in-depth logic.
func BenchmarkAtomicReplace(b *testing.B) {
	tempDir, err := os.MkdirTemp("", "bench-atomic-replace-")
	if err != nil {
		b.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	logger := hclog.NewNullLogger()

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		srcPath := filepath.Join(tempDir, fmt.Sprintf("src-%d.txt", i))
		dstPath := filepath.Join(tempDir, fmt.Sprintf("dst-%d.txt", i))

		content := []byte("benchmark content")
		if err := os.WriteFile(srcPath, content, 0644); err != nil {
			b.Fatalf("Failed to write source: %v", err)
		}

		if err := os.WriteFile(dstPath, []byte("old"), 0644); err != nil {
			b.Fatalf("Failed to write destination: %v", err)
		}

		if err := atomicReplace(srcPath, dstPath, logger); err != nil {
			b.Fatalf("atomicReplace failed: %v", err)
		}
	}
}

// TestAtomicReplaceLayerTwoGC tests that GC-based cleanup works.
// This would require more complex setup to simulate file locks,
// so it's documented as a manual test case.
//
// Manual test: Modify atomicReplaceWithMoveFileEx to fail on first 2 attempts,
// then verify Layer 2 (GC + extended delays) succeeds.
func TestAtomicReplaceLayerTwoGC_Manual(t *testing.T) {
	// This test requires mocking Windows APIs or manipulating file handles,
	// which is complex in Go. It's better suited for integration tests
	// that run the actual Go builder with locked files.
	//
	// To test Layer 2, run:
	// 1. Build a test binary that opens a file in exclusive mode
	// 2. Run flavor-go-builder while file is locked
	// 3. Verify "Strategy 2: Force GC + extended delays" appears in logs
	// 4. Verify operation eventually succeeds
	t.Skip("Requires external process to lock file - use integration test instead")
}

// TestAtomicReplaceLayerThreeFallback tests delete-then-move fallback.
// Similar to Layer 2, this needs external process to test effectively.
func TestAtomicReplaceLayerThreeFallback_Manual(t *testing.T) {
	// To test Layer 3, run:
	// 1. Build a test binary that locks the destination file
	// 2. Run flavor-go-builder trying to replace locked file
	// 3. Verify "Strategy 3: Delete-then-move fallback" appears in logs
	// 4. Verify operation eventually succeeds
	// 5. Verify no data is lost (backup works)
	t.Skip("Requires external process to lock file - use integration test instead")
}

func TestShouldUseResourceEmbeddingForOS(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	goLauncher := syntheticPELauncher(t, 0x80)
	rustLauncher := syntheticPELauncher(t, 0xE8)

	tests := []struct {
		name string
		goos string
		data []byte
		want bool
	}{
		{name: "non-windows always appends", goos: "linux", data: goLauncher, want: false},
		{name: "windows go launcher embeds", goos: "windows", data: goLauncher, want: true},
		{name: "windows rust launcher appends", goos: "windows", data: rustLauncher, want: false},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			if got := shouldUseResourceEmbeddingForOS(tt.goos, tt.data, logger); got != tt.want {
				t.Fatalf("shouldUseResourceEmbeddingForOS(%q, ...) = %v, want %v", tt.goos, got, tt.want)
			}
		})
	}

	if runtime.GOOS != "windows" {
		if got := shouldUseResourceEmbedding(goLauncher, logger); got {
			t.Fatalf("shouldUseResourceEmbedding() on %s = true, want false", runtime.GOOS)
		}
	}
}

func TestAdjustPSPFOffsetsRebasesOffsets(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	launcherSize := int64(100)
	pspfData, slotStart := syntheticPSPFData(t, launcherSize, 180, 200, 240)

	adjusted, err := adjustPSPFOffsets(pspfData, launcherSize, logger)
	if err != nil {
		t.Fatalf("adjustPSPFOffsets() error = %v", err)
	}

	adjustedDesc, err := UnpackSlotDescriptor(adjusted[slotStart : slotStart+SlotDescriptorSize])
	if err != nil {
		t.Fatalf("UnpackSlotDescriptor() error = %v", err)
	}
	if got, want := adjustedDesc.Offset, uint64(140); got != want {
		t.Fatalf("descriptor offset = %d, want %d", got, want)
	}

	trailerStart := len(adjusted) - MagicTrailerSize
	var index PSPFIndex
	if err := index.Unpack(adjusted[trailerStart+4 : trailerStart+4+IndexSize]); err != nil {
		t.Fatalf("index.Unpack() error = %v", err)
	}
	if got, want := index.MetadataOffset, uint64(80); got != want {
		t.Fatalf("metadata offset = %d, want %d", got, want)
	}
	if got, want := index.SlotTableOffset, uint64(100); got != want {
		t.Fatalf("slot table offset = %d, want %d", got, want)
	}
	if got, want := index.PackageSize, uint64(len(pspfData)); got != want {
		t.Fatalf("package size = %d, want %d", got, want)
	}
	if got, want := index.LauncherSize, uint64(0); got != want {
		t.Fatalf("launcher size = %d, want %d", got, want)
	}
}

func TestAdjustPSPFOffsetsRejectsInvalidInputs(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	validData, _ := syntheticPSPFData(t, 100, 180, 200, 240)

	tests := []struct {
		name         string
		data         []byte
		launcherSize int64
		wantErr      string
	}{
		{name: "too small", data: make([]byte, MagicTrailerSize-1), launcherSize: 0, wantErr: "PSPF data too small"},
		{name: "bad trailer magic", data: mutateTrailerMagic(t, validData), launcherSize: 100, wantErr: "missing 📦"},
		{name: "launcher underflow", data: validData, launcherSize: 250, wantErr: "launcher size exceeds slot table offset"},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			_, err := adjustPSPFOffsets(tt.data, tt.launcherSize, logger)
			if err == nil || !bytes.Contains([]byte(err.Error()), []byte(tt.wantErr)) {
				t.Fatalf("adjustPSPFOffsets() error = %v, want substring %q", err, tt.wantErr)
			}
		})
	}
}

func TestConvertToResourceEmbeddingRejectsShortFile(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "bundle.pspf")
	if err := os.WriteFile(filePath, []byte("launcher"), 0644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	err := convertToResourceEmbedding(filePath, 64, hclog.NewNullLogger())
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("file is too small")) {
		t.Fatalf("convertToResourceEmbedding() error = %v, want short-file failure", err)
	}
}

func TestGetFileSize(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "size.txt")
	content := []byte("flavorpack")
	if err := os.WriteFile(filePath, content, 0644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	got, err := getFileSize(filePath)
	if err != nil {
		t.Fatalf("getFileSize() error = %v", err)
	}
	if want := int64(len(content)); got != want {
		t.Fatalf("getFileSize() = %d, want %d", got, want)
	}
}

func syntheticPELauncher(t *testing.T, peOffset int) []byte {
	t.Helper()

	data := make([]byte, peOffset+4)
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], uint32(peOffset))
	copy(data[peOffset:peOffset+4], []byte{'P', 'E', 0, 0})
	return data
}

func syntheticPSPFData(t *testing.T, launcherSize int64, metadataOffset, slotTableOffset, descriptorOffset uint64) ([]byte, int) {
	t.Helper()

	slotStart := int(slotTableOffset) - int(launcherSize)
	if slotStart < 0 {
		t.Fatalf("slot table start underflow: launcher=%d offset=%d", launcherSize, slotTableOffset)
	}

	totalSize := slotStart + SlotDescriptorSize + 32 + MagicTrailerSize
	data := make([]byte, totalSize)

	desc := (&SlotDescriptor{
		ID:     1,
		Offset: descriptorOffset,
		Size:   16,
	}).Pack()
	copy(data[slotStart:slotStart+SlotDescriptorSize], desc)

	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(totalSize) + uint64(launcherSize),
		LauncherSize:    uint64(launcherSize),
		MetadataOffset:  metadataOffset,
		MetadataSize:    16,
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
	}

	trailerStart := totalSize - MagicTrailerSize
	copy(data[trailerStart:trailerStart+4], PackageEmojiBytes)
	copy(data[trailerStart+4:trailerStart+4+IndexSize], index.Pack())
	copy(data[trailerStart+MagicTrailerSize-4:], MagicWandEmojiBytes)

	return data, slotStart
}

func mutateTrailerMagic(t *testing.T, data []byte) []byte {
	t.Helper()

	mutated := append([]byte(nil), data...)
	trailerStart := len(mutated) - MagicTrailerSize
	mutated[trailerStart] = 'X'
	return mutated
}
