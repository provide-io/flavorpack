package format_2025

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"testing"
)

// ── ReadSlot: seek failure after ReadIndex ────────────────────────────────────

// TestReadSlotSeekFailureAfterReadIndex covers the seek error path in ReadSlot
// (reader_slots.go:30-33) by closing the file after priming the index cache.
func TestReadSlotSeekFailureAfterReadIndex(t *testing.T) {
	t.Parallel()

	raw := []byte("slot data for seek failure test")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "seek-fail-slot",
		Target: "{workenv}/file.bin",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Prime index cache.
	if _, err := reader.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	// Close the file so the seek inside ReadSlot fails.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("close file: %v", err)
	}

	_, err = reader.ReadSlot(0)
	if err == nil {
		t.Fatal("expected error when ReadSlot seek fails (file closed), got nil")
	}
}

// ── ExtractSlot: failure path after ReadMetadata ─────────────────────────────

// TestExtractSlotSeekFailureAfterReadMetadata covers ExtractSlot's seek failure
// path (reader_slots.go:174-176) when reading the slot table after ReadMetadata.
func TestExtractSlotSeekFailureAfterReadMetadata(t *testing.T) {
	t.Parallel()

	raw := []byte("extract slot seek failure test data")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "ext-seek-slot",
		Target: "{workenv}/file.bin",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Prime metadata cache.
	if _, err := reader.ReadMetadata(); err != nil {
		t.Fatalf("ReadMetadata: %v", err)
	}

	// Close the file so ExtractSlot's internal ReadSlot seek fails.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("close file: %v", err)
	}

	_, err = reader.ExtractSlot(0, t.TempDir())
	if err == nil {
		t.Fatal("expected error when ExtractSlot's ReadSlot fails after file close, got nil")
	}
}

// ── ReadMetadataArchive: seek failure ─────────────────────────────────────────

// TestReadMetadataArchiveSeekFailure2 covers the file.Seek error path in
// ReadMetadataArchive (reader.go:198-200) by closing the file after ReadIndex.
func TestReadMetadataArchiveSeekFailure2(t *testing.T) {
	t.Parallel()

	raw := []byte("metadata archive seek failure payload")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "arch-seek-slot",
		Target: "{workenv}/file.bin",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Prime the index cache so ReadMetadataArchive skips ReadIndex.
	if _, err := reader.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	// Close the file so Seek in ReadMetadataArchive fails.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("close file: %v", err)
	}

	_, err = reader.ReadMetadataArchive()
	if err == nil {
		t.Fatal("expected error when seek fails in ReadMetadataArchive, got nil")
	}
}

// TestReadMetadataArchiveChecksumMismatch2 covers the ErrChecksumMismatch path
// in ReadMetadataArchive (reader.go:209-211) with a zero-filled checksum.
func TestReadMetadataArchiveChecksumMismatch2(t *testing.T) {
	t.Parallel()

	gzMeta := gzipData(t, []byte(`{"package":{"name":"cs-mismatch"},"slots":[]}`))

	f, err := os.CreateTemp(t.TempDir(), "pspf-rma-csmismatch-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
	}

	// Leave MetadataChecksum as all-zeros — guaranteed mismatch.
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: uint64(len(gzMeta)),
	}

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
		t.Fatal("expected ErrChecksumMismatch from ReadMetadataArchive, got nil")
	}
}

// ── ReadIndex: version mismatch ───────────────────────────────────────────────

// TestReadIndexVersionMismatch covers the ErrInvalidVersion path in ReadIndex
// (reader.go:139-141).
func TestReadIndexVersionMismatch(t *testing.T) {
	t.Parallel()

	gzMeta := gzipData(t, []byte(`{"package":{"name":"bad-version"},"slots":[]}`))

	f, err := os.CreateTemp(t.TempDir(), "pspf-badver-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
	}

	idx := &PSPFIndex{
		FormatVersion:   0xDEADBEEF, // wrong version
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: uint64(len(gzMeta)),
	}
	mh := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], mh[:])

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
		t.Fatal("expected ErrInvalidVersion, got nil")
	}
}

// ── VerifyAttestationSbomDigest: read descriptor beyond EOF ──────────────────

