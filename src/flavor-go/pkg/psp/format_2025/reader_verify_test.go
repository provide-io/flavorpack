// SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package format_2025

import (
	"bytes"
	"compress/gzip"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"testing"
)

func TestReaderVerifyMagicTrailer(t *testing.T) {
	t.Parallel()

	bundlePath := buildPolicyHashBundle(t, nil, "")
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	ok, err := reader.VerifyMagicTrailer()
	if err != nil || !ok {
		t.Fatalf("VerifyMagicTrailer() = %v, %v", ok, err)
	}
}

func TestReaderVerifyAllChecksumsAndMetadataArchive(t *testing.T) {
	t.Parallel()

	slotContent := []byte("sbom content")
	digest := sha256.Sum256(slotContent)
	bundlePath := buildAttestationBundle(t, slotContent, hex.EncodeToString(digest[:]))
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	if err := reader.VerifyAllChecksums(); err != nil {
		t.Fatalf("VerifyAllChecksums() error = %v", err)
	}

	archive, err := reader.ReadMetadataArchive()
	if err != nil {
		t.Fatalf("ReadMetadataArchive() error = %v", err)
	}
	gr, err := gzip.NewReader(bytes.NewReader(archive))
	if err != nil {
		t.Fatalf("gzip.NewReader() error = %v", err)
	}
	defer func() { _ = gr.Close() }()
	data, err := io.ReadAll(gr)
	if err != nil {
		t.Fatalf("ReadAll() error = %v", err)
	}
	if !json.Valid(data) {
		t.Fatalf("expected valid metadata json, got %q", string(data))
	}
}

func TestReaderVerifyIntegritySeal(t *testing.T) {
	t.Parallel()

	f, err := os.CreateTemp(t.TempDir(), "pspf-signed-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp(): %v", err)
	}
	defer func() { _ = f.Close() }()

	metaJSON := []byte(`{"package":{"name":"signed","version":"1.0.0"},"slots":[]}`)
	gzMeta := gzipData(t, metaJSON)

	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatalf("GenerateKey(): %v", err)
	}
	sig := ed25519.Sign(priv, metaJSON)

	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write metadata: %v", err)
	}

	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		SlotTableOffset: uint64(len(gzMeta)),
		SlotTableSize:   0,
		SlotCount:       0,
		MetadataOffset:  0,
		MetadataSize:    uint64(len(gzMeta)),
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

	reader, err := NewReader(f.Name())
	if err != nil {
		t.Fatalf("NewReader(): %v", err)
	}
	defer func() { _ = reader.Close() }()

	ok, err := reader.VerifyIntegritySeal()
	if err != nil || !ok {
		t.Fatalf("VerifyIntegritySeal() = %v, %v", ok, err)
	}
}

// TestNewReaderWithLoggerNilLoggerFallback exercises the nil-logger branch.
func TestNewReaderWithLoggerNilLoggerFallback(t *testing.T) {
	// Pass nil logger — NewReaderWithLogger must substitute a null logger, not panic.
	r, err := NewReaderWithLogger("/dev/null", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if r == nil {
		t.Fatal("expected non-nil reader")
	}
}

// TestReadSlotReturnsErrInvalidSlotIndex covers the out-of-range slot index guard.
func TestReadSlotReturnsErrInvalidSlotIndex(t *testing.T) {
	t.Parallel()

	// Build a bundle with 0 slots; reading slot 0 must return ErrInvalidSlotIndex.
	bundlePath := buildPolicyHashBundle(t, nil, "")
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	_, err = reader.ReadSlot(0)
	if !errors.Is(err, ErrInvalidSlotIndex) {
		t.Fatalf("expected ErrInvalidSlotIndex, got %v", err)
	}
}

// TestReadSlotNilLoggerFallback constructs a Reader with nil logger to cover the
// slog.Default() fallback path in ReadSlot.
func TestReadSlotNilLoggerFallback(t *testing.T) {
	t.Parallel()

	slotContent := []byte("sbom content")
	digest := sha256.Sum256(slotContent)
	bundlePath := buildAttestationBundle(t, slotContent, hex.EncodeToString(digest[:]))

	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Pre-populate the index cache so ReadIndex returns without touching r.logger,
	// then set logger to nil to trigger the slog.Default() fallback inside ReadSlot.
	if _, err := reader.ReadIndex(); err != nil {
		t.Fatalf("ReadIndex: %v", err)
	}
	reader.logger = nil

	// Reading the slot now exercises the nil-logger branch in ReadSlot.
	_, err = reader.ReadSlot(0)
	// We only care that the nil-logger path was exercised without panicking.
	_ = err
}
