//
// SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

package format_2025

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"testing"
)

// TestVerifyMagicTrailerFileStatFailure covers the file.Stat() error path in
// VerifyMagicTrailer by pre-opening the file and then closing it.
func TestVerifyMagicTrailerFileStatFailure(t *testing.T) {
	t.Parallel()

	bundlePath := buildValidMinimalBundle(t)
	reader, err := NewReader(bundlePath)
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	// Pre-open and immediately close the underlying file handle.
	if err := reader.Open(); err != nil {
		t.Fatalf("Open: %v", err)
	}
	if err := reader.file.Close(); err != nil {
		t.Fatalf("close underlying file: %v", err)
	}

	ok, err := reader.VerifyMagicTrailer()
	if ok {
		t.Fatal("expected false for closed file, got true")
	}
	if err == nil {
		t.Fatal("expected error for closed file, got nil")
	}
}

// TestVerifyAllChecksumsWhenReadIndexFails covers the ReadIndex error propagation
// in VerifyAllChecksums — passing a bundle path that doesn't exist.
func TestVerifyAllChecksumsWhenReadIndexFails(t *testing.T) {
	t.Parallel()

	reader, err := NewReader("/nonexistent/bundle.pspf")
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	err = reader.VerifyAllChecksums()
	if err == nil {
		t.Fatal("expected error when ReadIndex fails (missing file), got nil")
	}
}

// TestVerifyIntegritySealSeekFailure covers the Seek error in VerifyIntegritySeal.
// We prime the index cache and then close the file so the seek fails.
func TestVerifyIntegritySealSeekFailure(t *testing.T) {
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

	// Close the underlying file — Seek will fail.
	if err := reader.file.Close(); err != nil {
		t.Fatalf("close underlying file: %v", err)
	}

	ok, err := reader.VerifyIntegritySeal()
	if ok {
		t.Fatal("expected false when Seek fails, got true")
	}
	if err == nil {
		t.Fatal("expected error when Seek fails, got nil")
	}
}

// TestVerifyIntegritySealReadFailure covers the Read error path in VerifyIntegritySeal.
// We build a bundle with an inflated MetadataSize to trigger EOF on read.
func TestVerifyIntegritySealReadFailure(t *testing.T) {
	t.Parallel()

	f, err := os.CreateTemp(t.TempDir(), "pspf-seal-readfail-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	gzMeta := gzipData(t, []byte(`{"package":{"name":"x"},"slots":[]}`))
	if _, err := f.Write(gzMeta); err != nil {
		t.Fatalf("write: %v", err)
	}

	// Point MetadataOffset beyond end of file so Read gets EOF.
	beyondEOF := uint64(len(gzMeta)) + uint64(MagicTrailerSize) + 100
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(gzMeta) + MagicTrailerSize),
		MetadataOffset:  beyondEOF,
		MetadataSize:    100,
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

	ok, err := reader.VerifyIntegritySeal()
	if ok {
		t.Fatal("expected false when Read fails, got true")
	}
	if err == nil {
		t.Fatal("expected error when metadata offset is beyond file, got nil")
	}
}

// TestVerifyIntegritySealGzipFailure covers the gzip.NewReader error path in
// VerifyIntegritySeal. We build a bundle with non-gzip metadata.
func TestVerifyIntegritySealGzipFailure(t *testing.T) {
	t.Parallel()

	// Use plain JSON (not gzip-compressed) — gzip.NewReader will fail.
	plainJSON := []byte(`{"package":{"name":"test"},"slots":[]}`)
	f, err := os.CreateTemp(t.TempDir(), "pspf-seal-gzipfail-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(plainJSON); err != nil {
		t.Fatalf("write: %v", err)
	}

	metaHash := sha256.Sum256(plainJSON)
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(plainJSON) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(plainJSON)),
		SlotTableOffset: uint64(len(plainJSON)),
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

	ok, err := reader.VerifyIntegritySeal()
	if ok {
		t.Fatal("expected false for non-gzip metadata in VerifyIntegritySeal, got true")
	}
	if err == nil {
		t.Fatal("expected error for non-gzip metadata in VerifyIntegritySeal, got nil")
	}
}

