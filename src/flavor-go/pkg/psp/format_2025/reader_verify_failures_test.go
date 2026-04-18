// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"os"
	"testing"
)

// TestVerifyMagicTrailerFailsOnWrongStartEmoji verifies that VerifyMagicTrailer
// returns ErrInvalidEmojiMagic when the start emoji bytes are wrong.
func TestVerifyMagicTrailerFailsOnWrongStartEmoji(t *testing.T) {
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

	ok, err := reader.VerifyMagicTrailer()
	if ok {
		t.Fatal("expected false for wrong start emoji")
	}
	if !errors.Is(err, ErrInvalidEmojiMagic) {
		t.Fatalf("expected ErrInvalidEmojiMagic, got %v", err)
	}
}

// TestVerifyMagicTrailerFailsOnWrongEndEmoji verifies that VerifyMagicTrailer
// returns ErrInvalidEmojiMagic when the end emoji bytes are wrong.
func TestVerifyMagicTrailerFailsOnWrongEndEmoji(t *testing.T) {
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

	ok, err := reader.VerifyMagicTrailer()
	if ok {
		t.Fatal("expected false for wrong end emoji")
	}
	if !errors.Is(err, ErrInvalidEmojiMagic) {
		t.Fatalf("expected ErrInvalidEmojiMagic, got %v", err)
	}
}

// TestVerifyAllChecksumsFailsOnCorruptedSlotData verifies that VerifyAllChecksums
// returns an error wrapping ErrChecksumMismatch when a slot's stored bytes have
// been corrupted (checksum mismatch).
func TestVerifyAllChecksumsFailsOnCorruptedSlotData(t *testing.T) {
	t.Parallel()

	// Build a single-slot bundle where the checksum is deliberately wrong.
	raw := []byte("payload-data-for-checksum-test")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "bad-cksum-slot",
		Target: "{workenv}/file.txt",
	}, 0o644, true /* corruptChecksum */)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	err = reader.VerifyAllChecksums()
	if err == nil {
		t.Fatal("expected error for corrupted slot checksum, got nil")
	}
	if !errors.Is(err, ErrChecksumMismatch) {
		t.Fatalf("expected ErrChecksumMismatch in error chain, got %v", err)
	}
}

// TestVerifyIntegritySealFailsWithWrongKey verifies that VerifyIntegritySeal
// returns ErrSignatureInvalid when the signature was made with a different key
// than the one stored in the index.
func TestVerifyIntegritySealFailsWithWrongKey(t *testing.T) {
	t.Parallel()

	metaJSON := []byte(`{"package":{"name":"signed","version":"1.0.0"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)

	// Sign with one key pair but store a different public key.
	_, signerPriv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey (signer): %v", err)
	}
	differentPub, _, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey (different): %v", err)
	}

	sig := ed25519.Sign(signerPriv, metaJSON)

	bundlePath := buildSignedBundleForTest(t, gzMeta, differentPub, sig)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	ok, err := reader.VerifyIntegritySeal()
	if ok {
		t.Fatal("expected false for wrong public key")
	}
	if !errors.Is(err, ErrSignatureInvalid) {
		t.Fatalf("expected ErrSignatureInvalid, got %v", err)
	}
}

// TestVerifyIntegritySealFailsWithNoSeal verifies that VerifyIntegritySeal returns
// ErrNoIntegritySeal when the signature field is all zeros (absent).
func TestVerifyIntegritySealFailsWithNoSeal(t *testing.T) {
	t.Parallel()

	metaJSON := []byte(`{"package":{"name":"unsigned","version":"1.0.0"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)

	pub, _, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey: %v", err)
	}

	// Pass an all-zero signature (absent seal).
	zeroSig := make([]byte, 64)
	bundlePath := buildSignedBundleForTest(t, gzMeta, pub, zeroSig)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	ok, err := reader.VerifyIntegritySeal()
	if ok {
		t.Fatal("expected false for absent seal")
	}
	if !errors.Is(err, ErrNoIntegritySeal) {
		t.Fatalf("expected ErrNoIntegritySeal, got %v", err)
	}
}

// buildSignedBundleForTest writes a minimal PSPF file with a given gzip-metadata
// block, public key, and signature embedded in the index. Used to test
// VerifyIntegritySeal with wrong keys or absent sigs.
func buildSignedBundleForTest(t *testing.T, gzMeta []byte, pub ed25519.PublicKey, sig []byte) string {
	t.Helper()

	f, err := createTempBinFile(t)
	if err != nil {
		t.Fatalf("createTempBinFile: %v", err)
	}
	defer func() { _ = f.Close() }()

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
	metaHash := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], metaHash[:])
	copy(idx.PublicKey[:], pub)
	copy(idx.IntegritySignature[:], sig)

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	return f.Name()
}

