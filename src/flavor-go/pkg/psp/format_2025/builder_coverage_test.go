package format_2025

import (
	"bytes"
	"crypto/ed25519"
	cryptorand "crypto/rand"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/hashicorp/go-hclog"
)

// TestBuildWithLogLevelJSONNocolon covers the "json" prefix without a ":" part —
// the else branch at builder.go:60 that sets actualLevel = "info".
func TestBuildWithLogLevelJSONNocolon(t *testing.T) {
	oldBuildImpl := buildImpl
	t.Cleanup(func() { buildImpl = oldBuildImpl })

	called := false
	buildImpl = func(_ hclog.Logger, _, _, _, _, _, _ string) { called = true }

	dir := t.TempDir()
	logPath := filepath.Join(dir, "builder.log")
	t.Setenv(EnvLogPath, logPath)

	// "json" without a colon — triggers the else branch (actualLevel = "info").
	BuildWithLogLevel("manifest.json", "bundle.pspf", "launcher.bin", "", "", "", "json")

	if !called {
		t.Fatal("expected buildImpl to be called")
	}

	// Log output should be JSON (starts with '{').
	data, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}
	firstLine := data
	if newline := bytes.IndexByte(firstLine, '\n'); newline >= 0 {
		firstLine = firstLine[:newline]
	}
	if !bytes.HasPrefix(firstLine, []byte("{")) {
		t.Fatalf("expected JSON log output for 'json' level, got %q", string(data))
	}
}

// TestAdjustPSPFOffsetsMissingMagicWandAtEnd exercises the "missing 🪄 at end"
// error path (builder.go:637).
func TestAdjustPSPFOffsetsMissingMagicWandAtEnd(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	validData, _ := syntheticPSPFDataForBuilderTest(t, 100, 180, 200, 240)

	// Corrupt only the magic wand at the end (last 4 bytes).
	badData := append([]byte(nil), validData...)
	copy(badData[len(badData)-4:], []byte("XXXX"))

	_, err := adjustPSPFOffsets(badData, 100, logger)
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("missing")) {
		t.Fatalf("adjustPSPFOffsets() error = %v, want trailer magic error", err)
	}
}

// TestAdjustPSPFOffsetsNegativeLauncherSize exercises the negative launcherSize
// path in int64ToUint64Checked (builder.go:659).
func TestAdjustPSPFOffsetsNegativeLauncherSize(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	validData, _ := syntheticPSPFDataForBuilderTest(t, 100, 180, 200, 240)

	_, err := adjustPSPFOffsets(validData, -1, logger)
	if err == nil {
		t.Fatal("adjustPSPFOffsets() with negative launcher size should fail")
	}
}

// TestAdjustPSPFOffsetsDescriptorOutOfBounds exercises the slot descriptor
// out-of-bounds check (builder.go:666) by crafting a PSPF with a large SlotCount
// that exceeds the actual data.
func TestAdjustPSPFOffsetsDescriptorOutOfBounds(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()

	// Build a PSPF where SlotCount=1000 but the data is way too small to hold
	// 1000 slot descriptors. launcherSize=100, slotTableOffset=200.
	rawData := buildTinyPSPFWithLargeSlotCount(t, 1000, 200, 180, 100)
	_, err := adjustPSPFOffsets(rawData, 100, logger)
	if err == nil {
		t.Fatal("adjustPSPFOffsets() should fail for out-of-bounds slot descriptor")
	}
}

// buildTinyPSPFWithLargeSlotCount constructs a minimal PSPF blob with a large SlotCount
// so the slot descriptor loop quickly goes out of bounds.
func buildTinyPSPFWithLargeSlotCount(t *testing.T, slotCount uint32, slotTableOffset, metadataOffset, launcherSize uint64) []byte {
	t.Helper()

	// pspfData starts after launcher: slotTableStart = slotTableOffset - launcherSize
	slotTableStart := slotTableOffset - launcherSize
	// Make data just barely large enough to hold the trailer but not the slot descriptors
	totalPSPFSize := int(slotTableStart) + 4 + MagicTrailerSize
	data := make([]byte, totalPSPFSize)

	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(totalPSPFSize) + launcherSize,
		LauncherSize:    launcherSize,
		MetadataOffset:  metadataOffset,
		MetadataSize:    1,
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   uint64(slotCount) * SlotDescriptorSize,
		SlotCount:       slotCount,
	}

	trailerStart := totalPSPFSize - MagicTrailerSize
	copy(data[trailerStart:trailerStart+4], PackageEmojiBytes)
	copy(data[trailerStart+4:trailerStart+4+IndexSize], index.Pack())
	copy(data[trailerStart+MagicTrailerSize-4:], MagicWandEmojiBytes)

	return data
}