// TestVerifyAttestationPolicyHashReadMetadataFails covers the ReadMetadata error
// propagation path in VerifyAttestationPolicyHash. We build a bundle that has a
// non-zero policy hash stored but corrupt (non-gzip) metadata so ReadMetadata fails.
func TestVerifyAttestationPolicyHashReadMetadataFails(t *testing.T) {
	t.Parallel()

	// Build a bundle with non-gzip metadata and a non-zero policy hash.
	plainJSON := []byte(`{"package":{"name":"x"},"slots":[]}`)
	f, err := os.CreateTemp(t.TempDir(), "pspf-policyhash-readfail-*.bin")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.Write(plainJSON); err != nil {
		t.Fatalf("write: %v", err)
	}

	metaHash := sha256.Sum256(plainJSON)
	fakeHash := hex.EncodeToString(metaHash[:]) // non-zero policy hash
	idx := &PSPFIndex{
		FormatVersion:   PSPFVersion,
		PackageSize:     uint64(len(plainJSON) + MagicTrailerSize),
		MetadataOffset:  0,
		MetadataSize:    uint64(len(plainJSON)),
		SlotTableOffset: uint64(len(plainJSON)),
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
		t.Fatal("expected error when ReadMetadata fails in VerifyAttestationPolicyHash, got nil")
	}
}

// TestVerifyAttestationPolicyHashInvalidPolicyJSON covers the json.Unmarshal failure
// path in VerifyAttestationPolicyHash when PolicyRaw contains invalid JSON.
func TestVerifyAttestationPolicyHashInvalidPolicyJSON(t *testing.T) {
	t.Parallel()

	// Build a bundle where metadata.policy is valid JSON (so it gets stored),
	// but we need PolicyRaw to be invalid JSON. Since PolicyRaw is set from the
	// raw JSON field, we can't easily inject invalid JSON post-parse.
	// Instead, we test the mismatch path (which covers the json.Marshal success path).
	//
	// For invalid json.Unmarshal: we need PolicyRaw to be non-JSON bytes.
	// PackagePolicy.PolicyRaw is a json.RawMessage — it gets set from the "policy" key.
	// If we build metadata with policy as a string instead of object, Unmarshal into
	// map[string]interface{} will fail.
	//
	// The metadata JSON will have "policy": "not-an-object" — this will be
	// unmarshaled into PolicyRaw as a JSON string (valid JSON), but then
	// json.Unmarshal(PolicyRaw, &policyMap) where policyMap is map[string]interface{}
	// will fail because the JSON string is not a JSON object.

	type metaWithStringPolicy struct {
		Package struct {
			Name    string `json:"name"`
			Version string `json:"version"`
		} `json:"package"`
		Slots  []interface{} `json:"slots"`
		Policy interface{}   `json:"policy,omitempty"`
	}

	meta := metaWithStringPolicy{
		Slots: []interface{}{},
	}
	meta.Package.Name = "test"
	meta.Package.Version = "0.0.1"
	meta.Policy = "not-a-policy-object" // string, not object

	metaJSON, err := json.Marshal(meta)
	if err != nil {
		t.Fatalf("Marshal: %v", err)
	}
	gzMeta := gzipData(t, metaJSON)

	// Compute a non-zero policy hash so VerifyAttestationPolicyHash proceeds.
	fakeSum := sha256.Sum256([]byte("fake"))
	fakeHash := hex.EncodeToString(fakeSum[:])

	f, err := os.CreateTemp(t.TempDir(), "pspf-invalidpolicy-*.bin")
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
	// Should either fail at policy unmarshal or at hash mismatch — either is an error.
	if err == nil {
		t.Fatal("expected error for invalid/non-object policy JSON, got nil")
	}
}

// TestVerifyAttestationSbomDigestReadIndexFails covers the ReadIndex error
// propagation path in VerifyAttestationSbomDigest.
func TestVerifyAttestationSbomDigestReadIndexFails(t *testing.T) {
	t.Parallel()

	reader, err := NewReader("/nonexistent/bundle.pspf")
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	err = reader.VerifyAttestationSbomDigest()
	if err == nil {
		t.Fatal("expected error when ReadIndex fails (missing file), got nil")
	}
}

// TestVerifyAttestationPolicyHashReadIndexFails covers the ReadIndex error path
// in VerifyAttestationPolicyHash.
func TestVerifyAttestationPolicyHashReadIndexFails(t *testing.T) {
	t.Parallel()

	reader, err := NewReader("/nonexistent/bundle.pspf")
	if err != nil {
		t.Fatalf("NewReader: %v", err)
	}
	defer func() { _ = reader.Close() }()

	err = reader.VerifyAttestationPolicyHash()
	if !errors.Is(err, os.ErrNotExist) && err == nil {
		t.Fatal("expected error when bundle does not exist, got nil")
	}
}
