package format_2025

import (
	"archive/tar"
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func testBundlePath(t *testing.T, suffix string) string {
	t.Helper()

	replacer := strings.NewReplacer("/", "_", " ", "_", ":", "_")
	return filepath.Join(t.TempDir(), replacer.Replace(t.Name())+suffix)
}

func buildSingleSlotBundleForTests(t *testing.T, storedData, originalData []byte, operations []uint8, slotMeta SlotMetadata, permissions uint16, corruptChecksum bool) string {
	t.Helper()

	if originalData == nil {
		originalData = storedData
	}
	if slotMeta.ID == "" {
		slotMeta.ID = "slot-0"
	}

	bundlePath := testBundlePath(t, ".psp")
	f, err := os.Create(bundlePath)
	if err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	defer func() {
		if err := f.Close(); err != nil {
			t.Fatalf("Close() error = %v", err)
		}
	}()

	if _, err := f.Write(storedData); err != nil {
		t.Fatalf("Write(slot data) error = %v", err)
	}

	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName(slotMeta.ID),
		Offset:       0,
		Size:         uint64(len(storedData)),
		OriginalSize: uint64(len(originalData)),
		Operations:   PackOperations(operations),
	}
	checksum := sha256.Sum256(storedData)
	if corruptChecksum {
		checksum[0] ^= 0xFF
	}
	desc.Checksum = binary.LittleEndian.Uint64(checksum[:8])
	desc.SetPermissions(permissions)

	slotTableOffset := uint64(len(storedData))
	if _, err := f.Write(desc.Pack()); err != nil {
		t.Fatalf("Write(slot descriptor) error = %v", err)
	}

	slotMeta.Size = int64(len(originalData))
	metadata := Metadata{
		Format:        "PSPF/2025",
		FormatVersion: "2025.0",
		Package: PackageInfo{
			Name:    "demo",
			Version: "1.0.0",
		},
		Slots:     []SlotMetadata{slotMeta},
		Execution: &ExecutionInfo{PrimarySlot: 0, Command: "/bin/true"},
		Build:     &BuildInfo{Tool: "flavor-go"},
	}
	metaJSON, err := json.Marshal(metadata)
	if err != nil {
		t.Fatalf("Marshal(metadata) error = %v", err)
	}
	gzMeta := gzipData(t, metaJSON)
	metadataOffset := slotTableOffset + SlotDescriptorSize
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("Write(metadata) error = %v", err)
	}

	index := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(storedData) + SlotDescriptorSize + len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  metadataOffset,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
	}
	metaHash := sha256.Sum256(gzMeta)
	copy(index.MetadataChecksum[:], metaHash[:])

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], index.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("Write(trailer) error = %v", err)
	}

	return bundlePath
}

func buildTarArchiveWithDirAndFile(t *testing.T, dirName, fileName string, mode int64, content []byte) []byte {
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

	if err := tw.WriteHeader(&tar.Header{
		Typeflag: tar.TypeReg,
		Name:     filepath.Join(dirName, fileName),
		Mode:     mode,
		Size:     int64(len(content)),
	}); err != nil {
		t.Fatalf("WriteHeader(file) error = %v", err)
	}
	if _, err := tw.Write(content); err != nil {
		t.Fatalf("Write(file data) error = %v", err)
	}
	if err := tw.Close(); err != nil {
		t.Fatalf("Close(tar writer) error = %v", err)
	}

	return buf.Bytes()
}

