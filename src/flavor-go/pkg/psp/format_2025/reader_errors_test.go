package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// buildMinimalBundleWithMetadata constructs a minimal valid PSPF bundle (no slots)
// whose metadata block is the gzip-compressed JSON provided. The caller controls
// whether the magic-trailer emoji bytes are correct.
func buildMinimalBundleWithMetadata(t *testing.T, gzMeta []byte, startEmoji, endEmoji []byte) string {
	t.Helper()

	f, err := os.CreateTemp(t.TempDir(), "pspf-minimal-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	var offset uint64

	metaOffset := offset
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}
	offset += uint64(len(gzMeta))

	metaHash := sha256.Sum256(gzMeta)

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     offset + uint64(MagicTrailerSize),
		MetadataOffset:  metaOffset,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: offset,
	}
	copy(idx.MetadataChecksum[:], metaHash[:])

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], startEmoji)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], endEmoji)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	return f.Name()
}

// buildValidMinimalBundle creates a fully valid minimal bundle (no slots).
func buildValidMinimalBundle(t *testing.T) string {
	t.Helper()

	metaJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)
	return buildMinimalBundleWithMetadata(t, gzMeta, PackageEmojiBytes, MagicWandEmojiBytes)
}

// TestReadMagicTrailerFileTooShort verifies that ReadMagicTrailer returns an error
// when the file is smaller than MagicTrailerSize.
func TestReadMagicTrailerFileTooShort(t *testing.T) {
	t.Parallel()

	f, err := os.CreateTemp(t.TempDir(), "pspf-short-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	// Write fewer bytes than MagicTrailerSize.
	if _, err := f.Write(bytes.Repeat([]byte{0x00}, MagicTrailerSize-1)); err != nil {
		t.Fatalf("Write: %v", err)
	}
	_ = f.Close()

	reader, err := NewReader(f.Name())
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadMagicTrailer()
	if err == nil {
		t.Fatal("expected error for file smaller than MagicTrailerSize, got nil")
	}
}

// TestReadMagicTrailerWrongStartEmoji verifies that ReadMagicTrailer returns an error
// when the start emoji bytes are wrong.
func TestReadMagicTrailerWrongStartEmoji(t *testing.T) {
	t.Parallel()

	metaJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)
	badStart := []byte{0x00, 0x00, 0x00, 0x00}
	bundlePath := buildMinimalBundleWithMetadata(t, gzMeta, badStart, MagicWandEmojiBytes)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadMagicTrailer()
	if err == nil {
		t.Fatal("expected error for wrong start emoji, got nil")
	}
}

// TestReadMagicTrailerWrongEndEmoji verifies that ReadMagicTrailer returns an error
// when the end emoji bytes are wrong.
func TestReadMagicTrailerWrongEndEmoji(t *testing.T) {
	t.Parallel()

	metaJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)
	badEnd := []byte{0x00, 0x00, 0x00, 0x00}
	bundlePath := buildMinimalBundleWithMetadata(t, gzMeta, PackageEmojiBytes, badEnd)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadMagicTrailer()
	if err == nil {
		t.Fatal("expected error for wrong end emoji, got nil")
	}
}

// TestReadIndexWrongFormatVersion verifies ReadIndex fails when the index contains
// an unexpected format version.
func TestReadIndexWrongFormatVersion(t *testing.T) {
	t.Parallel()

	f, err := os.CreateTemp(t.TempDir(), "pspf-badver-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	metaJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}

	// Build an index with a wrong FormatVersion.
	idx := &PSPFIndex{
		FormatVersion:   0xDEADBEEF, // wrong version
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: uint64(len(gzMeta)),
	}
	metaHash := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], metaHash[:])

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	reader, err := NewReader(f.Name())
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadIndex()
	if err == nil {
		t.Fatal("expected error for wrong format version, got nil")
	}
}