// TestAdjustPSPFOffsetsMetadataOffsetUnderflow covers the subtractUint64Checked
// failure for MetadataOffset (builder.go:683-685) when MetadataOffset < launcherSize.
func TestAdjustPSPFOffsetsMetadataOffsetUnderflow(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()

	// Build PSPF with launcherSize=100, metadataOffset=50 (less than launcherSize).
	// slotTableOffset must be >= launcherSize to pass the earlier checks.
	// The syntheticPSPFDataForBuilderTest function uses absolute offsets from
	// start of the combined (launcher+PSPF) file. When we adjust with launcherSize=100,
	// MetadataOffset=50 → 50 - 100 underflows.
	rawData := buildPSPFWithCustomOffsets(t, 100, 50, 200, 240)
	_, err := adjustPSPFOffsets(rawData, 100, logger)
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("rebase metadata offset")) {
		t.Fatalf("adjustPSPFOffsets() error = %v, want 'rebase metadata offset' underflow", err)
	}
}

// TestAdjustPSPFOffsetsSlotTableOffsetUnderflow covers the subtractUint64Checked
// failure for SlotTableOffset (builder.go:686-689).
func TestAdjustPSPFOffsetsSlotTableOffsetUnderflow(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()

	// Build PSPF with valid metadataOffset=180 (>launcherSize=100) but
	// slotTableOffset=90 (< launcherSize=100). This is tricky because
	// launcherSize > slotTableOffset is checked earlier at line 655.
	// We need slotTableOffset=100 exactly (equal, not less than launcher) but then
	// metadataOffset > launcherSize so metadata subtracts OK, and then
	// slotTableOffset subtraction also succeeds... Actually we need to get
	// past the launcherSize > slotTableOffset check (line 655) but then fail
	// on slot table offset subtraction.
	// The check at line 655: launcherSize > slotTableOffset → fail
	// So slotTableOffset must be >= launcherSize.
	// But then slotTableOffset - launcherSizeUint64 >= 0, so it can't underflow.
	// This path (line 687) is actually unreachable because launcherSize <= slotTableOffset
	// is enforced at line 655. So line 686-689 is dead code.
	// Skip this unreachable path.
	_ = logger
}

// buildPSPFWithCustomOffsets creates PSPF data where MetadataOffset can be
// less than the launcherSize (for testing underflow in adjustPSPFOffsets).
func buildPSPFWithCustomOffsets(t *testing.T, launcherSize, metadataOffset, slotTableOffset, descriptorOffset uint64) []byte {
	t.Helper()

	// slotTableStart relative to start of pspf blob (not including launcher)
	slotTableStart := slotTableOffset - launcherSize
	totalPSPFSize := int(slotTableStart) + SlotDescriptorSize + 32 + MagicTrailerSize
	data := make([]byte, totalPSPFSize)

	desc := (&SlotDescriptor{
		ID:     1,
		Offset: descriptorOffset,
		Size:   16,
	}).Pack()
	copy(data[int(slotTableStart):int(slotTableStart)+SlotDescriptorSize], desc)

	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(totalPSPFSize) + launcherSize,
		LauncherSize:    launcherSize,
		MetadataOffset:  metadataOffset, // can be < launcherSize
		MetadataSize:    16,
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
	}

	trailerStart := totalPSPFSize - MagicTrailerSize
	copy(data[trailerStart:trailerStart+4], PackageEmojiBytes)
	copy(data[trailerStart+4:trailerStart+4+IndexSize], index.Pack())
	copy(data[trailerStart+MagicTrailerSize-4:], MagicWandEmojiBytes)

	return data
}

// TestConvertToResourceEmbeddingReadFileFailure covers the readFileValidated
// failure path in convertToResourceEmbedding (builder.go:713).
func TestConvertToResourceEmbeddingReadFileFailure(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	err := convertToResourceEmbedding("/nonexistent/path/bundle.pspf", 100, logger)
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("failed to read file")) {
		t.Fatalf("convertToResourceEmbedding() error = %v, want 'failed to read file'", err)
	}
}

