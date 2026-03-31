package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"os"
	"testing"
)

// gzipData compresses src with gzip and returns the result.
func gzipData(t *testing.T, src []byte) []byte {
	t.Helper()
	var buf bytes.Buffer
	w := gzip.NewWriter(&buf)
	if _, err := w.Write(src); err != nil {
		t.Fatalf("gzip write: %v", err)
	}
	if err := w.Close(); err != nil {
		t.Fatalf("gzip close: %v", err)
	}
	return buf.Bytes()
}

// buildAttestationBundle writes a minimal valid PSPF/2025 bundle where:
//   - slotContents is the raw bytes to place in the attestation slot (lifecycle=11)
//   - digestHex is the hex string to store in index.AttestationSbomDigest
//     (pass "" to leave the field all-zero, i.e. absent)
//
// The returned path is in a temp dir managed by t.
func buildAttestationBundle(t *testing.T, slotContents []byte, digestHex string) string {
	t.Helper()

	f, err := os.CreateTemp(t.TempDir(), "pspf-*.bin")
	if err != nil {
		t.Fatalf("create temp file: %v", err)
	}
	defer f.Close()

	var offset uint64

	// Write slot data.
	slotOffset := offset
	slotSize := uint64(len(slotContents))
	if _, err := f.Write(slotContents); err != nil {
		t.Fatalf("write slot data: %v", err)
	}
	offset += slotSize

	// Build slot descriptor (lifecycle = LifecycleAttestation = 11).
	slotHash := sha256.Sum256(slotContents)
	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName("attestation"),
		Offset:       slotOffset,
		Size:         slotSize,
		OriginalSize: slotSize,
		Operations:   0,
		Checksum:     binary.LittleEndian.Uint64(slotHash[:8]),
		Purpose:      PurposeData,
		Lifecycle:    LifecycleAttestation,
	}

	// Write slot table.
	slotTableOffset := offset
	if _, err := f.Write(desc.Pack()); err != nil {
		t.Fatalf("write slot descriptor: %v", err)
	}
	offset += SlotDescriptorSize

	// Write minimal gzip-compressed JSON metadata.
	metaJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)
	metaOffset := offset
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}
	offset += uint64(len(gzMeta))

	// The MagicTrailer follows immediately.
	trailerOffset := offset

	// Build index.
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     trailerOffset + uint64(MagicTrailerSize),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
		MetadataOffset:  metaOffset,
		MetadataSize:    uint64(len(gzMeta)),
	}

	mh := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], mh[:])

	if digestHex != "" {
		copy(idx.AttestationSbomDigest[:], []byte(digestHex))
	}

	// Compute Adler-32 index checksum.
	idxBytes := idx.Pack()
	// IndexChecksum of 0 is accepted by the reader (skip verification).
	_ = idxBytes

	// Write MagicTrailer.
	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write MagicTrailer: %v", err)
	}

	return f.Name()
}

// TestVerifyAttestationSbomDigest_Match checks that verification passes when the
// stored digest matches the actual slot content.
func TestVerifyAttestationSbomDigest_Match(t *testing.T) {
	slotContent := []byte("sbom+provenance content for testing")

	// Compute the correct digest.
	h := sha256.Sum256(slotContent)
	correctHex := hex.EncodeToString(h[:])

	bundlePath := buildAttestationBundle(t, slotContent, correctHex)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	if err := reader.VerifyAttestationSbomDigest(); err != nil {
		t.Errorf("expected no error for matching digest, got: %v", err)
	}
}

// TestVerifyAttestationSbomDigest_Mismatch checks that verification fails when the
// stored digest does not match the slot content.
func TestVerifyAttestationSbomDigest_Mismatch(t *testing.T) {
	slotContent := []byte("original sbom content")
	wrongHex := hex.EncodeToString(sha256.New().Sum(nil)) // SHA-256 of empty string

	bundlePath := buildAttestationBundle(t, slotContent, wrongHex)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	err = reader.VerifyAttestationSbomDigest()
	if err == nil {
		t.Error("expected error for mismatched digest, got nil")
	}
}

// TestVerifyAttestationSbomDigest_NoDigest checks that when no digest is stored and
// there is an attestation slot, verification is skipped (backwards-compat).
func TestVerifyAttestationSbomDigest_NoDigest(t *testing.T) {
	slotContent := []byte("some attestation data")

	// Pass "" so the digest field stays all-zero.
	bundlePath := buildAttestationBundle(t, slotContent, "")

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	if err := reader.VerifyAttestationSbomDigest(); err != nil {
		t.Errorf("expected no error when digest field is absent, got: %v", err)
	}
}

// TestVerifyAttestationSbomDigest_DigestPresentNoSlot checks that when a digest is
// stored but no attestation slot exists, verification fails (fail-closed).
func TestVerifyAttestationSbomDigest_DigestPresentNoSlot(t *testing.T) {
	// Build a bundle with no attestation slot but inject a digest.
	f, err := os.CreateTemp(t.TempDir(), "pspf-*.bin")
	if err != nil {
		t.Fatalf("create temp file: %v", err)
	}
	defer f.Close()

	// Write a single non-attestation slot (lifecycle = LifecycleRuntime = 2).
	slotContent := []byte("payload")
	slotHash := sha256.Sum256(slotContent)
	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName("payload"),
		Offset:       0,
		Size:         uint64(len(slotContent)),
		OriginalSize: uint64(len(slotContent)),
		Operations:   0,
		Checksum:     binary.LittleEndian.Uint64(slotHash[:8]),
		Purpose:      PurposeData,
		Lifecycle:    LifecycleRuntime,
	}
	if _, err := f.Write(slotContent); err != nil {
		t.Fatalf("write slot data: %v", err)
	}
	var offset uint64 = uint64(len(slotContent))

	slotTableOffset := offset
	if _, err := f.Write(desc.Pack()); err != nil {
		t.Fatalf("write slot descriptor: %v", err)
	}
	offset += SlotDescriptorSize

	metaJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)
	metaOffset := offset
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}
	offset += uint64(len(gzMeta))

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     offset + uint64(MagicTrailerSize),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
		MetadataOffset:  metaOffset,
		MetadataSize:    uint64(len(gzMeta)),
	}
	mh := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], mh[:])

	// Store a non-zero digest (points to a slot that doesn't exist).
	nonexistentHash := sha256.Sum256([]byte("nonexistent"))
	fakeDigest := hex.EncodeToString(nonexistentHash[:])
	copy(idx.AttestationSbomDigest[:], []byte(fakeDigest))

	idxBytes := idx.Pack()
	// IndexChecksum of 0 is accepted by the reader (skip verification).
	_ = idxBytes

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write MagicTrailer: %v", err)
	}
	bundlePath := f.Name()
	f.Close()

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer reader.Close()

	err = reader.VerifyAttestationSbomDigest()
	if err == nil {
		t.Error("expected error when digest is present but no attestation slot found, got nil")
	}
}