// TestReadMetadataNonGzip verifies that ReadMetadata returns an error when the
// metadata block contains non-gzip data.
func TestReadMetadataNonGzip(t *testing.T) {
	t.Parallel()

	// Use plain JSON (not gzip-compressed) as the metadata block.
	plainJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	// Build a bundle but inject a non-gzip metadata block.
	// We need a valid MagicTrailer so ReadIndex succeeds, but the metadata is plain JSON.
	f, err := os.CreateTemp(t.TempDir(), "pspf-nongzip-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(plainJSON); err != nil {
		t.Fatalf("write metadata: %v", err)
	}

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(plainJSON) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(plainJSON)),
		SlotTableOffset: uint64(len(plainJSON)),
	}
	metaHash := sha256.Sum256(plainJSON)
	copy(idx.MetadataChecksum[:], metaHash[:])

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	reader, err := NewReader(f.Name())
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadMetadata()
	if err == nil {
		t.Fatal("expected gzip error for non-gzip metadata, got nil")
	}
}

// TestReadMetadataArchiveChecksumMismatch verifies that ReadMetadataArchive returns
// ErrChecksumMismatch when the stored metadata checksum doesn't match the data.
func TestReadMetadataArchiveChecksumMismatch(t *testing.T) {
	t.Parallel()

	f, err := os.CreateTemp(t.TempDir(), "pspf-badcksum-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	metaJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: uint64(len(gzMeta)),
	}
	// Deliberately set wrong checksum (all zeros ≠ actual hash).
	// MetadataChecksum stays zero-filled.

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	reader, err := NewReader(f.Name())
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadMetadataArchive()
	if err != ErrChecksumMismatch {
		t.Fatalf("expected ErrChecksumMismatch, got %v", err)
	}
}

// TestReadMetadataArchiveReturnsRawBytesForNonGzip verifies that ReadMetadataArchive
// returns the raw (non-gzip) bytes without error when the checksum matches — this
// exercises the path where isTarball would be false for the raw metadata.
func TestReadMetadataArchiveReturnsRawBytesWhenChecksumMatches(t *testing.T) {
	t.Parallel()

	// A valid bundle built by buildValidMinimalBundle has correct gzip metadata
	// and a matching checksum — ReadMetadataArchive should return the raw gzip bytes.
	bundlePath := buildValidMinimalBundle(t)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	raw, err := reader.ReadMetadataArchive()
	if err != nil {
		t.Fatalf("ReadMetadataArchive: %v", err)
	}
	if len(raw) == 0 {
		t.Fatal("expected non-empty metadata archive bytes")
	}
	// Confirm the returned bytes are valid gzip.
	gr, err := gzip.NewReader(bytes.NewReader(raw))
	if err != nil {
		t.Fatalf("gzip.NewReader on archive bytes: %v", err)
	}
	defer func() { _ = gr.Close() }()
}

// TestIsTarballDirectly exercises isTarball directly with tar and non-tar input.
func TestIsTarballDirectly(t *testing.T) {
	t.Parallel()

	// Build a real tar archive (POSIX/ustar format via Go's archive/tar).
	tarData := buildTarArchiveWithFile(t, "hello.txt", 0o644, []byte("hello"))
	if !isTarball(tarData) {
		t.Fatal("expected isTarball to return true for tar data")
	}

	// Plain JSON is not a tarball.
	if isTarball([]byte(`{"key":"value"}`)) {
		t.Fatal("expected isTarball to return false for JSON data")
	}

	// Empty data is not a tarball.
	if isTarball([]byte{}) {
		t.Fatal("expected isTarball to return false for empty data")
	}

	// Data shorter than 512 bytes is not a tarball.
	short := bytes.Repeat([]byte{0x00}, 300)
	if isTarball(short) {
		t.Fatal("expected isTarball to return false for short data")
	}

	// Synthesise a GNU oldgnu-style tar header: at offset 257 place "ustar  \x00"
	// (8 chars: u s t a r space space NUL).
	gnuTar := make([]byte, 512)
	copy(gnuTar[257:265], []byte("ustar  \x00"))
	if !isTarball(gnuTar) {
		t.Fatal("expected isTarball to return true for GNU tar magic at offset 257")
	}
}

