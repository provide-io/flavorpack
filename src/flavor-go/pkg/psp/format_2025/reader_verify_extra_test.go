//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"os"
	"testing"
)

// TestVerifyIntegritySealValidSignature covers the happy path (return true, nil).
func TestVerifyIntegritySealValidSignature(t *testing.T) {
	t.Parallel()

	// Generate an Ed25519 key pair.
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey: %v", err)
	}

	// Build gzip-compressed JSON metadata.
	metaJSON := []byte(`{"package":{"name":"signed","version":"1.0.0"},"slots":[]}`)
	var buf bytes.Buffer
	gz := gzip.NewWriter(&buf)
	if _, err := gz.Write(metaJSON); err != nil {
		t.Fatalf("gzip write: %v", err)
	}
	if err := gz.Close(); err != nil {
		t.Fatalf("gzip close: %v", err)
	}
	gzMeta := buf.Bytes()

	// Sign the raw JSON (not the gzip wrapper) — that's what VerifyIntegritySeal does.
	sig := ed25519.Sign(priv, metaJSON)

	f, err := os.CreateTemp(t.TempDir(), "pspf-signed-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
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
	copy(idx.IntegritySignature[:], sig)
	copy(idx.PublicKey[:], pub)

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

	ok, sealErr := reader.VerifyIntegritySeal()
	if !ok {
		t.Fatalf("expected VerifyIntegritySeal to return true for valid signature, got false (err=%v)", sealErr)
	}
	if sealErr != nil {
		t.Fatalf("expected nil error for valid signature, got: %v", sealErr)
	}
}

// TestVerifyIntegritySealNoSignature covers the allZeros → ErrNoIntegritySeal branch.
func TestVerifyIntegritySealNoSignature(t *testing.T) {
	t.Parallel()

	// Build a bundle with valid gzip metadata but leave IntegritySignature all zeros.
	gzMeta := gzipData(t, []byte(`{"package":{"name":"test"},"slots":[]}`))
	f, err := os.CreateTemp(t.TempDir(), "pspf-nosig-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
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
	// IntegritySignature is all zeros (default) — this exercises the allZeros → ErrNoIntegritySeal path.

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

	ok, err := reader.VerifyIntegritySeal()
	if ok {
		t.Fatal("expected false when integrity signature is all zeros")
	}
	if err == nil {
		t.Fatal("expected ErrNoIntegritySeal when signature is all zeros, got nil")
	}
}

// TestVerifyIntegritySealInvalidSignature covers the ed25519.Verify failure path:
// signature bytes are non-zero but don't actually verify against the key/data.
func TestVerifyIntegritySealInvalidSignature(t *testing.T) {
	t.Parallel()

	gzMeta := gzipData(t, []byte(`{"package":{"name":"test"},"slots":[]}`))
	f, err := os.CreateTemp(t.TempDir(), "pspf-badsig-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
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

	// Set a non-zero but invalid signature (64 bytes of 0x01).
	for i := range idx.IntegritySignature {
		idx.IntegritySignature[i] = 0x01
	}
	// Generate a random public key so verification fails (signature doesn't match).
	pub, _, err2 := ed25519.GenerateKey(nil)
	if err2 != nil {
		t.Fatalf("GenerateKey: %v", err2)
	}
	copy(idx.PublicKey[:], pub)

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

	ok, err := reader.VerifyIntegritySeal()
	if ok {
		t.Fatal("expected false when signature verification fails")
	}
	if err == nil {
		t.Fatal("expected ErrSignatureInvalid, got nil")
	}
}

// TestVerifyAttestationSbomDigestDigestPresentSlotAbsent covers the error path where
// the stored digest is non-zero but there is no attestation slot in the bundle.
func TestVerifyAttestationSbomDigestDigestPresentSlotAbsent(t *testing.T) {
	t.Parallel()

	// Build a valid minimal bundle (no attestation slot), then inject a non-zero digest.
	bundlePath := buildValidMinimalBundle(t)

	// Read the bundle, grab the index, inject a non-zero AttestationSbomDigest, and rewrite.
	// Instead, use buildAttestationBundle with content but a fake non-matching digest
	// for a bundle that has no attestation slot: we build with buildValidMinimalBundle and
	// manually create a wrapper that injects a non-zero digest.
	//
	// Simpler: build a fresh file with a non-zero digest but SlotCount=0 (no slots).
	gzMeta := gzipData(t, []byte(`{"package":{"name":"x"},"slots":[]}`))
	f, err := os.CreateTemp(t.TempDir(), "pspf-noatt-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()
	_ = bundlePath // use buildValidMinimalBundle just to reference it

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
	}

	metaHash := sha256.Sum256(gzMeta)
	fakeDigest := hex.EncodeToString(metaHash[:]) // non-zero digest value

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
		SlotTableOffset: uint64(len(gzMeta)),
		SlotCount:       0,
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
		t.Fatal("expected error when digest present but no attestation slot, got nil")
	}
}

// TestVerifyAttestationSbomDigestChecksumMismatch covers the slot checksum mismatch path
// in VerifyAttestationSbomDigest where the per-slot checksum doesn't match the data.
func TestVerifyAttestationSbomDigestChecksumMismatch(t *testing.T) {
	t.Parallel()

	slotContent := []byte("attestation data for checksum mismatch test")

	// Use buildAttestationBundle but tamper with the slot checksum after writing.
	// We'll build it the raw way to have fine-grained control.
	h := sha256.Sum256(slotContent)
	correctDigest := hex.EncodeToString(h[:])

	// Build as in buildAttestationBundle but write a wrong checksum in the descriptor.
	f, err := os.CreateTemp(t.TempDir(), "pspf-csmismatch-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	var offset uint64

	slotOffset := offset
	slotSize := uint64(len(slotContent))
	if _, err := f.Write(slotContent); err != nil {
		t.Fatalf("write slot data: %v", err)
	}
	offset += slotSize

	slotHash := sha256.Sum256(slotContent)
	// Flip all bits of the checksum bytes to get a wrong value.
	for i := range slotHash {
		slotHash[i] = ^slotHash[i]
	}

	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName("attestation"),
		Offset:       slotOffset,
		Size:         slotSize,
		OriginalSize: slotSize,
		Operations:   0,
		// Use the wrong checksum to trigger the slot integrity failure path.
		Checksum:  uint64(slotHash[0]) | uint64(slotHash[1])<<8 | uint64(slotHash[2])<<16 | uint64(slotHash[3])<<24,
		Purpose:   PurposeData,
		Lifecycle: LifecycleAttestation,
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
	copy(idx.AttestationSbomDigest[:], []byte(correctDigest))

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
		t.Fatal("expected error for attestation slot checksum mismatch, got nil")
	}
}

// TestVerifyIntegritySealReadIndexFails covers the ReadIndex error path (line 60-62)
// in VerifyIntegritySeal by using a non-existent file.
func TestVerifyIntegritySealReadIndexFails(t *testing.T) {
	t.Parallel()

	reader, err := NewReader("/nonexistent/bundle-integrity.pspf")
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	ok, err := reader.VerifyIntegritySeal()
	if ok {
		t.Fatal("expected false when ReadIndex fails in VerifyIntegritySeal, got true")
	}
	if err == nil {
		t.Fatal("expected error when bundle does not exist, got nil")
	}
}

// TestVerifyAttestationSbomDigestSeekSlotDescriptorFails covers the file Seek error
// path (line 161-163) in the slot scanning loop, by closing the file after ReadIndex.
func TestVerifyAttestationSbomDigestSeekSlotDescriptorFails(t *testing.T) {
	t.Parallel()

	slotContent := []byte("attestation bytes for seek failure test")
	h := sha256.Sum256(slotContent)
	correctDigest := hex.EncodeToString(h[:])
	bundlePath := buildAttestationBundle(t, slotContent, correctDigest)

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Prime the index cache so the initial ReadIndex succeeds.
	if _, err := reader.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}

	// Close the underlying file so the loop's first Seek fails.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("close file: %v", err)
	}

	err = reader.VerifyAttestationSbomDigest()
	if err == nil {
		t.Fatal("expected error when file is closed during VerifyAttestationSbomDigest, got nil")
	}
}