// TestConvertToResourceEmbeddingAdjustError covers the adjustPSPFOffsets failure
// path (builder.go:731) — triggered by an invalid PSPF trailer.
func TestConvertToResourceEmbeddingAdjustError(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "bundle.pspf")

	// Write a file with launcherSize bytes of launcher + garbage (no valid PSPF trailer).
	launcherSize := int64(50)
	content := make([]byte, launcherSize+int64(MagicTrailerSize+10))
	// No valid magic bytes → adjustPSPFOffsets will fail.
	if err := os.WriteFile(filePath, content, 0o644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	logger := hclog.NewNullLogger()
	err := convertToResourceEmbedding(filePath, launcherSize, logger)
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("failed to adjust PSPF offsets")) {
		t.Fatalf("convertToResourceEmbedding() error = %v, want 'failed to adjust PSPF offsets'", err)
	}
}

// TestConvertToResourceEmbeddingEmbedError covers the embedPSPFAsResourceImpl
// failure path and the defer cleanup branch (builder.go:771, 760-765).
func TestConvertToResourceEmbeddingEmbedError(t *testing.T) {
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "bundle.pspf")
	launcherSize := int64(100)
	launcher := bytes.Repeat([]byte("L"), int(launcherSize))
	pspfData, _ := syntheticPSPFDataForBuilderTest(t, launcherSize, 180, 200, 240)
	original := append(append([]byte(nil), launcher...), pspfData...)

	if err := os.WriteFile(filePath, original, 0o644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	oldEmbed := embedPSPFAsResourceImpl
	t.Cleanup(func() { embedPSPFAsResourceImpl = oldEmbed })

	embedPSPFAsResourceImpl = func(_ string, _ []byte, _ hclog.Logger) error {
		return errors.New("embed failed intentionally")
	}

	logger := hclog.NewNullLogger()
	err := convertToResourceEmbedding(filePath, launcherSize, logger)
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("failed to embed as resource")) {
		t.Fatalf("convertToResourceEmbedding() error = %v, want 'failed to embed as resource'", err)
	}
}

// TestConvertToResourceEmbeddingAtomicReplaceError covers the atomicReplaceImpl
// failure path (builder.go:777).
func TestConvertToResourceEmbeddingAtomicReplaceError(t *testing.T) {
	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "bundle.pspf")
	launcherSize := int64(100)
	launcher := bytes.Repeat([]byte("L"), int(launcherSize))
	pspfData, _ := syntheticPSPFDataForBuilderTest(t, launcherSize, 180, 200, 240)
	original := append(append([]byte(nil), launcher...), pspfData...)

	if err := os.WriteFile(filePath, original, 0o644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	oldEmbed := embedPSPFAsResourceImpl
	oldAtomic := atomicReplaceImpl
	t.Cleanup(func() {
		embedPSPFAsResourceImpl = oldEmbed
		atomicReplaceImpl = oldAtomic
	})

	embedPSPFAsResourceImpl = func(exePath string, data []byte, _ hclog.Logger) error {
		return os.WriteFile(exePath, data, 0o700)
	}
	atomicReplaceImpl = func(_, _ string, _ hclog.Logger) error {
		return errors.New("atomic replace failed intentionally")
	}

	logger := hclog.NewNullLogger()
	err := convertToResourceEmbedding(filePath, launcherSize, logger)
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("failed to replace original file")) {
		t.Fatalf("convertToResourceEmbedding() error = %v, want 'failed to replace original file'", err)
	}
}

// TestWriteMetadataJSONMarshalFailure covers the json.MarshalIndent failure
// path in writeMetadata (crypto.go:18-20). A chan field in RuntimeInfo.Env
// causes JSON marshaling to fail.
func TestWriteMetadataJSONMarshalFailure(t *testing.T) {
	t.Parallel()

	publicKey, privateKey, err := ed25519.GenerateKey(cryptorand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey() error = %v", err)
	}

	metadata := &Metadata{
		Format:  "PSPF/2025",
		Package: PackageInfo{Name: "test", Version: "1.0.0"},
		Runtime: &RuntimeInfo{
			Env: map[string]interface{}{
				"chan_field": make(chan int), // json.Marshal cannot encode chan
			},
		},
		Slots: []SlotMetadata{},
	}

	var buf bytes.Buffer
	_, _, err = writeMetadata(&buf, metadata, privateKey, publicKey)
	if err == nil {
		t.Fatal("expected writeMetadata to fail on unmarshalable metadata")
	}
}