// TestExtractSlotFailsWhenMetadataReadFails verifies that ExtractSlot propagates
// an error if the bundle has corrupt metadata (non-gzip metadata block).
func TestExtractSlotFailsWhenMetadataReadFails(t *testing.T) {
	t.Parallel()

	// Build a bundle whose metadata block is plain JSON (not gzip).
	// ReadMetadata will fail with a gzip error, so ExtractSlot must return an error.
	f, err := os.CreateTemp(t.TempDir(), "pspf-extract-fail-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	plainJSON := []byte(`{"package":{"name":"bad"},"slots":[]}`)
	if _, err := f.Write(plainJSON); err != nil {
		t.Fatalf("write: %v", err)
	}

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(plainJSON) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(plainJSON)),
		SlotTableOffset: uint64(len(plainJSON)),
	}
	metaHash := sha256.Sum256(plainJSON)
	copy(idx.MetadataChecksum[:], metaHash[:])

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	reader, err := NewReader(f.Name())
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error from ExtractSlot when metadata is corrupt, got nil")
	}
}

// TestExtractSlotFailsWhenOutOfRange verifies ExtractSlot returns ErrInvalidSlotIndex
// for an out-of-range slot index on a valid bundle.
func TestExtractSlotFailsWhenOutOfRange(t *testing.T) {
	t.Parallel()

	bundlePath := buildValidMinimalBundle(t)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Bundle has zero slots; requesting slot 0 should return ErrInvalidSlotIndex.
	_, err = reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected ErrInvalidSlotIndex for out-of-range slot, got nil")
	}
}

// TestExtractSlotSingleFileWithoutTargetSubdir exercises the path where a non-tar
// slot is written directly to a slot-specific subdirectory (empty/dot target).
func TestExtractSlotSingleFileWithoutTargetSubdir(t *testing.T) {
	t.Parallel()

	raw := []byte("bare-file content")
	// Use a target of "{workenv}" (maps to the destDir with a slot-named subdir).
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "bare-slot",
		Target: "{workenv}",
	}, 0o644, false)

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
	if extractedPath == "" {
		t.Fatal("expected non-empty extracted path")
	}
}

// TestReadOpenFailsOnMissingFile verifies that Open (called by ReadMagicTrailer)
// returns an error for a non-existent file path.
func TestReadOpenFailsOnMissingFile(t *testing.T) {
	t.Parallel()

	reader, err := NewReader(filepath.Join(t.TempDir(), "nonexistent.pspf"))
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadMagicTrailer()
	if err == nil {
		t.Fatal("expected error for missing file, got nil")
	}
}

// TestReadSlotRejectsAES256GCM verifies that ReadSlot returns an error for a
// slot encoded with OP_AES256_GCM (encryption not yet implemented).
func TestReadSlotRejectsAES256GCM(t *testing.T) {
	t.Parallel()

	raw := []byte("secret-data")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, []uint8{OP_AES256_GCM}, SlotMetadata{
		ID:     "encrypted-slot",
		Target: "{workenv}/secret.bin",
	}, 0o600, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadSlot(0)
	if err == nil || err.Error() == "" {
		t.Fatal("expected error for AES256_GCM operation, got nil or empty")
	}
}

// TestReadSlotRejectsZSTD verifies that ReadSlot returns an error for a slot
// encoded with OP_ZSTD (not yet implemented).
func TestReadSlotRejectsZSTD(t *testing.T) {
	t.Parallel()

	raw := []byte("zstd data")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, []uint8{OP_ZSTD}, SlotMetadata{
		ID:     "zstd-slot",
		Target: "{workenv}/zstd.bin",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error for ZSTD operation, got nil")
	}
}

// TestReadMetadataWithValidBundle exercises the full ReadMetadata happy path
// to confirm metadata fields are decoded correctly.
func TestReadMetadataWithValidBundle(t *testing.T) {
	t.Parallel()

	type minMeta struct {
		Package struct {
			Name    string `json:"name"`
			Version string `json:"version"`
		} `json:"package"`
		Slots []interface{} `json:"slots"`
	}
	var m minMeta
	m.Package.Name = "coverage-test"
	m.Package.Version = "9.9.9"
	m.Slots = []interface{}{}
	metaJSON, err := json.Marshal(m)
	if err != nil {
		t.Fatalf("Marshal: %v", err)
	}
	gzMeta := gzipData(t, metaJSON)
	bundlePath := buildMinimalBundleWithMetadata(t, gzMeta, PackageEmojiBytes, MagicWandEmojiBytes)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	meta, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}
	if meta.Package.Name != "coverage-test" {
		t.Fatalf("Package.Name = %q, want %q", meta.Package.Name, "coverage-test")
	}
}
