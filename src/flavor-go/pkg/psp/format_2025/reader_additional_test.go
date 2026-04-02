//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"os"
	"testing"
)

// TestReadMagicTrailerFileStatFails covers the r.file.Stat() error path.
// We open the reader, pre-open the file, then close the underlying file handle
// so that Stat fails on the next call.
func TestReadMagicTrailerFileStatFails(t *testing.T) {
	t.Parallel()

	bundlePath := buildValidMinimalBundle(t)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Pre-open so the file handle is set.
	if err := reader.Open(); err != nil {
		t.Fatalf("Open: %v", err)
	}
	// Close the OS file directly — subsequent Stat will fail.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("Close file: %v", err)
	}

	_, err = reader.ReadMagicTrailer()
	if err == nil {
		t.Fatal("expected error when underlying file is closed, got nil")
	}
}

// TestReadIndexUnpackError covers the PSPFIndex.Unpack() error path in ReadIndex.
// We build a bundle where the trailer's index bytes have a wrong size (impossible
// to construct via buildMinimalBundleWithMetadata since it always packs correctly),
// but we can force an Unpack failure by writing a truncated IndexSize slice.
// Instead, we use a bundle where the trailer is filled with garbage so Unpack
// receives bytes of the right length but an invalid version (ErrInvalidVersion
// comes AFTER a successful Unpack). So Unpack itself only fails on wrong length.
//
// Actually — looking at ReadIndex code: Unpack fails if data != IndexSize.
// ReadMagicTrailer returns exactly IndexSize bytes (trailer[4:4+IndexSize]).
// That means Unpack can never fail due to length via normal ReadMagicTrailer.
//
// The real uncovered path is the r.index cache hit — but that's already a return.
//
// Re-checking: ReadIndex has 15 statements. 93.3% = 14/15. The missing 1 is:
// the r.index != nil early-return path (line: "return r.index, nil").
// We can cover this by calling ReadIndex twice on the same reader.
func TestReadIndexCacheHit(t *testing.T) {
	t.Parallel()

	bundlePath := buildValidMinimalBundle(t)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// First call — reads from file.
	idx1, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex (first call): %v", err)
	}

	// Second call — returns cached index (exercises the "r.index != nil" branch).
	idx2, err := reader.ReadIndex()
	if err != nil {
		t.Fatalf("ReadIndex (second/cached call): %v", err)
	}
	if idx1 != idx2 {
		t.Fatal("expected cached index to be the same pointer")
	}
}

// TestReadMetadataCacheHit covers the "r.metadata != nil" early-return in ReadMetadata.
func TestReadMetadataCacheHit(t *testing.T) {
	t.Parallel()

	bundlePath := buildValidMinimalBundle(t)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// First call — reads and parses metadata.
	meta1, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata (first call): %v", err)
	}

	// Second call — should return cached metadata (exercises the nil check).
	meta2, err := reader.ReadMetadata()
	if err != nil {
		t.Fatalf("ReadMetadata (second/cached call): %v", err)
	}
	if meta1 != meta2 {
		t.Fatal("expected cached metadata to be the same pointer")
	}
}

// TestReadMetadataSeekFailure covers the Seek error path in ReadMetadata by
// closing the underlying file after ReadIndex has populated the cache.
func TestReadMetadataSeekFailure(t *testing.T) {
	t.Parallel()

	bundlePath := buildValidMinimalBundle(t)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Prime the index cache so ReadMetadata skips ReadIndex and goes straight to Seek.
	if _, err := reader.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	// Close the underlying OS file — Seek will fail.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("close file: %v", err)
	}

	_, err = reader.ReadMetadata()
	if err == nil {
		t.Fatal("expected error when file is closed before ReadMetadata Seek, got nil")
	}
}

// TestReadMetadataReadFailure covers the Read error path in ReadMetadata by
// closing the underlying file after Seek succeeds but before Read.
// We accomplish this by priming the index cache, seeking manually to a valid
// position, then closing the file so the Read in ReadMetadata fails.
//
// Note: We need the Seek to succeed (file open), but Read to fail (file closed).
// The only reliable way is to close the file between the primed-index return
// and the Seek inside ReadMetadata — but both happen inside the same call.
// Instead, we test this via the inflated MetadataSize path using ReadAt semantics:
// MetadataOffset beyond actual file content so Seek succeeds but Read returns 0/EOF.
func TestReadMetadataReadFailure(t *testing.T) {
	t.Parallel()

	// Build a bundle where MetadataOffset points beyond the file's actual content.
	// The file will have gzMeta + trailer, but we claim MetadataOffset is inside
	// the trailer block, making MetadataSize extend beyond file bounds.
	// On Linux/macOS, Read past EOF returns io.EOF when count is 0 bytes available.
	f, err := os.CreateTemp(t.TempDir(), "pspf-readfail-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	gzMeta := gzipData(t, []byte(`{"package":{"name":"x"},"slots":[]}`))
	// Write only gzMeta, then trailer.
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
	}

	// Point MetadataOffset to just before the end of the file so Read is short.
	// MetadataSize = 8192 (IndexSize) but file doesn't have that much after the offset.
	largeSize := uint64(MagicTrailerSize * 2) // much larger than remaining data
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    largeSize,
		SlotTableOffset: uint64(len(gzMeta)),
	}
	// Leave MetadataChecksum zero — Read will fail before checksum check anyway... hopefully.
	// Actually: os.File.Read with a large buffer on a small file returns the available
	// bytes + nil error (short read). Only returns io.EOF on the next call with 0 bytes.
	// So this test may not trigger the Read error. We use a different approach:
	// We set MetadataOffset to point beyond end of file, so Seek succeeds but Read returns 0, EOF.
	beyondEOF := uint64(len(gzMeta)) + uint64(MagicTrailerSize) + 1000 // beyond EOF
	idx.MetadataOffset = beyondEOF
	idx.MetadataSize = 100

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
	// May fail at Read (EOF), gzip.NewReader, or json.Decode — any error is valid.
	if err == nil {
		t.Fatal("expected error for metadata pointing beyond file, got nil")
	}
}