// TestVerifyAttestationSbomDigestAbsentWithNoSlots verifies that VerifyAttestationSbomDigest
// returns nil when there are no slots and no digest stored (backwards-compatible path).
func TestVerifyAttestationSbomDigestAbsentWithNoSlots(t *testing.T) {
	t.Parallel()

	// buildPolicyHashBundle creates a bundle with 0 slots and no digest.
	bundlePath := buildPolicyHashBundle(t, nil, "")

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	if err := reader.VerifyAttestationSbomDigest(); err != nil {
		t.Fatalf("VerifyAttestationSbomDigest() error = %v, want nil", err)
	}
}

// TestVerifyAttestationPolicyHashAbsentPolicyAbsent verifies that
// VerifyAttestationPolicyHash returns nil when both hash and policy are absent.
func TestVerifyAttestationPolicyHashAbsentPolicyAbsent(t *testing.T) {
	t.Parallel()

	bundlePath := buildPolicyHashBundle(t, nil, "")

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	if err := reader.VerifyAttestationPolicyHash(); err != nil {
		t.Fatalf("VerifyAttestationPolicyHash() error = %v, want nil", err)
	}
}

// TestVerifyAllChecksumsPassesForEmptyBundle verifies VerifyAllChecksums returns
// nil for a bundle with no slots.
func TestVerifyAllChecksumsPassesForEmptyBundle(t *testing.T) {
	t.Parallel()

	bundlePath := buildValidMinimalBundle(t)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	if err := reader.VerifyAllChecksums(); err != nil {
		t.Fatalf("VerifyAllChecksums() error = %v, want nil", err)
	}
}

// TestVerifyAllChecksumsPassesForValidSlot verifies VerifyAllChecksums passes for
// a bundle with a valid slot.
func TestVerifyAllChecksumsPassesForValidSlot(t *testing.T) {
	t.Parallel()

	raw := []byte("hello checksums")
	bundle := buildSingleSlotBundleForTests(t, raw, raw, nil, SlotMetadata{
		ID:     "valid-slot",
		Target: "{workenv}/ok.txt",
	}, 0o644, false)

	reader, err := NewReader(bundle)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	if err := reader.VerifyAllChecksums(); err != nil {
		t.Fatalf("VerifyAllChecksums() error = %v, want nil", err)
	}
}

// buildCorruptChecksumAttestationBundle creates an attestation bundle where the
// attestation slot's checksum in the descriptor is flipped — so VerifyAttestationSbomDigest
// will fail at the per-slot checksum check.
func buildCorruptChecksumAttestationBundle(t *testing.T, slotContents []byte, digestHex string) string {
	t.Helper()

	f, err := createTempBinFile(t)
	if err != nil {
		t.Fatalf("createTempBinFile: %v", err)
	}
	defer func() { _ = f.Close() }()

	var offset uint64

	slotOffset := offset
	slotSize := uint64(len(slotContents))
	if _, err := f.Write(slotContents); err != nil {
		t.Fatalf("write slot data: %v", err)
	}
	offset += slotSize

	slotHash := sha256.Sum256(slotContents)
	checksum := binary.LittleEndian.Uint64(slotHash[:8])
	// Flip a bit in the checksum to simulate corruption.
	checksum ^= 0xFF

	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName("attestation"),
		Offset:       slotOffset,
		Size:         slotSize,
		OriginalSize: slotSize,
		Operations:   0,
		Checksum:     checksum,
		Purpose:      PurposeData,
		Lifecycle:    LifecycleAttestation,
	}

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
	if digestHex != "" {
		copy(idx.AttestationSbomDigest[:], []byte(digestHex))
	}

	trailer := make([]byte, MagicTrailerSize)
	copy(trailer[0:4], PackageEmojiBytes)
	copy(trailer[4:4+IndexSize], idx.Pack())
	copy(trailer[4+IndexSize:], MagicWandEmojiBytes)
	if _, err := f.Write(trailer); err != nil {
		t.Fatalf("write trailer: %v", err)
	}

	return f.Name()
}

// TestVerifyAttestationSbomDigestFailsOnCorruptedSlotChecksum verifies that
// VerifyAttestationSbomDigest returns an error when the slot checksum is corrupted.
func TestVerifyAttestationSbomDigestFailsOnCorruptedSlotChecksum(t *testing.T) {
	t.Parallel()

	slotContent := []byte("attestation bytes")
	// Compute the correct digest so the digest field is non-zero.
	h := sha256.Sum256(slotContent)
	digestHex := hex.EncodeToString(h[:])

	bundlePath := buildCorruptChecksumAttestationBundle(t, slotContent, digestHex)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	if err := reader.VerifyAttestationSbomDigest(); err == nil {
		t.Fatal("expected error for corrupted slot checksum, got nil")
	}
}

// createTempBinFile creates a temp file for test bundle writing.
func createTempBinFile(t *testing.T) (*os.File, error) {
	t.Helper()
	return os.CreateTemp(t.TempDir(), "pspf-verify-*.bin")
}