// TestVerifyAttestationSbomDigestReadDescriptorBeyondEOF covers the
// "reading slot descriptor" error path in VerifyAttestationSbomDigest
// (reader_verify.go:165-167) when the slot table is placed beyond file end
// so Read returns EOF.
func TestVerifyAttestationSbomDigestReadDescriptorBeyondEOF(t *testing.T) {
	t.Parallel()

	gzMeta := gzipData(t, []byte(`{"package":{"name":"seek-beyond"},"slots":[]}`))

	f, err := os.CreateTemp(t.TempDir(), "pspf-att-seekbeyond-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}

	metaHash := sha256.Sum256(gzMeta)
	fakeDigest := hex.EncodeToString(metaHash[:])

	// Set SlotTableOffset well past the end of file so Read returns EOF
	// when trying to read the slot descriptor bytes.
	beyondEOF := uint64(len(gzMeta)) + uint64(MagicTrailerSize) + 1024

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: beyondEOF,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
	}
	copy(idx.MetadataChecksum[:], metaHash[:])
	copy(idx.AttestationSbomDigest[:], []byte(fakeDigest))

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

	err = reader.VerifyAttestationSbomDigest()
	if err == nil {
		t.Fatal("expected error when slot descriptor is beyond file end, got nil")
	}
}

// ── VerifyAttestationPolicyHash: policy absent in metadata ───────────────────

// TestVerifyAttestationPolicyHashPolicyAbsentInMetadata covers the "no policy"
// error path in VerifyAttestationPolicyHash (reader_verify.go:248-250):
// when AttestationPolicyHash is non-zero but metadata.PolicyRaw is empty.
func TestVerifyAttestationPolicyHashPolicyAbsentInMetadata(t *testing.T) {
	t.Parallel()

	// Build metadata JSON without a "policy" field.
	gzMeta := gzipData(t, []byte(`{"package":{"name":"nopol","version":"1.0.0"},"slots":[]}`))

	metaHash := sha256.Sum256(gzMeta)
	fakeHash := hex.EncodeToString(metaHash[:])

	f, err := os.CreateTemp(t.TempDir(), "pspf-nopol-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
	}

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: uint64(len(gzMeta)),
	}
	copy(idx.MetadataChecksum[:], metaHash[:])
	copy(idx.AttestationPolicyHash[:], []byte(fakeHash))

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

	err = reader.VerifyAttestationPolicyHash()
	if err == nil {
		t.Fatal("expected error when policy hash set but metadata has no policy, got nil")
	}
}

// ── VerifyAttestationPolicyHash: hash mismatch ───────────────────────────────

// TestVerifyAttestationPolicyHashMismatch covers the hash mismatch path
// in VerifyAttestationPolicyHash (reader_verify.go:264-266).
func TestVerifyAttestationPolicyHashMismatch(t *testing.T) {
	t.Parallel()

	// Build metadata with a real policy object.
	type metaShape struct {
		Package struct {
			Name    string `json:"name"`
			Version string `json:"version"`
		} `json:"package"`
		Slots  []interface{}          `json:"slots"`
		Policy map[string]interface{} `json:"policy,omitempty"`
	}

	m := metaShape{
		Slots:  []interface{}{},
		Policy: map[string]interface{}{"allow_network": false, "version": 1},
	}
	m.Package.Name = "hash-mismatch-test"
	m.Package.Version = "1.0.0"

	metaJSON, err := json.Marshal(m)
	if err != nil {
		t.Fatalf("json.Marshal: %v", err)
	}
	gzMeta := gzipData(t, metaJSON)

	// Store a wrong policy hash (64 hex 'a' chars).
	wrongHash := bytes.Repeat([]byte("a"), 64)

	f, err := os.CreateTemp(t.TempDir(), "pspf-hashmismatch-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}

	metaHash := sha256.Sum256(gzMeta)
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: uint64(len(gzMeta)),
	}
	copy(idx.MetadataChecksum[:], metaHash[:])
	copy(idx.AttestationPolicyHash[:], wrongHash)

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

	err = reader.VerifyAttestationPolicyHash()
	if err == nil {
		t.Fatal("expected error for policy hash mismatch, got nil")
	}
}