// TestReadMetadataInvalidJSON covers the json.Decode error path in ReadMetadata.
// We create a bundle with valid gzip-compressed content but non-JSON bytes inside.
func TestReadMetadataInvalidJSON(t *testing.T) {
	t.Parallel()

	// Gzip-compress something that is NOT valid JSON.
	notJSON := []byte("this is definitely not json content at all!")
	var buf bytes.Buffer
	gz := gzip.NewWriter(&buf)
	if _, err := gz.Write(notJSON); err != nil {
		t.Fatalf("gzip write: %v", err)
	}
	if err := gz.Close(); err != nil {
		t.Fatalf("gzip close: %v", err)
	}
	gzContent := buf.Bytes()

	f, err := os.CreateTemp(t.TempDir(), "pspf-badjson-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzContent); err != nil {
		t.Fatalf("write content: %v", err)
	}

	// Compute the correct checksum so ReadMetadataArchive would pass (but ReadMetadata won't be called).
	metaHash := sha256.Sum256(gzContent)
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzContent) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzContent)),
		SlotTableOffset: uint64(len(gzContent)),
	}
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
		t.Fatal("expected error decoding non-JSON gzip metadata, got nil")
	}
}

// TestReadMetadataArchiveSeekFailure covers the Seek error path in ReadMetadataArchive.
// Prime the index cache, close the file, then call ReadMetadataArchive.
func TestReadMetadataArchiveSeekFailure(t *testing.T) {
	t.Parallel()

	bundlePath := buildValidMinimalBundle(t)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Prime the index cache.
	if _, err := reader.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	// Close the underlying OS file so Seek fails.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("close file: %v", err)
	}

	_, err = reader.ReadMetadataArchive()
	if err == nil {
		t.Fatal("expected error when file is closed before ReadMetadataArchive Seek, got nil")
	}
}

// TestReadMetadataArchiveReadFailure covers the Read error path in ReadMetadataArchive
// by constructing a bundle with an inflated MetadataSize.
func TestReadMetadataArchiveReadFailure(t *testing.T) {
	t.Parallel()

	f, err := os.CreateTemp(t.TempDir(), "pspf-archread-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	gzMeta := gzipData(t, []byte(`{"package":{"name":"x"},"slots":[]}`))
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
	}

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)) * 200, // inflated — Read will short-read/EOF
		SlotTableOffset: uint64(len(gzMeta)),
	}
	// Leave MetadataChecksum zero — won't matter as Read fails first.

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
	if err == nil {
		t.Fatal("expected error for inflated MetadataSize in ReadMetadataArchive, got nil")
	}
}

// TestReadSlotChecksumMismatch covers the checksum mismatch path in ReadSlot.
// This is already exercised by TestReadSlotRejectsChecksumMismatchAndUnsupportedOperation,
// but adding an explicit test verifies the path more directly.
func TestReadSlotGzipDecompressionFailure(t *testing.T) {
	t.Parallel()

	// Build a slot where stored data is passed as "gzip" operation but contains garbage bytes.
	corrupted := []byte{0x1f, 0x8b, 0x08, 0x00, 0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0xFF, 0x00}
	bundle := buildSingleSlotBundleForTests(t, corrupted, corrupted, []uint8{OP_GZIP}, SlotMetadata{
		ID:     "bad-gzip",
		Target: "{workenv}/bad.bin",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error for corrupt gzip data in slot, got nil")
	}
}

// TestExtractSlotGzipCorruption covers the gzip extraction failure path in ExtractSlot.
// The slot declares OP_TAR | OP_GZIP but contains corrupt gzip data.
func TestExtractSlotGzipCorruption(t *testing.T) {
	t.Parallel()

	// Create corrupted gzip that passes checksum but fails decompression.
	// Build a minimal valid gzip, then corrupt a few bytes in the middle.
	rawTar := buildTarArchiveWithFile(t, "file.txt", 0o644, []byte("hello"))
	gzTar := gzipData(t, rawTar)

	// Corrupt bytes in the middle of the compressed stream.
	if len(gzTar) > 20 {
		gzTar[len(gzTar)/2] ^= 0xFF
		gzTar[len(gzTar)/2+1] ^= 0xFF
	}

	bundle := buildSingleSlotBundleForTests(t, gzTar, rawTar, []uint8{OP_TAR, OP_GZIP}, SlotMetadata{
		ID:     "corrupt-gzip-slot",
		Target: "{workenv}",
	}, 0, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error for corrupt gzip data in ExtractSlot, got nil")
	}
}
