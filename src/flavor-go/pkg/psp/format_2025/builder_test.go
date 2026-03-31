package format_2025

import (
	"bytes"
	"encoding/binary"
	"math"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/hashicorp/go-hclog"
)

func TestBuilderBuildWithLogLevelDelegates(t *testing.T) {
	oldBuildImpl := buildImpl
	t.Cleanup(func() {
		buildImpl = oldBuildImpl
	})

	type call struct {
		manifestPath   string
		outputPath     string
		launcherBin    string
		privateKeyPath string
		publicKeyPath  string
		keySeed        string
	}

	var got call
	buildImpl = func(_ hclog.Logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {
		got = call{
			manifestPath:   manifestPath,
			outputPath:     outputPath,
			launcherBin:    launcherBin,
			privateKeyPath: privateKeyPath,
			publicKeyPath:  publicKeyPath,
			keySeed:        keySeed,
		}
	}

	t.Setenv(EnvBuilderLogLevel, "warn")
	t.Setenv(EnvLogLevel, "error")

	BuildWithLogLevel("manifest.json", "bundle.pspf", "launcher.bin", "private.key", "public.key", "seed", "json:debug")

	if got.manifestPath != "manifest.json" || got.outputPath != "bundle.pspf" || got.launcherBin != "launcher.bin" || got.privateKeyPath != "private.key" || got.publicKeyPath != "public.key" || got.keySeed != "seed" {
		t.Fatalf("BuildWithLogLevel() delegated unexpected arguments: %#v", got)
	}
}

func TestBuilderBuildWithOptionsDelegates(t *testing.T) {
	oldBuildImpl := buildImpl
	t.Cleanup(func() {
		buildImpl = oldBuildImpl
	})

	var got struct {
		manifestPath   string
		outputPath     string
		launcherBin    string
		privateKeyPath string
		publicKeyPath  string
		keySeed        string
	}
	buildImpl = func(_ hclog.Logger, manifestPath, outputPath, launcherBin, privateKeyPath, publicKeyPath, keySeed string) {
		got.manifestPath = manifestPath
		got.outputPath = outputPath
		got.launcherBin = launcherBin
		got.privateKeyPath = privateKeyPath
		got.publicKeyPath = publicKeyPath
		got.keySeed = keySeed
	}

	BuildWithOptions("manifest.json", "bundle.pspf", "launcher.bin", "private.key", "public.key", "seed")

	if got.manifestPath != "manifest.json" || got.outputPath != "bundle.pspf" || got.launcherBin != "launcher.bin" || got.privateKeyPath != "private.key" || got.publicKeyPath != "public.key" || got.keySeed != "seed" {
		t.Fatalf("BuildWithOptions() delegated unexpected arguments: %#v", got)
	}
}

func TestBuilderShouldUseResourceEmbeddingForOS(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	goLauncher := syntheticPELauncherForBuilderTest(t, 0x80)
	rustLauncher := syntheticPELauncherForBuilderTest(t, 0xE8)

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

func TestBuilderAdjustPSPFOffsetsRebasesOffsets(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	launcherSize := int64(100)
	pspfData, slotStart := syntheticPSPFDataForBuilderTest(t, launcherSize, 180, 200, 240)

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

func TestBuilderAdjustPSPFOffsetsRejectsInvalidInputs(t *testing.T) {
	t.Parallel()

	logger := hclog.NewNullLogger()
	validData, _ := syntheticPSPFDataForBuilderTest(t, 100, 180, 200, 240)

	tests := []struct {
		name         string
		data         []byte
		launcherSize int64
		wantErr      string
	}{
		{name: "too small", data: make([]byte, MagicTrailerSize-1), launcherSize: 0, wantErr: "PSPF data too small"},
		{name: "bad trailer magic", data: mutateTrailerMagicForBuilderTest(t, validData), launcherSize: 100, wantErr: "missing 📦"},
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

func TestBuilderConvertToResourceEmbeddingRejectsShortFile(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "bundle.pspf")
	if err := os.WriteFile(filePath, []byte("launcher"), 0o644); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}

	err := convertToResourceEmbedding(filePath, 64, hclog.NewNullLogger())
	if err == nil || !bytes.Contains([]byte(err.Error()), []byte("file is too small")) {
		t.Fatalf("convertToResourceEmbedding() error = %v, want short-file failure", err)
	}
}

func TestBuilderConvertToResourceEmbeddingRewritesFile(t *testing.T) {
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

	embedPSPFAsResourceImpl = func(exePath string, adjustedPSPF []byte, logger hclog.Logger) error {
		launcherBytes, err := os.ReadFile(exePath)
		if err != nil {
			return err
		}
		return os.WriteFile(exePath, append(launcherBytes, adjustedPSPF...), 0o700)
	}
	atomicReplaceImpl = func(sourcePath, destPath string, logger hclog.Logger) error {
		return os.Rename(sourcePath, destPath)
	}

	logger := hclog.NewNullLogger()
	if err := convertToResourceEmbedding(filePath, launcherSize, logger); err != nil {
		t.Fatalf("convertToResourceEmbedding() error = %v", err)
	}

	got, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}

	adjustedPSPF, err := adjustPSPFOffsets(pspfData, launcherSize, logger)
	if err != nil {
		t.Fatalf("adjustPSPFOffsets() error = %v", err)
	}
	want := append(append([]byte(nil), launcher...), adjustedPSPF...)
	if !bytes.Equal(got, want) {
		t.Fatalf("rewritten bundle mismatch")
	}
}

func TestBuilderGetFileSize(t *testing.T) {
	t.Parallel()

	tempDir := t.TempDir()
	filePath := filepath.Join(tempDir, "size.txt")
	content := []byte("flavorpack")
	if err := os.WriteFile(filePath, content, 0o644); err != nil {
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

func TestBuilderCheckedArithmeticHelpers(t *testing.T) {
	t.Parallel()

	if got, err := int64ToUint64Checked(42, "value"); err != nil || got != 42 {
		t.Fatalf("int64ToUint64Checked() = (%d, %v), want (42, nil)", got, err)
	}
	if _, err := int64ToUint64Checked(-1, "value"); err == nil {
		t.Fatal("int64ToUint64Checked() should fail for negative values")
	}

	if got, err := intToUint32Checked(42, "value"); err != nil || got != 42 {
		t.Fatalf("intToUint32Checked() = (%d, %v), want (42, nil)", got, err)
	}
	if _, err := intToUint32Checked(math.MaxUint32+1, "value"); err == nil {
		t.Fatal("intToUint32Checked() should fail for oversized values")
	}

	if got, err := addUint64Checked(10, 20, "value"); err != nil || got != 30 {
		t.Fatalf("addUint64Checked() = (%d, %v), want (30, nil)", got, err)
	}
	if _, err := addUint64Checked(math.MaxUint64, 1, "value"); err == nil {
		t.Fatal("addUint64Checked() should fail on overflow")
	}

	if got, err := subtractUint64Checked(30, 10, "value"); err != nil || got != 20 {
		t.Fatalf("subtractUint64Checked() = (%d, %v), want (20, nil)", got, err)
	}
	if _, err := subtractUint64Checked(10, 20, "value"); err == nil {
		t.Fatal("subtractUint64Checked() should fail on underflow")
	}

	if got, err := multiplyUint64Checked(3, 7, "value"); err != nil || got != 21 {
		t.Fatalf("multiplyUint64Checked() = (%d, %v), want (21, nil)", got, err)
	}
	if _, err := multiplyUint64Checked(math.MaxUint64, 2, "value"); err == nil {
		t.Fatal("multiplyUint64Checked() should fail on overflow")
	}
}

func syntheticPELauncherForBuilderTest(t *testing.T, peOffset int) []byte {
	t.Helper()

	data := make([]byte, peOffset+4)
	data[0] = 'M'
	data[1] = 'Z'
	binary.LittleEndian.PutUint32(data[0x3C:0x40], uint32(peOffset))
	copy(data[peOffset:peOffset+4], []byte{'P', 'E', 0, 0})
	return data
}

func syntheticPSPFDataForBuilderTest(t *testing.T, launcherSize int64, metadataOffset, slotTableOffset, descriptorOffset uint64) ([]byte, int) {
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

func mutateTrailerMagicForBuilderTest(t *testing.T, data []byte) []byte {
	t.Helper()

	mutated := append([]byte(nil), data...)
	trailerStart := len(mutated) - MagicTrailerSize
	mutated[trailerStart] = 'X'
	return mutated
}