func TestReadSlotDecompressesGzip(t *testing.T) {
	t.Parallel()

	raw := []byte("hello from gzip slot")
	stored := gzipData(t, raw)
	bundle := buildSingleSlotBundleForTests(t, stored, raw, []uint8{OP_GZIP}, SlotMetadata{
		ID:     "gzip-slot",
		Target: "{workenv}/payload.txt",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer reader.Close()

	got, err := reader.ReadSlot(0)
	if err != nil {
		t.Fatalf("ReadSlot() error = %v", err)
	}
	if string(got) != string(raw) {
		t.Fatalf("ReadSlot() = %q, want %q", string(got), string(raw))
	}
}

func TestReadSlotRejectsChecksumMismatchAndUnsupportedOperation(t *testing.T) {
	t.Parallel()

	mismatchBundle := buildSingleSlotBundleForTests(t, []byte("plain"), []byte("plain"), nil, SlotMetadata{
		ID:     "bad-checksum",
		Target: "{workenv}",
	}, 0, true)

	reader, err := NewReader(mismatchBundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer reader.Close()

	if _, err := reader.ReadSlot(0); err != ErrChecksumMismatch {
		t.Fatalf("ReadSlot() checksum mismatch error = %v, want %v", err, ErrChecksumMismatch)
	}

	unsupportedBundle := buildSingleSlotBundleForTests(t, []byte("compressed? no"), []byte("compressed? no"), []uint8{OP_BZIP2}, SlotMetadata{
		ID:     "unsupported-op",
		Target: "{workenv}",
	}, 0, false)

	reader2, err := NewReader(unsupportedBundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer reader2.Close()

	if _, err := reader2.ReadSlot(0); err == nil || !strings.Contains(err.Error(), "operation BZIP2 not yet implemented") {
		t.Fatalf("ReadSlot() unsupported-op error = %v, want BZIP2 unsupported", err)
	}
}

func TestExtractSlotWritesSingleFileAndTarball(t *testing.T) {
	t.Parallel()

	raw := []byte("single-file payload")
	fileBundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "file-slot",
		Target: "{workenv}/bin/app.txt",
	}, 0o755, false)

	reader, err := NewReader(fileBundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer reader.Close()

	destDir := filepath.Join(t.TempDir(), "single")
	extractedPath, err := reader.ExtractSlot(0, destDir)
	if err != nil {
		t.Fatalf("ExtractSlot(file) error = %v", err)
	}
	if extractedPath != filepath.Join(destDir, "bin", "app.txt") {
		t.Fatalf("ExtractSlot(file) path = %q, want %q", extractedPath, filepath.Join(destDir, "bin", "app.txt"))
	}

	content, err := os.ReadFile(extractedPath)
	if err != nil {
		t.Fatalf("ReadFile(extracted file) error = %v", err)
	}
	if string(content) != string(raw) {
		t.Fatalf("extracted file content = %q, want %q", string(content), string(raw))
	}

	info, err := os.Stat(extractedPath)
	if err != nil {
		t.Fatalf("Stat(extracted file) error = %v", err)
	}
	// Windows does not support Unix-style permission bits; skip executable-bit check.
	if runtime.GOOS != "windows" {
		if info.Mode().Perm()&0o111 == 0 {
			t.Fatalf("expected executable bit to be preserved, got mode %v", info.Mode().Perm())
		}
	}

	tarRaw := buildTarArchiveWithDirAndFile(t, "bundle", "payload.txt", 0o755, []byte("tar payload"))
	tarStored := gzipData(t, tarRaw)
	tarBundle := buildSingleSlotBundleForTests(t, tarStored, tarRaw, []uint8{OP_TAR, OP_GZIP}, SlotMetadata{
		ID:     "tar-slot",
		Target: "{workenv}",
	}, 0, false)

	reader2, err := NewReader(tarBundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer reader2.Close()

	tarDest := filepath.Join(t.TempDir(), "tar")
	extractedDir, err := reader2.ExtractSlot(0, tarDest)
	if err != nil {
		t.Fatalf("ExtractSlot(tar) error = %v", err)
	}
	if extractedDir != tarDest {
		t.Fatalf("ExtractSlot(tar) path = %q, want %q", extractedDir, tarDest)
	}

	tarContent, err := os.ReadFile(filepath.Join(tarDest, "bundle", "payload.txt"))
	if err != nil {
		t.Fatalf("ReadFile(tar payload) error = %v", err)
	}
	if string(tarContent) != "tar payload" {
		t.Fatalf("tar payload = %q, want %q", string(tarContent), "tar payload")
	}

	tarInfo, err := os.Stat(filepath.Join(tarDest, "bundle", "payload.txt"))
	if err != nil {
		t.Fatalf("Stat(tar payload) error = %v", err)
	}
	// Windows does not support Unix-style permission bits; skip executable-bit check.
	if runtime.GOOS != "windows" {
		if tarInfo.Mode().Perm()&0o111 == 0 {
			t.Fatalf("expected tar payload to stay executable, got mode %v", tarInfo.Mode().Perm())
		}
	}
}

func TestExtractSlotRejectsSymlink(t *testing.T) {
	t.Parallel()

	tarStored := buildGzippedTarWithSymlink("evil_link", "/etc/passwd")
	bundle := buildSingleSlotBundleForTests(t, tarStored, tarStored, []uint8{OP_TAR, OP_GZIP}, SlotMetadata{
		ID:     "symlink-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer reader.Close()

	if _, err := reader.ExtractSlot(0, t.TempDir()); err == nil || !strings.Contains(err.Error(), "symlink") {
		t.Fatalf("ExtractSlot(symlink) error = %v, want symlink rejection", err)
	}
}

func TestExtractSlotTarRespectsTargetSubdirectory(t *testing.T) {
	t.Parallel()

	tarRaw := buildTarArchiveWithDirAndFile(t, "images", "logo.txt", 0o644, []byte("logo"))
	tarStored := gzipData(t, tarRaw)
	bundle := buildSingleSlotBundleForTests(t, tarStored, tarRaw, []uint8{OP_TAR, OP_GZIP}, SlotMetadata{
		ID:     "assets-slot",
		Target: "assets",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader() error = %v", err)
	}
	defer reader.Close()

	destDir := filepath.Join(t.TempDir(), "targeted")
	extractedDir, err := reader.ExtractSlot(0, destDir)
	if err != nil {
		t.Fatalf("ExtractSlot(targeted tar) error = %v", err)
	}

	wantDir := filepath.Join(destDir, "assets")
	if extractedDir != wantDir {
		t.Fatalf("ExtractSlot(targeted tar) path = %q, want %q", extractedDir, wantDir)
	}

	got, err := os.ReadFile(filepath.Join(wantDir, "images", "logo.txt"))
	if err != nil {
		t.Fatalf("ReadFile(targeted tar payload) error = %v", err)
	}
	if string(got) != "logo" {
		t.Fatalf("targeted tar payload = %q, want %q", string(got), "logo")
	}
}