// TestVerifyAttestationSbomDigestReadAttestationDataFails covers the Read error path
// (line 197-199) when reading the attestation slot's raw bytes. We build a bundle
// where the attestation slot descriptor says the slot data is at offset beyond the file
// end, so the Seek succeeds but Read returns io.EOF.
func TestVerifyAttestationSbomDigestReadAttestationDataFails(t *testing.T) {
	t.Parallel()

	slotContent := []byte("attestation data for read-fail test")

	// Compute digest from slotContent as if it were at the claimed offset.
	slotHash := sha256.Sum256(slotContent)
	correctDigest := hex.EncodeToString(slotHash[:])

	// Build a custom bundle: write slot data at offset 0, then build a descriptor
	// that points BEYOND the file end with a matching checksum.
	f, err := os.CreateTemp(t.TempDir(), "pspf-readfail-att-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	// Write actual slot content at offset 0.
	if _, err := f.Write(slotContent); err != nil {
		t.Fatalf("write slot: %v", err)
	}
	actualOffset := uint64(0)
	_ = actualOffset

	// Slot table starts after the slot content.
	slotTableOffset := uint64(len(slotContent))

	// Build descriptor pointing to a valid location for checksum purposes
	// but use an offset beyond the file to trigger read failure.
	// Actually: we need the loop to succeed (seek+read slot descriptor OK),
	// then fail reading the actual slot bytes.
	// Strategy: put the slot descriptor at slotTableOffset with a large .Offset
	// value (beyond EOF), keeping .Checksum as if it were the correct data.
	beyondEOF := uint64(1 << 40) // 1 TiB — beyond file

	slotHashChecksum := binary.LittleEndian.Uint64(slotHash[:8])
	desc := SlotDescriptor{
		ID:           1,
		NameHash:     HashName("attestation"),
		Offset:       beyondEOF,
		Size:         uint64(len(slotContent)),
		OriginalSize: uint64(len(slotContent)),
		Operations:   0,
		Checksum:     slotHashChecksum,
		Purpose:      PurposeData,
		Lifecycle:    LifecycleAttestation,
	}
	if _, err := f.Write(desc.Pack()); err != nil {
		t.Fatalf("write descriptor: %v", err)
	}
	afterDescOffset := slotTableOffset + SlotDescriptorSize

	metaJSON := []byte(`{"package":{"name":"test","version":"0.0.1"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)
	metaOffset := afterDescOffset
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}
	totalSize := metaOffset + uint64(len(gzMeta))

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     totalSize + uint64(MagicTrailerSize),
		SlotTableOffset: slotTableOffset,
		SlotTableSize:   SlotDescriptorSize,
		SlotCount:       1,
		MetadataOffset:  metaOffset,
		MetadataSize:    uint64(len(gzMeta)),
	}
	mh := sha256.Sum256(gzMeta)
	copy(idx.MetadataChecksum[:], mh[:])
	copy(idx.AttestationSbomDigest[:], []byte(correctDigest))

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
		t.Fatal("expected error when attestation slot data is beyond file end, got nil")
	}
}
